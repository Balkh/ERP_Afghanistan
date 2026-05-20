"""Financial Explainability Layer — Read-Only Trace Visualization.

Answers "Why is this balance like this?" by tracing the full chain:
invoice → payment → allocation → journal entries.

Usage:
    trace = FinancialExplainability.explain_customer_balance(customer)
    chain = FinancialExplainability.trace_invoice(invoice)
"""
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone


class FinancialExplainability:
    """Read-only financial trace and explainability layer.
    
    Provides full audit trail visualization for any financial state.
    No writes, no mutations — pure trace computation.
    """

    @staticmethod
    def explain_customer_balance(customer) -> dict:
        """Explain why a customer has their current balance.
        
        Traces:
        - All contributing invoices
        - All payments received
        - FIFO allocations
        - Journal entries
        - Balance derivation
        """
        from sales.models import SalesInvoice, CustomerPayment, PaymentAllocation
        from accounting.models import JournalEntry
        from core.services.financial_truth_engine import FinancialTruthEngine

        derived_balance = FinancialTruthEngine.get_customer_balance(customer)

        # Invoice breakdown
        invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).order_by('invoice_date')

        invoice_breakdown = []
        total_invoice = Decimal('0.00')
        for inv in invoices:
            unpaid = inv.total_amount - inv.paid_amount
            total_invoice += inv.total_amount
            invoice_breakdown.append({
                'invoice_id': str(inv.pk),
                'invoice_number': inv.invoice_number,
                'total': str(inv.total_amount),
                'paid': str(inv.paid_amount),
                'unpaid': str(unpaid),
                'status': inv.status,
                'invoice_date': str(inv.invoice_date),
                'due_date': str(inv.due_date),
            })

        # Payment breakdown
        payments = CustomerPayment.objects.filter(
            customer=customer,
        ).order_by('payment_date')

        payment_breakdown = []
        total_payments = Decimal('0.00')
        for p in payments:
            total_payments += p.amount
            allocations = PaymentAllocation.objects.filter(payment=p)
            payment_breakdown.append({
                'payment_id': str(p.pk),
                'payment_reference': p.reference_number,
                'amount': str(p.amount),
                'date': str(p.payment_date),
                'method': p.payment_method,
                'linked_invoice': p.invoice.invoice_number if p.invoice else None,
                'fifo_allocations': [
                    {
                        'invoice_number': a.invoice.invoice_number,
                        'amount': str(a.allocated_amount),
                    }
                    for a in allocations
                ],
            })

        # Journal entry trace (via reference field matching)
        journal_entries = []
        for inv in invoices:
            jes = JournalEntry.objects.filter(reference=inv.invoice_number)
            for je in jes:
                journal_entries.append({
                    'entry_id': str(je.pk),
                    'entry_number': je.entry_number,
                    'date': str(je.entry_date),
                    'description': je.description,
                    'total_debit': str(je.total_debit),
                    'total_credit': str(je.total_credit),
                    'source_invoice': inv.invoice_number,
                })

        # Payment journal entries
        for p in payments:
            jes = JournalEntry.objects.filter(reference=p.reference_number) if p.reference_number else JournalEntry.objects.none()
            for je in jes:
                journal_entries.append({
                    'entry_id': str(je.pk),
                    'entry_number': je.entry_number,
                    'date': str(je.entry_date),
                    'description': je.description,
                    'total_debit': str(je.total_debit),
                    'total_credit': str(je.total_credit),
                    'source_payment': p.reference_number,
                })

        return {
            'customer_id': str(customer.pk),
            'customer_name': customer.name,
            'derived_balance': str(derived_balance),
            'stored_balance': str(customer.balance),
            'balance_matches': abs(derived_balance - customer.balance) <= Decimal('0.01'),
            'formula': 'derived_balance = sum(invoices) - sum(payments)',
            'total_invoices': str(total_invoice),
            'total_payments': str(total_payments),
            'computed_balance': str(total_invoice - total_payments),
            'invoice_breakdown': invoice_breakdown,
            'payment_breakdown': payment_breakdown,
            'journal_entries': journal_entries,
            'explanation': (
                f'Customer {customer.name} has a derived balance of {derived_balance} '
                f'from {len(invoice_breakdown)} invoices totaling {total_invoice} '
                f'and {len(payment_breakdown)} payments totaling {total_payments}.'
            ),
        }

    @staticmethod
    def explain_supplier_balance(supplier) -> dict:
        """Explain why a supplier has their current balance.
        
        Mirrors customer balance explanation for supplier parity.
        """
        from purchases.models import PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation
        from accounting.models import JournalEntry
        from core.services.financial_truth_engine import FinancialTruthEngine

        derived_balance = FinancialTruthEngine.get_supplier_balance(supplier)

        invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).order_by('invoice_date')

        invoice_breakdown = []
        total_invoice = Decimal('0.00')
        for inv in invoices:
            unpaid = inv.total_amount - inv.paid_amount
            total_invoice += inv.total_amount
            invoice_breakdown.append({
                'invoice_id': str(inv.pk),
                'invoice_number': inv.invoice_number,
                'total': str(inv.total_amount),
                'paid': str(inv.paid_amount),
                'unpaid': str(unpaid),
                'status': inv.status,
                'invoice_date': str(inv.invoice_date),
                'due_date': str(inv.due_date),
            })

        payments = SupplierPayment.objects.filter(
            supplier=supplier,
        ).order_by('payment_date')

        payment_breakdown = []
        total_payments = Decimal('0.00')
        for p in payments:
            total_payments += p.amount
            allocations = SupplierPaymentAllocation.objects.filter(payment=p)
            payment_breakdown.append({
                'payment_id': str(p.pk),
                'payment_reference': p.reference_number,
                'amount': str(p.amount),
                'date': str(p.payment_date),
                'method': p.payment_method,
                'linked_invoice': p.invoice.invoice_number if p.invoice else None,
                'fifo_allocations': [
                    {
                        'invoice_number': a.invoice.invoice_number,
                        'amount': str(a.allocated_amount),
                    }
                    for a in allocations
                ],
            })

        journal_entries = []
        for inv in invoices:
            jes = JournalEntry.objects.filter(reference=inv.invoice_number)
            for je in jes:
                journal_entries.append({
                    'entry_id': str(je.pk),
                    'entry_number': je.entry_number,
                    'date': str(je.entry_date),
                    'description': je.description,
                    'total_debit': str(je.total_debit),
                    'total_credit': str(je.total_credit),
                    'source_invoice': inv.invoice_number,
                })

        for p in payments:
            jes = JournalEntry.objects.filter(reference=p.reference_number) if p.reference_number else JournalEntry.objects.none()
            for je in jes:
                journal_entries.append({
                    'entry_id': str(je.pk),
                    'entry_number': je.entry_number,
                    'date': str(je.entry_date),
                    'description': je.description,
                    'total_debit': str(je.total_debit),
                    'total_credit': str(je.total_credit),
                    'source_payment': p.reference_number,
                })

        return {
            'supplier_id': str(supplier.pk),
            'supplier_name': supplier.name,
            'derived_balance': str(derived_balance),
            'stored_balance': str(supplier.balance),
            'balance_matches': abs(derived_balance - supplier.balance) <= Decimal('0.01'),
            'formula': 'derived_balance = sum(invoices) - sum(payments)',
            'total_invoices': str(total_invoice),
            'total_payments': str(total_payments),
            'computed_balance': str(total_invoice - total_payments),
            'invoice_breakdown': invoice_breakdown,
            'payment_breakdown': payment_breakdown,
            'journal_entries': journal_entries,
            'explanation': (
                f'Supplier {supplier.name} has a derived balance of {derived_balance} '
                f'from {len(invoice_breakdown)} invoices totaling {total_invoice} '
                f'and {len(payment_breakdown)} payments totaling {total_payments}.'
            ),
        }

    @staticmethod
    def trace_invoice(invoice) -> dict:
        """Full trace chain for a specific invoice.
        
        Returns: invoice → payments → allocations → journal entries.
        """
        from accounting.models import JournalEntry

        result = {
            'invoice_id': str(invoice.pk),
            'invoice_number': invoice.invoice_number,
            'total_amount': str(invoice.total_amount),
            'paid_amount': str(invoice.paid_amount),
            'remaining': str(invoice.total_amount - invoice.paid_amount),
            'status': invoice.status,
            'trace_chain': [],
        }

        # Determine entity type
        if hasattr(invoice, 'customer'):
            from sales.models import CustomerPayment, PaymentAllocation
            result['entity_type'] = 'SalesInvoice'
            result['party'] = invoice.customer.name

            # Direct payments
            direct_payments = invoice.payments.filter(invoice=invoice)
            for p in direct_payments:
                result['trace_chain'].append({
                    'type': 'DIRECT_PAYMENT',
                    'payment_reference': p.reference_number,
                    'amount': str(p.amount),
                    'date': str(p.payment_date),
                    'method': p.payment_method,
                })

            # FIFO allocations
            allocations = PaymentAllocation.objects.filter(invoice=invoice).select_related('payment')
            for a in allocations:
                result['trace_chain'].append({
                    'type': 'FIFO_ALLOCATION',
                    'payment_reference': a.payment.reference_number,
                    'allocated_amount': str(a.allocated_amount),
                    'date': str(a.allocated_at),
                    'notes': a.notes,
                })

        elif hasattr(invoice, 'supplier'):
            from purchases.models import SupplierPayment, SupplierPaymentAllocation
            result['entity_type'] = 'PurchaseInvoice'
            result['party'] = invoice.supplier.name

            direct_payments = invoice.supplierpayments.filter(invoice=invoice)
            for p in direct_payments:
                result['trace_chain'].append({
                    'type': 'DIRECT_PAYMENT',
                    'payment_reference': p.reference_number,
                    'amount': str(p.amount),
                    'date': str(p.payment_date),
                    'method': p.payment_method,
                })

            allocations = SupplierPaymentAllocation.objects.filter(invoice=invoice).select_related('payment')
            for a in allocations:
                result['trace_chain'].append({
                    'type': 'FIFO_ALLOCATION',
                    'payment_reference': a.payment.reference_number,
                    'allocated_amount': str(a.allocated_amount),
                    'date': str(a.allocated_at),
                    'notes': a.notes,
                })

        # Journal entries
        jes = JournalEntry.objects.filter(reference=invoice.invoice_number)
        for je in jes:
            result['trace_chain'].append({
                'type': 'JOURNAL_ENTRY',
                'entry_number': je.entry_number,
                'date': str(je.entry_date),
                'description': je.description,
                'total_debit': str(je.total_debit),
                'total_credit': str(je.total_credit),
                'posted': je.is_posted,
            })

        return result

    @staticmethod
    def trace_payment(payment) -> dict:
        """Full trace chain for a specific payment.
        
        Returns: payment → allocations → journal entries → affected invoices.
        """
        from accounting.models import JournalEntry

        result = {
            'payment_id': str(payment.pk),
            'payment_reference': payment.reference_number,
            'amount': str(payment.amount),
            'date': str(payment.payment_date),
            'method': payment.payment_method,
            'trace_chain': [],
        }

        if hasattr(payment, 'customer'):
            from sales.models import PaymentAllocation
            result['entity_type'] = 'CustomerPayment'
            result['party'] = payment.customer.name

            if payment.invoice:
                result['trace_chain'].append({
                    'type': 'DIRECT_INVOICE_LINK',
                    'invoice_number': payment.invoice.invoice_number,
                    'amount': str(payment.amount),
                })

            allocations = PaymentAllocation.objects.filter(payment=payment).select_related('invoice')
            for a in allocations:
                result['trace_chain'].append({
                    'type': 'FIFO_ALLOCATION',
                    'invoice_number': a.invoice.invoice_number,
                    'allocated_amount': str(a.allocated_amount),
                    'date': str(a.allocated_at),
                })

        elif hasattr(payment, 'supplier'):
            from purchases.models import SupplierPaymentAllocation
            result['entity_type'] = 'SupplierPayment'
            result['party'] = payment.supplier.name

            if payment.invoice:
                result['trace_chain'].append({
                    'type': 'DIRECT_INVOICE_LINK',
                    'invoice_number': payment.invoice.invoice_number,
                    'amount': str(payment.amount),
                })

            allocations = SupplierPaymentAllocation.objects.filter(payment=payment).select_related('invoice')
            for a in allocations:
                result['trace_chain'].append({
                    'type': 'FIFO_ALLOCATION',
                    'invoice_number': a.invoice.invoice_number,
                    'allocated_amount': str(a.allocated_amount),
                    'date': str(a.allocated_at),
                })

        # Journal entries for this payment
        jes = JournalEntry.objects.filter(reference=payment.reference_number) if payment.reference_number else JournalEntry.objects.none()
        for je in jes:
            result['trace_chain'].append({
                'type': 'JOURNAL_ENTRY',
                'entry_number': je.entry_number,
                'date': str(je.entry_date),
                'description': je.description,
                'total_debit': str(je.total_debit),
                'total_credit': str(je.total_credit),
                'posted': je.is_posted,
            })

        return result
