from django.conf import settings
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_openai import ChatOpenAI

from .prompts import SYSTEM_PROMPT
from .schemas import AnalysisContext, FinancialAnalysis
from .tools import FINANCIAL_TOOLS

MODEL_CALL_LIMIT = 8
TOOL_CALL_LIMIT = 10
# Each agent turn walks ~5 graph nodes (model, tools and the middleware
# hooks), so 8 model calls need ~40 steps. With 50 the ModelCallLimit
# middleware is what ends a runaway run; recursion_limit is only a backstop.
RECURSION_LIMIT = 50


def build_model():
    """Chat model used by the agent (key read only from settings/env)."""
    return ChatOpenAI(
        model=settings.AI_MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.AI_REQUEST_TIMEOUT,
        max_retries=2,
        max_completion_tokens=settings.AI_MAX_COMPLETION_TOKENS,
        reasoning_effort='low',
    )


def build_agent():
    """Financial agent: read-only tools, structured output and limits.

    ``response_format=FinancialAnalysis`` lets LangChain pick the provider's
    native structured output (``ProviderStrategy``) when the model supports
    it and fall back to ``ToolStrategy`` otherwise.
    """
    return create_agent(
        model=build_model(),
        tools=FINANCIAL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=FinancialAnalysis,
        context_schema=AnalysisContext,
        middleware=[
            ModelCallLimitMiddleware(
                run_limit=MODEL_CALL_LIMIT, exit_behavior='end'
            ),
            ToolCallLimitMiddleware(
                run_limit=TOOL_CALL_LIMIT, exit_behavior='continue'
            ),
        ],
    )
