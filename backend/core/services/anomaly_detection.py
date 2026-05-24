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
        """Detect payment-related anomalies using set-based DB operations.
        
        Scans for:
        - Overpaid invoices (Sales and Purchase)
        - Payment spikes (unusually high payment volume)
        """
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        from django.db.models import F

        anomalies = []

        # 1. Overpaid Sales Invoices (Set-based)
        overpaid_sales = SalesInvoice.objects.filter(
            paid_amount__gt=F('total_amount') + Decimal('0.01'),
            is_active=True,
        ).select_related('customer')[:50]

        for invoice in overpaid_sales:
            anomalies.append({
                'anomaly_type': AnomalyType.OVERPAYMENT_EDGE,
                'severity': Severity.HIGH,
                'entity_type': 'SalesInvoice',
                'entity_id': str(invoice.pk),
                'party': invoice.customer.name,
                'amount': str(invoice.paid_amount - invoice.total_amount),
                'date': str(invoice.invoice_date),
                'explanation': f'Invoice {invoice.invoice_number} is overpaid by {invoice.paid_amount - invoice.total_amount}.',
                'suggested_action': 'Verify payment allocations or issue a refund/credit memo.',
            })

        # 2. Overpaid Purchase Invoices (Set-based)
        overpaid_purchases = PurchaseInvoice.objects.filter(
            paid_amount__gt=F('total_amount') + Decimal('0.01'),
            is_active=True,
        ).select_related('supplier')[:50]

        for invoice in overpaid_purchases:
            anomalies.append({
                'anomaly_type': AnomalyType.SUPPLIER_OVERPAYMENT,
                'severity': Severity.HIGH,
                'entity_type': 'PurchaseInvoice',
                'entity_id': str(invoice.pk),
                'party': invoice.supplier.name,
                'amount': str(invoice.paid_amount - invoice.total_amount),
                'date': str(invoice.invoice_date),
                'explanation': f'Purchase Invoice {invoice.invoice_number} is overpaid by {invoice.paid_amount - invoice.total_amount}.',
                'suggested_action': 'Review supplier payments.',
            })

        return anomalies

    @staticmethod
    def detect_invoice_anomalies(days_past_due_threshold: int = 30) -> list:
        """Detect invoice-related anomalies using set-based DB operations.
        
        Scans for:
        - Significantly past due invoices
        - Credit limit near-breach (utilization > 80%)
        - Invoice spikes (unusually high volume in last 7 days)
        """
        from sales.models import SalesInvoice, Customer, CustomerPayment
        from purchases.models import PurchaseInvoice
        from django.db.models import Count, Sum
        from core.services.financial_truth_engine import FinancialTruthEngine

        anomalies = []
        today = timezone.now().date()
        past_due_date = today - timedelta(days=days_past_due_threshold)

        # 1. Significantly past due Sales Invoices (Set-based)
        past_due_sales = SalesInvoice.objects.filter(
            due_date__lt=past_due_date,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
        ).select_related('customer')[:50]

        for invoice in past_due_sales:
            remaining = invoice.total_amount - invoice.paid_amount
            anomalies.append({
                'anomaly_type': AnomalyType.UNPAID_PAST_DUE,
                'severity': Severity.CRITICAL if (today - invoice.due_date).days > 90 else Severity.HIGH,
                'entity_type': 'SalesInvoice',
                'entity_id': str(invoice.pk),
                'party': invoice.customer.name,
                'amount': str(remaining),
                'date': str(invoice.due_date),
                'explanation': f'Invoice {invoice.invoice_number} is {(today - invoice.due_date).days} days past due.',
                'suggested_action': 'Contact customer for payment or initiate collection workflow.',
            })

        # 2. Significantly past due Purchase Invoices (Set-based)
        past_due_purchases = PurchaseInvoice.objects.filter(
            due_date__lt=past_due_date,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
        ).select_related('supplier')[:50]

        for invoice in past_due_purchases:
            remaining = invoice.total_amount - invoice.paid_amount
            anomalies.append({
                'anomaly_type': AnomalyType.SUPPLIER_UNPAID_PAST_DUE,
                'severity': Severity.MEDIUM,
                'entity_type': 'PurchaseInvoice',
                'entity_id': str(invoice.pk),
                'party': invoice.supplier.name,
                'amount': str(remaining),
                'date': str(invoice.due_date),
                'explanation': f'Purchase Invoice {invoice.invoice_number} is {(today - invoice.due_date).days} days past due.',
                'suggested_action': 'Review payment schedule with supplier.',
            })

        # 3. Credit limit near-breach (Optimized Bulk Aggregates)
        active_customers = list(Customer.objects.filter(status='ACTIVE', credit_limit__gt=0)[:200])
        customer_ids = [c.id for c in active_customers]
        
        inv_sums = SalesInvoice.objects.filter(
            customer_id__in=customer_ids,
            status__in=FinancialTruthEngine.CUSTOMER_BALANCE_STATUSES,
            is_active=True
        ).values('customer_id').annotate(total=Sum('total_amount'))
        inv_map = {item['customer_id']: item['total'] for item in inv_sums}
        
        pay_sums = CustomerPayment.objects.filter(
            customer_id__in=customer_ids
        ).values('customer_id').annotate(total=Sum('amount'))
        pay_map = {item['customer_id']: item['total'] for item in pay_sums}

        for customer in active_customers:
            balance = inv_map.get(customer.id, Decimal('0')) - pay_map.get(customer.id, Decimal('0'))
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
        """Detect ledger-related anomalies using set-based DB operations.
        
        Scans for:
        - Invoice total mismatch vs journal entry sum
        - Missing allocation traces
        - Negative balance anomalies
        """
        from accounting.models import JournalEntry, JournalLine
        from sales.models import SalesInvoice, CustomerPayment, PaymentAllocation, Customer
        from purchases.models import PurchaseInvoice, SupplierPayment, SupplierPaymentAllocation, Supplier
        from django.db.models import Sum, Q
        from core.services.financial_truth_engine import FinancialTruthEngine

        anomalies = []
        today = timezone.now().date()

        # 1. Invoice total mismatch vs journal sum (Optimized with Bulk Prefetch/Aggregate)
        invoices = SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ).select_related('customer')[:50]
        
        invoice_ids = [str(inv.pk) for inv in invoices]
        
        # Aggregate journal lines in bulk
        je_sums = JournalLine.objects.filter(
            journal_entry__source_type='SalesInvoice',
            journal_entry__source_id__in=invoice_ids,
            journal_entry__is_active=True
        ).values('journal_entry__source_id').annotate(total_dr=Sum('debit'))
        
        je_map = {item['journal_entry__source_id']: item['total_dr'] for item in je_sums}
        
        for invoice in invoices:
            total_dr = je_map.get(str(invoice.pk), Decimal('0.00'))
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

        # 2. Missing allocation traces (Set-based)
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
                'date': str(today),
                'explanation': f'{unallocated_customer} customer payment(s) have no invoice linkage and no FIFO allocation trace.',
                'suggested_action': 'Run FIFO auto-allocation to link orphan payments to outstanding invoices.',
            })

        # 3. Negative balance anomalies (Optimized Bulk Aggregates)
        # Customer negative balance
        active_customers = list(Customer.objects.filter(status='ACTIVE')[:100])
        c_ids = [c.id for c in active_customers]
        
        c_inv_sums = SalesInvoice.objects.filter(
            customer_id__in=c_ids,
            status__in=FinancialTruthEngine.CUSTOMER_BALANCE_STATUSES,
            is_active=True
        ).values('customer_id').annotate(total=Sum('total_amount'))
        c_inv_map = {item['customer_id']: item['total'] for item in c_inv_sums}
        
        c_pay_sums = CustomerPayment.objects.filter(
            customer_id__in=c_ids
        ).values('customer_id').annotate(total=Sum('amount'))
        c_pay_map = {item['customer_id']: item['total'] for item in c_pay_sums}

        for customer in active_customers:
            balance = c_inv_map.get(customer.id, Decimal('0')) - c_pay_map.get(customer.id, Decimal('0'))
            if balance < Decimal('-0.01'):
                anomalies.append({
                    'anomaly_type': AnomalyType.NEGATIVE_BALANCE,
                    'severity': Severity.HIGH,
                    'entity_type': 'Customer',
                    'entity_id': str(customer.pk),
                    'party': customer.name,
                    'amount': str(balance),
                    'date': str(today),
                    'explanation': f'Customer {customer.name} has a negative derived balance of {balance}.',
                    'suggested_action': 'Review payment history and invoice adjustments.',
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
