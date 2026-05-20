"""Phase 20: Financial Operations Cohesion — Payment Operation APIs.

Provides complete operational payment workflows:
- Customer payment entry with invoice awareness
- Outstanding balance visibility
- FIFO allocation preview
- Unallocated payment management
- Payment allocation explorer
- Mixed payment support
- Supplier payment parity

All endpoints are read-only except explicit payment creation/allocation actions.
No balance mutation occurs in frontend — all truth from SSOT/backend.
"""
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from sales.models import Customer, SalesInvoice, CustomerPayment, PaymentAllocation
from purchases.models import Supplier, PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation
from payments.models import PaymentMethod, PaymentAccount
from accounting.models import Account, JournalEntry
from core.balance_sync import BalanceSyncService
from core.services.financial_truth_engine import FinancialTruthEngine
from sales.services.fifo_allocation import FIFOAllocationService
from purchases.services.fifo_allocation import SupplierFIFOAllocationService
from security.permissions import RoleBasedPermission


class PaymentOperationsViewSet(viewsets.ViewSet):
    """Unified payment operations API for customer and supplier payment workflows.

    Provides operational visibility and action endpoints for:
    - Payment entry with balance preview
    - FIFO allocation management
    - Unallocated payment explorer
    - Settlement traceability
    - Mixed payment processing
    """
    permission_classes = [RoleBasedPermission]

    # ========================================================================
    # CUSTOMER PAYMENT OPERATIONS
    # ========================================================================

    @action(detail=False, methods=['get'], url_path='customers/(?P<customer_id>[^/.]+)/payment-workspace')
    def customer_payment_workspace(self, request, customer_id=None):
        """Complete customer payment workspace data.

        Returns:
        - customer info with derived balance
        - outstanding invoices
        - unallocated payments
        - recent payment history
        - FIFO allocation summary
        """
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        derived_balance = FinancialTruthEngine.get_customer_balance(customer)
        available_credit = customer.credit_limit - derived_balance if customer.credit_limit else None

        outstanding = FIFOAllocationService.get_outstanding_invoices(customer)
        unallocated = FIFOAllocationService.get_unallocated_payments(customer)

        recent_payments = CustomerPayment.objects.filter(
            customer=customer
        ).select_related('invoice').order_by('-payment_date')[:20]

        allocation_summary = {
            'total_allocated': PaymentAllocation.objects.filter(
                payment__customer=customer
            ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0.00'),
            'allocation_count': PaymentAllocation.objects.filter(
                payment__customer=customer
            ).count(),
        }

        return Response({
            'customer': {
                'id': str(customer.id),
                'name': customer.name,
                'code': customer.code,
                'stored_balance': customer.balance,
                'derived_balance': derived_balance,
                'credit_limit': customer.credit_limit,
                'available_credit': available_credit,
            },
            'outstanding_invoices': outstanding,
            'unallocated_payments': unallocated,
            'recent_payments': [
                {
                    'id': str(p.id),
                    'amount': p.amount,
                    'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                    'payment_method': p.payment_method,
                    'reference_number': p.reference_number,
                    'invoice_number': p.invoice.invoice_number if p.invoice else None,
                    'invoice_id': str(p.invoice.id) if p.invoice else None,
                }
                for p in recent_payments
            ],
            'allocation_summary': allocation_summary,
        })

    @action(detail=False, methods=['post'], url_path='customers/process-payment')
    def process_customer_payment(self, request):
        """Process a customer payment with full validation.

        Request body:
        - customer_id: UUID
        - invoice_id: UUID (optional for on-account payment)
        - amount: Decimal
        - payment_method: string (CASH, BANK_TRANSFER, etc.)
        - reference_number: string (optional)
        - notes: string (optional)
        - allocations: list of {invoice_id, amount} for manual allocation

        Returns:
        - payment_id
        - allocation_results
        - new_balance
        """
        data = request.data
        customer_id = data.get('customer_id')
        invoice_id = data.get('invoice_id')
        amount = Decimal(str(data.get('amount', 0)))
        payment_method = data.get('payment_method', 'CASH')
        reference_number = data.get('reference_number', '')
        notes = data.get('notes', '')
        allocations = data.get('allocations', [])

        if amount <= 0:
            return Response({'error': 'Payment amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        invoice = None
        if invoice_id:
            try:
                invoice = SalesInvoice.objects.get(pk=invoice_id)
                if invoice.customer_id != customer_id:
                    return Response({'error': 'Invoice does not belong to this customer'}, status=status.HTTP_400_BAD_REQUEST)
            except SalesInvoice.DoesNotExist:
                return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            payment = CustomerPayment.objects.create(
                customer=customer,
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes,
                payment_date=timezone.now().date(),
            )

            allocation_results = []
            if allocations and not invoice:
                for alloc in allocations:
                    try:
                        alloc_invoice = SalesInvoice.objects.get(pk=alloc['invoice_id'])
                        alloc_amount = Decimal(str(alloc['amount']))
                        PaymentAllocation.objects.create(
                            payment=payment,
                            invoice=alloc_invoice,
                            allocated_amount=alloc_amount,
                        )
                        alloc_invoice.paid_amount += alloc_amount
                        alloc_invoice.update_payment_status()
                        alloc_invoice.save(update_fields=['paid_amount', 'payment_status'])
                        allocation_results.append({
                            'invoice_id': str(alloc_invoice.id),
                            'invoice_number': alloc_invoice.invoice_number,
                            'amount': str(alloc_amount),
                            'status': 'allocated',
                        })
                    except (SalesInvoice.DoesNotExist, KeyError):
                        allocation_results.append({
                            'invoice_id': alloc.get('invoice_id', 'unknown'),
                            'status': 'failed',
                            'error': 'Invoice not found or invalid amount',
                        })

            new_balance = BalanceSyncService.sync_customer(customer, lock=False)

        return Response({
            'success': True,
            'payment_id': str(payment.id),
            'reference_number': payment.reference_number,
            'amount': str(amount),
            'allocation_results': allocation_results,
            'new_balance': str(new_balance),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='customers/(?P<customer_id>[^/.]+)/allocate-unallocated')
    def allocate_customer_unallocated(self, request, customer_id=None):
        """Run FIFO allocation for a specific customer's unallocated payments."""
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        result = FIFOAllocationService.allocate_for_customer(
            customer,
            user=request.user if hasattr(request, 'user') else None,
        )
        return Response(result)

    @action(detail=False, methods=['get'], url_path='customers/(?P<customer_id>[^/.]+)/payment-trace')
    def customer_payment_trace(self, request, customer_id=None):
        """Payment allocation explorer — which payment settled which invoice."""
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        payments = CustomerPayment.objects.filter(
            customer=customer
        ).prefetch_related('allocations__invoice').order_by('-payment_date')

        trace = []
        for payment in payments:
            allocations = []
            for alloc in payment.allocations.all():
                allocations.append({
                    'allocation_id': str(alloc.id),
                    'invoice_number': alloc.invoice.invoice_number,
                    'invoice_date': alloc.invoice.invoice_date.isoformat() if alloc.invoice.invoice_date else None,
                    'allocated_amount': str(alloc.allocated_amount),
                    'invoice_total': str(alloc.invoice.total_amount),
                    'invoice_paid': str(alloc.invoice.paid_amount),
                    'invoice_status': alloc.invoice.status,
                })

            trace.append({
                'payment_id': str(payment.id),
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'reference_number': payment.reference_number,
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'direct_invoice': payment.invoice.invoice_number if payment.invoice else None,
                'allocations': allocations,
                'is_fully_allocated': sum(
                    Decimal(str(a['allocated_amount'])) for a in allocations
                ) >= payment.amount,
            })

        return Response({
            'customer_id': str(customer.id),
            'customer_name': customer.name,
            'payment_trace': trace,
            'total_payments': len(trace),
        })

    # ========================================================================
    # SUPPLIER PAYMENT OPERATIONS (parity with customer)
    # ========================================================================

    @action(detail=False, methods=['get'], url_path='suppliers/(?P<supplier_id>[^/.]+)/payment-workspace')
    def supplier_payment_workspace(self, request, supplier_id=None):
        """Complete supplier payment workspace data."""
        try:
            supplier = Supplier.objects.get(pk=supplier_id)
        except Supplier.DoesNotExist:
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)

        derived_balance = FinancialTruthEngine.get_supplier_balance(supplier)

        outstanding = SupplierFIFOAllocationService.get_outstanding_invoices(supplier)
        unallocated = SupplierFIFOAllocationService.get_unallocated_payments(supplier)

        recent_payments = SupplierPayment.objects.filter(
            supplier=supplier
        ).select_related('invoice').order_by('-payment_date')[:20]

        allocation_summary = {
            'total_allocated': SupplierPaymentAllocation.objects.filter(
                payment__supplier=supplier
            ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0.00'),
            'allocation_count': SupplierPaymentAllocation.objects.filter(
                payment__supplier=supplier
            ).count(),
        }

        return Response({
            'supplier': {
                'id': str(supplier.id),
                'name': supplier.name,
                'code': supplier.code,
                'stored_balance': supplier.balance,
                'derived_balance': derived_balance,
            },
            'outstanding_invoices': outstanding,
            'unallocated_payments': unallocated,
            'recent_payments': [
                {
                    'id': str(p.id),
                    'amount': p.amount,
                    'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                    'payment_method': p.payment_method,
                    'reference_number': p.reference_number,
                    'invoice_number': p.invoice.invoice_number if p.invoice else None,
                    'invoice_id': str(p.invoice.id) if p.invoice else None,
                }
                for p in recent_payments
            ],
            'allocation_summary': allocation_summary,
        })

    @action(detail=False, methods=['post'], url_path='suppliers/process-payment')
    def process_supplier_payment(self, request):
        """Process a supplier payment with full validation."""
        data = request.data
        supplier_id = data.get('supplier_id')
        invoice_id = data.get('invoice_id')
        amount = Decimal(str(data.get('amount', 0)))
        payment_method = data.get('payment_method', 'CASH')
        reference_number = data.get('reference_number', '')
        notes = data.get('notes', '')
        allocations = data.get('allocations', [])

        if amount <= 0:
            return Response({'error': 'Payment amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            supplier = Supplier.objects.get(pk=supplier_id)
        except Supplier.DoesNotExist:
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)

        invoice = None
        if invoice_id:
            try:
                invoice = PurchaseInvoice.objects.get(pk=invoice_id)
                if invoice.supplier_id != supplier_id:
                    return Response({'error': 'Invoice does not belong to this supplier'}, status=status.HTTP_400_BAD_REQUEST)
            except PurchaseInvoice.DoesNotExist:
                return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            payment = SupplierPayment.objects.create(
                supplier=supplier,
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes,
                payment_date=timezone.now().date(),
            )

            allocation_results = []
            if allocations and not invoice:
                for alloc in allocations:
                    try:
                        alloc_invoice = PurchaseInvoice.objects.get(pk=alloc['invoice_id'])
                        alloc_amount = Decimal(str(alloc['amount']))
                        SupplierPaymentAllocation.objects.create(
                            payment=payment,
                            invoice=alloc_invoice,
                            allocated_amount=alloc_amount,
                        )
                        alloc_invoice.paid_amount += alloc_amount
                        alloc_invoice.update_payment_status()
                        alloc_invoice.save(update_fields=['paid_amount', 'payment_status'])
                        allocation_results.append({
                            'invoice_id': str(alloc_invoice.id),
                            'invoice_number': alloc_invoice.invoice_number,
                            'amount': str(alloc_amount),
                            'status': 'allocated',
                        })
                    except (PurchaseInvoice.DoesNotExist, KeyError):
                        allocation_results.append({
                            'invoice_id': alloc.get('invoice_id', 'unknown'),
                            'status': 'failed',
                            'error': 'Invoice not found or invalid amount',
                        })

            new_balance = BalanceSyncService.sync_supplier(supplier, lock=False)

        return Response({
            'success': True,
            'payment_id': str(payment.id),
            'reference_number': payment.reference_number,
            'amount': str(amount),
            'allocation_results': allocation_results,
            'new_balance': str(new_balance),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='suppliers/(?P<supplier_id>[^/.]+)/allocate-unallocated')
    def allocate_supplier_unallocated(self, request, supplier_id=None):
        """Run FIFO allocation for a specific supplier's unallocated payments."""
        try:
            supplier = Supplier.objects.get(pk=supplier_id)
        except Supplier.DoesNotExist:
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)

        result = SupplierFIFOAllocationService.allocate_for_supplier(
            supplier,
            user=request.user if hasattr(request, 'user') else None,
        )
        return Response(result)

    @action(detail=False, methods=['get'], url_path='suppliers/(?P<supplier_id>[^/.]+)/payment-trace')
    def supplier_payment_trace(self, request, supplier_id=None):
        """Payment allocation explorer for supplier payments."""
        try:
            supplier = Supplier.objects.get(pk=supplier_id)
        except Supplier.DoesNotExist:
            return Response({'error': 'Supplier not found'}, status=status.HTTP_404_NOT_FOUND)

        payments = SupplierPayment.objects.filter(
            supplier=supplier
        ).prefetch_related('allocations__invoice').order_by('-payment_date')

        trace = []
        for payment in payments:
            allocations = []
            for alloc in payment.allocations.all():
                allocations.append({
                    'allocation_id': str(alloc.id),
                    'invoice_number': alloc.invoice.invoice_number,
                    'invoice_date': alloc.invoice.invoice_date.isoformat() if alloc.invoice.invoice_date else None,
                    'allocated_amount': str(alloc.allocated_amount),
                    'invoice_total': str(alloc.invoice.total_amount),
                    'invoice_paid': str(alloc.invoice.paid_amount),
                    'invoice_status': alloc.invoice.status,
                })

            trace.append({
                'payment_id': str(payment.id),
                'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                'reference_number': payment.reference_number,
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'direct_invoice': payment.invoice.invoice_number if payment.invoice else None,
                'allocations': allocations,
                'is_fully_allocated': sum(
                    Decimal(str(a['allocated_amount'])) for a in allocations
                ) >= payment.amount,
            })

        return Response({
            'supplier_id': str(supplier.id),
            'supplier_name': supplier.name,
            'payment_trace': trace,
            'total_payments': len(trace),
        })

    # ========================================================================
    # MIXED PAYMENT OPERATIONS
    # ========================================================================

    @action(detail=False, methods=['get'], url_path='payment-methods')
    def list_payment_methods(self, request):
        """List available payment methods for mixed payment construction."""
        methods = PaymentMethod.objects.filter(is_active=True).values(
            'id', 'code', 'name', 'method_type', 'fee_percentage', 'fee_fixed'
        )
        return Response(list(methods))

    @action(detail=False, methods=['get'], url_path='payment-accounts')
    def list_payment_accounts(self, request):
        """List available payment accounts for mixed payment construction."""
        accounts = PaymentAccount.objects.filter(is_active=True).select_related(
            'accounting_account'
        ).values(
            'id', 'code', 'name', 'account_type', 'currency', 'current_balance',
            'accounting_account__code', 'accounting_account__name',
        )
        return Response(list(accounts))

    @action(detail=False, methods=['post'], url_path='validate-mixed-payment')
    def validate_mixed_payment(self, request):
        """Validate a mixed payment split before submission.

        Request body:
        - total_amount: Decimal
        - splits: list of {payment_method_code, amount, payment_account_code}

        Returns:
        - is_valid: bool
        - total_split: Decimal
        - difference: Decimal
        - warnings: list
        - errors: list
        """
        data = request.data
        total_amount = Decimal(str(data.get('total_amount', 0)))
        splits = data.get('splits', [])

        errors = []
        warnings = []

        if total_amount <= 0:
            errors.append('Total amount must be positive')
            return Response({'is_valid': False, 'errors': errors, 'warnings': warnings}, status=status.HTTP_400_BAD_REQUEST)

        split_total = Decimal('0.00')
        for i, split in enumerate(splits):
            try:
                amount = Decimal(str(split.get('amount', 0)))
            except Exception:
                errors.append(f'Split {i + 1}: invalid amount')
                continue

            if amount <= 0:
                errors.append(f'Split {i + 1}: amount must be positive')
                continue

            split_total += amount

            method_code = split.get('payment_method_code')
            if not PaymentMethod.objects.filter(code=method_code, is_active=True).exists():
                errors.append(f'Split {i + 1}: payment method "{method_code}" not found or inactive')

            account_code = split.get('payment_account_code')
            if account_code:
                account = PaymentAccount.objects.filter(code=account_code, is_active=True).first()
                if not account:
                    errors.append(f'Split {i + 1}: payment account "{account_code}" not found or inactive')
                elif account.current_balance < amount:
                    warnings.append(f'Split {i + 1}: account "{account_code}" balance ({account.current_balance}) is less than split amount ({amount})')

        difference = total_amount - split_total
        if difference != 0:
            errors.append(f'Split total ({split_total}) does not match payment total ({total_amount}). Difference: {difference}')

        if abs(difference) > 0:
            warnings.append('Unallocated remainder will be recorded as on-account payment')

        return Response({
            'is_valid': len(errors) == 0,
            'total_amount': str(total_amount),
            'split_total': str(split_total),
            'difference': str(difference),
            'warnings': warnings,
            'errors': errors,
        })

    # ========================================================================
    # PAYMENT ANOMALY DETECTION
    # ========================================================================

    @action(detail=False, methods=['get'], url_path='payment-anomalies')
    def payment_anomalies(self, request):
        """Detect payment anomalies: orphan payments, overpayments, duplicate references."""
        anomalies = []

        orphan_customer_payments = CustomerPayment.objects.filter(
            invoice__isnull=True
        ).exclude(
            id__in=PaymentAllocation.objects.values_list('payment_id', flat=True)
        )
        for p in orphan_customer_payments[:50]:
            anomalies.append({
                'type': 'ORPHAN_CUSTOMER_PAYMENT',
                'severity': 'WARNING',
                'payment_id': str(p.id),
                'customer': p.customer.name,
                'amount': str(p.amount),
                'date': p.payment_date.isoformat() if p.payment_date else None,
                'reference': p.reference_number,
                'suggestion': 'Allocate to outstanding invoice or mark as on-account credit',
            })

        orphan_supplier_payments = SupplierPayment.objects.filter(
            invoice__isnull=True
        ).exclude(
            id__in=SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        )
        for p in orphan_supplier_payments[:50]:
            anomalies.append({
                'type': 'ORPHAN_SUPPLIER_PAYMENT',
                'severity': 'WARNING',
                'payment_id': str(p.id),
                'supplier': p.supplier.name,
                'amount': str(p.amount),
                'date': p.payment_date.isoformat() if p.payment_date else None,
                'reference': p.reference_number,
                'suggestion': 'Allocate to outstanding invoice or mark as on-account credit',
            })

        duplicate_refs = CustomerPayment.objects.values(
            'reference_number'
        ).filter(
            reference_number__isnull=False,
            reference_number__gt='',
        ).annotate(
            count=Sum('amount')
        ).filter(count__gt=1)[:20]

        for ref in duplicate_refs:
            anomalies.append({
                'type': 'DUPLICATE_REFERENCE',
                'severity': 'INFO',
                'reference': ref['reference_number'],
                'count': ref['count'],
                'suggestion': 'Verify these are not duplicate entries',
            })

        return Response({
            'anomalies': anomalies,
            'total_count': len(anomalies),
            'by_severity': {
                'WARNING': len([a for a in anomalies if a['severity'] == 'WARNING']),
                'INFO': len([a for a in anomalies if a['severity'] == 'INFO']),
            },
        })
