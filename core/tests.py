import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from categories.models import Category
from transactions.models import Transaction

User = get_user_model()

PASSWORD = 'SenhaForte!2024'


def create_account(user, name='Conta', initial_balance='0.00'):
    return Account.objects.create(
        user=user,
        name=name,
        account_type=Account.CHECKING,
        initial_balance=Decimal(initial_balance),
    )


def create_category(user, name, category_type):
    return Category.objects.create(
        user=user, name=name, category_type=category_type
    )


def create_transaction(user, account, category, amount, date,
                       description='Lançamento'):
    return Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        transaction_type=category.category_type,
        description=description,
        amount=Decimal(amount),
        date=date,
    )


def first_day_of_previous_month(today):
    last_day_previous = today.replace(day=1) - datetime.timedelta(days=1)
    return last_day_previous.replace(day=1)


class LandingPageViewTests(TestCase):
    url = reverse('landing')

    def test_landing_is_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/landing.html')

    def test_anonymous_user_sees_login_and_signup_links(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Entrar')
        self.assertContains(response, 'Cadastre-se')
        self.assertContains(response, f'href="{reverse("users:login")}"')
        self.assertContains(response, f'href="{reverse("users:signup")}"')
        self.assertNotContains(response, 'Ir para o dashboard')

    def test_authenticated_user_sees_dashboard_link(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ir para o dashboard')
        self.assertContains(response, f'href="{reverse("dashboard")}"')
        self.assertNotContains(response, 'Cadastre-se</a>')


class PrivateRoutesRequireLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        cls.account = create_account(cls.user)
        cls.category = create_category(cls.user, 'Salário', Category.INCOME)
        cls.transaction = create_transaction(
            cls.user,
            cls.account,
            cls.category,
            '100.00',
            timezone.localdate(),
        )

    def get_private_urls(self):
        return [
            reverse('dashboard'),
            reverse('profiles:detail'),
            reverse('profiles:update'),
            reverse('accounts:list'),
            reverse('accounts:create'),
            reverse('accounts:update', args=[self.account.pk]),
            reverse('accounts:delete', args=[self.account.pk]),
            reverse('categories:list'),
            reverse('categories:create'),
            reverse('categories:update', args=[self.category.pk]),
            reverse('categories:delete', args=[self.category.pk]),
            reverse('transactions:list'),
            reverse('transactions:create'),
            reverse('transactions:update', args=[self.transaction.pk]),
            reverse('transactions:delete', args=[self.transaction.pk]),
        ]

    def test_anonymous_get_redirects_to_login_with_next(self):
        login_url = reverse('users:login')
        for url in self.get_private_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f'{login_url}?next={url}')

    def test_anonymous_post_redirects_to_login_and_changes_nothing(self):
        login_url = reverse('users:login')
        for url in self.get_private_urls():
            with self.subTest(url=url):
                response = self.client.post(url, {})
                self.assertRedirects(response, f'{login_url}?next={url}')
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())
        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )
        self.assertTrue(
            Transaction.objects.filter(pk=self.transaction.pk).exists()
        )


class DashboardViewTests(TestCase):
    url = reverse('dashboard')

    @classmethod
    def setUpTestData(cls):
        cls.today = timezone.localdate()
        cls.previous_month = first_day_of_previous_month(cls.today)

        cls.user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        cls.checking = create_account(cls.user, 'Corrente', '1000.00')
        cls.wallet = create_account(cls.user, 'Carteira', '50.50')
        cls.salary = create_category(cls.user, 'Salário', Category.INCOME)
        cls.food = create_category(cls.user, 'Alimentação', Category.EXPENSE)

        # Mês corrente.
        create_transaction(
            cls.user, cls.checking, cls.salary, '3000.00', cls.today,
            'Salário do mês',
        )
        create_transaction(
            cls.user, cls.checking, cls.food, '250.25', cls.today,
            'Mercado',
        )
        create_transaction(
            cls.user, cls.wallet, cls.food, '20.00', cls.today, 'Lanche',
        )
        # Mês anterior: entra no saldo, mas não nos totais do mês.
        create_transaction(
            cls.user, cls.checking, cls.salary, '500.00',
            cls.previous_month, 'Freela antigo',
        )
        create_transaction(
            cls.user, cls.wallet, cls.food, '10.00', cls.previous_month,
            'Café antigo',
        )

        cls.other = User.objects.create_user(
            email='bruno@example.com', password=PASSWORD
        )
        other_account = create_account(cls.other, 'Conta do Bruno', '9999')
        other_income = create_category(cls.other, 'Bônus', Category.INCOME)
        other_expense = create_category(
            cls.other, 'Viagem', Category.EXPENSE
        )
        create_transaction(
            cls.other, other_account, other_income, '7777.00', cls.today,
            'Bônus do Bruno',
        )
        create_transaction(
            cls.other, other_account, other_expense, '333.00', cls.today,
            'Viagem do Bruno',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_dashboard_renders_for_authenticated_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/dashboard.html')

    def test_total_balance_sums_all_account_balances(self):
        response = self.client.get(self.url)
        # Corrente: 1000 + 3000 + 500 - 250.25 = 4249.75
        # Carteira: 50.50 - 20 - 10 = 20.50
        self.assertEqual(response.context['total_balance'], Decimal('4270.25'))

    def test_month_income_only_counts_current_month(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['month_income'], Decimal('3000.00'))

    def test_month_expense_only_counts_current_month(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['month_expense'], Decimal('270.25'))

    def test_month_result_is_income_minus_expense(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['month_result'], Decimal('2729.75'))

    def test_accounts_in_context_belong_only_to_user(self):
        response = self.client.get(self.url)
        accounts = response.context['accounts']
        self.assertEqual(
            {account.pk for account in accounts},
            {self.checking.pk, self.wallet.pk},
        )
        balances = {account.name: account.balance for account in accounts}
        self.assertEqual(balances['Corrente'], Decimal('4249.75'))
        self.assertEqual(balances['Carteira'], Decimal('20.50'))

    def test_recent_transactions_belong_only_to_user(self):
        response = self.client.get(self.url)
        recent = response.context['recent_transactions']
        self.assertTrue(recent)
        for transaction in recent:
            self.assertEqual(transaction.user, self.user)
        self.assertNotContains(response, 'Bônus do Bruno')
        self.assertNotContains(response, 'Viagem do Bruno')

    def test_recent_transactions_are_limited_to_five_and_ordered(self):
        for day_offset in range(1, 5):
            create_transaction(
                self.user, self.checking, self.food, '1.00',
                self.previous_month - datetime.timedelta(days=day_offset),
                f'Antiga {day_offset}',
            )
        response = self.client.get(self.url)
        recent = response.context['recent_transactions']
        self.assertEqual(len(recent), 5)
        expected = list(
            Transaction.objects.filter(user=self.user)
            .order_by('-date', '-created_at')[:5]
        )
        self.assertEqual(list(recent), expected)
        dates = [transaction.date for transaction in recent]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertNotIn(
            'Antiga 1',
            [transaction.description for transaction in recent],
        )

    def test_recent_transactions_same_date_ordered_by_created_at_desc(self):
        # Fixa created_at: o relógio do sistema pode gerar empates.
        base = timezone.now()
        for offset, description in enumerate(
            ['Salário do mês', 'Mercado', 'Lanche']
        ):
            Transaction.objects.filter(
                user=self.user, description=description
            ).update(created_at=base + datetime.timedelta(seconds=offset))
        response = self.client.get(self.url)
        recent = response.context['recent_transactions']
        same_day = [t for t in recent if t.date == self.today]
        created = [transaction.created_at for transaction in same_day]
        self.assertEqual(created, sorted(created, reverse=True))
        self.assertEqual(same_day[0].description, 'Lanche')

    def test_user_without_data_gets_zero_values(self):
        empty_user = User.objects.create_user(
            email='vazio@example.com', password=PASSWORD
        )
        self.client.force_login(empty_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for key in (
            'total_balance', 'month_income', 'month_expense', 'month_result'
        ):
            with self.subTest(key=key):
                value = response.context[key]
                self.assertIsInstance(value, Decimal)
                self.assertEqual(value, Decimal('0'))
        self.assertEqual(list(response.context['accounts']), [])
        self.assertEqual(list(response.context['recent_transactions']), [])

    def test_user_with_accounts_but_no_transactions(self):
        user = User.objects.create_user(
            email='carla@example.com', password=PASSWORD
        )
        create_account(user, 'Poupança', '123.45')
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_balance'], Decimal('123.45'))
        self.assertEqual(response.context['month_income'], Decimal('0'))
        self.assertEqual(response.context['month_expense'], Decimal('0'))

    def test_other_user_sees_only_own_totals(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url)
        self.assertEqual(
            response.context['total_balance'], Decimal('17443.00')
        )
        self.assertEqual(response.context['month_income'], Decimal('7777.00'))
        self.assertEqual(response.context['month_expense'], Decimal('333.00'))
        self.assertEqual(
            response.context['month_result'], Decimal('7444.00')
        )
        descriptions = [
            transaction.description
            for transaction in response.context['recent_transactions']
        ]
        self.assertEqual(
            sorted(descriptions), ['Bônus do Bruno', 'Viagem do Bruno']
        )

    def test_dashboard_reflects_new_transaction(self):
        create_transaction(
            self.user, self.wallet, self.salary, '100.00', self.today,
            'Extra',
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context['month_income'], Decimal('3100.00'))
        self.assertEqual(response.context['total_balance'], Decimal('4370.25'))
        self.assertEqual(
            response.context['recent_transactions'][0].description, 'Extra'
        )
