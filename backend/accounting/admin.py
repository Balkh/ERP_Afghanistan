from django.contrib import admin
from accounting.models import Currency, ExchangeRate, PaymentTransaction, Account, JournalEntry, JournalEntryLine


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 1
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'account_category', 'parent', 'balance', 'is_active', 'is_system']
    list_filter = ['account_type', 'account_category', 'is_active', 'is_system']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    ordering = ['code']
    list_editable = ['is_active']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'entry_date', 'entry_type', 'total_debit', 'total_credit', 'is_posted', 'is_active']
    list_filter = ['entry_type', 'is_posted', 'is_active', 'entry_date']
    search_fields = ['entry_number', 'description', 'reference']
    readonly_fields = ['total_debit', 'total_credit', 'is_balanced', 'created_at', 'updated_at']
    inlines = [JournalEntryLineInline]
    ordering = ['-entry_date']
    date_hierarchy = 'entry_date'


@admin.register(JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
    list_display = ['entry', 'account', 'debit', 'credit', 'description']
    list_filter = ['entry__entry_type', 'account__account_type']
    search_fields = ['account__name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'is_active', 'is_default', 'created_at']
    list_filter = ['is_active', 'is_default']
    search_fields = ['code', 'name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['code']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['from_currency', 'to_currency', 'rate', 'effective_date', 'source', 'is_active']
    list_filter = ['is_active', 'effective_date', 'source']
    search_fields = ['from_currency__code', 'to_currency__code']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-effective_date']
    date_hierarchy = 'effective_date'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'payment_date', 'payment_method', 'transaction_type',
        'amount', 'currency', 'amount_in_base', 'reference_number'
    ]
    list_filter = ['payment_method', 'transaction_type', 'payment_date', 'currency']
    search_fields = ['reference_number', 'notes']
    readonly_fields = ['amount_in_base', 'created_at', 'updated_at']
    ordering = ['-payment_date']
    date_hierarchy = 'payment_date'
