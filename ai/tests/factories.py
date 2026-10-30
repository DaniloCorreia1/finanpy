import datetime
import logging
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from langchain.tools import ToolRuntime

from accounts.models import Account
from categories.models import Category
from transactions.models import Transaction

from ..schemas import AnalysisContext, FinancialAnalysis, InsightItem

User = get_user_model()

PERIOD_START = datetime.date(2026, 8, 1)
PERIOD_END = datetime.date(2026, 10, 29)


def create_user(email, **kwargs):
    return User.objects.create_user(
        email=email, password='senha-forte-123', **kwargs
    )


def create_account(user, name='Conta Corrente', account_type=None,
                   initial_balance='100.00', bank='Banco Secreto'):
    return Account.objects.create(
        user=user,
        name=name,
        bank=bank,
        account_type=account_type or Account.CHECKING,
        initial_balance=Decimal(initial_balance),
    )


def create_category(user, name, category_type=Category.EXPENSE):
    return Category.objects.create(
        user=user, name=name, category_type=category_type
    )


def create_transaction(user, account, category, amount, date,
                       description='Descrição sigilosa'):
    return Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        transaction_type=category.category_type,
        description=description,
        amount=Decimal(amount),
        date=date,
    )


def make_runtime(user_id, period_start=PERIOD_START, period_end=PERIOD_END):
    """Fake ``ToolRuntime`` holding only the ``AnalysisContext``."""
    return ToolRuntime(
        state={},
        context=AnalysisContext(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        ),
        config={},
        stream_writer=lambda chunk: None,
        tool_call_id='test-call',
        store=None,
    )


def make_analysis(insights=2, tips=2, summary='Você gastou menos.'):
    return FinancialAnalysis(
        summary=summary,
        insights=[
            InsightItem(title=f'Insight {i}', description=f'Detalhe {i}')
            for i in range(insights)
        ],
        tips=[
            InsightItem(title=f'Dica {i}', description=f'Detalhe {i}')
            for i in range(tips)
        ],
    )


class QuietAiLogsMixin:
    """Keep the ``ai`` console logs out of the test output.

    ``assertLogs`` still works, since it installs its own handler.
    """

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(
            logging.getLogger('ai'), 'handlers', [logging.NullHandler()]
        )
        patcher.start()
        self.addCleanup(patcher.stop)
