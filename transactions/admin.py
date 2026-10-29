from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'description', 'transaction_type', 'amount', 'date', 'account',
        'category', 'user',
    ]
    list_filter = ['transaction_type', 'date']
    search_fields = ['description']
    list_select_related = ['account', 'category', 'user']
