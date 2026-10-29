from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

PASSWORD = 'SenhaForte!2024'


def get_message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class UserManagerCreateUserTests(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password=PASSWORD)

    def test_create_user_requires_email_not_none(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email=None, password=PASSWORD)

    def test_create_user_normalizes_email_to_lowercase(self):
        user = User.objects.create_user(
            email='Fulano.Silva@EXAMPLE.COM', password=PASSWORD
        )
        self.assertEqual(user.email, 'fulano.silva@example.com')

    def test_create_user_hashes_password(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.check_password('outra-senha'))

    def test_create_user_defaults_to_regular_user(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_has_no_username_and_uses_email_as_str(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertFalse(hasattr(user, 'username') and user.username)
        self.assertEqual(str(user), 'ana@example.com')


class UserManagerCreateSuperuserTests(TestCase):
    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = User.objects.create_superuser(
            email='admin@example.com', password=PASSWORD
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(PASSWORD))

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='admin@example.com', password=PASSWORD, is_staff=False
            )

    def test_create_superuser_rejects_is_superuser_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='admin@example.com',
                password=PASSWORD,
                is_superuser=False,
            )


class SignUpViewTests(TestCase):
    url = reverse('users:signup')

    def get_payload(self, **overrides):
        data = {
            'first_name': 'Ana',
            'last_name': 'Souza',
            'email': 'ana@example.com',
            'password1': PASSWORD,
            'password2': PASSWORD,
        }
        data.update(overrides)
        return data

    def test_signup_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/signup.html')

    def test_signup_success_creates_user(self):
        self.client.post(self.url, self.get_payload())
        user = User.objects.get(email='ana@example.com')
        self.assertEqual(user.first_name, 'Ana')
        self.assertEqual(user.last_name, 'Souza')
        self.assertTrue(user.check_password(PASSWORD))

    def test_signup_success_redirects_to_dashboard(self):
        response = self.client.post(self.url, self.get_payload())
        self.assertRedirects(response, reverse('dashboard'))

    def test_signup_success_logs_user_in(self):
        self.client.post(self.url, self.get_payload())
        user = User.objects.get(email='ana@example.com')
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.user, user)

    def test_signup_success_shows_welcome_message(self):
        response = self.client.post(
            self.url, self.get_payload(), follow=True
        )
        self.assertIn(
            'Conta criada com sucesso. Bem-vindo(a) ao Finanpy!',
            get_message_texts(response),
        )

    def test_signup_stores_email_in_lowercase(self):
        self.client.post(
            self.url, self.get_payload(email='Ana@Example.COM')
        )
        self.assertTrue(User.objects.filter(email='ana@example.com').exists())

    def test_signup_duplicate_email_shows_error(self):
        User.objects.create_user(email='ana@example.com', password=PASSWORD)
        response = self.client.post(self.url, self.get_payload())
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'email',
            'Já existe um usuário com este e-mail.',
        )
        self.assertEqual(User.objects.count(), 1)

    def test_signup_duplicate_email_with_different_case_shows_error(self):
        User.objects.create_user(email='ana@example.com', password=PASSWORD)
        response = self.client.post(
            self.url, self.get_payload(email='ANA@Example.com')
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'email',
            'Já existe um usuário com este e-mail.',
        )
        self.assertContains(response, 'Já existe um usuário com este e-mail.')
        self.assertEqual(User.objects.count(), 1)

    def test_signup_password_mismatch_shows_error_on_password2(self):
        response = self.client.post(
            self.url, self.get_payload(password2='OutraSenha!2024')
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors.get('password2'))
        self.assertFalse(User.objects.exists())
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_signup_requires_first_name(self):
        response = self.client.post(
            self.url, self.get_payload(first_name='')
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('first_name', response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_signup_requires_last_name(self):
        response = self.client.post(
            self.url, self.get_payload(last_name='')
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_name', response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_authenticated_user_is_redirected_from_signup_get(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard'))

    def test_authenticated_user_post_to_signup_does_not_create_user(self):
        user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )
        self.client.force_login(user)
        response = self.client.post(
            self.url, self.get_payload(email='novo@example.com')
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(
            User.objects.filter(email='novo@example.com').exists()
        )


class LoginViewTests(TestCase):
    url = reverse('users:login')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='ana@example.com',
            password=PASSWORD,
            first_name='Ana',
            last_name='Souza',
        )

    def test_login_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')

    def test_login_with_email_succeeds_and_redirects_to_dashboard(self):
        response = self.client.post(
            self.url, {'username': 'ana@example.com', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_login_with_email_in_different_case_succeeds(self):
        response = self.client.post(
            self.url, {'username': 'ANA@Example.com', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_login_with_wrong_password_shows_error(self):
        response = self.client.post(
            self.url,
            {'username': 'ana@example.com', 'password': 'SenhaErrada!1'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E-mail ou senha inválidos.')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_with_unknown_email_shows_error(self):
        response = self.client.post(
            self.url,
            {'username': 'ninguem@example.com', 'password': PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E-mail ou senha inválidos.')
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_respects_next_parameter(self):
        next_url = reverse('accounts:list')
        response = self.client.post(
            f'{self.url}?next={next_url}',
            {'username': 'ana@example.com', 'password': PASSWORD},
        )
        self.assertRedirects(response, next_url)

    def test_login_respects_next_in_post_data(self):
        next_url = reverse('transactions:list')
        response = self.client.post(
            self.url,
            {
                'username': 'ana@example.com',
                'password': PASSWORD,
                'next': next_url,
            },
        )
        self.assertRedirects(response, next_url)

    def test_login_ignores_external_next(self):
        response = self.client.post(
            self.url,
            {
                'username': 'ana@example.com',
                'password': PASSWORD,
                'next': 'https://malicioso.example.com/',
            },
        )
        self.assertRedirects(response, reverse('dashboard'))

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard'))


class LogoutViewTests(TestCase):
    url = reverse('users:logout')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='ana@example.com', password=PASSWORD
        )

    def test_logout_post_redirects_to_landing(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('landing'))

    def test_logout_post_ends_session(self):
        self.client.force_login(self.user)
        self.client.post(self.url)
        self.assertNotIn(SESSION_KEY, self.client.session)
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            response,
            f'{reverse("users:login")}?next={reverse("dashboard")}',
        )

    def test_logout_get_is_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)
