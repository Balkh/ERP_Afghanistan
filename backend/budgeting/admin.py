from django.contrib import admin
from budgeting.models import Budget, BudgetLine


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'fiscal_year', 'period_type', 'status', 'total_budgeted', 'total_actual']
    list_filter = ['status', 'period_type', 'fiscal_year']
    search_fields = ['name', 'notes']
    ordering = ['-fiscal_year', '-created_at']


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ['budget', 'account', 'period', 'budgeted_amount', 'actual_amount']
    list_filter = ['period', 'budget__fiscal_year']
    search_fields = ['account__code', 'account__name', 'budget__name']
    ordering = ['period', 'account__code']