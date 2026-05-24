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

    @staticmethod
    def explain_journal_entry(entry) -> dict:
        """Explain why a journal entry exists and its impact."""
        from accounting.models import JournalEntryLine, JournalEventLog

        lines = JournalEntryLine.objects.filter(entry=entry).select_related('account')
        line_details = []
        for line in lines:
            line_details.append({
                'account_code': line.account.code,
                'account_name': line.account.name,
                'account_type': line.account.account_type,
                'debit': str(line.debit),
                'credit': str(line.credit),
                'description': line.description,
            })

        reversal_chain = []
        if entry.original_entry:
            reversal_chain.append({
                'entry_id': str(entry.original_entry.id),
                'entry_number': entry.original_entry.entry_number,
                'relationship': 'reverses',
            })
        if hasattr(entry, 'reversed_by_entry') and entry.reversed_by_entry:
            reversal_chain.append({
                'entry_id': str(entry.reversed_by_entry.id),
                'entry_number': entry.reversed_by_entry.entry_number,
                'relationship': 'reversed_by',
            })

        event_history = JournalEventLog.objects.filter(entry=entry).order_by('-timestamp')[:20]
        events = []
        for event in event_history:
            events.append({
                'event_type': event.event_type,
                'timestamp': str(event.timestamp),
                'user': str(event.user) if event.user else 'System',
                'notes': event.notes,
            })

        return {
            'entry_id': str(entry.id),
            'entry_number': entry.entry_number,
            'entry_type': entry.entry_type,
            'entry_date': str(entry.entry_date),
            'description': entry.description,
            'reference': entry.reference,
            'is_posted': entry.is_posted,
            'posted_at': str(entry.posted_at) if entry.posted_at else None,
            'posted_by': entry.posted_by,
            'created_by': entry.created_by,
            'source_module': entry.source_module or '',
            'source_document': entry.source_document or '',
            'total_debit': str(entry.total_debit),
            'total_credit': str(entry.total_credit),
            'is_balanced': abs(entry.total_debit - entry.total_credit) <= Decimal('0.01'),
            'line_count': len(line_details),
            'lines': line_details,
            'reversal_chain': reversal_chain,
            'event_history': events,
            'explanation': (
                f'Journal entry {entry.entry_number} ({entry.entry_type}) was created on '
                f'{entry.entry_date} for {entry.description}. '
                f'{"Posted" if entry.is_posted else "Not posted"} '
                f'with {len(line_details)} line(s) totaling {entry.total_debit}.'
            ),
        }

    @staticmethod
    def explain_return(return_order) -> dict:
        """Explain a return order's full impact."""
        from accounting.models import JournalEntry

        result = {
            'return_id': str(return_order.id),
            'return_number': return_order.return_number if hasattr(return_order, 'return_number') else str(return_order.id),
            'status': return_order.status,
            'return_date': str(return_order.return_date) if hasattr(return_order, 'return_date') else None,
            'total_amount': str(return_order.total_amount) if hasattr(return_order, 'total_amount') else '0.00',
            'original_invoice': None,
            'inventory_impact': [],
            'accounting_impact': [],
            'refund_impact': [],
            'reversal_linkage': [],
            'explanation': '',
        }

        if hasattr(return_order, 'invoice') and return_order.invoice:
            result['original_invoice'] = {
                'invoice_id': str(return_order.invoice.id),
                'invoice_number': return_order.invoice.invoice_number,
                'total_amount': str(return_order.invoice.total_amount),
            }

        if hasattr(return_order, 'items'):
            for item in return_order.items.all():
                result['inventory_impact'].append({
                    'product': item.product.name if hasattr(item, 'product') and item.product else '',
                    'quantity': str(item.quantity),
                    'reason': item.reason if hasattr(item, 'reason') else '',
                })

        if hasattr(return_order, 'reversal_journal_entry') and return_order.reversal_journal_entry:
            je = return_order.reversal_journal_entry
            result['accounting_impact'].append({
                'entry_id': str(je.id),
                'entry_number': je.entry_number,
                'entry_type': je.entry_type,
                'total_debit': str(je.total_debit),
                'total_credit': str(je.total_credit),
                'is_posted': je.is_posted,
            })

        jes = JournalEntry.objects.filter(
            reference=return_order.return_number if hasattr(return_order, 'return_number') else str(return_order.id)
        )
        for je in jes:
            result['accounting_impact'].append({
                'entry_id': str(je.id),
                'entry_number': je.entry_number,
                'entry_type': je.entry_type,
                'total_debit': str(je.total_debit),
                'total_credit': str(je.total_credit),
                'is_posted': je.is_posted,
            })

        if hasattr(return_order, 'refund_payment') and return_order.refund_payment:
            result['refund_impact'].append({
                'payment_id': str(return_order.refund_payment.id),
                'amount': str(return_order.refund_payment.amount),
                'method': str(return_order.refund_payment.payment_method),
                'date': str(return_order.refund_payment.payment_date),
            })

        if hasattr(return_order, 'voided_at') and return_order.voided_at:
            result['reversal_linkage'].append({
                'action': 'VOIDED',
                'voided_at': str(return_order.voided_at),
                'voided_by': str(return_order.voided_by) if hasattr(return_order, 'voided_by') and return_order.voided_by else 'Unknown',
                'reason': return_order.void_reason if hasattr(return_order, 'void_reason') else '',
            })

        result['explanation'] = (
            f'Return {result["return_number"]} was created on {result["return_date"]} '
            f'for {result["total_amount"]}. '
            f'Status: {result["status"]}. '
            f'{"Voided" if hasattr(return_order, "voided_at") and return_order.voided_at else "Active"}.'
        )

        return result

    @staticmethod
    def explain_asset(asset) -> dict:
        """Explain a fixed asset's lifecycle and accounting impact."""
        from accounting.models import JournalEntry

        result = {
            'asset_id': str(asset.id),
            'asset_code': asset.code if hasattr(asset, 'code') else '',
            'asset_name': asset.name if hasattr(asset, 'name') else str(asset),
            'category': asset.category.name if hasattr(asset, 'category') and asset.category else '',
            'acquisition_date': str(asset.acquisition_date) if hasattr(asset, 'acquisition_date') else None,
            'acquisition_cost': str(asset.acquisition_cost) if hasattr(asset, 'acquisition_cost') else '0.00',
            'salvage_value': str(asset.salvage_value) if hasattr(asset, 'salvage_value') else '0.00',
            'useful_life_years': asset.useful_life_years if hasattr(asset, 'useful_life_years') else 0,
            'depreciation_method': asset.depreciation_method if hasattr(asset, 'depreciation_method') else '',
            'current_book_value': str(asset.current_book_value) if hasattr(asset, 'current_book_value') else '0.00',
            'accumulated_depreciation': str(asset.accumulated_depreciation) if hasattr(asset, 'accumulated_depreciation') else '0.00',
            'status': asset.status if hasattr(asset, 'status') else '',
            'depreciation_schedule': [],
            'journal_entries': [],
            'disposal_info': None,
            'explanation': '',
        }

        if hasattr(asset, 'depreciations'):
            for dep in asset.depreciations.all().order_by('depreciation_date'):
                result['depreciation_schedule'].append({
                    'date': str(dep.depreciation_date),
                    'amount': str(dep.amount),
                    'accumulated': str(dep.accumulated_depreciation) if hasattr(dep, 'accumulated_depreciation') else '',
                    'journal_entry': dep.journal_entry.entry_number if hasattr(dep, 'journal_entry') and dep.journal_entry else None,
                })

        if hasattr(asset, 'disposal') and asset.disposal:
            result['disposal_info'] = {
                'disposal_date': str(asset.disposal.disposal_date),
                'sale_price': str(asset.disposal.sale_price) if hasattr(asset.disposal, 'sale_price') else '0.00',
                'gain_loss': str(asset.disposal.gain_loss) if hasattr(asset.disposal, 'gain_loss') else '0.00',
            }

        jes = JournalEntry.objects.filter(
            source_document=f'FixedAsset:{asset.id}'
        ).order_by('entry_date')
        for je in jes:
            result['journal_entries'].append({
                'entry_id': str(je.id),
                'entry_number': je.entry_number,
                'entry_type': je.entry_type,
                'date': str(je.entry_date),
                'description': je.description,
                'total_debit': str(je.total_debit),
                'total_credit': str(je.total_credit),
            })

        result['explanation'] = (
            f'Asset {result["asset_name"]} was acquired on {result["acquisition_date"]} '
            f'for {result["acquisition_cost"]}. '
            f'Current book value: {result["current_book_value"]}. '
            f'Accumulated depreciation: {result["accumulated_depreciation"]}. '
            f'Status: {result["status"]}.'
        )

        return result
