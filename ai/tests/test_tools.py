import datetime
import json
from decimal import Decimal

from django.test import TestCase

from accounts.models import Account
from categories.models import Category

from ..tools import (
    FINANCIAL_TOOLS,
    clamp_period,
    get_accounts_overview,
    get_financial_summary,
    get_monthly_evolution,
    get_spending_by_category,
    get_top_expenses,
    money,
)
from .factories import (
    PERIOD_END,
    PERIOD_START,
    create_account,
    create_category,
    create_transaction,
    create_user,
    make_runtime,
)


def call(tool, user_id, **args):
    return tool.invoke({**args, 'runtime': make_runtime(user_id)})


class HelperTests(TestCase):
    def setUp(self):
        self.context = make_runtime(1).context

    def test_clamp_period_defaults_to_window(self):
        self.assertEqual(
            clamp_period(self.context), (PERIOD_START, PERIOD_END)
        )

    def test_clamp_period_limits_dates_to_window(self):
        self.assertEqual(
            clamp_period(self.context, '2020-01-01', '2030-12-31'),
            (PERIOD_START, PERIOD_END),
        )
        self.assertEqual(
            clamp_period(self.context, '2026-09-01', '2026-09-30'),
            (datetime.date(2026, 9, 1), datetime.date(2026, 9, 30)),
        )

    def test_clamp_period_invalid_or_inverted_dates_use_window(self):
        self.assertEqual(
            clamp_period(self.context, 'ontem', 'xx'),
            (PERIOD_START, PERIOD_END),
        )
        self.assertEqual(
            clamp_period(self.context, '2026-10-10', '2026-09-01'),
            (PERIOD_START, PERIOD_END),
        )

    def test_money_serializes_decimal_as_text(self):
        self.assertEqual(money(Decimal('1234.5')), '1234.50')
        self.assertEqual(money(None), '0.00')


class ToolSchemaTests(TestCase):
    def test_financial_tools_list(self):
        self.assertEqual(
            [tool.name for tool in FINANCIAL_TOOLS],
            [
                'get_financial_summary', 'get_spending_by_category',
                'get_top_expenses', 'get_monthly_evolution',
                'get_accounts_overview',
            ],
        )

    def test_schema_exposed_to_model_has_no_user_or_runtime(self):
        for tool in FINANCIAL_TOOLS:
            with self.subTest(tool=tool.name):
                schema = json.dumps(tool.tool_call_schema.model_json_schema())
                properties = tool.tool_call_schema.model_json_schema().get(
                    'properties', {}
                )
                self.assertNotIn('runtime', properties)
                self.assertNotIn('user_id', properties)
                self.assertNotIn('user_id', schema)
                self.assertNotIn('user', properties)

    def test_schema_inputs_match_specification(self):
        expected = {
            'get_financial_summary': {'start_date', 'end_date'},
            'get_spending_by_category': {
                'transaction_type', 'start_date', 'end_date',
            },
            'get_top_expenses': {'limit', 'start_date', 'end_date'},
            'get_monthly_evolution': set(),
            'get_accounts_overview': set(),
        }
        for tool in FINANCIAL_TOOLS:
            properties = tool.tool_call_schema.model_json_schema().get(
                'properties', {}
            )
            self.assertEqual(set(properties), expected[tool.name])


class ToolDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('ana@example.com')
        cls.other = create_user('bruno@example.com')

        cls.account = create_account(cls.user, initial_balance='1000.00')
        cls.savings = create_account(
            cls.user, name='Reserva', account_type=Account.SAVINGS,
            initial_balance='500.00',
        )
        cls.food = create_category(cls.user, 'Alimentação')
        cls.rent = create_category(cls.user, 'Moradia')
        cls.salary = create_category(
            cls.user, 'Salário', Category.INCOME
        )

        add = create_transaction
        add(cls.user, cls.account, cls.salary, '3000.00',
            datetime.date(2026, 8, 5))
        add(cls.user, cls.account, cls.rent, '1200.00',
            datetime.date(2026, 8, 10))
        add(cls.user, cls.account, cls.food, '300.00',
            datetime.date(2026, 9, 12))
        add(cls.user, cls.account, cls.salary, '3000.00',
            datetime.date(2026, 10, 5))
        add(cls.user, cls.account, cls.food, '500.00',
            datetime.date(2026, 10, 20))
        # Outside the window: ignored by every period-based tool.
        add(cls.user, cls.account, cls.food, '9999.00',
            datetime.date(2026, 7, 31))

        # Another user's data must never leak.
        other_account = create_account(cls.other, initial_balance='7777.00')
        other_food = create_category(cls.other, 'Alimentação')
        other_salary = create_category(
            cls.other, 'Salário', Category.INCOME
        )
        add(cls.other, other_account, other_food, '4444.00',
            datetime.date(2026, 9, 1))
        add(cls.other, other_account, other_salary, '8888.00',
            datetime.date(2026, 9, 1))


class FinancialSummaryToolTests(ToolDataMixin, TestCase):
    def test_aggregates_user_window(self):
        data = call(get_financial_summary, self.user.pk)
        self.assertEqual(data, {
            'start_date': '2026-08-01',
            'end_date': '2026-10-29',
            'total_income': '6000.00',
            'total_expense': '2000.00',
            'result': '4000.00',
            'transaction_count': 5,
            'savings_rate': '66.7',
        })

    def test_dates_limited_to_window(self):
        data = call(
            get_financial_summary, self.user.pk,
            start_date='2026-01-01', end_date='2026-08-31',
        )
        self.assertEqual(data['start_date'], '2026-08-01')
        self.assertEqual(data['total_expense'], '1200.00')

    def test_isolation_between_users(self):
        data = call(get_financial_summary, self.other.pk)
        self.assertEqual(data['total_income'], '8888.00')
        self.assertEqual(data['total_expense'], '4444.00')
        self.assertEqual(data['transaction_count'], 2)

    def test_savings_rate_none_without_income(self):
        data = call(
            get_financial_summary, self.user.pk,
            start_date='2026-09-01', end_date='2026-09-30',
        )
        self.assertIsNone(data['savings_rate'])


class SpendingByCategoryToolTests(ToolDataMixin, TestCase):
    def test_expenses_grouped_and_ordered(self):
        data = call(get_spending_by_category, self.user.pk)
        self.assertEqual(data, [
            {'category': 'Moradia', 'total': '1200.00',
             'share_percent': '60.0', 'count': 1},
            {'category': 'Alimentação', 'total': '800.00',
             'share_percent': '40.0', 'count': 2},
        ])

    def test_income_type(self):
        data = call(
            get_spending_by_category, self.user.pk,
            transaction_type='income',
        )
        self.assertEqual(data, [{
            'category': 'Salário', 'total': '6000.00',
            'share_percent': '100.0', 'count': 2,
        }])

    def test_invalid_type_falls_back_to_expense(self):
        data = call(
            get_spending_by_category, self.user.pk,
            transaction_type='DROP TABLE',
        )
        self.assertEqual(data[0]['category'], 'Moradia')

    def test_top_ten_limit(self):
        for index in range(12):
            category = create_category(self.user, f'Extra {index:02d}')
            create_transaction(
                self.user, self.account, category, f'{index + 1}.00',
                datetime.date(2026, 9, 2),
            )
        data = call(get_spending_by_category, self.user.pk)
        self.assertEqual(len(data), 10)

    def test_isolation_between_users(self):
        data = call(get_spending_by_category, self.other.pk)
        self.assertEqual(data, [{
            'category': 'Alimentação', 'total': '4444.00',
            'share_percent': '100.0', 'count': 1,
        }])


class TopExpensesToolTests(ToolDataMixin, TestCase):
    def test_returns_largest_expenses_without_description(self):
        data = call(get_top_expenses, self.user.pk, limit=2)
        self.assertEqual(data, [
            {'date': '2026-08-10', 'category': 'Moradia',
             'amount': '1200.00'},
            {'date': '2026-10-20', 'category': 'Alimentação',
             'amount': '500.00'},
        ])
        self.assertNotIn('Descrição sigilosa', json.dumps(data))

    def test_limit_is_clamped(self):
        self.assertEqual(len(call(get_top_expenses, self.user.pk, limit=0)), 1)
        data = call(get_top_expenses, self.user.pk, limit=50)
        self.assertEqual(len(data), 3)  # only 3 expenses in the window

    def test_window_and_isolation(self):
        data = call(get_top_expenses, self.user.pk)
        self.assertNotIn('9999.00', [item['amount'] for item in data])
        self.assertNotIn('4444.00', [item['amount'] for item in data])


class MonthlyEvolutionToolTests(ToolDataMixin, TestCase):
    def test_months_of_the_window(self):
        data = call(get_monthly_evolution, self.user.pk)
        self.assertEqual(data, [
            {'month': '2026-08', 'income': '3000.00', 'expense': '1200.00',
             'result': '1800.00', 'is_partial': False},
            {'month': '2026-09', 'income': '0.00', 'expense': '300.00',
             'result': '-300.00', 'is_partial': False},
            {'month': '2026-10', 'income': '3000.00', 'expense': '500.00',
             'result': '2500.00', 'is_partial': True},
        ])

    def test_isolation_between_users(self):
        data = call(get_monthly_evolution, self.other.pk)
        self.assertEqual(data[1]['expense'], '4444.00')
        self.assertEqual(data[0]['expense'], '0.00')


class AccountsOverviewToolTests(ToolDataMixin, TestCase):
    def test_groups_by_type_without_names(self):
        data = call(get_accounts_overview, self.user.pk)
        # 1000 + 6000 - 2000 - 9999 (all-time balance) = -5000; +500.
        self.assertEqual(data, {
            'total_balance': '-4499.00',
            'by_account_type': [
                {'account_type': 'Conta corrente', 'accounts': 1,
                 'balance': '-4999.00'},
                {'account_type': 'Poupança', 'accounts': 1,
                 'balance': '500.00'},
            ],
        })
        serialized = json.dumps(data)
        self.assertNotIn('Banco Secreto', serialized)
        self.assertNotIn('Reserva', serialized)

    def test_isolation_between_users(self):
        data = call(get_accounts_overview, self.other.pk)
        self.assertEqual(data['total_balance'], '12221.00')
        self.assertEqual(len(data['by_account_type']), 1)
