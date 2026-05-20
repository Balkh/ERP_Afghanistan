"""FIFO (First-In-First-Out) payment allocation service.

Automatically allocates unallocated customer payments to the oldest
outstanding invoices, ensuring payments are applied in chronological order.

Usage:
    FIFOAllocationService.allocate_for_customer(customer)
    FIFOAllocationService.allocate_all_unallocated()
    FIFOAllocationService.allocate_payment(payment)
"""
from decimal import Decimal
from typing import Optional
from django.db import transaction, models
from django.utils import timezone

from sales.models import CustomerPayment, SalesInvoice, PaymentAllocation


class FIFOAllocationService:
    """Lightweight FIFO payment allocation.

    Strategy: oldest unpaid/partially-paid invoices are paid first.
    All allocations are atomic and idempotent.
    """

    @staticmethod
    @transaction.atomic
    def allocate_payment(payment: CustomerPayment, user=None) -> list:
        """Allocate a single unallocated payment to outstanding invoices.

        Args:
            payment: CustomerPayment with no invoice reference (orphan payment)
            user: Optional user performing the allocation (for audit)

        Returns:
            List of PaymentAllocation instances created
        """
        from core.services.financial_audit import FinancialAuditService

        if payment.invoice:
            return []  # Already allocated to a specific invoice

        remaining = payment.amount
        allocations = []

        # Get oldest outstanding invoices for this customer
        outstanding = list(SalesInvoice.objects.filter(
            customer=payment.customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
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

            allocation = PaymentAllocation.objects.create(
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
    def allocate_for_customer(customer, user=None) -> dict:
        """Allocate all unallocated payments for a customer using FIFO.

        Args:
            customer: Customer instance
            user: Optional user (for audit)

        Returns:
            Dict with allocation summary
        """
        from sales.models import Customer

        # Lock customer row for concurrent safety
        customer = Customer.objects.select_for_update().get(pk=customer.pk)

        # Find unallocated payments (no invoice reference)
        unallocated_payments = CustomerPayment.objects.filter(
            customer=customer,
            invoice__isnull=True,
        ).order_by('payment_date', 'id')

        total_allocated = Decimal('0.00')
        total_payments = 0
        total_invoices_paid = 0
        all_allocations = []

        for payment in unallocated_payments:
            allocations = FIFOAllocationService.allocate_payment(payment, user=user)
            if allocations:
                total_payments += 1
                total_allocated += payment.amount
                all_allocations.extend(allocations)

                # Count fully paid invoices
                for alloc in allocations:
                    if alloc.invoice.status == 'PAID':
                        total_invoices_paid += 1

        return {
            'customer': customer.name,
            'payments_processed': total_payments,
            'total_allocated': total_allocated,
            'invoices_fully_paid': total_invoices_paid,
            'allocations_created': len(all_allocations),
        }

    @staticmethod
    @transaction.atomic
    def allocate_all_unallocated(user=None) -> dict:
        """Run FIFO allocation for ALL customers with unallocated payments.

        Returns:
            Dict with overall summary
        """
        from sales.models import Customer

        customers_with_unallocated = Customer.objects.filter(
            payments__invoice__isnull=True,
        ).distinct()

        total_customers = 0
        total_payments = 0
        total_allocated = Decimal('0.00')
        total_invoices_paid = 0
        errors = []

        for customer in customers_with_unallocated:
            try:
                result = FIFOAllocationService.allocate_for_customer(customer, user=user)
                total_customers += 1
                total_payments += result['payments_processed']
                total_allocated += result['total_allocated']
                total_invoices_paid += result['invoices_fully_paid']
            except Exception as e:
                errors.append(f"Customer {customer.code}: {e}")

        return {
            'customers_processed': total_customers,
            'payments_allocated': total_payments,
            'total_amount_allocated': total_allocated,
            'invoices_fully_paid': total_invoices_paid,
            'errors': errors,
            'success': len(errors) == 0,
        }

    @staticmethod
    def get_unallocated_payments(customer=None) -> list:
        """Get list of unallocated payments.

        Args:
            customer: Optional Customer filter

        Returns:
            List of dicts with payment info and remaining unallocated amount
        """
        qs = CustomerPayment.objects.filter(invoice__isnull=True)
        if customer:
            qs = qs.filter(customer=customer)

        qs = qs.order_by('payment_date', 'id')

        results = []
        for payment in qs:
            allocated = PaymentAllocation.objects.filter(
                payment=payment
            ).aggregate(total=models.Sum('allocated_amount'))['total'] or Decimal('0.00')

            remaining = payment.amount - allocated
            if remaining > 0:
                results.append({
                    'payment_id': str(payment.id),
                    'customer': payment.customer.name,
                    'amount': payment.amount,
                    'already_allocated': allocated,
                    'remaining': remaining,
                    'payment_date': payment.payment_date.isoformat(),
                    'reference': payment.reference_number,
                })

        return results

    @staticmethod
    def get_outstanding_invoices(customer=None) -> list:
        """Get list of outstanding invoices eligible for FIFO allocation.

        Args:
            customer: Optional Customer filter

        Returns:
            List of dicts with invoice info and remaining balance
        """
        qs = SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
        )
        if customer:
            qs = qs.filter(customer=customer)

        qs = qs.order_by('invoice_date', 'id')

        results = []
        for invoice in qs:
            remaining = invoice.total_amount - invoice.paid_amount
            if remaining > 0:
                results.append({
                    'invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'customer': invoice.customer.name,
                    'total_amount': invoice.total_amount,
                    'paid_amount': invoice.paid_amount,
                    'remaining': remaining,
                    'status': invoice.status,
                    'invoice_date': invoice.invoice_date.isoformat(),
                })

        return results
