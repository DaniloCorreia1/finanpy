import datetime

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()

PASSWORD = 'SenhaForte!2024'


def get_message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class ProfileSignalTests(TestCase):
    def test_profile_is_created_when_user_is_created(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertIsInstance(user.profile, Profile)
        self.assertEqual(user.profile.phone, '')
        self.assertIsNone(user.profile.birth_date)

    def test_profile_is_created_for_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com', password=PASSWORD
        )
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_profile_is_created_on_signup(self):
        self.client.post(
            reverse('users:signup'),
            {
                'first_name': 'Ana',
                'last_name': 'Souza',
                'email': 'ana@example.com',
                'password1': PASSWORD,
                'password2': PASSWORD,
            },
        )
        user = User.objects.get(email='ana@example.com')
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_saving_user_again_does_not_duplicate_profile(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        user.first_name = 'Ana'
        user.save()
        user.save()
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(Profile.objects.count(), 1)

    def test_profile_str(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.assertEqual(str(user.profile), 'Perfil de ana@example.com')


class ProfileDetailViewTests(TestCase):
    url = reverse('profiles:detail')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='ana@example.com',
            password=PASSWORD,
            first_name='Ana',
            last_name='Souza',
        )
        cls.user.profile.phone = '(11) 98765-4321'
        cls.user.profile.birth_date = datetime.date(1990, 5, 17)
        cls.user.profile.save()

    def setUp(self):
        self.client.force_login(self.user)

    def test_detail_renders_user_data(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile_detail.html')
        self.assertEqual(response.context['profile'], self.user.profile)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Souza')
        self.assertContains(response, 'ana@example.com')
        self.assertContains(response, '(11) 98765-4321')
        self.assertContains(response, '17/05/1990')

    def test_detail_shows_only_logged_user_profile(self):
        other = User.objects.create_user(
            email='bruno@example.com',
            password=PASSWORD,
            first_name='Bruno',
            last_name='Lima',
        )
        response = self.client.get(self.url)
        self.assertEqual(response.context['profile'].user, self.user)
        self.assertNotContains(response, other.email)

    def test_detail_shows_placeholder_for_missing_data(self):
        user = User.objects.create_user(
            email='vazio@example.com',
            password=PASSWORD,
            first_name='Carla',
            last_name='Dias',
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertContains(response, 'Não informado')


class ProfileUpdateViewTests(TestCase):
    url = reverse('profiles:update')

    def setUp(self):
        self.user = User.objects.create_user(
            email='ana@example.com',
            password=PASSWORD,
            first_name='Ana',
            last_name='Souza',
        )
        self.client.force_login(self.user)

    def get_payload(self, **overrides):
        data = {
            'first_name': 'Ana Maria',
            'last_name': 'Souza Lima',
            'phone': '(21) 99999-0000',
            'birth_date': '1992-03-08',
        }
        data.update(overrides)
        return data

    def test_update_get_renders_forms_with_current_data(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile_form.html')
        self.assertIn('form', response.context)
        self.assertIn('user_form', response.context)
        self.assertEqual(response.context['user_form'].instance, self.user)
        self.assertEqual(
            response.context['form'].instance, self.user.profile
        )
        self.assertContains(response, 'value="Ana"')
        self.assertContains(response, 'value="Souza"')

    def test_valid_post_updates_user_and_profile(self):
        self.client.post(self.url, self.get_payload())
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana Maria')
        self.assertEqual(self.user.last_name, 'Souza Lima')
        self.assertEqual(self.user.profile.phone, '(21) 99999-0000')
        self.assertEqual(
            self.user.profile.birth_date, datetime.date(1992, 3, 8)
        )

    def test_valid_post_redirects_to_detail(self):
        response = self.client.post(self.url, self.get_payload())
        self.assertRedirects(response, reverse('profiles:detail'))

    def test_valid_post_shows_success_message(self):
        response = self.client.post(
            self.url, self.get_payload(), follow=True
        )
        self.assertIn(
            'Perfil atualizado com sucesso.', get_message_texts(response)
        )

    def test_valid_post_accepts_empty_optional_fields(self):
        response = self.client.post(
            self.url, self.get_payload(phone='', birth_date='')
        )
        self.assertRedirects(response, reverse('profiles:detail'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '')
        self.assertIsNone(self.user.profile.birth_date)

    def test_post_with_empty_first_name_does_not_save_anything(self):
        response = self.client.post(
            self.url, self.get_payload(first_name='')
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('first_name', response.context['user_form'].errors)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana')
        self.assertEqual(self.user.last_name, 'Souza')
        self.assertEqual(self.user.profile.phone, '')
        self.assertIsNone(self.user.profile.birth_date)
        self.assertEqual(get_message_texts(response), [])

    def test_post_with_empty_last_name_does_not_save_anything(self):
        response = self.client.post(
            self.url, self.get_payload(last_name='')
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_name', response.context['user_form'].errors)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana')
        self.assertEqual(self.user.profile.phone, '')

    def test_post_with_invalid_birth_date_does_not_save_anything(self):
        response = self.client.post(
            self.url, self.get_payload(birth_date='data-invalida')
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('birth_date', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana')

    def test_email_is_not_changed_even_if_sent_in_post(self):
        response = self.client.post(
            self.url, self.get_payload(email='hacker@example.com')
        )
        self.assertRedirects(response, reverse('profiles:detail'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'ana@example.com')
        self.assertFalse(
            User.objects.filter(email='hacker@example.com').exists()
        )

    def test_update_only_affects_logged_user(self):
        other = User.objects.create_user(
            email='bruno@example.com',
            password=PASSWORD,
            first_name='Bruno',
            last_name='Lima',
        )
        self.client.post(self.url, self.get_payload())
        other.refresh_from_db()
        other.profile.refresh_from_db()
        self.assertEqual(other.first_name, 'Bruno')
        self.assertEqual(other.profile.phone, '')
