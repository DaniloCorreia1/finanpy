from django.conf import settings
from django.db import models


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

    class Meta:
        verbose_name = 'conta'
        verbose_name_plural = 'contas'
        ordering = ['name']

    def __str__(self):
        return self.name

    def current_balance(self):
        # Sprint 6: somar entradas e subtrair saídas das transações com
        # aggregate(Sum(..., filter=Q(...))). Até lá, só o saldo inicial.
        return self.initial_balance
