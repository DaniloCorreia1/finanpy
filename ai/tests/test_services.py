import datetime
from unittest import mock

import httpx2
import openai
from django.test import TestCase, override_settings
from django.utils import timezone
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from .. import agent as agent_module
from ..agent import RECURSION_LIMIT, build_agent, build_model
from ..models import FinancialInsight
from ..prompts import SYSTEM_PROMPT
from ..schemas import AnalysisContext, FinancialAnalysis
from ..services import (
    INSUFFICIENT_DATA_SUMMARY,
    GenerationResult,
    generate_insight_for_user,
    get_analysis_period,
    get_latest_insight,
)
from ..tools import FINANCIAL_TOOLS
from .factories import (
    QuietAiLogsMixin,
    create_account,
    create_category,
    create_transaction,
    create_user,
    make_analysis,
)

REQUEST = httpx2.Request('POST', 'https://api.openai.com/v1/responses')


def api_errors():
    return {
        'timeout': openai.APITimeoutError(request=REQUEST),
        'rate_limit': openai.RateLimitError(
            'rate limit',
            response=httpx2.Response(429, request=REQUEST),
            body=None,
        ),
        'api_error': openai.APIError('erro', REQUEST, body=None),
        'invalid_output': StructuredOutputValidationError(
            'FinancialAnalysis', ValueError('json'), AIMessage(content='')
        ),
        'limit': GraphRecursionError('Recursion limit of 50 reached'),
        # The message carries a value: it must never reach the logs.
        'unexpected': RuntimeError('saldo 1234.56'),
    }


def agent_result(analysis=None, messages=None):
    if messages is None:
        messages = [
            HumanMessage(content='pedido'),
            AIMessage(
                content='',
                usage_metadata={
                    'input_tokens': 100, 'output_tokens': 20,
                    'total_tokens': 120,
                },
            ),
            ToolMessage(content='{}', tool_call_id='1'),
            AIMessage(
                content='{}',
                usage_metadata={
                    'input_tokens': 300, 'output_tokens': 80,
                    'total_tokens': 380,
                },
            ),
        ]
    return {
        'structured_response': analysis or make_analysis(),
        'messages': messages,
    }


class AnalysisPeriodTests(TestCase):
    def test_period_starts_two_months_before(self):
        self.assertEqual(
            get_analysis_period(datetime.date(2026, 10, 29)),
            (datetime.date(2026, 8, 1), datetime.date(2026, 10, 29)),
        )

    def test_period_crosses_year(self):
        self.assertEqual(
            get_analysis_period(datetime.date(2027, 2, 15)),
            (datetime.date(2026, 12, 1), datetime.date(2027, 2, 15)),
        )
        self.assertEqual(
            get_analysis_period(datetime.date(2027, 1, 31)),
            (datetime.date(2026, 11, 1), datetime.date(2027, 1, 31)),
        )

    def test_default_uses_local_date(self):
        self.assertEqual(get_analysis_period()[1], timezone.localdate())


@override_settings(
    OPENAI_API_KEY='sk-test-fake', AI_MODEL_NAME='gpt-5-mini',
    AI_MIN_TRANSACTIONS=5,
)
class GenerateInsightTests(QuietAiLogsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_user('ana@example.com')
        cls.other = create_user('bruno@example.com')
        account = create_account(cls.user)
        category = create_category(cls.user, 'Alimentação')
        cls.period_start, cls.period_end = get_analysis_period()
        for _ in range(5):
            create_transaction(
                cls.user, account, category, '10.00', cls.period_start
            )

    @mock.patch('ai.services.build_agent')
    def test_completed_insight_is_saved(self, build_agent):
        build_agent.return_value.invoke.return_value = agent_result()

        result = generate_insight_for_user(self.user)

        self.assertEqual(result.status, GenerationResult.COMPLETED)
        insight = FinancialInsight.objects.get()
        self.assertEqual(result.insight, insight)
        self.assertEqual(insight.user, self.user)
        self.assertEqual(insight.status, FinancialInsight.COMPLETED)
        self.assertEqual(insight.summary, 'Você gastou menos.')
        self.assertEqual(insight.insights, [
            {'title': 'Insight 0', 'description': 'Detalhe 0'},
            {'title': 'Insight 1', 'description': 'Detalhe 1'},
        ])
        self.assertEqual(len(insight.tips), 2)
        self.assertEqual(insight.period_start, self.period_start)
        self.assertEqual(insight.period_end, self.period_end)
        self.assertEqual(insight.model_name, 'gpt-5-mini')
        self.assertEqual(insight.input_tokens, 400)
        self.assertEqual(insight.output_tokens, 100)

    @mock.patch('ai.services.build_agent')
    def test_context_passed_to_agent(self, build_agent):
        build_agent.return_value.invoke.return_value = agent_result()

        generate_insight_for_user(self.user)

        args, kwargs = build_agent.return_value.invoke.call_args
        self.assertEqual(kwargs['context'], AnalysisContext(
            user_id=self.user.pk,
            period_start=self.period_start,
            period_end=self.period_end,
        ))
        self.assertEqual(kwargs['config'], {'recursion_limit': 50})
        content = args[0]['messages'][0]['content']
        self.assertIn(f'{self.period_start:%d/%m/%Y}', content)
        self.assertNotIn(self.user.email, content)

    @mock.patch('ai.services.build_agent')
    def test_tokens_none_without_usage_metadata(self, build_agent):
        build_agent.return_value.invoke.return_value = agent_result(
            messages=[AIMessage(content='{}')]
        )
        generate_insight_for_user(self.user)
        insight = FinancialInsight.objects.get()
        self.assertIsNone(insight.input_tokens)
        self.assertIsNone(insight.output_tokens)

    @mock.patch('ai.services.build_agent')
    def test_history_is_preserved(self, build_agent):
        build_agent.return_value.invoke.return_value = agent_result()

        first = generate_insight_for_user(self.user).insight
        second = generate_insight_for_user(self.user).insight

        self.assertEqual(FinancialInsight.objects.count(), 2)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(get_latest_insight(self.user), second)

    @mock.patch('ai.services.build_agent')
    def test_insufficient_data_skips_llm(self, build_agent):
        result = generate_insight_for_user(self.other)

        build_agent.assert_not_called()
        self.assertEqual(result.status, GenerationResult.INSUFFICIENT_DATA)
        insight = FinancialInsight.objects.get()
        self.assertEqual(insight.user, self.other)
        self.assertEqual(insight.status, FinancialInsight.INSUFFICIENT_DATA)
        self.assertEqual(insight.summary, INSUFFICIENT_DATA_SUMMARY)
        self.assertEqual(insight.insights, [])
        self.assertEqual(insight.tips, [])
        self.assertEqual(insight.model_name, '')

    @mock.patch('ai.services.build_agent')
    def test_insufficient_data_is_not_duplicated(self, build_agent):
        generate_insight_for_user(self.other)
        result = generate_insight_for_user(self.other)

        self.assertEqual(result.status, GenerationResult.UNCHANGED)
        self.assertEqual(FinancialInsight.objects.count(), 1)

    @mock.patch('ai.services.build_agent')
    def test_insufficient_data_after_completed_is_saved(self, build_agent):
        FinancialInsight.objects.create(
            user=self.other, status=FinancialInsight.COMPLETED,
            summary='Antiga', period_start=self.period_start,
            period_end=self.period_end,
        )
        result = generate_insight_for_user(self.other)

        self.assertEqual(result.status, GenerationResult.INSUFFICIENT_DATA)
        self.assertEqual(
            FinancialInsight.objects.filter(user=self.other).count(), 2
        )

    @override_settings(AI_MIN_TRANSACTIONS=6)
    @mock.patch('ai.services.build_agent')
    def test_min_transactions_setting(self, build_agent):
        result = generate_insight_for_user(self.user)
        build_agent.assert_not_called()
        self.assertEqual(result.status, GenerationResult.INSUFFICIENT_DATA)

    @mock.patch('ai.services.build_agent')
    def test_transactions_outside_period_do_not_count(self, build_agent):
        account = create_account(self.other)
        category = create_category(self.other, 'Lazer')
        old_date = self.period_start - datetime.timedelta(days=1)
        for _ in range(5):
            create_transaction(self.other, account, category, '1.00', old_date)

        result = generate_insight_for_user(self.other)

        build_agent.assert_not_called()
        self.assertEqual(result.status, GenerationResult.INSUFFICIENT_DATA)

    @override_settings(OPENAI_API_KEY='')
    @mock.patch('ai.services.build_agent')
    def test_missing_key_fails_without_saving(self, build_agent):
        result = generate_insight_for_user(self.user)

        build_agent.assert_not_called()
        self.assertEqual(result.status, GenerationResult.FAILED)
        self.assertFalse(FinancialInsight.objects.exists())

    @mock.patch('ai.services.build_agent')
    def test_api_errors_do_not_save(self, build_agent):
        for reason, error in api_errors().items():
            with self.subTest(reason=reason):
                build_agent.return_value.invoke.side_effect = error
                with self.assertLogs('ai', level='WARNING') as logs:
                    result = generate_insight_for_user(self.user)
                self.assertEqual(result.status, GenerationResult.FAILED)
                self.assertIsNone(result.insight)
                self.assertFalse(FinancialInsight.objects.exists())
                output = '\n'.join(logs.output)
                self.assertIn(f'reason={reason}', output)
                self.assertIn(f'user_id={self.user.pk}', output)
                self.assertNotIn('1234.56', output)
                self.assertTrue(
                    all(not record.exc_info for record in logs.records)
                )
                self.assertIn(type(error).__name__, output)
                self.assertNotIn(self.user.email, output)
                self.assertNotIn('sk-test-fake', output)

    @mock.patch('ai.services.build_agent')
    def test_recursion_limit_is_an_expected_failure(self, build_agent):
        build_agent.return_value.invoke.side_effect = GraphRecursionError(
            'Recursion limit of 50 reached'
        )
        with self.assertLogs('ai', level='WARNING') as logs:
            result = generate_insight_for_user(self.user)
        self.assertEqual(result.status, GenerationResult.FAILED)
        self.assertFalse(FinancialInsight.objects.exists())
        self.assertEqual(logs.records[0].levelname, 'WARNING')
        self.assertIn('reason=limit', logs.output[0])
        self.assertIn('GraphRecursionError', logs.output[0])

    @mock.patch('ai.services.build_agent')
    def test_build_agent_error_does_not_save(self, build_agent):
        build_agent.side_effect = openai.OpenAIError('config')
        with self.assertLogs('ai', level='ERROR'):
            result = generate_insight_for_user(self.user)
        self.assertEqual(result.status, GenerationResult.FAILED)
        self.assertFalse(FinancialInsight.objects.exists())

    @mock.patch('ai.services.build_agent')
    def test_missing_structured_response_does_not_save(self, build_agent):
        build_agent.return_value.invoke.return_value = {
            'messages': [AIMessage(content='limite atingido')],
        }
        with self.assertLogs('ai', level='WARNING') as logs:
            result = generate_insight_for_user(self.user)
        self.assertEqual(result.status, GenerationResult.FAILED)
        self.assertIn('reason=invalid_output', '\n'.join(logs.output))
        self.assertFalse(FinancialInsight.objects.exists())

    @mock.patch('ai.services.build_agent')
    def test_lists_out_of_range_are_rejected(self, build_agent):
        valid = make_analysis()
        cases = {
            'one_insight': {'insights': valid.insights[:1]},
            'six_tips': {'tips': valid.tips * 3},
            'empty_summary': {'summary': '   '},
        }
        for name, changes in cases.items():
            with self.subTest(case=name):
                # model_construct skips Pydantic validation, simulating a
                # response that bypassed the schema constraints.
                analysis = FinancialAnalysis.model_construct(
                    **{**dict(valid), **changes}
                )
                build_agent.return_value.invoke.return_value = agent_result(
                    analysis
                )
                with self.assertLogs('ai', level='WARNING'):
                    result = generate_insight_for_user(self.user)
                self.assertEqual(result.status, GenerationResult.FAILED)
                self.assertFalse(FinancialInsight.objects.exists())

    @mock.patch('ai.services.build_agent')
    def test_dict_structured_response_is_validated(self, build_agent):
        build_agent.return_value.invoke.return_value = agent_result(
            {'summary': 'Resumo', 'insights': [], 'tips': []}
        )
        with self.assertLogs('ai', level='WARNING'):
            result = generate_insight_for_user(self.user)
        self.assertEqual(result.status, GenerationResult.FAILED)
        self.assertFalse(FinancialInsight.objects.exists())

    @mock.patch('ai.services.build_agent')
    def test_success_log_has_no_financial_text(self, build_agent):
        build_agent.return_value.invoke.return_value = agent_result()
        with self.assertLogs('ai', level='INFO') as logs:
            generate_insight_for_user(self.user)
        output = '\n'.join(logs.output)
        self.assertIn('status=completed', output)
        self.assertNotIn('Você gastou menos', output)
        self.assertNotIn('10.00', output)


class LatestInsightTests(TestCase):
    def test_returns_none_without_insight(self):
        self.assertIsNone(get_latest_insight(create_user('x@example.com')))

    def test_returns_only_own_latest(self):
        user = create_user('ana@example.com')
        other = create_user('bruno@example.com')
        period = get_analysis_period()
        old = FinancialInsight.objects.create(
            user=user, status=FinancialInsight.COMPLETED, summary='A',
            period_start=period[0], period_end=period[1],
        )
        new = FinancialInsight.objects.create(
            user=user, status=FinancialInsight.COMPLETED, summary='B',
            period_start=period[0], period_end=period[1],
        )
        FinancialInsight.objects.create(
            user=other, status=FinancialInsight.COMPLETED, summary='C',
            period_start=period[0], period_end=period[1],
        )
        self.assertNotEqual(old, new)
        self.assertEqual(get_latest_insight(user), new)


class FinancialInsightModelTests(TestCase):
    def test_str_uses_local_date(self):
        user = create_user('ana@example.com')
        insight = FinancialInsight.objects.create(
            user=user, status=FinancialInsight.COMPLETED, summary='A',
            period_start=datetime.date(2026, 8, 1),
            period_end=datetime.date(2026, 10, 29),
        )
        # 01:43 UTC on 30/10 is 22:43 on 29/10 in America/Sao_Paulo.
        insight.created_at = datetime.datetime(
            2026, 10, 30, 1, 43, tzinfo=datetime.timezone.utc
        )
        self.assertEqual(
            str(insight), 'Análise de ana@example.com em 29/10/2026'
        )


@override_settings(
    OPENAI_API_KEY='sk-test-fake', AI_MODEL_NAME='gpt-5-mini',
    AI_REQUEST_TIMEOUT=45, AI_MAX_COMPLETION_TOKENS=3000,
)
class BuildAgentTests(TestCase):
    """Builds the real agent without network (no request is made)."""

    def test_model_parameters(self):
        model = build_model()
        self.assertEqual(model.model_name, 'gpt-5-mini')
        self.assertEqual(model.request_timeout, 45)
        self.assertEqual(model.max_retries, 2)
        self.assertEqual(model.max_tokens, 3000)  # max_completion_tokens
        self.assertEqual(model.reasoning_effort, 'low')
        self.assertEqual(
            model.openai_api_key.get_secret_value(), 'sk-test-fake'
        )

    def test_agent_configuration(self):
        with mock.patch(
            'ai.agent.create_agent', wraps=agent_module.create_agent
        ) as create:
            agent = build_agent()

        self.assertTrue(hasattr(agent, 'invoke'))
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs['tools'], FINANCIAL_TOOLS)
        self.assertEqual(kwargs['system_prompt'], SYSTEM_PROMPT)
        self.assertIs(kwargs['response_format'], FinancialAnalysis)
        self.assertIs(kwargs['context_schema'], AnalysisContext)

        model_limit, tool_limit = kwargs['middleware']
        self.assertIsInstance(model_limit, ModelCallLimitMiddleware)
        self.assertEqual(model_limit.run_limit, 8)
        self.assertEqual(model_limit.exit_behavior, 'end')
        self.assertIsInstance(tool_limit, ToolCallLimitMiddleware)
        self.assertEqual(tool_limit.run_limit, 10)
        self.assertEqual(tool_limit.exit_behavior, 'continue')
        self.assertEqual(RECURSION_LIMIT, 50)
