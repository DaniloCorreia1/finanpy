"""Read-only tools used by the financial agent.

Every query starts by filtering on ``runtime.context.user_id``: the user is
injected by the execution context and is never an argument chosen by the
model. Dates informed by the model are limited to the analysis window, and
only aggregates, category names, account types, dates and amounts are
returned (no descriptions, account names or banks).
"""
from collections import OrderedDict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from langchain.tools import ToolRuntime, tool

from accounts.models import Account
from transactions.models import Transaction

from .schemas import AnalysisContext

CATEGORY_LIMIT = 10
TOP_EXPENSES_DEFAULT = 5
TOP_EXPENSES_MAX = 10

CENTS = Decimal('0.01')
TENTHS = Decimal('0.1')


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def clamp_period(context, start_date=None, end_date=None):
    """Limit the dates informed by the model to the context window.

    Missing, invalid or inverted dates fall back to the whole window.
    """
    window_start = context.period_start
    window_end = context.period_end
    start = _parse_date(start_date) or window_start
    end = _parse_date(end_date) or window_end
    start = min(max(start, window_start), window_end)
    end = min(max(end, window_start), window_end)
    if start > end:
        return window_start, window_end
    return start, end


def money(value):
    """Serialize a monetary value as text with two decimal places."""
    if value is None:
        value = Decimal('0')
    return str(Decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP))


def percent(part, whole):
    """Return ``part / whole`` in % as text with one decimal place."""
    if not whole:
        return None
    value = Decimal(part) * 100 / Decimal(whole)
    return str(value.quantize(TENTHS, rounding=ROUND_HALF_UP))


def _user_transactions(runtime):
    return Transaction.objects.filter(user_id=runtime.context.user_id)


@tool
def get_financial_summary(
    runtime: ToolRuntime[AnalysisContext],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Totais de entradas e saídas, resultado, quantidade de transações e
    taxa de poupança (%) no intervalo.

    Args:
        start_date: Data inicial opcional (YYYY-MM-DD), dentro do período.
        end_date: Data final opcional (YYYY-MM-DD), dentro do período.
    """
    start, end = clamp_period(runtime.context, start_date, end_date)
    totals = _user_transactions(runtime).filter(
        date__range=(start, end)
    ).aggregate(
        income=Sum('amount', filter=Q(transaction_type=Transaction.INCOME)),
        expense=Sum('amount', filter=Q(transaction_type=Transaction.EXPENSE)),
        count=Count('id'),
    )
    income = totals['income'] or Decimal('0')
    expense = totals['expense'] or Decimal('0')
    result = income - expense
    return {
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'total_income': money(income),
        'total_expense': money(expense),
        'result': money(result),
        'transaction_count': totals['count'],
        'savings_rate': percent(result, income),
    }


@tool
def get_spending_by_category(
    runtime: ToolRuntime[AnalysisContext],
    transaction_type: str = Transaction.EXPENSE,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list:
    """Totais por categoria (até 10, do maior para o menor), com a
    participação (%) no total do tipo e a quantidade de transações.

    Args:
        transaction_type: 'expense' (saídas, padrão) ou 'income' (entradas).
        start_date: Data inicial opcional (YYYY-MM-DD), dentro do período.
        end_date: Data final opcional (YYYY-MM-DD), dentro do período.
    """
    if transaction_type not in (Transaction.INCOME, Transaction.EXPENSE):
        transaction_type = Transaction.EXPENSE
    start, end = clamp_period(runtime.context, start_date, end_date)
    queryset = _user_transactions(runtime).filter(
        transaction_type=transaction_type, date__range=(start, end)
    )
    grand_total = queryset.aggregate(total=Sum('amount'))['total']
    rows = (
        queryset.order_by()
        .values('category__name')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total', 'category__name')[:CATEGORY_LIMIT]
    )
    return [
        {
            'category': row['category__name'],
            'total': money(row['total']),
            'share_percent': percent(row['total'], grand_total),
            'count': row['count'],
        }
        for row in rows
    ]


@tool
def get_top_expenses(
    runtime: ToolRuntime[AnalysisContext],
    limit: int = TOP_EXPENSES_DEFAULT,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list:
    """Maiores saídas individuais do intervalo (data, categoria e valor).

    Args:
        limit: Quantidade de saídas, de 1 a 10 (padrão 5).
        start_date: Data inicial opcional (YYYY-MM-DD), dentro do período.
        end_date: Data final opcional (YYYY-MM-DD), dentro do período.
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = TOP_EXPENSES_DEFAULT
    limit = min(max(limit, 1), TOP_EXPENSES_MAX)
    start, end = clamp_period(runtime.context, start_date, end_date)
    expenses = (
        _user_transactions(runtime)
        .filter(
            transaction_type=Transaction.EXPENSE, date__range=(start, end)
        )
        .select_related('category')
        .order_by('-amount', '-date')[:limit]
    )
    return [
        {
            'date': expense.date.isoformat(),
            'category': expense.category.name,
            'amount': money(expense.amount),
        }
        for expense in expenses
    ]


@tool
def get_monthly_evolution(runtime: ToolRuntime[AnalysisContext]) -> list:
    """Entradas, saídas e resultado de cada mês do período. O mês corrente
    vem com is_partial = true, pois pode estar incompleto."""
    context = runtime.context
    start, end = context.period_start, context.period_end

    months = OrderedDict()
    cursor = start.replace(day=1)
    while cursor <= end:
        months[(cursor.year, cursor.month)] = {
            'income': Decimal('0'), 'expense': Decimal('0'),
        }
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    rows = (
        _user_transactions(runtime)
        .filter(date__range=(start, end))
        .order_by()
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            income=Sum(
                'amount', filter=Q(transaction_type=Transaction.INCOME)
            ),
            expense=Sum(
                'amount', filter=Q(transaction_type=Transaction.EXPENSE)
            ),
        )
    )
    for row in rows:
        key = (row['month'].year, row['month'].month)
        if key in months:
            months[key]['income'] = row['income'] or Decimal('0')
            months[key]['expense'] = row['expense'] or Decimal('0')

    current = (end.year, end.month)
    return [
        {
            'month': f'{year:04d}-{month:02d}',
            'income': money(values['income']),
            'expense': money(values['expense']),
            'result': money(values['income'] - values['expense']),
            'is_partial': (year, month) == current,
        }
        for (year, month), values in months.items()
    ]


@tool
def get_accounts_overview(runtime: ToolRuntime[AnalysisContext]) -> dict:
    """Saldo atual total e saldos agrupados por tipo de conta (sem nomes de
    contas ou bancos)."""
    accounts = Account.objects.filter(
        user_id=runtime.context.user_id
    ).with_balance()
    groups = OrderedDict()
    total = Decimal('0')
    for account in accounts:
        label = account.get_account_type_display()
        group = groups.setdefault(
            label, {'accounts': 0, 'balance': Decimal('0')}
        )
        group['accounts'] += 1
        group['balance'] += account.balance
        total += account.balance
    return {
        'total_balance': money(total),
        'by_account_type': [
            {
                'account_type': label,
                'accounts': group['accounts'],
                'balance': money(group['balance']),
            }
            for label, group in groups.items()
        ],
    }


FINANCIAL_TOOLS = [
    get_financial_summary,
    get_spending_by_category,
    get_top_expenses,
    get_monthly_evolution,
    get_accounts_overview,
]
