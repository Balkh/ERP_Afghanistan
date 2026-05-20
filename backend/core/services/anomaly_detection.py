"""Financial Anomaly Detection Engine — Read-Only Anomaly Scanner.

Detects inconsistencies across payment, invoice, and ledger domains
without modifying any financial state. Pure observation layer.

Usage:
    anomalies = AnomalyDetectionEngine.detect_all()
    payment_anomalies = AnomalyDetectionEngine.detect_payment_anomalies()
"""
from decimal import Decimal
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from core.services.financial_truth_engine import FinancialTruthEngine


class AnomalyType:
    ORPHAN_PAYMENT = 'ORPHAN_PAYMENT'
    OVERPAYMENT_EDGE = 'OVERPAYMENT_EDGE'
    DUPLICATE_SEMANTIC_PAYMENT = 'DUPLICATE_SEMANTIC_PAYMENT'
    UNPAID_PAST_DUE = 'UNPAID_PAST_DUE'
    CREDIT_NEAR_BREACH = 'CREDIT_NEAR_BREACH'
    INVOICE_SPIKE = 'INVOICE_SPIKE'
    LEDGER_INVOICE_MISMATCH = 'LEDGER_INVOICE_MISMATCH'
    MISSING_ALLOCATION_TRACE = 'MISSING_ALLOCATION_TRACE'
    ORPHAN_LEDGER_ENTRY = 'ORPHAN_LEDGER_ENTRY'
    SUPPLIER_OVERPAYMENT = 'SUPPLIER_OVERPAYMENT'
    SUPPLIER_UNPAID_PAST_DUE = 'SUPPLIER_UNPAID_PAST_DUE'
    NEGATIVE_BALANCE = 'NEGATIVE_BALANCE'


class Severity:
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class AnomalyDetectionEngine:
    """Read-only anomaly detection across financial domains.
    
    All methods are pure analysis — no writes, no mutations.
    Returns structured anomaly reports only.
    """

    @staticmethod
    def detect_payment_anomalies() -> list:
        """Detect payment-related anomalies.
        
        Scans for:
        - Orphan payments (no invoice linkage, no allocation)
        - Overpayment edge cases (payment > invoice total)
        - Duplicate semantic payments (same amount, same day, same party)
        """
        from sales.models import CustomerPayment, PaymentAllocation
        from purchases.models import SupplierPayment, SupplierPaymentAllocation

        anomalies = []

        # 1. Orphan customer payments
        orphan_customer_payments = CustomerPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(
            pk__in=PaymentAllocation.objects.values_list('payment_id', flat=True)
        )
        for p in orphan_customer_payments[:50]:
            anomalies.append({
                'anomaly_type': AnomalyType.ORPHAN_PAYMENT,
                'severity': Severity.MEDIUM,
                'entity_type': 'CustomerPayment',
                'entity_id': str(p.pk),
                'party': p.customer.name,
                'amount': str(p.amount),
                'date': str(p.payment_date),
                'explanation': f'Payment {p.reference_number} ({p.amount}) has no invoice linkage and no FIFO allocation.',
                'suggested_action': 'Run FIFO auto-allocation or manually link to an outstanding invoice.',
            })

        # 2. Orphan supplier payments
        orphan_supplier_payments = SupplierPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(
            pk__in=SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        )
        for p in orphan_supplier_payments[:50]:
            anomalies.append({
                'anomaly_type': AnomalyType.ORPHAN_PAYMENT,
                'severity': Severity.MEDIUM,
                'entity_type': 'SupplierPayment',
                'entity_id': str(p.pk),
                'party': p.supplier.name,
                'amount': str(p.amount),
                'date': str(p.payment_date),
                'explanation': f'Supplier payment {p.reference_number} ({p.amount}) has no invoice linkage and no FIFO allocation.',
                'suggested_action': 'Run supplier FIFO auto-allocation or manually link to an outstanding purchase invoice.',
            })

        # 3. Overpayment edge cases — customer payments exceeding invoice total
        from sales.models import SalesInvoice
        for invoice in SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).select_related('customer'):
            if invoice.paid_amount > invoice.total_amount:
                overpaid = invoice.paid_amount - invoice.total_amount
                anomalies.append({
                    'anomaly_type': AnomalyType.OVERPAYMENT_EDGE,
                    'severity': Severity.HIGH,
                    'entity_type': 'SalesInvoice',
                    'entity_id': str(invoice.pk),
                    'party': invoice.customer.name,
                    'amount': str(overpaid),
                    'date': str(invoice.invoice_date),
                    'explanation': f'Invoice {invoice.invoice_number} is overpaid by {overpaid} (paid: {invoice.paid_amount}, total: {invoice.total_amount}).',
                    'suggested_action': 'Review overpayment — may indicate duplicate payment or incorrect allocation.',
                })

        # 4. Supplier overpayment edge cases
        from purchases.models import PurchaseInvoice
        for invoice in PurchaseInvoice.objects.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).select_related('supplier'):
            if invoice.paid_amount > invoice.total_amount:
                overpaid = invoice.paid_amount - invoice.total_amount
                anomalies.append({
                    'anomaly_type': AnomalyType.SUPPLIER_OVERPAYMENT,
                    'severity': Severity.HIGH,
                    'entity_type': 'PurchaseInvoice',
                    'entity_id': str(invoice.pk),
                    'party': invoice.supplier.name,
                    'amount': str(overpaid),
                    'date': str(invoice.invoice_date),
                    'explanation': f'Purchase invoice {invoice.invoice_number} is overpaid by {overpaid}.',
                    'suggested_action': 'Review supplier overpayment.',
                })

        # 5. Duplicate semantic payments (same party, same amount, same day)
        customer_payment_groups = CustomerPayment.objects.values(
            'customer', 'amount', 'payment_date'
        ).annotate(count=Count('id')).filter(count__gt=1)
        for group in customer_payment_groups[:20]:
            payments = CustomerPayment.objects.filter(
                customer_id=group['customer'],
                amount=group['amount'],
                payment_date=group['payment_date'],
            )
            payment_ids = [str(p.pk) for p in payments]
            anomalies.append({
                'anomaly_type': AnomalyType.DUPLICATE_SEMANTIC_PAYMENT,
                'severity': Severity.MEDIUM,
                'entity_type': 'CustomerPayment',
                'entity_id': payment_ids[0],
                'party': payments.first().customer.name,
                'amount': str(group['amount']),
                'date': str(group['payment_date']),
                'explanation': f'{len(payment_ids)} customer payments with same amount ({group["amount"]}) on same date for same customer.',
                'suggested_action': f'Verify these are not duplicate entries: {", ".join(payment_ids[:5])}',
            })

        supplier_payment_groups = SupplierPayment.objects.values(
            'supplier', 'amount', 'payment_date'
        ).annotate(count=Count('id')).filter(count__gt=1)
        for group in supplier_payment_groups[:20]:
            payments = SupplierPayment.objects.filter(
                supplier_id=group['supplier'],
                amount=group['amount'],
                payment_date=group['payment_date'],
            )
            payment_ids = [str(p.pk) for p in payments]
            anomalies.append({
                'anomaly_type': AnomalyType.DUPLICATE_SEMANTIC_PAYMENT,
                'severity': Severity.MEDIUM,
                'entity_type': 'SupplierPayment',
                'entity_id': payment_ids[0],
                'party': payments.first().supplier.name,
                'amount': str(group['amount']),
                'date': str(group['payment_date']),
                'explanation': f'{len(payment_ids)} supplier payments with same amount ({group["amount"]}) on same date for same supplier.',
                'suggested_action': f'Verify these are not duplicate entries: {", ".join(payment_ids[:5])}',
            })

        return anomalies

    @staticmethod
    def detect_invoice_anomalies(days_past_due_threshold: int = 30) -> list:
        """Detect invoice-related anomalies.
        
        Scans for:
        - Unpaid invoices beyond due date threshold
        - Credit limit near-breach patterns (>80% utilization)
        - Unusual invoice spikes (customer with >5x average invoices in recent period)
        """
        from sales.models import SalesInvoice, Customer
        from purchases.models import PurchaseInvoice, Supplier
        from core.services.financial_truth_engine import FinancialTruthEngine

        anomalies = []
        today = timezone.now().date()
        threshold_date = today - timedelta(days=days_past_due_threshold)

        # 1. Unpaid past-due invoices (customer)
        past_due = SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lt=threshold_date,
        ).select_related('customer')
        for inv in past_due[:50]:
            unpaid = inv.total_amount - inv.paid_amount
            days_overdue = (today - inv.due_date).days
            anomalies.append({
                'anomaly_type': AnomalyType.UNPAID_PAST_DUE,
                'severity': Severity.HIGH if days_overdue > 60 else Severity.MEDIUM,
                'entity_type': 'SalesInvoice',
                'entity_id': str(inv.pk),
                'party': inv.customer.name,
                'amount': str(unpaid),
                'date': str(inv.due_date),
                'explanation': f'Invoice {inv.invoice_number} is {days_overdue} days past due with {unpaid} outstanding.',
                'suggested_action': 'Follow up with customer or escalate to collections.',
            })

        # 2. Unpaid past-due invoices (supplier)
        past_due_supplier = PurchaseInvoice.objects.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lt=threshold_date,
        ).select_related('supplier')
        for inv in past_due_supplier[:50]:
            unpaid = inv.total_amount - inv.paid_amount
            days_overdue = (today - inv.due_date).days
            anomalies.append({
                'anomaly_type': AnomalyType.SUPPLIER_UNPAID_PAST_DUE,
                'severity': Severity.HIGH if days_overdue > 60 else Severity.MEDIUM,
                'entity_type': 'PurchaseInvoice',
                'entity_id': str(inv.pk),
                'party': inv.supplier.name,
                'amount': str(unpaid),
                'date': str(inv.due_date),
                'explanation': f'Purchase invoice {inv.invoice_number} is {days_overdue} days past due with {unpaid} outstanding.',
                'suggested_action': 'Review supplier payment schedule.',
            })

        # 3. Credit limit near-breach (>80% utilization)
        for customer in Customer.objects.filter(
            status='ACTIVE',
            credit_limit__gt=0,
        ):
            balance = FinancialTruthEngine.get_customer_balance(customer)
            if customer.credit_limit > 0:
                utilization = balance / customer.credit_limit
                if utilization >= Decimal('0.8'):
                    anomalies.append({
                        'anomaly_type': AnomalyType.CREDIT_NEAR_BREACH,
                        'severity': Severity.CRITICAL if utilization >= Decimal('1.0') else Severity.HIGH,
                        'entity_type': 'Customer',
                        'entity_id': str(customer.pk),
                        'party': customer.name,
                        'amount': str(balance),
                        'date': str(today),
                        'explanation': f'Customer {customer.name} credit utilization is {utilization * 100:.1f}% ({balance}/{customer.credit_limit}).',
                        'suggested_action': 'Review credit limit or restrict new invoices.',
                    })

        # 4. Invoice spike detection (customers with >5 invoices in last 7 days)
        week_ago = today - timedelta(days=7)
        spike_customers = SalesInvoice.objects.filter(
            invoice_date__gte=week_ago,
            is_active=True,
        ).values('customer').annotate(
            count=Count('id')
        ).filter(count__gt=5)
        for entry in spike_customers[:20]:
            customer = Customer.objects.filter(pk=entry['customer']).first()
            if customer:
                anomalies.append({
                    'anomaly_type': AnomalyType.INVOICE_SPIKE,
                    'severity': Severity.LOW,
                    'entity_type': 'Customer',
                    'entity_id': str(customer.pk),
                    'party': customer.name,
                    'amount': str(entry['count']),
                    'date': str(today),
                    'explanation': f'Customer {customer.name} has {entry["count"]} invoices in the last 7 days.',
                    'suggested_action': 'Verify invoice volume is expected for this customer.',
                })

        return anomalies

    @staticmethod
    def detect_ledger_anomalies() -> list:
        """Detect ledger-related anomalies.
        
        Scans for:
        - Invoice total mismatch vs journal entry sum
        - Missing allocation traces (payments with no FIFO allocation and no direct invoice link)
        - Negative balance anomalies
        """
        from accounting.models import JournalEntry
        from sales.models import SalesInvoice, CustomerPayment, PaymentAllocation
        from purchases.models import PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation

        anomalies = []

        # 1. Invoice total mismatch vs journal sum
        for invoice in SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).select_related('customer')[:100]:
            journal_entries = JournalEntry.objects.filter(
                source_type='SalesInvoice',
                source_id=invoice.pk,
            )
            if journal_entries.exists():
                total_dr = sum(
                    je.total_debit for je in journal_entries
                ) if journal_entries else Decimal('0.00')
                if abs(total_dr - invoice.total_amount) > Decimal('0.01'):
                    anomalies.append({
                        'anomaly_type': AnomalyType.LEDGER_INVOICE_MISMATCH,
                        'severity': Severity.CRITICAL,
                        'entity_type': 'SalesInvoice',
                        'entity_id': str(invoice.pk),
                        'party': invoice.customer.name,
                        'amount': str(invoice.total_amount),
                        'date': str(invoice.invoice_date),
                        'explanation': f'Invoice {invoice.invoice_number} total ({invoice.total_amount}) does not match journal entries sum ({total_dr}).',
                        'suggested_action': 'Investigate journal entry creation for this invoice.',
                    })

        # 2. Missing allocation traces — customer payments with no invoice and no allocation
        unallocated_customer = CustomerPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(
            pk__in=PaymentAllocation.objects.values_list('payment_id', flat=True)
        ).count()
        if unallocated_customer > 0:
            anomalies.append({
                'anomaly_type': AnomalyType.MISSING_ALLOCATION_TRACE,
                'severity': Severity.MEDIUM,
                'entity_type': 'CustomerPayment',
                'entity_id': None,
                'party': None,
                'amount': str(unallocated_customer),
                'date': str(timezone.now().date()),
                'explanation': f'{unallocated_customer} customer payment(s) have no invoice linkage and no FIFO allocation trace.',
                'suggested_action': 'Run FIFO auto-allocation to link orphan payments to outstanding invoices.',
            })

        # 3. Missing allocation traces — supplier payments
        unallocated_supplier = SupplierPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(
            pk__in=SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        ).count()
        if unallocated_supplier > 0:
            anomalies.append({
                'anomaly_type': AnomalyType.MISSING_ALLOCATION_TRACE,
                'severity': Severity.MEDIUM,
                'entity_type': 'SupplierPayment',
                'entity_id': None,
                'party': None,
                'amount': str(unallocated_supplier),
                'date': str(timezone.now().date()),
                'explanation': f'{unallocated_supplier} supplier payment(s) have no invoice linkage and no FIFO allocation trace.',
                'suggested_action': 'Run supplier FIFO auto-allocation.',
            })

        # 4. Negative balance anomalies (customers/suppliers with negative derived balance)
        from sales.models import Customer
        from purchases.models import Supplier
        for customer in Customer.objects.filter(status='ACTIVE')[:200]:
            balance = FinancialTruthEngine.get_customer_balance(customer)
            if balance < Decimal('0.00'):
                anomalies.append({
                    'anomaly_type': AnomalyType.NEGATIVE_BALANCE,
                    'severity': Severity.HIGH,
                    'entity_type': 'Customer',
                    'entity_id': str(customer.pk),
                    'party': customer.name,
                    'amount': str(balance),
                    'date': str(timezone.now().date()),
                    'explanation': f'Customer {customer.name} has a negative derived balance of {balance} (overpaid or credit memo).',
                    'suggested_action': 'Review payment history and invoice adjustments.',
                })

        for supplier in Supplier.objects.filter(status='ACTIVE')[:200]:
            balance = FinancialTruthEngine.get_supplier_balance(supplier)
            if balance < Decimal('0.00'):
                anomalies.append({
                    'anomaly_type': AnomalyType.NEGATIVE_BALANCE,
                    'severity': Severity.HIGH,
                    'entity_type': 'Supplier',
                    'entity_id': str(supplier.pk),
                    'party': supplier.name,
                    'amount': str(balance),
                    'date': str(timezone.now().date()),
                    'explanation': f'Supplier {supplier.name} has a negative derived balance of {balance}.',
                    'suggested_action': 'Review supplier payment history.',
                })

        return anomalies

    @staticmethod
    def detect_all(days_past_due_threshold: int = 30) -> dict:
        """Run all anomaly detectors and return a structured report.
        
        Returns:
            dict with 'anomalies' list, 'summary' counts by severity, and 'scan_timestamp'.
        """
        payment_anomalies = AnomalyDetectionEngine.detect_payment_anomalies()
        invoice_anomalies = AnomalyDetectionEngine.detect_invoice_anomalies(days_past_due_threshold)
        ledger_anomalies = AnomalyDetectionEngine.detect_ledger_anomalies()

        all_anomalies = payment_anomalies + invoice_anomalies + ledger_anomalies

        # Bound result size
        all_anomalies = all_anomalies[:200]

        # Summary counts
        severity_counts = {Severity.LOW: 0, Severity.MEDIUM: 0, Severity.HIGH: 0, Severity.CRITICAL: 0}
        type_counts = {}
        for a in all_anomalies:
            severity_counts[a['severity']] = severity_counts.get(a['severity'], 0) + 1
            type_counts[a['anomaly_type']] = type_counts.get(a['anomaly_type'], 0) + 1

        return {
            'scan_timestamp': timezone.now().isoformat(),
            'total_anomalies': len(all_anomalies),
            'summary': {
                'by_severity': severity_counts,
                'by_type': type_counts,
            },
            'anomalies': all_anomalies,
        }
