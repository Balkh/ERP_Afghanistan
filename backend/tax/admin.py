from django.contrib import admin
from tax.models import (
    TaxCategory, TaxRate, TaxJurisdiction, TaxReturn, TaxTransaction
)


@admin.register(TaxCategory)
class TaxCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'default_rate', 'is_exempt', 'is_active']
    list_filter = ['is_exempt', 'is_active']
    search_fields = ['name', 'code']


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'rate_percentage', 'tax_type', 'effective_from', 'is_active']
    list_filter = ['tax_type', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['-effective_from']


@admin.register(TaxJurisdiction)
class TaxJurisdictionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'tax_rate', 'is_active']
    list_filter = ['is_active']


@admin.register(TaxReturn)
class TaxReturnAdmin(admin.ModelAdmin):
    list_display = ['period_start', 'period_end', 'status', 'net_tax', 'filing_date']
    list_filter = ['status']
    ordering = ['-period_end']


@admin.register(TaxTransaction)
class TaxTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'base_amount', 'tax_amount', 'transaction_date', 'is_reversed']
    list_filter = ['transaction_type', 'is_reversed']
    ordering = ['-transaction_date']