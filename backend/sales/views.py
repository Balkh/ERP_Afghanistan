from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.multitenant.views import UnifiedEnterpriseViewSetMixin
from core.view_logging import log_business_event
from core.balance_sync import BalanceSyncService
from core.services.financial_integrity import FinancialIntegrityService
from sales.services.fifo_allocation import FIFOAllocationService
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
    def create_sales_journal_entry(cls, invoice: SalesInvoice, allocations: list = None, cogs_override: Decimal = None) -> dict:
        """Create journal entry for a sales invoice.

        Debit: Accounts Receivable (total_amount)
        Debit: COGS (cost of goods sold) - if allocations provided
        Credit: Sales Revenue (subtotal - tax)
        Credit: Tax Payable (tax)
        Credit: Inventory (1300) - if COGS calculated
        """
        revenue_amount = invoice.subtotal - invoice.discount

        lines = [
            {
                'account_code': cls.AR_ACCOUNT_CODE,
                'debit': invoice.total_amount,
                'credit': 0,
                'description': f'Sale invoice {invoice.invoice_number} - {invoice.customer.name}'
            },
        ]

        # Calculate COGS once (either from override or allocations)
        cogs_amount = Decimal('0.00')
        if allocations:
            if cogs_override is not None:
                cogs_amount = cogs_override.quantize(Decimal('0.01'))
            else:
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

        if cogs_amount > 0:
            lines.append({
                'account_code': cls.INVENTORY_ACCOUNT_CODE,
                'debit': 0,
                'credit': cogs_amount,
                'description': f'Inventory reduction for invoice {invoice.invoice_number}'
            })

        from core.drift_prevention.migration_router import MigrationRouter
        result = MigrationRouter.create_entry(
            module='sales',
            operation='create_entry',
            entry_type='SALE',
            description=f'Sales invoice {invoice.invoice_number} - {invoice.customer.name}',
            lines=lines,
            entry_date=invoice.invoice_date,
            reference=invoice.invoice_number,
            auto_post=True,
            entity_type='SalesInvoice',
            entity_id=str(invoice.id),
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
        
        from core.drift_prevention.migration_router import MigrationRouter
        result = MigrationRouter.create_entry(
            module='sales',
            operation='create_entry',
            entry_type='RECEIPT',
            description=f'Payment received from {payment.customer.name}',
            lines=lines,
            entry_date=payment.payment_date,
            reference=payment.reference_number or '',
            auto_post=True,
            entity_type='CustomerPayment',
            entity_id=str(payment.id),
        )

        return result

    @classmethod
    def reverse_sales_journal_entry(cls, invoice: SalesInvoice, reason: str = '') -> dict:
        """Reverse the journal entry for a cancelled invoice."""
        if not invoice.journal_entry_id:
            return {'success': False, 'errors': ['No journal entry to reverse']}
        
        from core.drift_prevention.migration_router import MigrationRouter
        result = MigrationRouter.reverse_entry(
            module='sales',
            operation='reverse_entry',
            entry_id=str(invoice.journal_entry_id),
            reason=reason or f'Invoice {invoice.invoice_number} cancelled',
            entity_type='SalesInvoice',
            entity_id=str(invoice.id),
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


class CustomerViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
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

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        """Generate customer statement with running balance."""
        from core.services.statement_engine import StatementService
        from datetime import datetime

        customer = self.get_object()
        from_date_str = request.query_params.get('from_date')
        to_date_str = request.query_params.get('to_date')

        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else None
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None

        statement = StatementService.customer_statement(customer, from_date, to_date)
        return Response(statement)

    @action(detail=True, methods=['get'])
    def credit_risk(self, request, pk=None):
        """Get comprehensive credit risk visibility for a customer using bulk aggregates."""
        from datetime import date
        from sales.models import CreditApprovalRequest
        from django.db.models import Sum, Count, F

        customer = self.get_object()
        today = date.today()

        # 1. Optimized Overdue invoices fetch
        overdue_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lt=today,
        ).annotate(
            remaining=F('total_amount') - F('paid_amount')
        ).filter(remaining__gt=0).order_by('due_date')

        # Compute aging and total overdue in memory from pre-filtered queryset
        overdue_list = []
        total_overdue = Decimal('0.00')
        aging = {
            'current': Decimal('0.00'),
            '1_30_days': Decimal('0.00'),
            '31_60_days': Decimal('0.00'),
            '61_90_days': Decimal('0.00'),
            'over_90_days': Decimal('0.00'),
        }

        for inv in overdue_invoices:
            remaining = inv.remaining
            days_overdue = (today - inv.due_date).days
            
            overdue_list.append({
                'invoice_number': inv.invoice_number,
                'due_date': inv.due_date.isoformat(),
                'remaining': str(remaining),
                'days_overdue': days_overdue,
            })
            total_overdue += remaining
            
            if days_overdue <= 30:
                aging['1_30_days'] += remaining
            elif days_overdue <= 60:
                aging['31_60_days'] += remaining
            elif days_overdue <= 90:
                aging['61_90_days'] += remaining
            else:
                aging['over_90_days'] += remaining

        # 2. Pending credit approvals
        pending_approvals = list(CreditApprovalRequest.objects.filter(
            customer=customer,
            status='PENDING',
        ).select_related('invoice', 'requested_by').order_by('-created_at'))

        pending_list = [
            {
                'request_id': str(req.pk),
                'invoice_number': req.invoice.invoice_number,
                'requested_amount': str(req.requested_amount),
                'requested_at': req.created_at.isoformat(),
                'requested_by': req.requested_by.username if req.requested_by else 'unknown',
            }
            for req in pending_approvals
        ]

        # Risk level calculation
        utilization = (customer.balance / customer.credit_limit * 100) if customer.credit_limit > 0 else 0
        if customer.status == 'BLOCKED' or utilization > 100:
            risk_level = 'CRITICAL'
        elif utilization > 80 or total_overdue > 0:
            risk_level = 'HIGH'
        elif utilization > 60:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        return Response({
            'customer': {
                'id': str(customer.pk),
                'code': customer.code,
                'name': customer.name,
                'status': customer.status,
            },
            'credit_summary': {
                'credit_limit': str(customer.credit_limit),
                'current_balance': str(customer.balance),
                'available_credit': str(customer.available_credit),
                'utilization_pct': round(utilization, 1),
            },
            'overdue_summary': {
                'total_overdue': str(total_overdue),
                'overdue_count': len(overdue_list),
                'invoices': overdue_list,
            },
            'aging': {k: str(v) for k, v in aging.items()},
            'pending_approvals': pending_list,
            'risk_level': risk_level,
        })


class SalesInvoiceViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
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
        """Create invoice with centralized credit limit enforcement via CreditPolicyEngine."""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        customer = serializer.validated_data.get('customer')
        total_amount = serializer.validated_data.get('total_amount', Decimal('0.00'))

        if customer:
            from core.services.credit_policy_engine import CreditPolicyEngine
            from core.services.financial_truth_engine import FinancialTruthEngine

            result = CreditPolicyEngine.check_customer_invoice(
                customer=customer,
                total_amount=total_amount,
                user=self.request.user if hasattr(self.request, 'user') else None,
            )

            if not result.allowed and not result.requires_override:
                raise ValidationError({'customer': result.reason})

            if not result.allowed and result.requires_override:
                request_override = self.request.data.get('request_credit_override', False)
                if request_override:
                    invoice = serializer.save(status='CREDIT_PENDING')
                    CreditPolicyEngine.handle_credit_override(
                        customer=customer,
                        invoice=invoice,
                        total_amount=total_amount,
                        user=self.request.user if hasattr(self.request, 'user') else None,
                    )
                    return invoice
                else:
                    available = FinancialTruthEngine.get_customer_available_credit(customer)
                    raise ValidationError({
                        'customer': f'Credit limit exceeded. Available: {available}, Required: {total_amount}. Use request_credit_override=true to submit for approval.'
                    })

        invoice = serializer.save()
        BalanceSyncService.sync_customer_by_invoice(invoice, lock=True)

    def perform_update(self, serializer):
        """Update invoice and sync customer balance."""
        invoice = serializer.save()
        BalanceSyncService.sync_customer_by_invoice(invoice, lock=True)

    def perform_destroy(self, instance):
        """Soft delete invoice and sync customer balance."""
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        BalanceSyncService.sync_customer_by_invoice(instance, lock=True)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an invoice. Idempotent — safe to call multiple times."""
        invoice = self.get_object()

        # Idempotent: already cancelled
        if invoice.status == 'CANCELLED':
            serializer = self.get_serializer(invoice)
            return Response(serializer.data)

        # Cannot cancel DRAFT (never dispatched, no stock to reverse)
        if invoice.status == 'DRAFT':
            return Response(
                {'error': 'Cannot cancel a draft invoice. Delete it instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot cancel PAID — would orphan payment
        if invoice.status == 'PAID':
            log_business_event(request, 'invoice.sales.cancel_blocked',
                               {'invoice_id': str(pk), 'current_status': invoice.status, 'reason': 'paid'})
            return Response(
                {'error': 'Cannot cancel a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot cancel PARTIAL_PAID — would orphan partial payment
        if invoice.status == 'PARTIAL_PAID':
            log_business_event(request, 'invoice.sales.cancel_blocked',
                               {'invoice_id': str(pk), 'current_status': invoice.status, 'reason': 'partial_paid'})
            return Response(
                {'error': 'Cannot cancel a partially paid invoice. Full refund required first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Reverse stock movements first
            stock_result = StockIntegrationService.reverse_sale_stock(invoice.id)
            if not stock_result.success:
                return Response(
                    {'error': 'Failed to reverse stock', 'details': stock_result.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Reverse accounting journal entry if exists
            if invoice.journal_entry_id:
                reversal_result = SalesAccountingService.reverse_sales_journal_entry(
                    invoice,
                    reason=f'Invoice {invoice.invoice_number} cancelled'
                )
                if not reversal_result.get('success'):
                    log_business_event(request, 'invoice.sales.cancel_failed',
                                       {'invoice_id': str(pk), 'reason': 'reversal_failed', 'errors': reversal_result.get('errors')})
                    return Response(
                        {'error': 'Failed to reverse accounting entry', 'details': reversal_result.get('errors')},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            invoice.status = 'CANCELLED'
            invoice.save(update_fields=['status', 'updated_at'])

        log_business_event(request, 'invoice.sales.cancelled', {'invoice_id': str(pk)})
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
                    raise ValidationError(
                        {
                            'error': 'Stock processing failed',
                            'details': stock_result.errors,
                            'shortages': stock_result.stock_shortages,
                        }
                    )
                
                invoice.status = 'DISPATCHED'
                invoice.save(update_fields=['status', 'updated_at'])
                
                # Create accounting journal entry (with allocations for COGS calculation)
                # COGS is calculated from actual batch costs via allocations
                accounting_result = SalesAccountingService.create_sales_journal_entry(
                    invoice, allocations=stock_result.allocations,
                    cogs_override=None,  # Uses batch purchase prices from allocations
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

    @action(detail=True, methods=['get'])
    def receipt_pdf(self, request, pk=None):
        """Generate PDF receipt for a sales invoice."""
        invoice = self.get_object()
        mode = request.query_params.get('mode', 'a4')

        try:
            from core.pdf_generator import generate_sales_invoice_pdf, pdf_response
            pdf_bytes = generate_sales_invoice_pdf(invoice, mode=mode)
            filename = f"invoice_{invoice.invoice_number}.pdf"
            return pdf_response(pdf_bytes, filename)
        except ImportError:
            return Response(
                {'error': 'ReportLab is not installed. Install with: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def pending_credit_approvals(self, request):
        """List all pending credit approval requests."""
        from sales.models import CreditApprovalRequest
        from sales.serializers.credit_approval import CreditApprovalRequestSerializer

        pending = CreditApprovalRequest.objects.filter(status='PENDING').order_by('-created_at')
        serializer = CreditApprovalRequestSerializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def approve_credit(self, request):
        """Approve a credit limit override request."""
        from sales.models import CreditApprovalRequest
        from core.services.financial_audit import FinancialAuditService

        request_id = request.data.get('request_id')
        reason = request.data.get('reason', '')

        if not request_id:
            return Response({'error': 'request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            credit_request = CreditApprovalRequest.objects.select_for_update().get(pk=request_id, status='PENDING')
        except CreditApprovalRequest.DoesNotExist:
            return Response({'error': 'Credit request not found or already processed'}, status=status.HTTP_404_NOT_FOUND)

        # Approve the request
        credit_request.status = 'APPROVED'
        credit_request.approved_by = request.user if hasattr(request, 'user') else None
        credit_request.approved_at = timezone.now()
        credit_request.approval_reason = reason
        credit_request.save()

        # Update invoice status from CREDIT_PENDING to CONFIRMED
        invoice = credit_request.invoice
        if invoice.status == 'CREDIT_PENDING':
            invoice.status = 'CONFIRMED'
            invoice.save(update_fields=['status', 'updated_at'])
            # Sync balance now that invoice is confirmed
            BalanceSyncService.sync_customer_by_invoice(invoice, lock=True)

        FinancialAuditService.log_credit_override(
            customer_id=str(credit_request.customer.pk),
            customer_name=credit_request.customer.name,
            credit_limit=credit_request.credit_limit,
            current_balance=credit_request.current_balance,
            invoice_amount=credit_request.requested_amount,
            user=request.user if hasattr(request, 'user') else None,
        )

        return Response({
            'success': True,
            'request_id': str(credit_request.pk),
            'invoice_id': str(invoice.pk),
            'approved_by': credit_request.approved_by.username if credit_request.approved_by else 'system',
            'approved_at': credit_request.approved_at.isoformat(),
        })

    @action(detail=False, methods=['post'])
    def reject_credit(self, request):
        """Reject a credit limit override request."""
        from sales.models import CreditApprovalRequest

        request_id = request.data.get('request_id')
        reason = request.data.get('reason', '')

        if not request_id:
            return Response({'error': 'request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            credit_request = CreditApprovalRequest.objects.select_for_update().get(pk=request_id, status='PENDING')
        except CreditApprovalRequest.DoesNotExist:
            return Response({'error': 'Credit request not found or already processed'}, status=status.HTTP_404_NOT_FOUND)

        # Reject the request
        credit_request.status = 'REJECTED'
        credit_request.approved_by = request.user if hasattr(request, 'user') else None
        credit_request.approved_at = timezone.now()
        credit_request.rejection_reason = reason
        credit_request.save()

        # Keep invoice as CREDIT_PENDING (not confirmed, not cancelled)
        return Response({
            'success': True,
            'request_id': str(credit_request.pk),
            'rejected_by': credit_request.approved_by.username if credit_request.approved_by else 'system',
            'rejected_at': credit_request.approved_at.isoformat(),
        })


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
        """Create payment with overpayment prevention and concurrent safety.
        
        Balance is now synced automatically via CustomerPayment.save()
        through BalanceSyncService (no direct mutation needed here).
        """
        invoice = serializer.validated_data.get('invoice')
        customer = serializer.validated_data.get('customer')
        amount = serializer.validated_data.get('amount', Decimal('0.00'))

        if invoice:
            with transaction.atomic():
                locked_invoice = SalesInvoice.objects.select_for_update().get(pk=invoice.pk)
                remaining = locked_invoice.total_amount - locked_invoice.paid_amount
                if amount > remaining:
                    raise ValidationError({
                        'amount': f'Payment exceeds remaining balance. Remaining: {remaining}, Attempted: {amount}'
                    })
                serializer.save()
        else:
            with transaction.atomic():
                if customer:
                    locked_customer = Customer.objects.select_for_update().get(pk=customer.pk)
                    if locked_customer.credit_limit and locked_customer.credit_limit > 0:
                        projected = locked_customer.balance - amount
                        if projected > locked_customer.credit_limit:
                            raise ValidationError({
                                'amount': f'Payment would exceed credit limit. Available credit: {locked_customer.available_credit}'
                            })
                serializer.save()

    @action(detail=False, methods=['post'])
    def fifo_allocate(self, request):
        """Run FIFO allocation for all unallocated payments."""
        customer_id = request.data.get('customer_id')
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                result = FIFOAllocationService.allocate_for_customer(customer, user=request.user if hasattr(request, 'user') else None)
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            result = FIFOAllocationService.allocate_all_unallocated(user=request.user if hasattr(request, 'user') else None)

        return Response(result)

    @action(detail=False, methods=['get'])
    def unallocated_payments(self, request):
        """List unallocated payments eligible for FIFO allocation."""
        customer_id = request.query_params.get('customer_id')
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        payments = FIFOAllocationService.get_unallocated_payments(customer)
        return Response(payments)

    @action(detail=False, methods=['get'])
    def outstanding_invoices(self, request):
        """List outstanding invoices eligible for FIFO allocation."""
        customer_id = request.query_params.get('customer_id')
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        invoices = FIFOAllocationService.get_outstanding_invoices(customer)
        return Response(invoices)

    @action(detail=False, methods=['get'])
    def financial_integrity(self, request):
        """Run full financial integrity validation."""
        result = FinancialIntegrityService.validate_all()
        return Response(result)

    @action(detail=False, methods=['post'])
    def fix_balances(self, request):
        """Auto-fix all customer and supplier balance mismatches."""
        user = request.user if hasattr(request, 'user') else None
        customer_result = FinancialIntegrityService.auto_fix_customer_balances(user=user)
        supplier_result = FinancialIntegrityService.auto_fix_supplier_balances(user=user)

        return Response({
            'customers': customer_result,
            'suppliers': supplier_result,
            'overall_success': customer_result['success'] and supplier_result['success'],
        })
