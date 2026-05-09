from django.contrib import admin
from cost_centers.models import CostCenter, CostAllocation, CostAllocationLine, CostTransaction


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'cost_center_type', 'budget', 'is_active']
    list_filter = ['cost_center_type', 'is_active']
    search_fields = ['name', 'code']


@admin.register(CostAllocation)
class CostAllocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_cost_center', 'allocation_method', 'is_active']
    list_filter = ['allocation_method', 'is_active']


@admin.register(CostTransaction)
class CostTransactionAdmin(admin.ModelAdmin):
    list_display = ['cost_center', 'amount', 'transaction_date']
    list_filter = ['transaction_date']
    ordering = ['-transaction_date']