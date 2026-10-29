import datetime
import html
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from categories.models import Category

from .forms import TransactionFilterForm, TransactionForm
from .models import Transaction

User = get_user_model()

LIST_URL = reverse('transactions:list')
CREATE_URL = reverse('transactions:create')


def create_user(email):
    return User.objects.create_user(email=email, password='senha-forte-123')


def create_account(user, name='Conta Corrente'):
    return Account.objects.create(
        user=user, name=name, account_type=Account.CHECKING,
        initial_balance=Decimal('100.00'),
    )


def create_category(user, name, category_type):
    return Category.objects.create(
        user=user, name=name, category_type=category_type
    )


def create_transaction(user, account, category, **kwargs):
    data = {
        'transaction_type': category.category_type,
        'description': 'Transação',
        'amount': Decimal('10.00'),
        'date': datetime.date(2026, 1, 15),
    }
    data.update(kwargs)
    return Transaction.objects.create(
        user=user, account=account, category=category, **data
    )


def message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class TransactionTestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('ana@example.com')
        cls.account = create_account(cls.user)
        cls.salary = create_category(cls.user, 'Salário', Category.INCOME)
        cls.food = create_category(cls.user, 'Alimentação', Category.EXPENSE)

        cls.other_user = create_user('bruno@example.com')
        cls.other_account = create_account(cls.other_user, 'Conta Alheia')
        cls.other_income = create_category(
            cls.other_user, 'Renda Alheia', Category.INCOME
        )
        cls.other_expense = create_category(
            cls.other_user, 'Gasto Alheio', Category.EXPENSE
        )

    def setUp(self):
        self.client.force_login(self.user)

    def valid_data(self, **overrides):
        data = {
            'transaction_type': Category.EXPENSE,
            'description': 'Mercado',
            'amount': '50.25',
            'date': '2026-02-10',
            'account': self.account.pk,
            'category': self.food.pk,
        }
        data.update(overrides)
        return data


class TransactionListViewTests(TransactionTestDataMixin, TestCase):
    def test_redirects_anonymous_user_to_login(self):
        self.client.logout()
        response = self.client.get(LIST_URL)
        self.assertRedirects(
            response, f"{reverse('users:login')}?next={LIST_URL}"
        )

    def test_lists_only_transactions_of_logged_user(self):
        own = create_transaction(
            self.user, self.account, self.food, description='Minha compra'
        )
        create_transaction(
            self.other_user, self.other_account, self.other_expense,
            description='Compra alheia',
        )
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['transactions']), [own])
        self.assertContains(response, 'Minha compra')
        self.assertNotContains(response, 'Compra alheia')

    def test_orders_by_date_desc_then_created_at_desc(self):
        old = create_transaction(
            self.user, self.account, self.food,
            date=datetime.date(2026, 1, 1),
        )
        first_same_day = create_transaction(
            self.user, self.account, self.food,
            date=datetime.date(2026, 3, 1),
        )
        second_same_day = create_transaction(
            self.user, self.account, self.food,
            date=datetime.date(2026, 3, 1),
        )
        now = timezone.now()
        Transaction.objects.filter(pk=first_same_day.pk).update(
            created_at=now - datetime.timedelta(hours=1)
        )
        Transaction.objects.filter(pk=second_same_day.pk).update(
            created_at=now
        )
        response = self.client.get(LIST_URL)
        self.assertEqual(
            list(response.context['transactions']),
            [second_same_day, first_same_day, old],
        )


class TransactionCreateViewTests(TransactionTestDataMixin, TestCase):
    def test_get_sets_initial_date_to_today(self):
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIsInstance(form, TransactionForm)
        self.assertEqual(
            form.fields['date'].initial, timezone.localdate()
        )

    def test_create_assigns_user_and_redirects_with_message(self):
        response = self.client.post(CREATE_URL, self.valid_data())
        self.assertRedirects(response, LIST_URL)
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.account, self.account)
        self.assertEqual(transaction.category, self.food)
        self.assertEqual(transaction.amount, Decimal('50.25'))
        self.assertEqual(transaction.date, datetime.date(2026, 2, 10))
        self.assertIn(
            'Transação registrada com sucesso.', message_texts(response)
        )

    def test_create_ignores_user_field_in_post(self):
        data = self.valid_data(user=self.other_user.pk)
        self.client.post(CREATE_URL, data)
        self.assertEqual(Transaction.objects.get().user, self.user)

    def test_redirects_anonymous_user_to_login(self):
        self.client.logout()
        response = self.client.post(CREATE_URL, self.valid_data())
        self.assertRedirects(
            response, f"{reverse('users:login')}?next={CREATE_URL}"
        )
        self.assertFalse(Transaction.objects.exists())


class TransactionUpdateViewTests(TransactionTestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.transaction = create_transaction(
            self.user, self.account, self.food, description='Original'
        )
        self.other_transaction = create_transaction(
            self.other_user, self.other_account, self.other_expense,
            description='Alheia',
        )

    def test_get_does_not_override_saved_date(self):
        response = self.client.get(
            reverse('transactions:update', args=[self.transaction.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].initial['date'],
            datetime.date(2026, 1, 15),
        )

    def test_update_saves_changes_and_shows_message(self):
        response = self.client.post(
            reverse('transactions:update', args=[self.transaction.pk]),
            self.valid_data(description='Editada', amount='99.90'),
        )
        self.assertRedirects(response, LIST_URL)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.description, 'Editada')
        self.assertEqual(self.transaction.amount, Decimal('99.90'))
        self.assertEqual(self.transaction.user, self.user)
        self.assertIn(
            'Transação atualizada com sucesso.', message_texts(response)
        )

    def test_get_other_user_transaction_returns_404(self):
        response = self.client.get(
            reverse('transactions:update', args=[self.other_transaction.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_post_other_user_transaction_returns_404(self):
        response = self.client.post(
            reverse('transactions:update', args=[self.other_transaction.pk]),
            self.valid_data(description='Invadida'),
        )
        self.assertEqual(response.status_code, 404)
        self.other_transaction.refresh_from_db()
        self.assertEqual(self.other_transaction.description, 'Alheia')


class TransactionDeleteViewTests(TransactionTestDataMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.transaction = create_transaction(
            self.user, self.account, self.food
        )
        self.other_transaction = create_transaction(
            self.other_user, self.other_account, self.other_expense
        )

    def test_get_shows_confirmation(self):
        response = self.client.get(
            reverse('transactions:delete', args=[self.transaction.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_removes_transaction_and_shows_message(self):
        response = self.client.post(
            reverse('transactions:delete', args=[self.transaction.pk])
        )
        self.assertRedirects(response, LIST_URL)
        self.assertFalse(
            Transaction.objects.filter(pk=self.transaction.pk).exists()
        )
        self.assertIn(
            'Transação excluída com sucesso.', message_texts(response)
        )

    def test_get_other_user_transaction_returns_404(self):
        response = self.client.get(
            reverse('transactions:delete', args=[self.other_transaction.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_post_other_user_transaction_returns_404(self):
        response = self.client.post(
            reverse('transactions:delete', args=[self.other_transaction.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Transaction.objects.filter(pk=self.other_transaction.pk).exists()
        )


class TransactionAmountValidationTests(TransactionTestDataMixin, TestCase):
    def test_zero_amount_is_rejected(self):
        form = TransactionForm(
            data=self.valid_data(amount='0'), user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['amount'], ['O valor deve ser maior que zero.']
        )

    def test_negative_amount_is_rejected(self):
        form = TransactionForm(
            data=self.valid_data(amount='-10.00'), user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['amount'], ['O valor deve ser maior que zero.']
        )

    def test_minimum_amount_is_accepted(self):
        form = TransactionForm(
            data=self.valid_data(amount='0.01'), user=self.user
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_view_shows_error_and_does_not_create_with_zero_amount(self):
        response = self.client.post(CREATE_URL, self.valid_data(amount='0'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'O valor deve ser maior que zero.')
        self.assertFalse(Transaction.objects.exists())


class TransactionCategoryTypeValidationTests(
    TransactionTestDataMixin, TestCase
):
    def test_expense_with_income_category_is_rejected(self):
        form = TransactionForm(
            data=self.valid_data(
                transaction_type=Category.EXPENSE, category=self.salary.pk
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['category'],
            ['A categoria deve ser do mesmo tipo da transação.'],
        )

    def test_income_with_expense_category_is_rejected(self):
        form = TransactionForm(
            data=self.valid_data(
                transaction_type=Category.INCOME, category=self.food.pk
            ),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['category'],
            ['A categoria deve ser do mesmo tipo da transação.'],
        )

    def test_matching_category_type_is_accepted(self):
        form = TransactionForm(
            data=self.valid_data(
                transaction_type=Category.INCOME, category=self.salary.pk
            ),
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_view_shows_error_for_mismatched_category(self):
        response = self.client.post(
            CREATE_URL,
            self.valid_data(
                transaction_type=Category.INCOME, category=self.food.pk
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'A categoria deve ser do mesmo tipo da transação.'
        )
        self.assertFalse(Transaction.objects.exists())


class TransactionFormIsolationTests(TransactionTestDataMixin, TestCase):
    def test_form_selects_only_contain_user_data(self):
        form = TransactionForm(user=self.user)
        self.assertQuerySetEqual(
            form.fields['account'].queryset, [self.account], ordered=False
        )
        self.assertQuerySetEqual(
            form.fields['category'].queryset,
            [self.salary, self.food],
            ordered=False,
        )

    def test_categories_are_grouped_in_optgroups(self):
        form = TransactionForm(user=self.user)
        choices = form.fields['category'].choices
        self.assertEqual(choices[0], ('', 'Selecione'))
        self.assertEqual(
            choices[1:],
            [
                ('Entradas', [(self.salary.pk, 'Salário')]),
                ('Saídas', [(self.food.pk, 'Alimentação')]),
            ],
        )
        rendered = str(form['category'])
        self.assertIn('<optgroup label="Entradas">', rendered)
        self.assertIn('<optgroup label="Saídas">', rendered)
        self.assertNotIn('Gasto Alheio', rendered)

    def test_create_page_does_not_render_other_user_data(self):
        response = self.client.get(CREATE_URL)
        self.assertContains(response, 'Conta Corrente')
        self.assertNotContains(response, 'Conta Alheia')
        self.assertNotContains(response, 'Renda Alheia')
        self.assertNotContains(response, 'Gasto Alheio')

    def test_other_user_account_is_rejected(self):
        form = TransactionForm(
            data=self.valid_data(account=self.other_account.pk),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('account', form.errors)

    def test_other_user_category_is_rejected(self):
        form = TransactionForm(
            data=self.valid_data(category=self.other_expense.pk),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)

    def test_view_does_not_create_with_other_user_account_or_category(self):
        self.client.post(
            CREATE_URL, self.valid_data(account=self.other_account.pk)
        )
        self.client.post(
            CREATE_URL, self.valid_data(category=self.other_expense.pk)
        )
        self.assertFalse(Transaction.objects.exists())

    def test_filter_form_selects_only_contain_user_data(self):
        form = TransactionFilterForm(user=self.user)
        self.assertQuerySetEqual(
            form.fields['account'].queryset, [self.account], ordered=False
        )
        self.assertQuerySetEqual(
            form.fields['category'].queryset,
            [self.salary, self.food],
            ordered=False,
        )

    def test_list_page_filter_does_not_render_other_user_data(self):
        response = self.client.get(LIST_URL)
        self.assertNotContains(response, 'Conta Alheia')
        self.assertNotContains(response, 'Gasto Alheio')


class TransactionListFilterTests(TransactionTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.savings = create_account(cls.user, 'Poupança Nubank')
        cls.income_jan = create_transaction(
            cls.user, cls.account, cls.salary,
            date=datetime.date(2026, 1, 5),
        )
        cls.expense_jan = create_transaction(
            cls.user, cls.account, cls.food,
            date=datetime.date(2026, 1, 20),
        )
        cls.income_feb_savings = create_transaction(
            cls.user, cls.savings, cls.salary,
            date=datetime.date(2026, 2, 10),
        )
        cls.expense_mar_savings = create_transaction(
            cls.user, cls.savings, cls.food,
            date=datetime.date(2026, 3, 1),
        )
        cls.other_transaction = create_transaction(
            cls.other_user, cls.other_account, cls.other_expense,
            date=datetime.date(2026, 1, 20),
        )

    def filtered(self, **params):
        response = self.client.get(LIST_URL, params)
        self.assertEqual(response.status_code, 200)
        return set(response.context['transactions'])

    def test_filter_by_transaction_type(self):
        self.assertEqual(
            self.filtered(transaction_type=Category.INCOME),
            {self.income_jan, self.income_feb_savings},
        )
        self.assertEqual(
            self.filtered(transaction_type=Category.EXPENSE),
            {self.expense_jan, self.expense_mar_savings},
        )

    def test_filter_by_account(self):
        self.assertEqual(
            self.filtered(account=self.savings.pk),
            {self.income_feb_savings, self.expense_mar_savings},
        )

    def test_filter_by_category(self):
        self.assertEqual(
            self.filtered(category=self.food.pk),
            {self.expense_jan, self.expense_mar_savings},
        )

    def test_filter_by_start_date_is_inclusive(self):
        self.assertEqual(
            self.filtered(start_date='2026-02-10'),
            {self.income_feb_savings, self.expense_mar_savings},
        )

    def test_filter_by_end_date_is_inclusive(self):
        self.assertEqual(
            self.filtered(end_date='2026-01-20'),
            {self.income_jan, self.expense_jan},
        )

    def test_filter_by_date_range_is_inclusive(self):
        self.assertEqual(
            self.filtered(start_date='2026-01-20', end_date='2026-02-10'),
            {self.expense_jan, self.income_feb_savings},
        )

    def test_combined_filters(self):
        self.assertEqual(
            self.filtered(
                transaction_type=Category.EXPENSE,
                account=self.savings.pk,
                category=self.food.pk,
                start_date='2026-03-01',
                end_date='2026-03-01',
            ),
            {self.expense_mar_savings},
        )
        self.assertEqual(
            self.filtered(
                transaction_type=Category.INCOME, account=self.account.pk,
                end_date='2026-01-04',
            ),
            set(),
        )

    def test_filter_with_other_user_account_does_not_leak_data(self):
        result = self.filtered(account=self.other_account.pk)
        self.assertNotIn(self.other_transaction, result)
        self.assertTrue(all(t.user == self.user for t in result))

    def test_filter_with_other_user_category_does_not_leak_data(self):
        result = self.filtered(category=self.other_expense.pk)
        self.assertNotIn(self.other_transaction, result)
        self.assertTrue(all(t.user == self.user for t in result))


class TransactionPaginationTests(TransactionTestDataMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for day in range(1, 26):
            create_transaction(
                cls.user, cls.account, cls.food,
                description=f'Despesa {day}',
                date=datetime.date(2026, 1, day),
            )
        create_transaction(
            cls.user, cls.account, cls.salary,
            date=datetime.date(2026, 1, 1),
        )

    def test_first_page_has_20_items(self):
        response = self.client.get(LIST_URL, {'category': self.food.pk})
        self.assertEqual(len(response.context['transactions']), 20)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(response.context['paginator'].num_pages, 2)

    def test_second_page_has_5_items(self):
        response = self.client.get(
            LIST_URL, {'category': self.food.pk, 'page': 2}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 5)
        self.assertTrue(
            all(t.category == self.food
                for t in response.context['transactions'])
        )

    def test_pagination_links_preserve_filters(self):
        response = self.client.get(
            LIST_URL,
            {
                'transaction_type': Category.EXPENSE,
                'category': self.food.pk,
                'start_date': '2026-01-01',
            },
        )
        content = html.unescape(response.content.decode())
        expected = (
            f'?transaction_type=expense&category={self.food.pk}'
            '&start_date=2026-01-01&page=2'
        )
        self.assertIn(f'href="{expected}"', content)

    def test_previous_link_preserves_filters(self):
        response = self.client.get(
            LIST_URL, {'category': self.food.pk, 'page': 2}
        )
        content = html.unescape(response.content.decode())
        self.assertIn(f'href="?category={self.food.pk}&page=1"', content)
