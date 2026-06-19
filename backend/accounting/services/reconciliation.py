"""
Accounting Reconciliation Service
===================================
Verifies integrity between operational data and accounting records.
Detects drift, missing entries, and balance discrepancies.
"""

from decimal import Decimal
from datetime import date
from typing import Optional, Dict, List
from django.db.models import Sum, Q, Count

from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Batch, StockMovement
from sales.models import SalesInvoice, CustomerPayment
from purchases.models import PurchaseInvoice, SupplierPayment
from payments.models import FinancialTransaction


class ReconciliationResult:
    """Container for reconciliation check results."""

    def __init__(self, name: str):
        self.name = name
        self.checks: List[Dict] = []
        self.is_healthy = True

    def add_check(self, name: str, passed: bool, detail: str = '', expected=None, actual=None):
        check = {
            'name': name,
            'passed': passed,
            'detail': detail,
        }
        if expected is not None:
            check['expected'] = str(expected)
        if actual is not None:
            check['actual'] = str(actual)
        self.checks.append(check)
        if not passed:
            self.is_healthy = False


class AccountingReconciliationService:
    """
    Verifies accounting integrity across all modules.
    Run periodically or on-demand to detect data drift.
    """

    @staticmethod
    def reconcile_inventory_vs_accounting(as_of_date: Optional[date] = None) -> ReconciliationResult:
        """
        Verify inventory account balance matches sum of stock valuations.
        
        Compares:
        - Sum of (batch.remaining_quantity * batch.purchase_price)
        - Accounting balance on inventory account (1300)
        """
        from accounting.services.financial_reports import FinancialReportEngine

        result = ReconciliationResult('Inventory vs Accounting')

        # Calculate total inventory value from operational data
        batches = Batch.objects.filter(
            remaining_quantity__gt=0,
            is_active=True
        ).select_related('product')

        total_operational_value = Decimal('0.00')
        batch_count = 0
        negative_cost_batches = []

        for batch in batches:
            if batch.purchase_price and batch.purchase_price > 0:
                batch_value = (batch.remaining_quantity * batch.purchase_price).quantize(Decimal('0.01'))
                total_operational_value += batch_value
                batch_count += 1
            elif batch.purchase_price is not None and batch.purchase_price <= 0:
                negative_cost_batches.append(batch.batch_number)

        # Get accounting balance for inventory account
        try:
            inventory_account = Account.objects.get(code='1300', is_active=True)
            ledger = FinancialReportEngine.get_account_ledger(inventory_account.id, end_date=as_of_date)
            accounting_balance = ledger.get('closing_balance', Decimal('0.00'))
        except Account.DoesNotExist:
            accounting_balance = None

        result.add_check(
            'inventory_account_exists',
            inventory_account is not None if 'inventory_account' in dir() else accounting_balance is not None,
            'Inventory account (1300) must exist'
        )

        result.add_check(
            'batch_count_positive',
            batch_count > 0,
            f'Found {batch_count} batches with positive purchase price'
        )

        if accounting_balance is not None:
            difference = abs(total_operational_value - accounting_balance)
            tolerance = Decimal('0.02')  # Allow small rounding differences

            result.add_check(
                'value_match',
                difference <= tolerance,
                f'Operational value vs accounting balance difference: {difference}',
                expected=str(accounting_balance),
                actual=str(total_operational_value)
            )

            if difference > tolerance:
                result.add_check(
                    'difference_within_reasonable_range',
                    difference < Decimal('10000'),
                    f'Difference of {difference} - may indicate missing journal entries'
                )

        if negative_cost_batches:
            result.add_check(
                'no_negative_costs',
                False,
                f'Batches with zero/negative purchase price: {negative_cost_batches[:10]}'
            )

        return result

    @staticmethod
    def reconcile_sales_journal_entries(as_of_date: Optional[date] = None) -> ReconciliationResult:
        """
        Verify all dispatched sales invoices have corresponding journal entries.
        """
        result = ReconciliationResult('Sales Journal Entries')

        # Find dispatched invoices without journal entries
        invoices_without_je = SalesInvoice.objects.filter(
            status='DISPATCHED',
            is_active=True,
            journal_entry_id__isnull=True
        )

        result.add_check(
            'all_dispatched_have_je',
            invoices_without_je.count() == 0,
            f'{invoices_without_je.count()} dispatched invoices missing journal entries'
        )

        # Find journal entries referencing non-existent invoices
        sale_journal_entries = JournalEntry.objects.filter(
            entry_type='SALE',
            is_posted=True,
            is_active=True
        )

        orphan_count = 0
        for je in sale_journal_entries:
            if not SalesInvoice.objects.filter(
                journal_entry_id=je.id, is_active=True
            ).exists():
                orphan_count += 1

        result.add_check(
            'no_orphan_sale_journal_entries',
            orphan_count == 0,
            f'{orphan_count} orphan sale journal entries found'
        )

        return result

    @staticmethod
    def reconcile_purchase_journal_entries(as_of_date: Optional[date] = None) -> ReconciliationResult:
        """
        Verify all received purchase invoices have corresponding journal entries.
        """
        result = ReconciliationResult('Purchase Journal Entries')

        # Find received invoices without journal entries
        invoices_without_je = PurchaseInvoice.objects.filter(
            status='RECEIVED',
            is_active=True,
            journal_entry_id__isnull=True
        )

        result.add_check(
            'all_received_have_je',
            invoices_without_je.count() == 0,
            f'{invoices_without_je.count()} received invoices missing journal entries'
        )

        # Find journal entries referencing non-existent purchases
        purchase_journal_entries = JournalEntry.objects.filter(
            entry_type='PURCHASE',
            is_posted=True,
            is_active=True
        )

        orphan_count = 0
        for je in purchase_journal_entries:
            if not PurchaseInvoice.objects.filter(
                journal_entry_id=je.id, is_active=True
            ).exists():
                orphan_count += 1

        result.add_check(
            'no_orphan_purchase_journal_entries',
            orphan_count == 0,
            f'{orphan_count} orphan purchase journal entries found'
        )

        return result

    @staticmethod
    def reconcile_payment_transactions() -> ReconciliationResult:
        """
        Verify all payment transactions have journal entries.
        Check for duplicate journal entries.
        """
        result = ReconciliationResult('Payment Transactions')

        # Find completed transactions without journal entries
        txns_without_je = FinancialTransaction.objects.filter(
            status='COMPLETED',
            journal_entry_id__isnull=True,
            is_active=True
        )

        # Exclude certain types that may not have journal entries yet
        critical_txns = txns_without_je.exclude(transaction_type='TRANSFER')

        result.add_check(
            'all_completed_have_je',
            critical_txns.count() == 0,
            f'{critical_txns.count()} completed transactions missing journal entries'
        )

        # Check for duplicate journal entries on single transaction
        txns_with_dupe_je = FinancialTransaction.objects.filter(
            status='COMPLETED',
            is_active=True
        ).exclude(journal_entry_id__isnull=True).values('journal_entry_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        result.add_check(
            'no_duplicate_journal_entries',
            txns_with_dupe_je.count() == 0,
            f'{txns_with_dupe_je.count()} journal entries linked to multiple transactions'
        )

        return result

    @staticmethod
    def reconcile_journal_entry_balances() -> ReconciliationResult:
        """
        Verify all posted journal entries are balanced (debits = credits).
        """
        result = ReconciliationResult('Journal Entry Balances')

        posted_entries = JournalEntry.objects.filter(
            is_posted=True,
            is_active=True
        ).select_related()

        unbalanced_count = 0
        unbalanced_entries = []

        for entry in posted_entries:
            if not entry.is_balanced:
                unbalanced_count += 1
                unbalanced_entries.append({
                    'entry_number': entry.entry_number,
                    'total_debit': str(entry.total_debit),
                    'total_credit': str(entry.total_credit),
                    'difference': str(entry.total_debit - entry.total_credit),
                })

        result.add_check(
            'all_posted_balanced',
            unbalanced_count == 0,
            f'{unbalanced_count} unbalanced posted entries',
        )

        if unbalanced_entries:
            result.add_check(
                'unbalanced_entries_detail',
                False,
                f'Unbalanced entries: {unbalanced_entries[:5]}'
            )

        return result

    @staticmethod
    def reconcile_customer_balances() -> ReconciliationResult:
        """
        Verify customer balances match accounting AR balances.
        """
        result = ReconciliationResult('Customer Balances')

        from sales.models import Customer

        # Get AR account balance
        try:
            ar_account = Account.objects.get(code='1200', is_active=True)
            from accounting.services.financial_reports import FinancialReportEngine
            ledger = FinancialReportEngine.get_account_ledger(ar_account.id)
            ar_balance = ledger.get('closing_balance', Decimal('0.00'))
        except Account.DoesNotExist:
            ar_balance = None
            result.add_check('ar_account_exists', False, 'AR account (1200) not found')

        # Sum customer balances
        total_customer_balance = Customer.objects.filter(
            is_active=True
        ).aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

        if ar_balance is not None:
            difference = abs(total_customer_balance - ar_balance)
            result.add_check(
                'customer_balance_match',
                difference <= Decimal('0.02'),
                f'Sum of customer balances ({total_customer_balance}) vs AR account ({ar_balance})',
                expected=str(ar_balance),
                actual=str(total_customer_balance),
            )

        return result

    @staticmethod
    def reconcile_supplier_balances() -> ReconciliationResult:
        """
        Verify supplier balances match accounting AP balances.
        """
        result = ReconciliationResult('Supplier Balances')

        from purchases.models import Supplier

        try:
            ap_account = Account.objects.get(code='2100', is_active=True)
            from accounting.services.financial_reports import FinancialReportEngine
            ledger = FinancialReportEngine.get_account_ledger(ap_account.id)
            ap_balance = ledger.get('closing_balance', Decimal('0.00'))
        except Account.DoesNotExist:
            ap_balance = None
            result.add_check('ap_account_exists', False, 'AP account (2100) not found')

        total_supplier_balance = Supplier.objects.filter(
            is_active=True
        ).aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

        if ap_balance is not None:
            difference = abs(total_supplier_balance - ap_balance)
            result.add_check(
                'supplier_balance_match',
                difference <= Decimal('0.02'),
                f'Sum of supplier balances ({total_supplier_balance}) vs AP account ({ap_balance})',
                expected=str(ap_balance),
                actual=str(total_supplier_balance),
            )

        return result

    @staticmethod
    def full_reconciliation(as_of_date: Optional[date] = None) -> Dict:
        """
        Run ALL reconciliation checks and return comprehensive report.
        """
        checks = [
            AccountingReconciliationService.reconcile_inventory_vs_accounting(as_of_date),
            AccountingReconciliationService.reconcile_sales_journal_entries(as_of_date),
            AccountingReconciliationService.reconcile_purchase_journal_entries(as_of_date),
            AccountingReconciliationService.reconcile_payment_transactions(),
            AccountingReconciliationService.reconcile_journal_entry_balances(),
            AccountingReconciliationService.reconcile_customer_balances(),
            AccountingReconciliationService.reconcile_supplier_balances(),
        ]

        all_healthy = all(c.is_healthy for c in checks)
        total_checks = sum(len(c.checks) for c in checks)
        passed_checks = sum(1 for c in checks for ch in c.checks if ch['passed'])
        failed_checks = total_checks - passed_checks

        return {
            'is_healthy': all_healthy,
            'summary': {
                'total_checks': total_checks,
                'passed': passed_checks,
                'failed': failed_checks,
            },
            'results': [
                {
                    'name': r.name,
                    'is_healthy': r.is_healthy,
                    'checks': r.checks,
                }
                for r in checks
            ],
        }