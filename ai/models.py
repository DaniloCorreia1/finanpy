from django.conf import settings
from django.db import models
from django.utils import timezone


class FinancialInsight(models.Model):
    COMPLETED = 'completed'
    INSUFFICIENT_DATA = 'insufficient_data'
    STATUS_CHOICES = [
        (COMPLETED, 'Concluída'),
        (INSUFFICIENT_DATA, 'Dados insuficientes'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='financial_insights',
        verbose_name='usuário',
    )
    status = models.CharField(
        'status', max_length=20, choices=STATUS_CHOICES
    )
    summary = models.TextField('resumo')
    insights = models.JSONField('insights', default=list)
    tips = models.JSONField('dicas', default=list)
    period_start = models.DateField('início do período')
    period_end = models.DateField('fim do período')
    model_name = models.CharField('modelo', max_length=50, blank=True)
    input_tokens = models.PositiveIntegerField(
        'tokens de entrada', null=True, blank=True
    )
    output_tokens = models.PositiveIntegerField(
        'tokens de saída', null=True, blank=True
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'análise financeira'
        verbose_name_plural = 'análises financeiras'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['user', '-created_at'],
                name='ai_insight_user_created_idx',
            ),
        ]

    def __str__(self):
        created_at = timezone.localtime(self.created_at)
        return f'Análise de {self.user} em {created_at:%d/%m/%Y}'
