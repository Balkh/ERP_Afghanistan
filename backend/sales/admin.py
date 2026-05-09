from django.contrib import admin
from sales.models import Customer, SalesInvoice, SalesItem, CustomerPayment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'customer_type', 'contact_person', 'email', 'phone', 'balance', 'credit_limit', 'is_active']
    list_filter = ['is_active', 'customer_type', 'city', 'country']
    search_fields = ['name', 'code', 'contact_person', 'email', 'phone']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    ordering = ['name']


class SalesItemInline(admin.TabularInline):
    model = SalesItem
    extra = 1
    readonly_fields = ['total', 'created_at', 'updated_at']


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer', 'order_date', 'invoice_date',
        'subtotal', 'discount', 'tax', 'total_amount',
        'paid_amount', 'status', 'payment_status', 'is_active'
    ]
    list_filter = ['status', 'payment_status', 'is_active']
    search_fields = ['invoice_number', 'customer__name', 'customer__code']
    readonly_fields = ['subtotal', 'total_amount', 'paid_amount', 'created_at', 'updated_at']
    inlines = [SalesItemInline]
    ordering = ['-order_date']


@admin.register(SalesItem)
class SalesItemAdmin(admin.ModelAdmin):
    list_display = [
        'invoice', 'product', 'batch', 'quantity', 'unit_price', 'discount', 'tax', 'total',
        'dispensed_quantity'
    ]
    list_filter = ['invoice__status']
    search_fields = ['product__name', 'batch__batch_number']
    readonly_fields = ['total', 'created_at', 'updated_at']


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'invoice', 'amount', 'payment_date',
        'payment_method', 'reference_number'
    ]
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['customer__name', 'reference_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-payment_date']
