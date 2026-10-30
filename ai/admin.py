from django.contrib import admin

from .models import FinancialInsight


@admin.register(FinancialInsight)
class FinancialInsightAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'status', 'period_start', 'period_end', 'model_name',
        'input_tokens', 'output_tokens', 'created_at',
    ]
    list_filter = ['status', 'model_name']
    search_fields = ['user__email']
    readonly_fields = [
        'user', 'status', 'summary', 'insights', 'tips', 'period_start',
        'period_end', 'model_name', 'input_tokens', 'output_tokens',
        'created_at', 'updated_at',
    ]

    def has_add_permission(self, request):
        # Analyses are created only by the AI service (history is preserved).
        return False

    def has_change_permission(self, request, obj=None):
        return False
