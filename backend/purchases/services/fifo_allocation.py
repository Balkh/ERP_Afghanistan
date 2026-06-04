"""Supplier FIFO (First-In-First-Out) Payment Allocation Service.

Mirrors the customer FIFO allocation engine for supplier parity.
Automatically allocates unallocated supplier payments to the oldest
outstanding purchase invoices, ensuring payments are applied in
chronological order.

Usage:
    SupplierFIFOAllocationService.allocate_for_supplier(supplier)
    SupplierFIFOAllocationService.allocate_all_unallocated()
    SupplierFIFOAllocationService.allocate_payment(payment)
"""
from decimal import Decimal
from django.db import transaction, models
from purchases.models import SupplierPayment, PurchaseInvoice, SupplierPaymentAllocation


class SupplierFIFOAllocationService:
    """FIFO payment allocation for suppliers.
    
    Strategy: oldest unpaid/partially-paid purchase invoices are paid first.
    All allocations are atomic, idempotent, and concurrency-safe.
    """

    @staticmethod
    @transaction.atomic
    def allocate_payment(payment: SupplierPayment, user=None) -> list:
        """Allocate a single unallocated supplier payment to outstanding invoices.
        
        Args:
            payment: SupplierPayment with no invoice reference (orphan payment)
            user: Optional user performing the allocation (for audit)
        
        Returns:
            List of SupplierPaymentAllocation instances created
        """
        from core.services.financial_audit import FinancialAuditService

        if payment.invoice:
            return []

        # Lock the supplier row for concurrent safety
        from purchases.models import Supplier
        Supplier.objects.select_for_update().get(pk=payment.supplier.pk)

        remaining = payment.amount
        allocations = []

        # Get oldest outstanding invoices for this supplier with row-level locking
        outstanding = list(PurchaseInvoice.objects.select_for_update().filter(
            supplier=payment.supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
        ).order_by('invoice_date', 'created_at', 'id'))

        for invoice in outstanding:
            if remaining <= Decimal('0.00'):
                break

            unpaid = invoice.total_amount - invoice.paid_amount
            if unpaid <= Decimal('0.00'):
                continue

            allocate = min(remaining, unpaid)

            if allocate <= Decimal('0.00'):
                continue

            allocation = SupplierPaymentAllocation.objects.create(
                payment=payment,
                invoice=invoice,
                allocated_amount=allocate,
                notes=f'FIFO auto-allocation',
            )
            allocations.append(allocation)

            FinancialAuditService.log_fifo_allocation(
                payment_id=str(payment.pk),
                invoice_id=str(invoice.pk),
                amount=allocate,
                user=user,
            )

            # Update invoice paid amount and status
            invoice.paid_amount += allocate
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = 'PAID'
                invoice.payment_status = 'PAID'
            elif invoice.paid_amount > Decimal('0.00'):
                invoice.status = 'PARTIAL_PAID'
                invoice.payment_status = 'PARTIAL'
            invoice.save(update_fields=['paid_amount', 'status', 'payment_status', 'updated_at'])

            remaining = remaining - allocate

        return allocations

    @staticmethod
    @transaction.atomic
    def allocate_for_supplier(supplier, user=None) -> dict:
        """Allocate all unallocated payments for a supplier using FIFO.
        
        Args:
            supplier: Supplier instance
            user: Optional user (for audit)
        
        Returns:
            Dict with allocation summary
        """
        from purchases.models import Supplier

        # Lock supplier row for concurrent safety
        supplier = Supplier.objects.select_for_update().get(pk=supplier.pk)

        # Find unallocated payments (no invoice reference)
        unallocated_payments = SupplierPayment.objects.filter(
            supplier=supplier,
            invoice__isnull=True,
        ).order_by('payment_date', 'id')

        total_allocated = Decimal('0.00')
        total_payments = 0
        total_invoices_paid = 0
        all_allocations = []

        for payment in unallocated_payments:
            allocations = SupplierFIFOAllocationService.allocate_payment(payment, user=user)
            if allocations:
                total_payments += 1
                total_allocated += payment.amount
                all_allocations.extend(allocations)

                # Count fully paid invoices
                for alloc in allocations:
                    if alloc.invoice.status == 'PAID':
                        total_invoices_paid += 1

        return {
            'supplier': supplier.name,
            'payments_processed': total_payments,
            'total_allocated': total_allocated,
            'invoices_fully_paid': total_invoices_paid,
            'allocations_created': len(all_allocations),
        }

    @staticmethod
    @transaction.atomic
    def allocate_all_unallocated(user=None) -> dict:
        """Run FIFO allocation for ALL suppliers with unallocated payments.
        
        Returns:
            Dict with overall summary
        """
        from purchases.models import Supplier

        suppliers_with_unallocated = Supplier.objects.filter(
            payments__invoice__isnull=True,
        ).distinct()

        total_suppliers = 0
        total_payments = 0
        total_allocated = Decimal('0.00')
        total_invoices_paid = 0
        errors = []

        for supplier in suppliers_with_unallocated:
            try:
                result = SupplierFIFOAllocationService.allocate_for_supplier(supplier, user=user)
                total_suppliers += 1
                total_payments += result['payments_processed']
                total_allocated += result['total_allocated']
                total_invoices_paid += result['invoices_fully_paid']
            except Exception as e:
                errors.append(f"Supplier {supplier.code}: {e}")

        return {
            'suppliers_processed': total_suppliers,
            'payments_allocated': total_payments,
            'total_amount_allocated': total_allocated,
            'invoices_fully_paid': total_invoices_paid,
            'errors': errors,
            'success': len(errors) == 0,
        }

    @staticmethod
    def get_unallocated_payments(supplier=None) -> list:
        """Get list of unallocated supplier payments.
        
        Args:
            supplier: Optional Supplier filter
        
        Returns:
            List of dicts with payment info and remaining unallocated amount
        """
        qs = SupplierPayment.objects.filter(invoice__isnull=True)
        if supplier:
            qs = qs.filter(supplier=supplier)

        qs = qs.order_by('payment_date', 'id')

        results = []
        for payment in qs:
            allocated = SupplierPaymentAllocation.objects.filter(
                payment=payment
            ).aggregate(total=models.Sum('allocated_amount'))['total'] or Decimal('0.00')

            remaining = payment.amount - allocated
            if remaining > 0:
                results.append({
                    'payment_id': str(payment.id),
                    'supplier': payment.supplier.name,
                    'amount': payment.amount,
                    'already_allocated': allocated,
                    'remaining': remaining,
                    'payment_date': payment.payment_date.isoformat(),
                    'reference': payment.reference_number,
                })

        return results

    @staticmethod
    def get_outstanding_invoices(supplier=None) -> list:
        """Get list of outstanding purchase invoices eligible for FIFO allocation.
        
        Args:
            supplier: Optional Supplier filter
        
        Returns:
            List of dicts with invoice info and remaining balance
        """
        qs = PurchaseInvoice.objects.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
        )
        if supplier:
            qs = qs.filter(supplier=supplier)

        qs = qs.order_by('invoice_date', 'id')

        results = []
        for invoice in qs:
            remaining = invoice.total_amount - invoice.paid_amount
            if remaining > 0:
                results.append({
                    'invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'supplier': invoice.supplier.name,
                    'total_amount': invoice.total_amount,
                    'paid_amount': invoice.paid_amount,
                    'remaining': remaining,
                    'status': invoice.status,
                    'invoice_date': invoice.invoice_date.isoformat(),
                })

        return results
