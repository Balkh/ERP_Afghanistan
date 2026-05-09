from django.contrib import admin
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem, SupplierPayment


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact_person', 'email', 'phone', 'balance', 'credit_limit', 'is_active']
    list_filter = ['is_active', 'city', 'country']
    search_fields = ['name', 'code', 'contact_person', 'email', 'phone']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    ordering = ['name']


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ['total', 'created_at', 'updated_at']


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'supplier', 'order_date', 'invoice_date',
        'subtotal', 'discount', 'tax', 'total_amount',
        'paid_amount', 'status', 'payment_status', 'is_active'
    ]
    list_filter = ['status', 'payment_status', 'is_active']
    search_fields = ['invoice_number', 'supplier__name', 'supplier__code']
    readonly_fields = ['subtotal', 'total_amount', 'paid_amount', 'created_at', 'updated_at']
    inlines = [PurchaseItemInline]
    ordering = ['-order_date']


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = [
        'invoice', 'product', 'batch_number', 'expiry_date',
        'quantity', 'unit_price', 'discount', 'tax', 'total',
        'received_quantity'
    ]
    list_filter = ['invoice__status']
    search_fields = ['product__name', 'batch_number']
    readonly_fields = ['total', 'created_at', 'updated_at']


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'supplier', 'invoice', 'amount', 'payment_date',
        'payment_method', 'reference_number'
    ]
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['supplier__name', 'reference_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-payment_date']
