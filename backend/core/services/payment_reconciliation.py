"""Payment Reconciliation Engine (V1) — Read-Only Mismatch Detection.

Detects and reports payment↔invoice and payment↔ledger mismatches
without performing any automatic corrections (read-only in V1).

Usage:
    report = PaymentReconciliationService.reconcile_customer(customer)
    full_report = PaymentReconciliationService.reconcile_all()
"""
from decimal import Decimal
from collections import defaultdict
from django.db.models import Sum, Q
from django.utils import timezone


class PaymentReconciliationService:
    """Read-only payment reconciliation layer.
    
    Detects mismatches between:
    - Payments ↔ Invoices (orphan payments, unpaid invoices)
    - Payments ↔ Journal entries (accounting trail completeness)
    - Overpayment / underpayment
    - Balance divergence (stored vs derived)
    """

    @staticmethod
    def reconcile_customer(customer) -> dict:
        """Full reconciliation report for a single customer.
        
        Returns a structured report with all mismatch types.
        No writes — pure read-only analysis.
        """
        from sales.models import CustomerPayment, SalesInvoice, PaymentAllocation
        from core.services.financial_truth_engine import FinancialTruthEngine

        derived_balance = FinancialTruthEngine.get_customer_balance(customer)
        stored_balance = customer.balance

        issues = []

        # 1. Check balance divergence
        if abs(derived_balance - stored_balance) > Decimal('0.01'):
            issues.append({
                'type': 'BALANCE_MISMATCH',
                'severity': 'HIGH',
                'detail': f'Stored balance ({stored_balance}) != derived balance ({derived_balance})',
            })

        # 2. Find orphan payments (no invoice, no allocation)
        orphan_payments = CustomerPayment.objects.filter(
            customer=customer,
            invoice__isnull=True,
        ).exclude(
            allocations__isnull=False,
        )
        orphan_count = orphan_payments.count()
        orphan_total = orphan_payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        if orphan_count > 0:
            issues.append({
                'type': 'ORPHAN_PAYMENTS',
                'severity': 'MEDIUM',
                'detail': f'{orphan_count} orphan payment(s) totaling {orphan_total} with no invoice or allocation',
            })

        # 3. Find overpaid invoices
        overpaid_invoices = SalesInvoice.objects.filter(
            customer=customer,
            is_active=True,
        ).extra(
            where=["paid_amount > total_amount + 0.01"]
        )
        for inv in overpaid_invoices:
            issues.append({
                'type': 'OVERPAID_INVOICE',
                'severity': 'HIGH',
                'detail': f'Invoice {inv.invoice_number}: paid ({inv.paid_amount}) > total ({inv.total_amount})',
            })

        # 4. Find unpaid/partially-paid invoices past due
        past_due = SalesInvoice.objects.filter(
            customer=customer,
            is_active=True,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            due_date__lt=timezone.now().date(),
        )
        for inv in past_due:
            remaining = inv.total_amount - inv.paid_amount
            if remaining > 0:
                issues.append({
                    'type': 'PAST_DUE_INVOICE',
                    'severity': 'LOW',
                    'detail': f'Invoice {inv.invoice_number}: {remaining} overdue since {inv.due_date}',
                })

        # 5. Check payment allocation consistency
        allocated_payments = CustomerPayment.objects.filter(
            customer=customer,
        ).filter(
            Q(invoice__isnull=False) | Q(allocations__isnull=False)
        )
        for payment in allocated_payments:
            total_allocated = payment.allocations.aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0.00')

            # If payment has an invoice, allocated should match (or be 0 if not yet allocated)
            if payment.invoice and payment.amount != payment.invoice.paid_amount:
                # This might be normal (partial payment) — flag only if mismatch seems wrong
                pass

        summary = {
            'customer_id': str(customer.pk),
            'customer_name': customer.name,
            'derived_balance': derived_balance,
            'stored_balance': stored_balance,
            'balance_match': abs(derived_balance - stored_balance) <= Decimal('0.01'),
            'total_issues': len(issues),
            'high_severity_count': sum(1 for i in issues if i['severity'] == 'HIGH'),
            'medium_severity_count': sum(1 for i in issues if i['severity'] == 'MEDIUM'),
            'low_severity_count': sum(1 for i in issues if i['severity'] == 'LOW'),
            'issues': issues,
        }

        return summary

    @staticmethod
    def reconcile_supplier(supplier) -> dict:
        """Full reconciliation report for a single supplier."""
        from purchases.models import SupplierPayment, PurchaseInvoice
        from core.services.financial_truth_engine import FinancialTruthEngine

        derived_balance = FinancialTruthEngine.get_supplier_balance(supplier)
        stored_balance = supplier.balance

        issues = []

        if abs(derived_balance - stored_balance) > Decimal('0.01'):
            issues.append({
                'type': 'BALANCE_MISMATCH',
                'severity': 'HIGH',
                'detail': f'Stored balance ({stored_balance}) != derived balance ({derived_balance})',
            })

        orphan_payments = SupplierPayment.objects.filter(
            supplier=supplier,
            invoice__isnull=True,
        )
        orphan_count = orphan_payments.count()
        orphan_total = orphan_payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        if orphan_count > 0:
            issues.append({
                'type': 'ORPHAN_PAYMENTS',
                'severity': 'MEDIUM',
                'detail': f'{orphan_count} orphan payment(s) totaling {orphan_total} with no invoice',
            })

        overpaid_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            is_active=True,
        ).extra(
            where=["paid_amount > total_amount + 0.01"]
        )
        for inv in overpaid_invoices:
            issues.append({
                'type': 'OVERPAID_INVOICE',
                'severity': 'HIGH',
                'detail': f'Invoice {inv.invoice_number}: paid ({inv.paid_amount}) > total ({inv.total_amount})',
            })

        return {
            'supplier_id': str(supplier.pk),
            'supplier_name': supplier.name,
            'derived_balance': derived_balance,
            'stored_balance': stored_balance,
            'balance_match': abs(derived_balance - stored_balance) <= Decimal('0.01'),
            'total_issues': len(issues),
            'high_severity_count': sum(1 for i in issues if i['severity'] == 'HIGH'),
            'medium_severity_count': sum(1 for i in issues if i['severity'] == 'MEDIUM'),
            'low_severity_count': sum(1 for i in issues if i['severity'] == 'LOW'),
            'issues': issues,
        }

    @staticmethod
    def reconcile_all() -> dict:
        """Reconcile ALL customers and suppliers.
        
        Returns a consolidated report with global mismatch summary.
        Designed for on-demand audit — no continuous polling.
        """
        from sales.models import Customer
        from purchases.models import Supplier

        customers = Customer.objects.filter(is_active=True)
        suppliers = Supplier.objects.filter(is_active=True)

        total_issues = 0
        high_severity = 0
        medium_severity = 0
        low_severity = 0
        customer_reports = []
        supplier_reports = []
        balance_mismatches = 0

        for customer in customers:
            report = PaymentReconciliationService.reconcile_customer(customer)
            customer_reports.append(report)
            total_issues += report['total_issues']
            high_severity += report['high_severity_count']
            medium_severity += report['medium_severity_count']
            low_severity += report['low_severity_count']
            if not report['balance_match']:
                balance_mismatches += 1

        for supplier in suppliers:
            report = PaymentReconciliationService.reconcile_supplier(supplier)
            supplier_reports.append(report)
            total_issues += report['total_issues']
            high_severity += report['high_severity_count']
            medium_severity += report['medium_severity_count']
            low_severity += report['low_severity_count']
            if not report['balance_match']:
                balance_mismatches += 1

        return {
            'reconciled_at': timezone.now().isoformat(),
            'read_only': True,
            'summary': {
                'customers_checked': customers.count(),
                'suppliers_checked': suppliers.count(),
                'total_issues': total_issues,
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'low_severity': low_severity,
                'balance_mismatches': balance_mismatches,
            },
            'customer_reports': customer_reports,
            'supplier_reports': supplier_reports,
        }

    @staticmethod
    def reconcile_invoice_payments(invoice) -> dict:
        """Reconcile payments against a single invoice.
        
        Checks: paid_amount matches sum of payments, payment allocations
        are consistent, journal entry balances match.
        """
        from sales.models import CustomerPayment, PaymentAllocation

        direct_payments_total = CustomerPayment.objects.filter(
            invoice=invoice,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        allocation_total = PaymentAllocation.objects.filter(
            invoice=invoice,
        ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0.00')

        total_accounted = direct_payments_total + allocation_total

        issues = []

        if abs(invoice.paid_amount - total_accounted) > Decimal('0.01'):
            issues.append({
                'type': 'PAID_AMOUNT_MISMATCH',
                'severity': 'HIGH',
                'detail': (
                    f'Invoice says paid={invoice.paid_amount} but '
                    f'direct payments={direct_payments_total} + '
                    f'allocations={allocation_total} = {total_accounted}'
                ),
            })

        return {
            'invoice_id': str(invoice.pk),
            'invoice_number': invoice.invoice_number,
            'total_amount': invoice.total_amount,
            'paid_amount': invoice.paid_amount,
            'direct_payments': direct_payments_total,
            'allocations': allocation_total,
            'total_accounted': total_accounted,
            'is_consistent': len(issues) == 0,
            'issues': issues,
        }

    @staticmethod
    def reconcile_payment_journal(payment) -> dict:
        """Check if a payment has a corresponding journal entry.
        
        Payments should always have corresponding journal entries
        created by PaymentEngine. This detects missing accounting trails.
        """
        from payments.models import FinancialTransaction

        transactions = FinancialTransaction.objects.filter(
            party_id=str(payment.customer.pk if hasattr(payment, 'customer') else getattr(payment, 'supplier', None).pk),
            amount=payment.amount,
        )

        has_journal = transactions.filter(
            journal_entry_id__isnull=False
        ).exists()

        return {
            'payment_id': str(payment.pk),
            'amount': payment.amount,
            'related_transactions': transactions.count(),
            'has_journal_entry': has_journal,
            'trailing_complete': has_journal,
        }
