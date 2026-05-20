"""System Health Financial Diagnostics — Financial Correctness Health Check.

Extends system health from technical → financial correctness.
Checks SSOT consistency, ledger integrity, FIFO allocation status,
credit enforcement coverage, and reconciliation lag.

Outputs health_score (0-100), warnings, and critical flags.
NO automatic fixes.

Usage:
    health = FinancialDiagnostics.run_full_health_check()
    ssot_health = FinancialDiagnostics.check_ssot_consistency()
"""
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone


class FinancialDiagnostics:
    """Financial system health diagnostics — read-only assessment.
    
    Computes a health score (0-100) based on multiple financial
    integrity dimensions. All checks are read-only.
    """

    @staticmethod
    def check_ssot_consistency() -> dict:
        """Check SSOT (FinancialTruthEngine) consistency.
        
        Compares stored balances vs derived balances for all active
        customers and suppliers.
        """
        from sales.models import Customer
        from purchases.models import Supplier
        from core.services.financial_truth_engine import FinancialTruthEngine

        mismatches = []
        total_checked = 0

        for customer in Customer.objects.filter(status='ACTIVE')[:200]:
            total_checked += 1
            derived = FinancialTruthEngine.get_customer_balance(customer)
            stored = customer.balance
            if abs(derived - stored) > Decimal('0.01'):
                mismatches.append({
                    'entity_type': 'Customer',
                    'entity_id': str(customer.pk),
                    'entity_name': customer.name,
                    'stored_balance': str(stored),
                    'derived_balance': str(derived),
                    'difference': str(derived - stored),
                })

        for supplier in Supplier.objects.filter(status='ACTIVE')[:200]:
            total_checked += 1
            derived = FinancialTruthEngine.get_supplier_balance(supplier)
            stored = supplier.balance
            if abs(derived - stored) > Decimal('0.01'):
                mismatches.append({
                    'entity_type': 'Supplier',
                    'entity_id': str(supplier.pk),
                    'entity_name': supplier.name,
                    'stored_balance': str(stored),
                    'derived_balance': str(derived),
                    'difference': str(derived - stored),
                })

        consistency_pct = (
            ((total_checked - len(mismatches)) / total_checked * 100)
            if total_checked > 0 else 100
        )

        return {
            'total_entities_checked': total_checked,
            'mismatch_count': len(mismatches),
            'consistency_pct': round(consistency_pct, 1),
            'mismatches': mismatches[:20],
            'status': 'HEALTHY' if len(mismatches) == 0 else 'DEGRADED',
        }

    @staticmethod
    def check_ledger_integrity() -> dict:
        """Check ledger vs derived mismatch detection.
        
        Verifies that journal entries match invoice totals.
        """
        from accounting.models import JournalEntry
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice

        issues = []

        # Check sales invoices with journal entries
        for inv in SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        )[:100]:
            jes = JournalEntry.objects.filter(
                source_type='SalesInvoice',
                source_id=inv.pk,
            )
            if jes.exists():
                total_dr = sum(je.total_debit for je in jes)
                total_cr = sum(je.total_credit for je in jes)
                if abs(total_dr - total_cr) > Decimal('0.01'):
                    issues.append({
                        'type': 'UNBALANCED_JOURNAL',
                        'entity': f'SalesInvoice {inv.invoice_number}',
                        'detail': f'Debit ({total_dr}) != Credit ({total_cr})',
                        'severity': 'CRITICAL',
                    })
                if abs(total_dr - inv.total_amount) > Decimal('0.01'):
                    issues.append({
                        'type': 'INVOICE_JOURNAL_MISMATCH',
                        'entity': f'SalesInvoice {inv.invoice_number}',
                        'detail': f'Invoice total ({inv.total_amount}) != Journal sum ({total_dr})',
                        'severity': 'HIGH',
                    })

        # Check purchase invoices
        for inv in PurchaseInvoice.objects.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        )[:100]:
            jes = JournalEntry.objects.filter(
                source_type='PurchaseInvoice',
                source_id=inv.pk,
            )
            if jes.exists():
                total_dr = sum(je.total_debit for je in jes)
                total_cr = sum(je.total_credit for je in jes)
                if abs(total_dr - total_cr) > Decimal('0.01'):
                    issues.append({
                        'type': 'UNBALANCED_JOURNAL',
                        'entity': f'PurchaseInvoice {inv.invoice_number}',
                        'detail': f'Debit ({total_dr}) != Credit ({total_cr})',
                        'severity': 'CRITICAL',
                    })

        return {
            'issues_found': len(issues),
            'critical_count': sum(1 for i in issues if i['severity'] == 'CRITICAL'),
            'high_count': sum(1 for i in issues if i['severity'] == 'HIGH'),
            'issues': issues[:20],
            'status': 'HEALTHY' if len(issues) == 0 else 'DEGRADED',
        }

    @staticmethod
    def check_fifo_allocation_integrity() -> dict:
        """Check FIFO allocation integrity status.
        
        Identifies unallocated payments and allocation completeness.
        """
        from sales.models import CustomerPayment, PaymentAllocation
        from purchases.models import SupplierPayment, SupplierPaymentAllocation

        # Customer side
        customer_allocated_ids = PaymentAllocation.objects.values_list('payment_id', flat=True)
        unallocated_customer = CustomerPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(pk__in=customer_allocated_ids).count()
        total_customer_payments = CustomerPayment.objects.count()
        total_customer_allocations = PaymentAllocation.objects.count()

        # Supplier side
        supplier_allocated_ids = SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        unallocated_supplier = SupplierPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(pk__in=supplier_allocated_ids).count()
        total_supplier_payments = SupplierPayment.objects.count()
        total_supplier_allocations = SupplierPaymentAllocation.objects.count()

        total_unallocated = unallocated_customer + unallocated_supplier
        total_payments = total_customer_payments + total_supplier_payments
        allocation_rate = (
            ((total_payments - total_unallocated) / total_payments * 100)
            if total_payments > 0 else 100
        )

        return {
            'customer': {
                'total_payments': total_customer_payments,
                'total_allocations': total_customer_allocations,
                'unallocated_payments': unallocated_customer,
            },
            'supplier': {
                'total_payments': total_supplier_payments,
                'total_allocations': total_supplier_allocations,
                'unallocated_payments': unallocated_supplier,
            },
            'allocation_rate_pct': round(allocation_rate, 1),
            'total_unallocated': total_unallocated,
            'status': 'HEALTHY' if total_unallocated == 0 else 'WARNING',
        }

    @staticmethod
    def check_credit_enforcement_coverage() -> dict:
        """Check credit enforcement coverage completeness.
        
        Verifies that all active customers have credit limits set
        and that no blocked customers have outstanding transactions.
        """
        from sales.models import Customer, SalesInvoice
        from core.services.financial_truth_engine import FinancialTruthEngine

        total_active = Customer.objects.filter(status='ACTIVE').count()
        no_credit_limit = Customer.objects.filter(
            status='ACTIVE',
            credit_limit__lte=0,
        ).count()

        # Customers with high utilization (>80%)
        high_utilization = 0
        for customer in Customer.objects.filter(status='ACTIVE', credit_limit__gt=0)[:200]:
            balance = FinancialTruthEngine.get_customer_balance(customer)
            if customer.credit_limit > 0:
                utilization = balance / customer.credit_limit
                if utilization >= Decimal('0.8'):
                    high_utilization += 1

        # Blocked customers with outstanding balance
        blocked_with_balance = 0
        for customer in Customer.objects.filter(status='BLOCKED')[:100]:
            balance = FinancialTruthEngine.get_customer_balance(customer)
            if balance > Decimal('0.00'):
                blocked_with_balance += 1

        coverage_pct = (
            ((total_active - no_credit_limit) / total_active * 100)
            if total_active > 0 else 100
        )

        return {
            'total_active_customers': total_active,
            'customers_with_credit_limit': total_active - no_credit_limit,
            'customers_without_credit_limit': no_credit_limit,
            'credit_limit_coverage_pct': round(coverage_pct, 1),
            'high_utilization_count': high_utilization,
            'blocked_with_outstanding_balance': blocked_with_balance,
            'status': 'HEALTHY' if no_credit_limit == 0 and blocked_with_balance == 0 else 'WARNING',
        }

    @staticmethod
    def check_reconciliation_lag() -> dict:
        """Detect reconciliation lag.
        
        Measures how many payments are pending reconciliation
        (unallocated and unlinked to invoices).
        """
        from sales.models import CustomerPayment, PaymentAllocation
        from purchases.models import SupplierPayment, SupplierPaymentAllocation

        customer_allocated = PaymentAllocation.objects.values_list('payment_id', flat=True)
        lag_customer = CustomerPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(pk__in=customer_allocated)

        supplier_allocated = SupplierPaymentAllocation.objects.values_list('payment_id', flat=True)
        lag_supplier = SupplierPayment.objects.filter(
            invoice__isnull=True,
        ).exclude(pk__in=supplier_allocated)

        # Calculate average lag (days since payment for unallocated)
        today = timezone.now().date()
        lag_days_customer = []
        for p in lag_customer[:50]:
            try:
                days = (today - p.payment_date).days
                lag_days_customer.append(days)
            except (TypeError, ValueError):
                pass

        lag_days_supplier = []
        for p in lag_supplier[:50]:
            try:
                days = (today - p.payment_date).days
                lag_days_supplier.append(days)
            except (TypeError, ValueError):
                pass

        avg_lag_customer = sum(lag_days_customer) / len(lag_days_customer) if lag_days_customer else 0
        avg_lag_supplier = sum(lag_days_supplier) / len(lag_days_supplier) if lag_days_supplier else 0

        return {
            'unreconciled_customer_payments': lag_customer.count(),
            'unreconciled_supplier_payments': lag_supplier.count(),
            'total_unreconciled': lag_customer.count() + lag_supplier.count(),
            'avg_lag_days_customer': round(avg_lag_customer, 1),
            'avg_lag_days_supplier': round(avg_lag_supplier, 1),
            'status': 'HEALTHY' if lag_customer.count() == 0 and lag_supplier.count() == 0 else 'LAG_DETECTED',
        }

    @staticmethod
    def run_full_health_check() -> dict:
        """Run all financial health checks and compute overall score.
        
        Returns:
            dict with health_score (0-100), component scores, warnings,
            critical flags, and detailed results.
        """
        ssot = FinancialDiagnostics.check_ssot_consistency()
        ledger = FinancialDiagnostics.check_ledger_integrity()
        fifo = FinancialDiagnostics.check_fifo_allocation_integrity()
        credit = FinancialDiagnostics.check_credit_enforcement_coverage()
        reconciliation = FinancialDiagnostics.check_reconciliation_lag()

        # Compute health score (0-100)
        score = 100

        # SSOT consistency: -2 per mismatch (max -30)
        score -= min(ssot['mismatch_count'] * 2, 30)

        # Ledger integrity: -10 per critical, -5 per high (max -30)
        score -= min(ledger['critical_count'] * 10 + ledger['high_count'] * 5, 30)

        # FIFO allocation: -1 per unallocated payment (max -15)
        score -= min(fifo['total_unallocated'], 15)

        # Credit enforcement: -5 per customer without limit (max -15)
        score -= min(credit['customers_without_credit_limit'] * 5, 15)

        # Reconciliation lag: -2 per unreconciled payment (max -10)
        score -= min(reconciliation['total_unreconciled'] * 2, 10)

        score = max(0, score)

        # Warnings and critical flags
        warnings = []
        critical = []

        if ssot['mismatch_count'] > 0:
            warnings.append(f"{ssot['mismatch_count']} balance mismatches detected between stored and derived balances.")
        if ledger['critical_count'] > 0:
            critical.append(f"{ledger['critical_count']} unbalanced journal entries found.")
        if ledger['high_count'] > 0:
            warnings.append(f"{ledger['high_count']} invoice-journal mismatches found.")
        if fifo['total_unallocated'] > 0:
            warnings.append(f"{fifo['total_unallocated']} payments pending FIFO allocation.")
        if credit['customers_without_credit_limit'] > 0:
            warnings.append(f"{credit['customers_without_credit_limit']} active customers have no credit limit set.")
        if credit['blocked_with_outstanding_balance'] > 0:
            critical.append(f"{credit['blocked_with_outstanding_balance']} blocked customers still have outstanding balances.")
        if reconciliation['total_unreconciled'] > 0:
            warnings.append(f"{reconciliation['total_unreconciled']} payments pending reconciliation.")

        # Determine overall status
        if score >= 90:
            status = 'HEALTHY'
        elif score >= 70:
            status = 'GOOD'
        elif score >= 50:
            status = 'DEGRADED'
        elif score >= 30:
            status = 'WARNING'
        else:
            status = 'CRITICAL'

        return {
            'health_score': score,
            'status': status,
            'timestamp': timezone.now().isoformat(),
            'components': {
                'ssot_consistency': ssot,
                'ledger_integrity': ledger,
                'fifo_allocation': fifo,
                'credit_enforcement': credit,
                'reconciliation_lag': reconciliation,
            },
            'warnings': warnings,
            'critical': critical,
        }
