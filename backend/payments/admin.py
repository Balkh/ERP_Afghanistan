from django.contrib import admin
from payments.models import (
    PaymentMethod,
    PaymentAccount,
    FinancialTransaction,
    TransactionSettlement,
    SettlementTransaction,
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'method_type', 'is_active', 'is_default']
    list_filter = ['method_type', 'is_active', 'is_default']
    search_fields = ['name', 'code', 'provider_name']


@admin.register(PaymentAccount)
class PaymentAccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'account_type', 'currency', 'current_balance', 'is_active']
    list_filter = ['account_type', 'currency', 'is_active']
    search_fields = ['name', 'code', 'provider_name']


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_number', 'transaction_type', 'amount', 'currency',
        'status', 'transaction_date', 'is_settled'
    ]
    list_filter = ['transaction_type', 'status', 'payment_method', 'is_settled']
    search_fields = ['transaction_number', 'description', 'reference_number']
    date_hierarchy = 'transaction_date'


@admin.register(TransactionSettlement)
class TransactionSettlementAdmin(admin.ModelAdmin):
    list_display = [
        'settlement_number', 'settlement_type', 'status',
        'expected_amount', 'actual_amount', 'difference'
    ]
    list_filter = ['settlement_type', 'status']
    search_fields = ['settlement_number', 'description']


@admin.register(SettlementTransaction)
class SettlementTransactionAdmin(admin.ModelAdmin):
    list_display = ['settlement', 'transaction', 'included_amount']
