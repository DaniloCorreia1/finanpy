"""Generation and storage of the financial analyses (PRD section 14).

Logs never contain financial values, analysis texts, e-mails or the API key:
only the user id, the outcome, the duration, tokens and exception classes.
"""
import logging
import time
from dataclasses import dataclass
from datetime import date

import openai
from django.conf import settings
from django.utils import timezone
from langchain.agents.structured_output import StructuredOutputError
from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError
from pydantic import ValidationError

from transactions.models import Transaction

from .agent import RECURSION_LIMIT, build_agent
from .models import FinancialInsight
from .prompts import build_user_message
from .schemas import AnalysisContext, FinancialAnalysis

logger = logging.getLogger('ai')

INSUFFICIENT_DATA_SUMMARY = (
    'Ainda não há lançamentos suficientes no período para uma análise. '
    'Continue registrando suas entradas e saídas.'
)

MIN_ITEMS = 2
MAX_ITEMS = 5


class InvalidAnalysisError(Exception):
    """The agent did not return a valid ``FinancialAnalysis``."""


@dataclass(frozen=True)
class GenerationResult:
    COMPLETED = 'completed'
    INSUFFICIENT_DATA = 'insufficient_data'
    UNCHANGED = 'unchanged'
    FAILED = 'failed'

    status: str
    insight: FinancialInsight | None = None


def get_analysis_period(today=None):
    """From the 1st day of the month two months ago up to ``today``."""
    today = today or timezone.localdate()
    month = today.month - 2
    year = today.year
    if month < 1:
        month += 12
        year -= 1
    return date(year, month, 1), today


def count_period_transactions(user, period_start, period_end):
    return Transaction.objects.filter(
        user=user, date__range=(period_start, period_end)
    ).count()


def has_minimum_data(user, period_start, period_end):
    count = count_period_transactions(user, period_start, period_end)
    return count >= settings.AI_MIN_TRANSACTIONS


def get_latest_insight(user):
    """Most recent analysis of the user (one indexed query) or ``None``."""
    # '-pk' only breaks ties between records created in the same instant.
    return FinancialInsight.objects.filter(user=user).order_by(
        '-created_at', '-pk'
    ).first()


def _register_insufficient_data(user, period_start, period_end):
    latest = get_latest_insight(user)
    if latest and latest.status == FinancialInsight.INSUFFICIENT_DATA:
        logger.info('ai.insight user_id=%s status=unchanged', user.pk)
        return GenerationResult(GenerationResult.UNCHANGED, latest)

    insight = FinancialInsight.objects.create(
        user=user,
        status=FinancialInsight.INSUFFICIENT_DATA,
        summary=INSUFFICIENT_DATA_SUMMARY,
        insights=[],
        tips=[],
        period_start=period_start,
        period_end=period_end,
    )
    logger.info('ai.insight user_id=%s status=insufficient_data', user.pk)
    return GenerationResult(GenerationResult.INSUFFICIENT_DATA, insight)


def _validate_analysis(structured):
    if structured is None:
        raise InvalidAnalysisError('missing structured_response')
    if not isinstance(structured, FinancialAnalysis):
        try:
            structured = FinancialAnalysis.model_validate(structured)
        except ValidationError as exc:
            raise InvalidAnalysisError('invalid structured_response') from exc
    if not (structured.summary or '').strip():
        raise InvalidAnalysisError('empty summary')
    for items in (structured.insights, structured.tips):
        if not MIN_ITEMS <= len(items or []) <= MAX_ITEMS:
            raise InvalidAnalysisError('list size out of range')
    return structured


def _sum_usage(messages):
    input_tokens = output_tokens = 0
    found = False
    for message in messages or []:
        usage = getattr(message, 'usage_metadata', None)
        if isinstance(message, AIMessage) and usage:
            found = True
            input_tokens += usage.get('input_tokens', 0) or 0
            output_tokens += usage.get('output_tokens', 0) or 0
    if not found:
        return None, None
    return input_tokens, output_tokens


def _items_to_json(items):
    return [
        {'title': item.title.strip(), 'description': item.description.strip()}
        for item in items
    ]


def _fail(user, reason, started, exc=None):
    logger.warning(
        'ai.insight user_id=%s status=failed reason=%s error=%s '
        'duration=%.2fs',
        user.pk, reason, type(exc).__name__ if exc else '-',
        time.monotonic() - started,
    )
    return GenerationResult(GenerationResult.FAILED)


def generate_insight_for_user(user):
    """Generate and store the analysis of ``user``; never raises."""
    started = time.monotonic()
    if not settings.OPENAI_API_KEY:
        return _fail(user, 'missing_api_key', started)

    try:
        period_start, period_end = get_analysis_period()
        if not has_minimum_data(user, period_start, period_end):
            return _register_insufficient_data(user, period_start, period_end)

        context = AnalysisContext(
            user_id=user.pk,
            period_start=period_start,
            period_end=period_end,
        )
        agent = build_agent()
        result = agent.invoke(
            {
                'messages': [{
                    'role': 'user',
                    'content': build_user_message(period_start, period_end),
                }],
            },
            context=context,
            config={'recursion_limit': RECURSION_LIMIT},
        )
        analysis = _validate_analysis(result.get('structured_response'))
        input_tokens, output_tokens = _sum_usage(result.get('messages'))

        insight = FinancialInsight.objects.create(
            user=user,
            status=FinancialInsight.COMPLETED,
            summary=analysis.summary.strip(),
            insights=_items_to_json(analysis.insights),
            tips=_items_to_json(analysis.tips),
            period_start=period_start,
            period_end=period_end,
            model_name=settings.AI_MODEL_NAME[:50],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except openai.APITimeoutError as exc:
        return _fail(user, 'timeout', started, exc)
    except openai.RateLimitError as exc:
        return _fail(user, 'rate_limit', started, exc)
    except openai.APIError as exc:
        return _fail(user, 'api_error', started, exc)
    except (StructuredOutputError, InvalidAnalysisError) as exc:
        return _fail(user, 'invalid_output', started, exc)
    except GraphRecursionError as exc:
        return _fail(user, 'limit', started, exc)
    except Exception as exc:
        # No exception message or traceback by default: they may carry
        # financial values. The traceback is only kept in DEBUG level.
        logger.error(
            'ai.insight user_id=%s status=failed reason=unexpected '
            'error=%s duration=%.2fs',
            user.pk, type(exc).__name__, time.monotonic() - started,
            exc_info=logger.isEnabledFor(logging.DEBUG),
        )
        return GenerationResult(GenerationResult.FAILED)

    logger.info(
        'ai.insight user_id=%s status=completed duration=%.2fs '
        'input_tokens=%s output_tokens=%s',
        user.pk, time.monotonic() - started, input_tokens, output_tokens,
    )
    return GenerationResult(GenerationResult.COMPLETED, insight)
