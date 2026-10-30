from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, Field


@dataclass
class AnalysisContext:
    """Execution context injected into the tools (never chosen by the LLM)."""

    user_id: int
    period_start: date
    period_end: date


class InsightItem(BaseModel):
    title: str = Field(description='Título curto, com até 80 caracteres.')
    description: str = Field(
        description='Explicação objetiva, com até 300 caracteres.'
    )


class FinancialAnalysis(BaseModel):
    summary: str = Field(
        description='Resumo do período em até 3 frases (até 500 caracteres).'
    )
    insights: list[InsightItem] = Field(min_length=2, max_length=5)
    tips: list[InsightItem] = Field(min_length=2, max_length=5)
