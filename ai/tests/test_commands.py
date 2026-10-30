from io import StringIO
from unittest import mock

import openai
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from ..models import FinancialInsight
from ..services import get_analysis_period
from .factories import (
    QuietAiLogsMixin,
    create_account,
    create_category,
    create_transaction,
    create_user,
    make_analysis,
)

COMMAND = 'generate_financial_insights'


def run_command(*args):
    stdout, stderr = StringIO(), StringIO()
    call_command(COMMAND, *args, stdout=stdout, stderr=stderr)
    return stdout.getvalue(), stderr.getvalue()


@override_settings(OPENAI_API_KEY='sk-test-fake', AI_MIN_TRANSACTIONS=5)
class GenerateFinancialInsightsCommandTests(QuietAiLogsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        period_start, _ = get_analysis_period()
        cls.ana = create_user('ana@example.com')
        cls.bruno = create_user('bruno@example.com')
        cls.carla = create_user('carla@example.com')  # no transactions
        cls.inactive = create_user('dani@example.com', is_active=False)
        for user in (cls.ana, cls.bruno, cls.inactive):
            account = create_account(user)
            category = create_category(user, 'Alimentação')
            for _ in range(5):
                create_transaction(
                    user, account, category, '10.00', period_start
                )

    def setUp(self):
        super().setUp()
        patcher = mock.patch('ai.services.build_agent')
        self.build_agent = patcher.start()
        self.addCleanup(patcher.stop)
        self.invoke = self.build_agent.return_value.invoke
        self.invoke.return_value = {
            'structured_response': make_analysis(), 'messages': [],
        }

    def test_processes_all_active_users(self):
        stdout, stderr = run_command()

        self.assertEqual(
            FinancialInsight.objects.filter(
                status=FinancialInsight.COMPLETED
            ).count(),
            2,
        )
        self.assertTrue(FinancialInsight.objects.filter(
            user=self.carla, status=FinancialInsight.INSUFFICIENT_DATA,
        ).exists())
        self.assertFalse(
            FinancialInsight.objects.filter(user=self.inactive).exists()
        )
        self.assertIn(
            'Resumo: 2 gerada(s), 1 com dados insuficientes, '
            '0 sem mudança, 0 falha(s).',
            stdout,
        )
        self.assertEqual(stderr, '')

    def test_insufficient_data_unchanged_on_second_run(self):
        run_command()
        stdout, _ = run_command()
        self.assertIn('0 com dados insuficientes, 1 sem mudança', stdout)
        self.assertEqual(
            FinancialInsight.objects.filter(user=self.carla).count(), 1
        )

    def test_single_user_option(self):
        stdout, _ = run_command('--user', 'BRUNO@example.com')

        self.assertEqual(self.invoke.call_count, 1)
        context = self.invoke.call_args.kwargs['context']
        self.assertEqual(context.user_id, self.bruno.pk)
        self.assertEqual(
            list(FinancialInsight.objects.values_list('user', flat=True)),
            [self.bruno.pk],
        )
        self.assertIn('1 gerada(s)', stdout)

    def test_unknown_email(self):
        with self.assertRaisesMessage(CommandError, 'Nenhum usuário ativo'):
            run_command('--user', 'ninguem@example.com')
        self.assertFalse(FinancialInsight.objects.exists())

    def test_inactive_user_email(self):
        with self.assertRaises(CommandError):
            run_command('--user', 'dani@example.com')

    @override_settings(OPENAI_API_KEY='')
    def test_missing_key(self):
        with self.assertRaisesMessage(CommandError, 'OPENAI_API_KEY'):
            run_command()
        self.build_agent.assert_not_called()
        self.assertFalse(FinancialInsight.objects.exists())

    def test_failure_does_not_stop_other_users(self):
        error = openai.APIError('erro', None, body=None)
        self.invoke.side_effect = [
            error,
            {'structured_response': make_analysis(), 'messages': []},
        ]

        stdout, stderr = run_command()

        self.assertIn(
            'Resumo: 1 gerada(s), 1 com dados insuficientes, '
            '0 sem mudança, 1 falha(s).',
            stdout,
        )
        self.assertIn(f'Falha nos usuários de id: {self.ana.pk}.', stderr)
        self.assertNotIn('@', stderr)
        self.assertFalse(
            FinancialInsight.objects.filter(user=self.ana).exists()
        )
        self.assertTrue(
            FinancialInsight.objects.filter(user=self.bruno).exists()
        )
