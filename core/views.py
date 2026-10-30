from decimal import Decimal

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import Account
from ai.services import get_latest_insight
from transactions.models import Transaction


class LandingPageView(TemplateView):
    template_name = 'core/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    recent_transactions_limit = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        accounts = list(Account.objects.filter(user=user).with_balance())
        total_balance = sum(
            (account.balance for account in accounts), Decimal('0')
        )

        month_totals = Transaction.objects.filter(
            user=user,
            date__year=today.year,
            date__month=today.month,
        ).aggregate(
            income=Sum(
                'amount', filter=Q(transaction_type=Transaction.INCOME)
            ),
            expense=Sum(
                'amount', filter=Q(transaction_type=Transaction.EXPENSE)
            ),
        )
        month_income = month_totals['income'] or Decimal('0')
        month_expense = month_totals['expense'] or Decimal('0')

        recent_transactions = list(
            Transaction.objects.filter(user=user).select_related(
                'account', 'category'
            )[:self.recent_transactions_limit]
        )

        context.update({
            'today': today,
            'accounts': accounts,
            'total_balance': total_balance,
            'month_income': month_income,
            'month_expense': month_expense,
            'month_result': month_income - month_expense,
            'recent_transactions': recent_transactions,
            'latest_insight': get_latest_insight(user),
            'ai_enabled': bool(settings.OPENAI_API_KEY),
        })
        return context
