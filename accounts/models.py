from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from categories.models import Category


class AccountQuerySet(models.QuerySet):
    def with_balance(self):
        """Anota `balance`: saldo inicial + entradas - saídas."""
        money = DecimalField(max_digits=12, decimal_places=2)
        zero = Value(Decimal('0'), output_field=money)
        income = Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(transactions__transaction_type=Category.INCOME),
            ),
            zero,
            output_field=money,
        )
        expense = Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(transactions__transaction_type=Category.EXPENSE),
            ),
            zero,
            output_field=money,
        )
        return self.annotate(
            balance=F('initial_balance') + income - expense
        )


class Account(models.Model):
    CHECKING = 'checking'
    SAVINGS = 'savings'
    WALLET = 'wallet'
    INVESTMENT = 'investment'
    TYPE_CHOICES = [
        (CHECKING, 'Conta corrente'),
        (SAVINGS, 'Poupança'),
        (WALLET, 'Carteira'),
        (INVESTMENT, 'Investimento'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=100)
    bank = models.CharField('banco', max_length=100, blank=True)
    account_type = models.CharField(
        'tipo', max_length=20, choices=TYPE_CHOICES
    )
    initial_balance = models.DecimalField(
        'saldo inicial', max_digits=12, decimal_places=2, default=0
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    objects = AccountQuerySet.as_manager()

    class Meta:
        verbose_name = 'conta'
        verbose_name_plural = 'contas'
        ordering = ['name']

    def __str__(self):
        return self.name

    def current_balance(self):
        totals = self.transactions.aggregate(
            income=Sum('amount', filter=Q(transaction_type=Category.INCOME)),
            expense=Sum(
                'amount', filter=Q(transaction_type=Category.EXPENSE)
            ),
        )
        income = totals['income'] or Decimal('0')
        expense = totals['expense'] or Decimal('0')
        return self.initial_balance + income - expense
