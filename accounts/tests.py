import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from transactions.models import Transaction

from .models import Account

User = get_user_model()

PASSWORD = 'senha-segura-123'


def create_account(user, name='Conta', initial_balance='0.00',
                   account_type=Account.CHECKING, bank=''):
    return Account.objects.create(
        user=user,
        name=name,
        bank=bank,
        account_type=account_type,
        initial_balance=Decimal(initial_balance),
    )


def create_category(user, name, category_type):
    return Category.objects.create(
        user=user, name=name, category_type=category_type
    )


def create_transaction(account, category, amount, description='Lançamento'):
    return Transaction.objects.create(
        user=account.user,
        account=account,
        category=category,
        transaction_type=category.category_type,
        description=description,
        amount=Decimal(amount),
        date=datetime.date(2026, 1, 15),
    )


def message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class AccountCrudViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.other_user = User.objects.create_user(
            email='outro@example.com', password=PASSWORD
        )
        cls.account = create_account(
            cls.user, name='Nubank', initial_balance='1234.56'
        )
        cls.other_account = create_account(
            cls.other_user, name='Conta Alheia', initial_balance='50.00'
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        self.client.logout()
        url = reverse('accounts:list')
        response = self.client.get(url)
        self.assertRedirects(
            response, f"{reverse('users:login')}?next={url}"
        )

    def test_list_shows_only_user_accounts(self):
        response = self.client.get(reverse('accounts:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_list.html')
        self.assertEqual(list(response.context['accounts']), [self.account])
        self.assertContains(response, 'Nubank')
        self.assertNotContains(response, 'Conta Alheia')

    def test_list_is_ordered_by_name(self):
        create_account(self.user, name='Carteira')
        create_account(self.user, name='Banco do Brasil')
        response = self.client.get(reverse('accounts:list'))
        names = [account.name for account in response.context['accounts']]
        self.assertEqual(names, ['Banco do Brasil', 'Carteira', 'Nubank'])

    def test_list_shows_formatted_balance(self):
        response = self.client.get(reverse('accounts:list'))
        self.assertContains(response, 'R$ 1.234,56')

    def test_list_shows_empty_state_without_accounts(self):
        self.client.force_login(
            User.objects.create_user(
                email='novo@example.com', password=PASSWORD
            )
        )
        response = self.client.get(reverse('accounts:list'))
        self.assertEqual(len(response.context['accounts']), 0)
        self.assertContains(
            response, 'Você ainda não cadastrou nenhuma conta.'
        )

    def test_create_get_renders_form(self):
        response = self.client.get(reverse('accounts:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_form.html')

    def test_create_assigns_user_and_redirects_with_message(self):
        response = self.client.post(reverse('accounts:create'), {
            'name': 'Poupança Caixa',
            'bank': 'Caixa',
            'account_type': Account.SAVINGS,
            'initial_balance': '300.50',
        })
        self.assertRedirects(response, reverse('accounts:list'))
        account = Account.objects.get(name='Poupança Caixa')
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.bank, 'Caixa')
        self.assertEqual(account.account_type, Account.SAVINGS)
        self.assertEqual(account.initial_balance, Decimal('300.50'))
        self.assertIn('Conta criada com sucesso.', message_texts(response))

    def test_create_ignores_user_from_post_data(self):
        self.client.post(reverse('accounts:create'), {
            'name': 'Tentativa',
            'account_type': Account.WALLET,
            'initial_balance': '0',
            'user': self.other_user.pk,
        })
        self.assertEqual(Account.objects.get(name='Tentativa').user, self.user)

    def test_create_requires_name_and_type(self):
        count = Account.objects.count()
        response = self.client.post(reverse('accounts:create'), {
            'name': '',
            'bank': '',
            'account_type': '',
            'initial_balance': '0',
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('name', form.errors)
        self.assertIn('account_type', form.errors)
        self.assertEqual(Account.objects.count(), count)

    def test_create_rejects_invalid_type(self):
        response = self.client.post(reverse('accounts:create'), {
            'name': 'Conta',
            'account_type': 'invalido',
            'initial_balance': '0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('account_type', response.context['form'].errors)

    def test_create_bank_is_optional(self):
        response = self.client.post(reverse('accounts:create'), {
            'name': 'Sem banco',
            'bank': '',
            'account_type': Account.WALLET,
            'initial_balance': '0',
        })
        self.assertRedirects(response, reverse('accounts:list'))
        self.assertTrue(Account.objects.filter(name='Sem banco').exists())

    def test_update_get_renders_form_with_instance(self):
        response = self.client.get(
            reverse('accounts:update', args=[self.account.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].instance, self.account)

    def test_update_changes_account_and_shows_message(self):
        response = self.client.post(
            reverse('accounts:update', args=[self.account.pk]),
            {
                'name': 'Nubank Renomeado',
                'bank': 'Nubank',
                'account_type': Account.INVESTMENT,
                'initial_balance': '10.00',
            },
        )
        self.assertRedirects(response, reverse('accounts:list'))
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Nubank Renomeado')
        self.assertEqual(self.account.account_type, Account.INVESTMENT)
        self.assertEqual(self.account.initial_balance, Decimal('10.00'))
        self.assertEqual(self.account.user, self.user)
        self.assertIn(
            'Conta atualizada com sucesso.', message_texts(response)
        )

    def test_update_requires_name(self):
        response = self.client.post(
            reverse('accounts:update', args=[self.account.pk]),
            {
                'name': '',
                'account_type': Account.CHECKING,
                'initial_balance': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.context['form'].errors)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Nubank')

    def test_delete_get_renders_confirmation(self):
        response = self.client.get(
            reverse('accounts:delete', args=[self.account.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'accounts/account_confirm_delete.html'
        )

    def test_delete_removes_account_and_shows_message(self):
        response = self.client.post(
            reverse('accounts:delete', args=[self.account.pk])
        )
        self.assertRedirects(response, reverse('accounts:list'))
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())
        self.assertIn('Conta excluída com sucesso.', message_texts(response))


class AccountIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.other_user = User.objects.create_user(
            email='outro@example.com', password=PASSWORD
        )
        cls.other_account = create_account(
            cls.other_user, name='Conta Alheia', initial_balance='50.00'
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_update_get_other_user_account_returns_404(self):
        response = self.client.get(
            reverse('accounts:update', args=[self.other_account.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_update_post_other_user_account_returns_404(self):
        response = self.client.post(
            reverse('accounts:update', args=[self.other_account.pk]),
            {
                'name': 'Invadida',
                'account_type': Account.WALLET,
                'initial_balance': '0',
            },
        )
        self.assertEqual(response.status_code, 404)
        self.other_account.refresh_from_db()
        self.assertEqual(self.other_account.name, 'Conta Alheia')
        self.assertEqual(self.other_account.initial_balance, Decimal('50.00'))
        self.assertEqual(self.other_account.user, self.other_user)

    def test_delete_get_other_user_account_returns_404(self):
        response = self.client.get(
            reverse('accounts:delete', args=[self.other_account.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_post_other_user_account_returns_404(self):
        response = self.client.post(
            reverse('accounts:delete', args=[self.other_account.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Account.objects.filter(pk=self.other_account.pk).exists()
        )

    def test_nonexistent_account_returns_404(self):
        response = self.client.get(reverse('accounts:update', args=[99999]))
        self.assertEqual(response.status_code, 404)


class AccountBalanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.income_category = create_category(
            cls.user, 'Salário', Category.INCOME
        )
        cls.expense_category = create_category(
            cls.user, 'Mercado', Category.EXPENSE
        )

    def assert_balance(self, account, expected):
        expected = Decimal(expected)
        self.assertEqual(account.current_balance(), expected)
        annotated = Account.objects.with_balance().get(pk=account.pk)
        self.assertEqual(annotated.balance, expected)

    def test_account_without_transactions_equals_initial_balance(self):
        account = create_account(self.user, initial_balance='150.75')
        self.assert_balance(account, '150.75')

    def test_zero_initial_balance_without_transactions(self):
        account = create_account(self.user, initial_balance='0.00')
        self.assert_balance(account, '0.00')

    def test_balance_adds_incomes_and_subtracts_expenses(self):
        account = create_account(self.user, initial_balance='100.00')
        create_transaction(account, self.income_category, '1000.00')
        create_transaction(account, self.income_category, '250.50')
        create_transaction(account, self.expense_category, '300.25')
        create_transaction(account, self.expense_category, '49.75')
        self.assert_balance(account, '1000.50')

    def test_balance_with_only_expenses(self):
        account = create_account(self.user, initial_balance='500.00')
        create_transaction(account, self.expense_category, '120.00')
        self.assert_balance(account, '380.00')

    def test_balance_can_be_negative(self):
        account = create_account(self.user, initial_balance='50.00')
        create_transaction(account, self.expense_category, '80.30')
        self.assert_balance(account, '-30.30')

    def test_negative_initial_balance(self):
        account = create_account(self.user, initial_balance='-20.00')
        create_transaction(account, self.income_category, '5.00')
        self.assert_balance(account, '-15.00')

    def test_transactions_of_other_accounts_do_not_interfere(self):
        account = create_account(self.user, name='A', initial_balance='10')
        other = create_account(self.user, name='B', initial_balance='20')
        create_transaction(account, self.income_category, '5.00')
        create_transaction(other, self.income_category, '1000.00')
        create_transaction(other, self.expense_category, '400.00')
        self.assert_balance(account, '15.00')
        self.assert_balance(other, '620.00')

    def test_with_balance_annotates_every_account(self):
        first = create_account(self.user, name='A', initial_balance='10')
        second = create_account(self.user, name='B', initial_balance='0')
        third = create_account(self.user, name='C', initial_balance='7.50')
        create_transaction(first, self.income_category, '90.00')
        create_transaction(first, self.expense_category, '30.00')
        create_transaction(second, self.expense_category, '12.34')
        balances = {
            account.pk: account.balance
            for account in Account.objects.with_balance()
        }
        self.assertEqual(balances[first.pk], Decimal('70.00'))
        self.assertEqual(balances[second.pk], Decimal('-12.34'))
        self.assertEqual(balances[third.pk], Decimal('7.50'))
        for account in (first, second, third):
            self.assertEqual(balances[account.pk], account.current_balance())

    def test_with_balance_does_not_duplicate_rows(self):
        account = create_account(self.user)
        create_transaction(account, self.income_category, '1.00')
        create_transaction(account, self.income_category, '2.00')
        create_transaction(account, self.expense_category, '3.00')
        self.assertEqual(
            Account.objects.with_balance().filter(pk=account.pk).count(), 1
        )

    def test_balance_updates_after_editing_transaction(self):
        account = create_account(self.user, initial_balance='100.00')
        transaction = create_transaction(
            account, self.expense_category, '40.00'
        )
        self.assert_balance(account, '60.00')
        transaction.amount = Decimal('10.00')
        transaction.save()
        self.assert_balance(account, '90.00')
        transaction.transaction_type = Category.INCOME
        transaction.category = self.income_category
        transaction.save()
        self.assert_balance(account, '110.00')

    def test_balance_updates_after_moving_transaction_to_other_account(self):
        account = create_account(self.user, name='A', initial_balance='0')
        other = create_account(self.user, name='B', initial_balance='0')
        transaction = create_transaction(
            account, self.income_category, '25.00'
        )
        transaction.account = other
        transaction.save()
        self.assert_balance(account, '0.00')
        self.assert_balance(other, '25.00')

    def test_balance_updates_after_deleting_transaction(self):
        account = create_account(self.user, initial_balance='100.00')
        create_transaction(account, self.income_category, '50.00')
        expense = create_transaction(account, self.expense_category, '70.00')
        self.assert_balance(account, '80.00')
        expense.delete()
        self.assert_balance(account, '150.00')

    def test_list_view_displays_computed_balance(self):
        account = create_account(
            self.user, name='Corrente', initial_balance='1000.00'
        )
        create_transaction(account, self.income_category, '500.00')
        create_transaction(account, self.expense_category, '265.44')
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:list'))
        self.assertEqual(
            response.context['accounts'][0].balance, Decimal('1234.56')
        )
        self.assertContains(response, 'R$ 1.234,56')

    def test_list_view_displays_negative_balance(self):
        account = create_account(self.user, initial_balance='0.00')
        create_transaction(account, self.expense_category, '1500.00')
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:list'))
        self.assertContains(response, 'R$ -1.500,00')
        self.assertContains(response, 'amount-expense')


class AccountProtectedDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.category = create_category(cls.user, 'Salário', Category.INCOME)

    def setUp(self):
        self.client.force_login(self.user)
        self.account = create_account(self.user, name='Com transações')
        create_transaction(self.account, self.category, '10.00')

    def test_delete_account_with_transactions_is_blocked(self):
        response = self.client.post(
            reverse('accounts:delete', args=[self.account.pk])
        )
        self.assertRedirects(response, reverse('accounts:list'))
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())
        self.assertEqual(self.account.transactions.count(), 1)
        messages = message_texts(response)
        self.assertIn(
            'Esta conta possui transações e não pode ser excluída.', messages
        )
        self.assertNotIn('Conta excluída com sucesso.', messages)

    def test_blocked_delete_message_is_shown_on_list(self):
        response = self.client.post(
            reverse('accounts:delete', args=[self.account.pk]), follow=True
        )
        self.assertContains(
            response, 'Esta conta possui transações e não pode ser excluída.'
        )
        self.assertContains(response, 'Com transações')

    def test_account_can_be_deleted_after_its_transactions_are_removed(self):
        self.account.transactions.all().delete()
        response = self.client.post(
            reverse('accounts:delete', args=[self.account.pk])
        )
        self.assertRedirects(response, reverse('accounts:list'))
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())
