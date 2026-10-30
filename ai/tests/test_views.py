import html
from unittest import mock

from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import FinancialInsight
from ..services import (
    INSUFFICIENT_DATA_SUMMARY,
    GenerationResult,
    get_analysis_period,
)
from .factories import (
    QuietAiLogsMixin,
    create_account,
    create_category,
    create_transaction,
    create_user,
    make_analysis,
)

GENERATE_URL = reverse('ai:generate')
DASHBOARD_URL = reverse('dashboard')
DISCLAIMER = (
    'Análise gerada por IA com base nos seus lançamentos. '
    'Não constitui recomendação de investimento.'
)
SUCCESS = 'Análise gerada com sucesso.'
COOLDOWN = (
    'Você gerou uma análise recentemente. Aguarde alguns minutos para gerar '
    'outra.'
)
FAILURE = (
    'Não foi possível gerar a análise agora. Tente novamente mais tarde.'
)


def insufficient(min_transactions):
    return (
        'Ainda não há dados suficientes para gerar uma análise. Registre ao '
        f'menos {min_transactions} transações nos últimos 3 meses.'
    )


def message_list(response):
    return [
        (message.level_tag, str(message))
        for message in get_messages(response.wsgi_request)
    ]


def page_text(response):
    return html.unescape(response.content.decode())


class DashboardCardTests(TestCase):
    def setUp(self):
        self.user = create_user('ana@example.com')
        self.client.force_login(self.user)
        self.period = get_analysis_period()

    def create_insight(self, user=None, **kwargs):
        data = {
            'user': user or self.user,
            'status': FinancialInsight.COMPLETED,
            'summary': 'Seus gastos caíram em outubro.',
            'insights': [
                {'title': 'Moradia pesa', 'description': 'Maior gasto.'},
                {'title': 'Lazer subiu', 'description': 'Cresceu 20%.'},
            ],
            'tips': [
                {'title': 'Reserva', 'description': 'Monte uma reserva.'},
                {'title': 'Revise', 'description': 'Revise o lazer.'},
            ],
            'period_start': self.period[0],
            'period_end': self.period[1],
            'model_name': 'gpt-5-mini',
        }
        data.update(kwargs)
        return FinancialInsight.objects.create(**data)

    @override_settings(OPENAI_API_KEY='sk-test-fake')
    def test_without_insight(self):
        response = self.client.get(DASHBOARD_URL)
        self.assertIsNone(response.context['latest_insight'])
        self.assertTrue(response.context['ai_enabled'])
        content = page_text(response)
        self.assertIn('Você ainda não tem uma análise financeira.', content)
        self.assertIn('Gerar análise', content)
        self.assertIn(GENERATE_URL, content)

    @override_settings(OPENAI_API_KEY='')
    def test_button_hidden_without_key(self):
        self.create_insight()
        response = self.client.get(DASHBOARD_URL)
        self.assertFalse(response.context['ai_enabled'])
        content = page_text(response)
        self.assertNotIn(GENERATE_URL, content)
        self.assertNotIn('Gerar nova análise', content)

    @override_settings(OPENAI_API_KEY='sk-test-fake')
    def test_insufficient_data(self):
        self.create_insight(
            status=FinancialInsight.INSUFFICIENT_DATA,
            summary=INSUFFICIENT_DATA_SUMMARY, insights=[], tips=[],
            model_name='',
        )
        response = self.client.get(DASHBOARD_URL)
        content = page_text(response)
        self.assertIn(INSUFFICIENT_DATA_SUMMARY, content)
        self.assertIn(reverse('transactions:create'), content)

    @override_settings(OPENAI_API_KEY='sk-test-fake')
    def test_completed(self):
        insight = self.create_insight()
        response = self.client.get(DASHBOARD_URL)
        self.assertEqual(response.context['latest_insight'], insight)
        content = page_text(response)
        for text in ('Seus gastos caíram em outubro.', 'Moradia pesa',
                     'Revise o lazer.', 'Gerar nova análise', DISCLAIMER,
                     f'{self.period[0]:%d/%m/%Y}'):
            self.assertIn(text, content)

    def test_shows_only_latest_own_insight(self):
        self.create_insight(summary='Análise antiga.')
        self.create_insight(summary='Análise nova.')
        other = create_user('bruno@example.com')
        self.create_insight(user=other, summary='Análise de outro.')
        content = page_text(self.client.get(DASHBOARD_URL))
        self.assertIn('Análise nova.', content)
        self.assertNotIn('Análise antiga.', content)
        self.assertNotIn('Análise de outro.', content)

    @mock.patch('ai.services.build_agent')
    def test_dashboard_never_calls_llm(self, build_agent):
        self.client.get(DASHBOARD_URL)
        build_agent.assert_not_called()


@override_settings(
    OPENAI_API_KEY='sk-test-fake', AI_MIN_TRANSACTIONS=5,
    AI_MANUAL_COOLDOWN_MINUTES=60,
)
class GenerateInsightViewTests(QuietAiLogsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('ana@example.com')
        account = create_account(cls.user)
        category = create_category(cls.user, 'Alimentação')
        period_start, _ = get_analysis_period()
        for _ in range(5):
            create_transaction(
                cls.user, account, category, '10.00', period_start
            )

    def setUp(self):
        super().setUp()
        cache.clear()
        self.addCleanup(cache.clear)
        self.client.force_login(self.user)
        patcher = mock.patch('ai.services.build_agent')
        self.build_agent = patcher.start()
        self.addCleanup(patcher.stop)
        self.invoke = self.build_agent.return_value.invoke
        self.invoke.return_value = {
            'structured_response': make_analysis(), 'messages': [],
        }

    def test_login_required(self):
        self.client.logout()
        response = self.client.post(GENERATE_URL)
        self.assertRedirects(
            response, f"{reverse('users:login')}?next={GENERATE_URL}"
        )
        self.build_agent.assert_not_called()

    def test_get_not_allowed(self):
        response = self.client.get(GENERATE_URL)
        self.assertEqual(response.status_code, 405)
        self.build_agent.assert_not_called()

    def test_success(self):
        response = self.client.post(GENERATE_URL)
        self.assertRedirects(response, DASHBOARD_URL)
        self.assertEqual(message_list(response), [('success', SUCCESS)])
        insight = FinancialInsight.objects.get()
        self.assertEqual(insight.user, self.user)
        context = self.invoke.call_args.kwargs['context']
        self.assertEqual(context.user_id, self.user.pk)

    def test_cooldown(self):
        self.client.post(GENERATE_URL, follow=True)
        response = self.client.post(GENERATE_URL)
        self.assertRedirects(response, DASHBOARD_URL)
        self.assertEqual(message_list(response), [('warning', COOLDOWN)])
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(FinancialInsight.objects.count(), 1)

    def test_cooldown_is_per_user(self):
        self.client.post(GENERATE_URL, follow=True)
        other = create_user('bruno@example.com')
        self.client.force_login(other)
        response = self.client.post(GENERATE_URL)
        # Not blocked by the first user's cooldown (no data -> warning).
        self.assertEqual(
            message_list(response), [('warning', insufficient(5))]
        )

    def test_failure_counts_for_cooldown(self):
        self.invoke.side_effect = RuntimeError('boom')
        self.client.post(GENERATE_URL, follow=True)
        response = self.client.post(GENERATE_URL)
        self.assertEqual(message_list(response), [('warning', COOLDOWN)])
        self.assertEqual(self.invoke.call_count, 1)

    def test_api_failure_redirects_with_error(self):
        self.invoke.side_effect = RuntimeError('boom')
        response = self.client.post(GENERATE_URL)
        self.assertRedirects(response, DASHBOARD_URL)
        self.assertEqual(message_list(response), [('error', FAILURE)])
        self.assertFalse(FinancialInsight.objects.exists())

    @override_settings(AI_MIN_TRANSACTIONS=10)
    def test_insufficient_data_message(self):
        response = self.client.post(GENERATE_URL)
        self.assertEqual(
            message_list(response), [('warning', insufficient(10))]
        )
        self.build_agent.assert_not_called()

    @mock.patch('ai.views.generate_insight_for_user')
    def test_unchanged_shows_insufficient_message(self, generate):
        generate.return_value = GenerationResult(GenerationResult.UNCHANGED)
        response = self.client.post(GENERATE_URL)
        self.assertEqual(
            message_list(response), [('warning', insufficient(5))]
        )

    @override_settings(OPENAI_API_KEY='')
    def test_missing_key(self):
        response = self.client.post(GENERATE_URL)
        self.assertRedirects(response, DASHBOARD_URL)
        self.assertEqual(message_list(response), [('error', FAILURE)])
        self.build_agent.assert_not_called()
        self.assertFalse(FinancialInsight.objects.exists())

    def test_redirected_dashboard_renders_after_failure(self):
        self.invoke.side_effect = RuntimeError('boom')
        response = self.client.post(GENERATE_URL, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(FAILURE, page_text(response))
