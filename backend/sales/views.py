from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.multitenant.views import CompanyScopedViewSetMixin
from sales.models import Customer, SalesInvoice, SalesItem, CustomerPayment
from sales.serializers import (
    CustomerSerializer,
    CustomerPaymentSerializer,
    SalesInvoiceSerializer,
    SalesItemSerializer,
)
from inventory.service import StockIntegrationService, StockSelectionMode
from inventory.models import Warehouse
from accounting.models import Account
from accounting.services.journal_engine import JournalEngine
from security.permissions import RoleBasedPermission


class SalesAccountingService:
    """Handles accounting journal entries for sales operations."""

    AR_ACCOUNT_CODE = '1200'
    REVENUE_ACCOUNT_CODE = '4100'
    TAX_ACCOUNT_CODE = '2100'
    CASH_ACCOUNT_CODE = '1010'
    COGS_ACCOUNT_CODE = '5100'
    INVENTORY_ACCOUNT_CODE = '1300'

    @classmethod
    def calculate_cogs(cls, invoice: SalesInvoice, allocations: list) -> Decimal:
        """Calculate Cost of Goods Sold from stock allocations.
        
        Uses actual batch unit costs from FIFO/FEFO selection.
        This ensures COGS reflects true cost, not average or std cost.
        """
        from decimal import Decimal
        
        total_cogs = Decimal('0.00')
        
        for item in invoice.items.all():
            item_quantity = item.quantity
            item_cost = Decimal('0.00')
            
            matching_allocations = [
                a for a in allocations 
                if str(a.product_id) == str(item.product_id)
            ]
            
            if matching_allocations:
                total_allocated = sum(a.quantity for a in matching_allocations)
                for alloc in matching_allocations:
                    if alloc.unit_cost is not None:
                        proportion = alloc.quantity / total_allocated if total_allocated > 0 else 0
                        item_cost += (item_quantity * proportion) * alloc.unit_cost
            else:
                if item.batch and item.batch.purchase_price:
                    item_cost = item_quantity * item.batch.purchase_price
            
            total_cogs += item_cost
        
        return total_cogs.quantize(Decimal('0.01'))

    @classmethod
    def create_sales_journal_entry(cls, invoice: SalesInvoice, allocations: list = None) -> dict:
        """Create journal entry for a sales invoice.
        
        Debit: Accounts Receivable (total_amount)
        Debit: COGS (cost of goods sold) - if allocations provided
        Credit: Sales Revenue (subtotal - tax)
        Credit: Tax Payable (tax)
        Credit: Inventory (1300) - if COGS calculated
        """
        revenue_amount = invoice.subtotal - invoice.tax if invoice.tax > 0 else invoice.subtotal
        
        lines = [
            {
                'account_code': cls.AR_ACCOUNT_CODE,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f'Sale invoice {invoice.invoice_number} - {invoice.customer.name}'
            },
        ]
        
        if allocations:
            cogs_amount = cls.calculate_cogs(invoice, allocations)
            if cogs_amount > 0:
                lines.append({
                    'account_code': cls.COGS_ACCOUNT_CODE,
                    'debit': cogs_amount,
                    'credit': 0,
                    'description': f'COGS for invoice {invoice.invoice_number}'
                })
        
        lines.append({
            'account_code': cls.REVENUE_ACCOUNT_CODE,
            'debit': 0,
            'credit': revenue_amount,
            'description': f'Revenue from invoice {invoice.invoice_number}'
        })
        
        if invoice.tax > 0:
            lines.append({
                'account_code': cls.TAX_ACCOUNT_CODE,
                'debit': 0,
                'credit': invoice.tax,
                'description': f'Tax on invoice {invoice.invoice_number}'
            })
        
        if allocations:
            cogs_amount = cls.calculate_cogs(invoice, allocations)
            if cogs_amount > 0:
                lines.append({
                    'account_code': cls.INVENTORY_ACCOUNT_CODE,
                    'debit': 0,
                    'credit': cogs_amount,
                    'description': f'Inventory reduction for invoice {invoice.invoice_number}'
                })
        
        result = JournalEngine.create_entry(
            entry_type='SALE',
            description=f'Sales invoice {invoice.invoice_number} - {invoice.customer.name}',
            lines=lines,
            entry_date=invoice.invoice_date,
            reference=invoice.invoice_number,
            auto_post=True
        )
        
        if result.get('success'):
            invoice.journal_entry_id = result.get('entry_id')
            invoice.save(update_fields=['journal_entry_id', 'updated_at'])
        
        return result

    @classmethod
    def create_receipt_journal_entry(cls, payment: CustomerPayment) -> dict:
        """Create journal entry for a customer payment.
        
        Debit: Cash/Bank
        Credit: Accounts Receivable
        """
        cash_account = cls._get_cash_account(payment.payment_method)
        
        lines = [
            {
                'account_code': cash_account,
                'debit': payment.amount,
                'credit': 0,
                'description': f'Payment received from {payment.customer.name} - Ref: {payment.reference_number or ""}'
            },
            {
                'account_code': cls.AR_ACCOUNT_CODE,
                'debit': 0,
                'credit': payment.amount,
                'description': f'AR reduction for payment from {payment.customer.name}'
            },
        ]
        
        return JournalEngine.create_entry(
            entry_type='RECEIPT',
            description=f'Payment received from {payment.customer.name}',
            lines=lines,
            entry_date=payment.payment_date,
            reference=payment.reference_number or '',
            auto_post=True
        )

    @classmethod
    def reverse_sales_journal_entry(cls, invoice: SalesInvoice, reason: str = '') -> dict:
        """Reverse the journal entry for a cancelled invoice."""
        if not invoice.journal_entry_id:
            return {'success': False, 'errors': ['No journal entry to reverse']}
        
        result = JournalEngine.reverse_entry(
            entry_id=invoice.journal_entry_id,
            reason=reason or f'Invoice {invoice.invoice_number} cancelled'
        )
        
        if result.get('success'):
            invoice.journal_entry_id = None
            invoice.save(update_fields=['journal_entry_id', 'updated_at'])
        
        return result

    @classmethod
    def _get_cash_account(cls, payment_method: str) -> str:
        """Get appropriate cash account code based on payment method."""
        method_accounts = {
            'CASH': cls.CASH_ACCOUNT_CODE,
            'BANK_TRANSFER': '1020',
            'CHEQUE': '1030',
            'CREDIT_CARD': '1040',
            'INSURANCE': '1210',
        }
        return method_accounts.get(payment_method, cls.CASH_ACCOUNT_CODE)


class CustomerViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD API for Customer management.
    """
    queryset = Customer.objects.filter(is_active=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'customer_type', 'city', 'country']
    search_fields = ['name', 'code', 'contact_person', 'email', 'phone']
    ordering_fields = ['name', 'code', 'balance', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Use GET parameters (compatible with both Django and DRF Request)
        include_inactive = self.request.GET.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = Customer.objects.all()
        return queryset

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get customer balance and debt information."""
        customer = self.get_object()
        return Response({
            'customer_id': customer.id,
            'customer_name': customer.name,
            'current_balance': customer.balance,
            'total_debt': customer.total_debt,
            'credit_limit': customer.credit_limit,
            'available_credit': customer.available_credit,
            'is_over_credit_limit': customer.is_over_credit_limit,
        })

    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """Get all invoices for a customer."""
        customer = self.get_object()
        invoices = customer.sales_invoices.all()
        serializer = SalesInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get all payments for a customer."""
        customer = self.get_object()
        payments = customer.payments.all()
        serializer = CustomerPaymentSerializer(payments, many=True)
        return Response(serializer.data)


class SalesInvoiceViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD API for Sales Invoice management.
    """
    queryset = SalesInvoice.objects.filter(is_active=True)
    serializer_class = SalesInvoiceSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'customer']
    search_fields = ['invoice_number', 'customer__name', 'customer__code']
    ordering_fields = ['order_date', 'invoice_date', 'total_amount', 'created_at']
    ordering = ['-order_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Use GET parameters (compatible with both Django and DRF Request)
        include_inactive = self.request.GET.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = SalesInvoice.objects.all()
        return queryset

    def perform_create(self, serializer):
        """Create invoice and update customer balance."""
        invoice = serializer.save()
        self._update_customer_balance(invoice)

    def perform_update(self, serializer):
        """Update invoice and adjust customer balance."""
        old_total = serializer.instance.total_amount if serializer.instance else Decimal('0.00')
        invoice = serializer.save()
        self._update_customer_balance(invoice, old_total)

    def perform_destroy(self, instance):
        """Soft delete invoice and adjust customer balance."""
        old_total = instance.total_amount
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        self._adjust_customer_balance(instance.customer, -old_total)

    def _update_customer_balance(self, invoice, old_total=None):
        """Update customer balance when invoice is created/updated."""
        if old_total is not None:
            self._adjust_customer_balance(invoice.customer, -old_total)
        self._adjust_customer_balance(invoice.customer, invoice.total_amount)

    def _adjust_customer_balance(self, customer, amount):
        """Adjust customer balance by the given amount."""
        with transaction.atomic():
            customer.balance = customer.balance + Decimal(amount)
            customer.save(update_fields=['balance', 'updated_at'])

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a draft invoice."""
        invoice = self.get_object()
        if invoice.status != 'DRAFT':
            return Response(
                {'error': 'Only draft invoices can be confirmed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        invoice.status = 'CONFIRMED'
        invoice.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def dispatch_invoice(self, request, pk=None):
        """Mark invoice as dispatched and deduct stock."""
        invoice = self.get_object()
        if invoice.status not in ['CONFIRMED']:
            return Response(
                {'error': 'Only confirmed invoices can be dispatched.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get warehouse from request or use default
        warehouse_id = request.data.get('warehouse_id')
        warehouse = None
        if warehouse_id:
            warehouse = Warehouse.objects.filter(id=warehouse_id).first()
        
        # Get selection mode
        selection_mode = StockSelectionMode(request.data.get('selection_mode', 'FEFO'))
        
        # Prepare items for stock processing
        items = []
        for item in invoice.items.all():
            items.append({
                'product': item.product,
                'quantity': item.quantity,
                'batch_id': item.batch.id if item.batch else None,
            })
        
        try:
            with transaction.atomic():
                # Process stock deduction
                stock_result = StockIntegrationService.process_sale(
                    invoice_id=invoice.id,
                    items=items,
                    warehouse=warehouse,
                    selection_mode=selection_mode
                )
                
                if not stock_result.success:
                    return Response(
                        {
                            'error': 'Stock processing failed',
                            'details': stock_result.errors,
                            'shortages': stock_result.stock_shortages,
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                invoice.status = 'DISPATCHED'
                invoice.save(update_fields=['status', 'updated_at'])
                
                # Create accounting journal entry (with allocations for COGS calculation)
                accounting_result = SalesAccountingService.create_sales_journal_entry(
                    invoice, allocations=stock_result.allocations
                )
                
                if not accounting_result.get('success'):
                    # Raise exception to rollback transaction if accounting fails
                    raise ValidationError(f"Accounting entry failed: {accounting_result.get('errors')}")

                serializer = self.get_serializer(invoice)
                
                response_data = {
                    'invoice': serializer.data,
                    'stock_movements': stock_result.movements,
                    'allocations': [
                        {
                            'batch_id': str(a.batch_id),
                            'batch_number': a.batch_number,
                            'quantity': a.quantity,
                            'expiry_date': a.expiry_date.isoformat() if a.expiry_date else None,
                        }
                        for a in stock_result.allocations
                    ],
                    'journal_entry': {
                        'entry_number': accounting_result.get('entry_number'),
                        'total_debit': str(accounting_result.get('total_debit')),
                        'total_credit': str(accounting_result.get('total_credit')),
                    }
                }
                
                return Response(response_data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Unexpected error during dispatch: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an invoice."""
        invoice = self.get_object()
        if invoice.status == 'PAID':
            return Response(
                {'error': 'Cannot cancel a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reverse accounting journal entry if exists
        if invoice.journal_entry_id:
            reversal_result = SalesAccountingService.reverse_sales_journal_entry(
                invoice,
                reason=f'Invoice {invoice.invoice_number} cancelled'
            )
            if not reversal_result.get('success'):
                return Response(
                    {'error': 'Failed to reverse accounting entry', 'details': reversal_result.get('errors')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        invoice.status = 'CANCELLED'
        invoice.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class SalesItemViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Sales Items.
    """
    queryset = SalesItem.objects.all()
    serializer_class = SalesItemSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['invoice', 'product', 'batch']
    search_fields = ['product__name', 'batch__batch_number']
    ordering_fields = ['quantity', 'unit_price', 'total', 'created_at']
    ordering = ['id']


class CustomerPaymentViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Customer Payments.
    """
    queryset = CustomerPayment.objects.all()
    serializer_class = CustomerPaymentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'invoice', 'payment_method']
    search_fields = ['customer__name', 'reference_number']
    ordering_fields = ['amount', 'payment_date', 'created_at']
    ordering = ['-payment_date']

    def perform_create(self, serializer):
        """Create payment, update balances, and create journal entry."""
        payment = serializer.save()
        payment.update_customer_balance()
        
        # Create accounting journal entry for the payment
        SalesAccountingService.create_receipt_journal_entry(payment)
