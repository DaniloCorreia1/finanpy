import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounts.models import Account
from transactions.models import Transaction

from .forms import CategoryForm
from .models import Category

User = get_user_model()

PASSWORD = 'senha-segura-123'
DUPLICATE_MESSAGE = 'Você já possui uma categoria com este nome e tipo.'


def create_category(user, name, category_type=Category.EXPENSE):
    return Category.objects.create(
        user=user, name=name, category_type=category_type
    )


def message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class CategoryCrudViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.other_user = User.objects.create_user(
            email='outro@example.com', password=PASSWORD
        )
        cls.salary = create_category(cls.user, 'Salário', Category.INCOME)
        cls.market = create_category(cls.user, 'Mercado', Category.EXPENSE)
        cls.rent = create_category(cls.user, 'Aluguel', Category.EXPENSE)
        cls.other_category = create_category(
            cls.other_user, 'Categoria Alheia', Category.EXPENSE
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        self.client.logout()
        url = reverse('categories:list')
        response = self.client.get(url)
        self.assertRedirects(
            response, f"{reverse('users:login')}?next={url}"
        )

    def test_list_shows_only_user_categories(self):
        response = self.client.get(reverse('categories:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories/category_list.html')
        self.assertCountEqual(
            response.context['categories'],
            [self.salary, self.market, self.rent],
        )
        self.assertContains(response, 'Salário')
        self.assertNotContains(response, 'Categoria Alheia')

    def test_list_splits_income_and_expense_categories(self):
        response = self.client.get(reverse('categories:list'))
        self.assertEqual(response.context['income_categories'], [self.salary])
        self.assertEqual(
            response.context['expense_categories'], [self.rent, self.market]
        )

    def test_create_get_renders_form(self):
        response = self.client.get(reverse('categories:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories/category_form.html')

    def test_create_assigns_user_and_redirects_with_message(self):
        response = self.client.post(reverse('categories:create'), {
            'name': 'Freelance',
            'category_type': Category.INCOME,
        })
        self.assertRedirects(response, reverse('categories:list'))
        category = Category.objects.get(name='Freelance')
        self.assertEqual(category.user, self.user)
        self.assertEqual(category.category_type, Category.INCOME)
        self.assertIn(
            'Categoria criada com sucesso.', message_texts(response)
        )

    def test_create_requires_name_and_type(self):
        count = Category.objects.count()
        response = self.client.post(reverse('categories:create'), {
            'name': '',
            'category_type': '',
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('name', form.errors)
        self.assertIn('category_type', form.errors)
        self.assertEqual(Category.objects.count(), count)

    def test_update_changes_category_and_shows_message(self):
        response = self.client.post(
            reverse('categories:update', args=[self.market.pk]),
            {'name': 'Supermercado', 'category_type': Category.EXPENSE},
        )
        self.assertRedirects(response, reverse('categories:list'))
        self.market.refresh_from_db()
        self.assertEqual(self.market.name, 'Supermercado')
        self.assertIn(
            'Categoria atualizada com sucesso.', message_texts(response)
        )

    def test_delete_get_renders_confirmation(self):
        response = self.client.get(
            reverse('categories:delete', args=[self.rent.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'categories/category_confirm_delete.html'
        )

    def test_delete_removes_category_and_shows_message(self):
        response = self.client.post(
            reverse('categories:delete', args=[self.rent.pk])
        )
        self.assertRedirects(response, reverse('categories:list'))
        self.assertFalse(Category.objects.filter(pk=self.rent.pk).exists())
        self.assertIn(
            'Categoria excluída com sucesso.', message_texts(response)
        )

    def test_update_get_other_user_category_returns_404(self):
        response = self.client.get(
            reverse('categories:update', args=[self.other_category.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_update_post_other_user_category_returns_404(self):
        response = self.client.post(
            reverse('categories:update', args=[self.other_category.pk]),
            {'name': 'Invadida', 'category_type': Category.INCOME},
        )
        self.assertEqual(response.status_code, 404)
        self.other_category.refresh_from_db()
        self.assertEqual(self.other_category.name, 'Categoria Alheia')
        self.assertEqual(self.other_category.category_type, Category.EXPENSE)

    def test_delete_get_other_user_category_returns_404(self):
        response = self.client.get(
            reverse('categories:delete', args=[self.other_category.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_post_other_user_category_returns_404(self):
        response = self.client.post(
            reverse('categories:delete', args=[self.other_category.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Category.objects.filter(pk=self.other_category.pk).exists()
        )


class CategoryDuplicateValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.other_user = User.objects.create_user(
            email='outro@example.com', password=PASSWORD
        )
        cls.market = create_category(cls.user, 'Mercado', Category.EXPENSE)
        cls.rent = create_category(cls.user, 'Aluguel', Category.EXPENSE)

    def setUp(self):
        self.client.force_login(self.user)

    def build_form(self, data, instance=None, user=None):
        return CategoryForm(
            data=data, instance=instance, user=user or self.user
        )

    def test_form_rejects_same_name_and_type(self):
        form = self.build_form(
            {'name': 'Mercado', 'category_type': Category.EXPENSE}
        )
        self.assertFalse(form.is_valid())
        self.assertIn(DUPLICATE_MESSAGE, form.non_field_errors())

    def test_form_rejects_same_name_with_different_case(self):
        form = self.build_form(
            {'name': 'MERCADO', 'category_type': Category.EXPENSE}
        )
        self.assertFalse(form.is_valid())
        self.assertIn(DUPLICATE_MESSAGE, form.non_field_errors())

    def test_form_allows_same_name_with_other_type(self):
        form = self.build_form(
            {'name': 'Mercado', 'category_type': Category.INCOME}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_allows_same_name_and_type_for_other_user(self):
        form = self.build_form(
            {'name': 'Mercado', 'category_type': Category.EXPENSE},
            user=self.other_user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_allows_editing_without_changing_name(self):
        form = self.build_form(
            {'name': 'Mercado', 'category_type': Category.EXPENSE},
            instance=self.market,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_allows_changing_only_case_of_own_name(self):
        form = self.build_form(
            {'name': 'mercado', 'category_type': Category.EXPENSE},
            instance=self.market,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_renaming_to_existing_name(self):
        form = self.build_form(
            {'name': 'aluguel', 'category_type': Category.EXPENSE},
            instance=self.market,
        )
        self.assertFalse(form.is_valid())
        self.assertIn(DUPLICATE_MESSAGE, form.non_field_errors())

    def test_create_view_shows_duplicate_error(self):
        count = Category.objects.count()
        response = self.client.post(reverse('categories:create'), {
            'name': 'mercado',
            'category_type': Category.EXPENSE,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], None, DUPLICATE_MESSAGE
        )
        self.assertContains(response, DUPLICATE_MESSAGE)
        self.assertEqual(Category.objects.count(), count)

    def test_create_view_allows_same_name_with_other_type(self):
        response = self.client.post(reverse('categories:create'), {
            'name': 'Mercado',
            'category_type': Category.INCOME,
        })
        self.assertRedirects(response, reverse('categories:list'))
        self.assertEqual(
            Category.objects.filter(user=self.user, name='Mercado').count(), 2
        )

    def test_create_view_allows_same_name_and_type_for_other_user(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('categories:create'), {
            'name': 'Mercado',
            'category_type': Category.EXPENSE,
        })
        self.assertRedirects(response, reverse('categories:list'))
        self.assertTrue(
            Category.objects.filter(
                user=self.other_user, name='Mercado'
            ).exists()
        )

    def test_update_view_allows_saving_without_changing_name(self):
        response = self.client.post(
            reverse('categories:update', args=[self.market.pk]),
            {'name': 'Mercado', 'category_type': Category.EXPENSE},
        )
        self.assertRedirects(response, reverse('categories:list'))

    def test_update_view_rejects_renaming_to_existing_name(self):
        response = self.client.post(
            reverse('categories:update', args=[self.market.pk]),
            {'name': 'Aluguel', 'category_type': Category.EXPENSE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], None, DUPLICATE_MESSAGE
        )
        self.market.refresh_from_db()
        self.assertEqual(self.market.name, 'Mercado')


class CategoryProtectedDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='dono@example.com', password=PASSWORD
        )
        cls.account = Account.objects.create(
            user=cls.user, name='Carteira', account_type=Account.WALLET
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.category = create_category(
            self.user, 'Mercado', Category.EXPENSE
        )
        Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.category,
            transaction_type=Transaction.EXPENSE,
            description='Compras',
            amount=Decimal('42.00'),
            date=datetime.date(2026, 1, 10),
        )

    def test_delete_category_with_transactions_is_blocked(self):
        response = self.client.post(
            reverse('categories:delete', args=[self.category.pk])
        )
        self.assertRedirects(response, reverse('categories:list'))
        self.assertTrue(
            Category.objects.filter(pk=self.category.pk).exists()
        )
        self.assertEqual(self.category.transactions.count(), 1)
        messages = message_texts(response)
        self.assertIn(
            'Esta categoria possui transações e não pode ser excluída.',
            messages,
        )
        self.assertNotIn('Categoria excluída com sucesso.', messages)

    def test_blocked_delete_message_is_shown_on_list(self):
        response = self.client.post(
            reverse('categories:delete', args=[self.category.pk]),
            follow=True,
        )
        self.assertContains(
            response,
            'Esta categoria possui transações e não pode ser excluída.',
        )
