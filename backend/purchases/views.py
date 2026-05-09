from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.multitenant.views import CompanyScopedViewSetMixin
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem, SupplierPayment
from purchases.serializers import (
    SupplierSerializer,
    SupplierPaymentSerializer,
    PurchaseInvoiceSerializer,
    PurchaseItemSerializer,
)
from inventory.service import StockIntegrationService
from inventory.models import Warehouse
from accounting.models import Account
from accounting.services.journal_engine import JournalEngine
from security.permissions import RoleBasedPermission


class PurchaseAccountingService:
    """Handles accounting journal entries for purchase operations."""

    AP_ACCOUNT_CODE = '2100'
    INVENTORY_ACCOUNT_CODE = '1300'
    TAX_ACCOUNT_CODE = '2110'
    CASH_ACCOUNT_CODE = '1010'

    @classmethod
    def create_purchase_journal_entry(cls, invoice: PurchaseInvoice) -> dict:
        """Create journal entry for a purchase invoice.
        
        Debit: Inventory/COGS (subtotal - tax)
        Debit: Tax Receivable (tax)
        Credit: Accounts Payable (total_amount)
        """
        expense_amount = invoice.subtotal - invoice.tax if invoice.tax > 0 else invoice.subtotal
        
        lines = [
            {
                'account_code': cls.INVENTORY_ACCOUNT_CODE,
                'debit': expense_amount,
                'credit': 0,
                'description': f'Purchase invoice {invoice.invoice_number} - {invoice.supplier.name}'
            },
        ]
        
        if invoice.tax > 0:
            lines.append({
                'account_code': cls.TAX_ACCOUNT_CODE,
                'debit': invoice.tax,
                'credit': 0,
                'description': f'Tax on purchase {invoice.invoice_number}'
            })
        
        lines.append({
            'account_code': cls.AP_ACCOUNT_CODE,
            'debit': 0,
            'credit': invoice.total_amount,
            'description': f'Payable for invoice {invoice.invoice_number}'
        })
        
        result = JournalEngine.create_entry(
            entry_type='PURCHASE',
            description=f'Purchase invoice {invoice.invoice_number} - {invoice.supplier.name}',
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
    def create_payment_journal_entry(cls, payment: SupplierPayment) -> dict:
        """Create journal entry for a supplier payment.
        
        Debit: Accounts Payable
        Credit: Cash/Bank
        """
        cash_account = cls._get_cash_account(payment.payment_method)
        
        lines = [
            {
                'account_code': cls.AP_ACCOUNT_CODE,
                'debit': payment.amount,
                'credit': 0,
                'description': f'AP reduction for payment to {payment.supplier.name} - Ref: {payment.reference_number or ""}'
            },
            {
                'account_code': cash_account,
                'debit': 0,
                'credit': payment.amount,
                'description': f'Payment to {payment.supplier.name}'
            },
        ]
        
        return JournalEngine.create_entry(
            entry_type='PAYMENT',
            description=f'Payment to {payment.supplier.name}',
            lines=lines,
            entry_date=payment.payment_date,
            reference=payment.reference_number or '',
            auto_post=True
        )

    @classmethod
    def reverse_purchase_journal_entry(cls, invoice: PurchaseInvoice, reason: str = '') -> dict:
        """Reverse the journal entry for a cancelled purchase invoice."""
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
        }
        return method_accounts.get(payment_method, cls.CASH_ACCOUNT_CODE)


class SupplierViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD API for Supplier management.
    """
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'city', 'country']
    search_fields = ['name', 'code', 'contact_person', 'email', 'phone']
    ordering_fields = ['name', 'code', 'balance', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = Supplier.objects.all()
        return queryset

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get supplier balance information."""
        supplier = self.get_object()
        return Response({
            'supplier_id': supplier.id,
            'supplier_name': supplier.name,
            'current_balance': supplier.balance,
            'credit_limit': supplier.credit_limit,
            'available_credit': supplier.available_credit,
            'is_over_credit_limit': supplier.is_over_credit_limit,
        })

    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """Get all invoices for a supplier."""
        supplier = self.get_object()
        invoices = supplier.purchase_invoices.all()
        serializer = PurchaseInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Get all payments for a supplier."""
        supplier = self.get_object()
        payments = supplier.payments.all()
        serializer = SupplierPaymentSerializer(payments, many=True)
        return Response(serializer.data)


class PurchaseInvoiceViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD API for Purchase Invoice management.
    """
    queryset = PurchaseInvoice.objects.filter(is_active=True)
    serializer_class = PurchaseInvoiceSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'supplier']
    search_fields = ['invoice_number', 'supplier__name', 'supplier__code']
    ordering_fields = ['order_date', 'invoice_date', 'total_amount', 'created_at']
    ordering = ['-order_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = PurchaseInvoice.objects.all()
        return queryset

    def perform_create(self, serializer):
        """Create invoice and update supplier balance."""
        invoice = serializer.save()
        self._update_supplier_balance(invoice)

    def perform_update(self, serializer):
        """Update invoice and adjust supplier balance."""
        old_total = serializer.instance.total_amount if serializer.instance else Decimal('0.00')
        invoice = serializer.save()
        self._update_supplier_balance(invoice, old_total)

    def perform_destroy(self, instance):
        """Soft delete invoice and adjust supplier balance."""
        old_total = instance.total_amount
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        self._adjust_supplier_balance(instance.supplier, -old_total)

    def _update_supplier_balance(self, invoice, old_total=None):
        """Update supplier balance when invoice is created/updated."""
        if old_total is not None:
            self._adjust_supplier_balance(invoice.supplier, -old_total)
        self._adjust_supplier_balance(invoice.supplier, invoice.total_amount)

    def _adjust_supplier_balance(self, supplier, amount):
        """Adjust supplier balance by the given amount."""
        with transaction.atomic():
            supplier.balance = supplier.balance + Decimal(amount)
            supplier.save(update_fields=['balance', 'updated_at'])

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
    def receive(self, request, pk=None):
        """Mark invoice as received and add stock."""
        invoice = self.get_object()
        if invoice.status not in ['CONFIRMED']:
            return Response(
                {'error': 'Only confirmed invoices can be received.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get warehouse from request or use default
        warehouse_id = request.data.get('warehouse_id')
        warehouse = None
        if warehouse_id:
            warehouse = Warehouse.objects.filter(id=warehouse_id).first()
        
        # Prepare items for stock processing
        items = []
        for item in invoice.items.all():
            items.append({
                'product': item.product,
                'quantity': item.quantity,
                'batch_number': item.batch_number,
                'expiry_date': item.expiry_date,
                'unit_price': item.unit_price,
                'manufacturing_date': getattr(item, 'manufacturing_date', None),
            })
        
        try:
            with transaction.atomic():
                # Process stock addition
                stock_result = StockIntegrationService.process_purchase(
                    invoice_id=invoice.id,
                    items=items,
                    warehouse=warehouse
                )
                
                if not stock_result.success:
                    return Response(
                        {
                            'error': 'Stock processing failed',
                            'details': stock_result.errors,
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                invoice.status = 'RECEIVED'
                invoice.save(update_fields=['status', 'updated_at'])
                
                # Create accounting journal entry
                accounting_result = PurchaseAccountingService.create_purchase_journal_entry(invoice)
                
                if not accounting_result.get('success'):
                    raise ValidationError(f"Accounting entry failed: {accounting_result.get('errors')}")

                serializer = self.get_serializer(invoice)
                
                response_data = {
                    'invoice': serializer.data,
                    'stock_movements': stock_result.movements,
                    'warnings': stock_result.warnings,
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
            return Response({'error': f"Unexpected error during receipt: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            reversal_result = PurchaseAccountingService.reverse_purchase_journal_entry(
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


class PurchaseItemViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Purchase Items.
    """
    queryset = PurchaseItem.objects.all()
    serializer_class = PurchaseItemSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['invoice', 'product']
    search_fields = ['product__name', 'batch_number']
    ordering_fields = ['quantity', 'unit_price', 'total', 'created_at']
    ordering = ['id']


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Supplier Payments.
    """
    queryset = SupplierPayment.objects.all()
    serializer_class = SupplierPaymentSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'invoice', 'payment_method']
    search_fields = ['supplier__name', 'reference_number']
    ordering_fields = ['amount', 'payment_date', 'created_at']
    ordering = ['-payment_date']

    def perform_create(self, serializer):
        """Create payment, update balances, and create journal entry."""
        payment = serializer.save()
        payment.update_supplier_balance()
        
        # Create accounting journal entry for the payment
        PurchaseAccountingService.create_payment_journal_entry(payment)
