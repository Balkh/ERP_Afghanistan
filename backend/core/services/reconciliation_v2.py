"""Smart Reconciliation Assistance Layer V2 — Guided Intelligence.

Upgrades V1 reconciliation into a guided matching engine that suggests
payment↔invoice matches with confidence scores, without auto-applying them.

Usage:
    suggestions = ReconciliationAssistanceV2.suggest_customer_matches(customer)
    unresolved = ReconciliationAssistanceV2.get_unresolved_items()
"""
from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone


class ReconciliationAssistanceV2:
    """Smart reconciliation assistance — suggests matches, never auto-applies.
    
    All methods are read-only. Returns structured suggestions with
    confidence scores (0-100) for human-in-the-loop reconciliation.
    """

    @staticmethod
    def _compute_match_confidence(payment_amount, invoice_unpaid, payment_date, invoice_due_date) -> int:
        """Compute match confidence score 0-100.
        
        Factors:
        - Amount match (exact = 50, close = 30, partial = 10)
        - Date proximity (within 7 days = 30, within 30 = 20, within 90 = 10)
        - Invoice status (past due = 20, current = 10)
        """
        score = 0

        # Amount matching (50 points max)
        if payment_amount == invoice_unpaid:
            score += 50
        elif abs(payment_amount - invoice_unpaid) <= Decimal('1.00'):
            score += 40
        elif payment_amount < invoice_unpaid:
            score += 20
        else:
            score += 10

        # Date proximity (30 points max)
        if payment_date and invoice_due_date:
            try:
                from datetime import date
                if isinstance(payment_date, date) and isinstance(invoice_due_date, date):
                    days_diff = abs((payment_date - invoice_due_date).days)
                else:
                    days_diff = 30
            except (TypeError, ValueError):
                days_diff = 30

            if days_diff <= 7:
                score += 30
            elif days_diff <= 30:
                score += 20
            elif days_diff <= 90:
                score += 10
        else:
            score += 15

        # Invoice status urgency (20 points max)
        today = timezone.now().date()
        if invoice_due_date and invoice_due_date < today:
            score += 20
        else:
            score += 10

        return min(score, 100)

    @staticmethod
    def suggest_customer_matches(customer) -> list:
        """Suggest payment-invoice matches for a customer.
        
        Matches orphan/unallocated payments to outstanding invoices
        with confidence scores.
        """
        from sales.models import CustomerPayment, SalesInvoice, PaymentAllocation
        from core.services.financial_truth_engine import FinancialTruthEngine

        # Find unallocated payments for this customer
        allocated_ids = PaymentAllocation.objects.values_list('payment_id', flat=True)
        unallocated_payments = CustomerPayment.objects.filter(
            customer=customer,
            invoice__isnull=True,
        ).exclude(pk__in=allocated_ids)

        # Find outstanding invoices
        outstanding_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
        ).order_by('invoice_date')

        suggestions = []
        for payment in unallocated_payments:
            best_match = None
            best_score = 0

            for invoice in outstanding_invoices:
                unpaid = invoice.total_amount - invoice.paid_amount
                if unpaid <= Decimal('0.00'):
                    continue

                score = ReconciliationAssistanceV2._compute_match_confidence(
                    payment_amount=payment.amount,
                    invoice_unpaid=unpaid,
                    payment_date=payment.payment_date,
                    invoice_due_date=invoice.due_date,
                )

                if score > best_score:
                    best_score = score
                    best_match = {
                        'payment_id': str(payment.pk),
                        'payment_reference': payment.reference_number,
                        'payment_amount': str(payment.amount),
                        'payment_date': str(payment.payment_date),
                        'invoice_id': str(invoice.pk),
                        'invoice_number': invoice.invoice_number,
                        'invoice_total': str(invoice.total_amount),
                        'invoice_unpaid': str(unpaid),
                        'invoice_due_date': str(invoice.due_date),
                        'confidence_score': best_score,
                        'match_type': 'EXACT' if payment.amount == unpaid else 'PARTIAL',
                    }

            if best_match:
                suggestions.append(best_match)

        return suggestions

    @staticmethod
    def suggest_supplier_matches(supplier) -> list:
        """Suggest supplier payment-invoice matches.
        
        Mirrors customer matching for supplier parity.
        """
        from purchases.models import SupplierPayment, PurchaseInvoice, SupplierPaymentAllocation

        allocated_ids = SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        unallocated_payments = SupplierPayment.objects.filter(
            supplier=supplier,
            invoice__isnull=True,
        ).exclude(pk__in=allocated_ids)

        outstanding_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
        ).order_by('invoice_date')

        suggestions = []
        for payment in unallocated_payments:
            best_match = None
            best_score = 0

            for invoice in outstanding_invoices:
                unpaid = invoice.total_amount - invoice.paid_amount
                if unpaid <= Decimal('0.00'):
                    continue

                score = ReconciliationAssistanceV2._compute_match_confidence(
                    payment_amount=payment.amount,
                    invoice_unpaid=unpaid,
                    payment_date=payment.payment_date,
                    invoice_due_date=invoice.due_date,
                )

                if score > best_score:
                    best_score = score
                    best_match = {
                        'payment_id': str(payment.pk),
                        'payment_reference': payment.reference_number,
                        'payment_amount': str(payment.amount),
                        'payment_date': str(payment.payment_date),
                        'invoice_id': str(invoice.pk),
                        'invoice_number': invoice.invoice_number,
                        'invoice_total': str(invoice.total_amount),
                        'invoice_unpaid': str(unpaid),
                        'invoice_due_date': str(invoice.due_date),
                        'confidence_score': best_score,
                        'match_type': 'EXACT' if payment.amount == unpaid else 'PARTIAL',
                    }

            if best_match:
                suggestions.append(best_match)

        return suggestions

    @staticmethod
    def get_unresolved_items() -> dict:
        """Group all unresolved reconciliation items across the system.
        
        Returns:
            dict with 'orphan_payments', 'partial_settlements', 'mismatched_allocations'.
        """
        from sales.models import CustomerPayment, PaymentAllocation
        from purchases.models import SupplierPayment, SupplierPaymentAllocation

        # Orphan customer payments
        allocated_ids = PaymentAllocation.objects.values_list('payment_id', flat=True)
        orphan_customer = CustomerPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(pk__in=allocated_ids).values(
            'id', 'reference_number', 'amount', 'payment_date', 'customer__name'
        )[:50]

        # Orphan supplier payments
        supplier_allocated_ids = SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        orphan_supplier = SupplierPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(pk__in=supplier_allocated_ids).values(
            'id', 'reference_number', 'amount', 'payment_date', 'supplier__name'
        )[:50]

        # Partial settlements (invoices with paid_amount > 0 but not fully paid)
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice

        partial_customer = SalesInvoice.objects.filter(
            status='PARTIAL_PAID',
            is_active=True,
        ).values(
            'id', 'invoice_number', 'total_amount', 'paid_amount', 'customer__name'
        )[:50]

        partial_supplier = PurchaseInvoice.objects.filter(
            status='PARTIAL_PAID',
            is_active=True,
        ).values(
            'id', 'invoice_number', 'total_amount', 'paid_amount', 'supplier__name'
        )[:50]

        return {
            'orphan_payments': {
                'customer': list(orphan_customer),
                'supplier': list(orphan_supplier),
            },
            'partial_settlements': {
                'customer': list(partial_customer),
                'supplier': list(partial_supplier),
            },
            'summary': {
                'total_orphan_customer': len(orphan_customer),
                'total_orphan_supplier': len(orphan_supplier),
                'total_partial_customer': len(partial_customer),
                'total_partial_supplier': len(partial_supplier),
            },
        }

    @staticmethod
    def reconcile_invoice_payments(invoice) -> dict:
        """Trace all payments related to a specific invoice.
        
        Returns payment history, allocations, and reconciliation status.
        """
        from sales.models import SalesInvoice, PaymentAllocation
        from purchases.models import PurchaseInvoice, SupplierPaymentAllocation

        result = {
            'invoice_id': str(invoice.pk),
            'invoice_number': invoice.invoice_number,
            'total_amount': str(invoice.total_amount),
            'paid_amount': str(invoice.paid_amount),
            'remaining': str(invoice.total_amount - invoice.paid_amount),
            'status': invoice.status,
            'payments': [],
        }

        # Check if it's a sales invoice
        if hasattr(invoice, 'customer'):
            allocations = PaymentAllocation.objects.filter(
                invoice=invoice,
            ).select_related('payment')
            for alloc in allocations:
                result['payments'].append({
                    'payment_id': str(alloc.payment.pk),
                    'payment_number': alloc.payment.payment_number,
                    'amount': str(alloc.allocated_amount),
                    'date': str(alloc.payment.payment_date),
                    'method': alloc.payment.payment_method,
                })

            # Also check direct invoice-linked payments
            direct_payments = invoice.payments.filter(invoice=invoice)
            for p in direct_payments:
                result['payments'].append({
                    'payment_id': str(p.pk),
                    'payment_reference': p.reference_number,
                    'amount': str(p.amount),
                    'date': str(p.payment_date),
                    'method': p.payment_method,
                    'type': 'DIRECT',
                })

        # Check if it's a purchase invoice
        if hasattr(invoice, 'supplier'):
            allocations = SupplierPaymentAllocation.objects.filter(
                invoice=invoice,
            ).select_related('payment')
            for alloc in allocations:
                result['payments'].append({
                    'payment_id': str(alloc.payment.pk),
                    'payment_number': alloc.payment.payment_number,
                    'amount': str(alloc.allocated_amount),
                    'date': str(alloc.payment.payment_date),
                    'method': alloc.payment.payment_method,
                })

        return result
