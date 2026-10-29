from django.conf import settings
from django.db import models


class Category(models.Model):
    INCOME = 'income'
    EXPENSE = 'expense'
    TYPE_CHOICES = [
        (INCOME, 'Entrada'),
        (EXPENSE, 'Saída'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=60)
    category_type = models.CharField(
        'tipo', max_length=10, choices=TYPE_CHOICES
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'
        ordering = ['category_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name', 'category_type'],
                name='unique_category_per_user_and_type',
            ),
        ]

    def __str__(self):
        return self.name
