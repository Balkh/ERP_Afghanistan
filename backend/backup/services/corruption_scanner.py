"""
Lightweight integrity scanners that detect silent corruption in the database.

CorruptionScanner performs read-only checks to identify data anomalies that
may indicate silent corruption, including impossible timestamps, broken
foreign keys, duplicated identifiers, and impossible accounting states.

All checks are:
    - Lightweight (no heavy queries)
    - Low CPU usage
    - No permanent background loops
    - No mutations (read-only)
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Count, Q, Sum, F

logger = logging.getLogger('erp.backup.corruption_scanner')


class CorruptionScanner:
    """Lightweight integrity scanner for silent corruption detection.

    Performs read-only checks across critical tables to detect anomalies
    that may indicate data corruption. Returns a structured result dict.

    Returns:
        {
            'valid': bool,
            'scans': [{'name': str, 'passed': bool, 'details': str, 'count': int}],
            'errors': [str],
            'warnings': [str],
        }
    """

    SYSTEM_INCEPTION_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)

    def __init__(self):
        self.scans: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def scan(self) -> Dict[str, Any]:
        """Run all corruption scans and return results."""
        self._scan_missing_critical_records()
        self._scan_impossible_timestamps()
        self._scan_broken_foreign_keys()
        self._scan_duplicated_identifiers()
        self._scan_impossible_accounting_states()
        self._scan_inventory_accounting_mismatch()

        return {
            'valid': len(self.errors) == 0,
            'scans': self.scans,
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def _add_scan(self, name: str, passed: bool, details: str, count: int = 0):
        """Record a scan result."""
        self.scans.append({
            'name': name,
            'passed': passed,
            'details': details,
            'count': count,
        })

    def _scan_missing_critical_records(self):
        """Check if essential tables have at least some records."""
        from accounting.models import Account
        from inventory.models import Product

        issues = []

        account_count = Account.objects.count()
        if account_count == 0:
            issues.append('No accounts found in chart of accounts')

        product_count = Product.objects.count()
        if product_count == 0:
            issues.append('No products found in inventory')

        passed = len(issues) == 0
        total = account_count + product_count

        if not passed:
            for issue in issues:
                self.errors.append(f"Missing critical records: {issue}")

        self._add_scan(
            name='missing_critical_records',
            passed=passed,
            details='Essential tables must contain baseline records',
            count=len(issues),
        )

    def _scan_impossible_timestamps(self):
        """Detect records with future dates or dates before system inception."""
        now = datetime.now(timezone.utc)
        issues = []

        self._check_model_timestamps(
            'accounting.Account',
            'Account',
            now,
            issues,
        )
        self._check_model_timestamps(
            'inventory.Product',
            'Product',
            now,
            issues,
        )
        self._check_model_timestamps(
            'sales.SalesInvoice',
            'SalesInvoice',
            now,
            issues,
        )
        self._check_model_timestamps(
            'purchases.PurchaseInvoice',
            'PurchaseInvoice',
            now,
            issues,
        )

        passed = len(issues) == 0

        if not passed:
            for issue in issues:
                self.warnings.append(f"Impossible timestamps: {issue}")

        self._add_scan(
            name='impossible_timestamps',
            passed=passed,
            details='Records must have timestamps within valid range',
            count=len(issues),
        )

    def _check_model_timestamps(
        self, model_path: str, label: str, now: datetime, issues: List[str]
    ):
        """Check a single model for impossible timestamps."""
        try:
            model = self._resolve_model(model_path)
            if model is None:
                return

            future_count = model.objects.filter(created_at__gt=now).count()
            if future_count > 0:
                issues.append(f"{label}: {future_count} records with future dates")

            old_count = model.objects.filter(
                created_at__lt=self.SYSTEM_INCEPTION_DATE
            ).count()
            if old_count > 0:
                issues.append(
                    f"{label}: {old_count} records before system inception"
                )
        except Exception as e:
            logger.warning(f"Timestamp check failed for {model_path}: {e}")

    def _scan_broken_foreign_keys(self):
        """Detect FK references to non-existent records using Django ORM."""
        from accounting.models import JournalEntryLine, Account
        from inventory.models import StockMovement, Product, Batch, Warehouse

        issues = []

        orphaned_lines = JournalEntryLine.objects.filter(
            Q(account__isnull=True) | ~Q(account__in=Account.objects.all())
        ).count()
        if orphaned_lines > 0:
            issues.append(
                f"JournalEntryLine: {orphaned_lines} orphaned account references"
            )

        orphaned_movements = StockMovement.objects.filter(
            Q(product__isnull=True) | ~Q(product__in=Product.objects.all())
        ).count()
        if orphaned_movements > 0:
            issues.append(
                f"StockMovement: {orphaned_movements} orphaned product references"
            )

        orphaned_batches = StockMovement.objects.filter(
            batch__isnull=False,
        ).exclude(
            batch__in=Batch.objects.all()
        ).count()
        if orphaned_batches > 0:
            issues.append(
                f"StockMovement: {orphaned_batches} orphaned batch references"
            )

        orphaned_warehouses = StockMovement.objects.filter(
            Q(warehouse__isnull=True) | ~Q(warehouse__in=Warehouse.objects.all())
        ).count()
        if orphaned_warehouses > 0:
            issues.append(
                f"StockMovement: {orphaned_warehouses} orphaned warehouse references"
            )

        passed = len(issues) == 0

        if not passed:
            for issue in issues:
                self.errors.append(f"Broken foreign keys: {issue}")

        self._add_scan(
            name='broken_foreign_keys',
            passed=passed,
            details='All foreign key references must point to existing records',
            count=len(issues),
        )

    def _scan_duplicated_identifiers(self):
        """Detect duplicate unique fields across critical tables."""
        from accounting.models import Account
        from inventory.models import Product, Batch

        issues = []

        dup_accounts = (
            Account.objects.values('code')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .count()
        )
        if dup_accounts > 0:
            issues.append(f"Account: {dup_accounts} duplicate account codes")

        dup_products = (
            Product.objects.values('code')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .count()
        )
        if dup_products > 0:
            issues.append(f"Product: {dup_products} duplicate product codes")

        dup_batches = (
            Batch.objects.values('batch_number')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .count()
        )
        if dup_batches > 0:
            issues.append(f"Batch: {dup_batches} duplicate batch numbers")

        passed = len(issues) == 0

        if not passed:
            for issue in issues:
                self.errors.append(f"Duplicated identifiers: {issue}")

        self._add_scan(
            name='duplicated_identifiers',
            passed=passed,
            details='Unique identifiers must not have duplicates',
            count=len(issues),
        )

    def _scan_impossible_accounting_states(self):
        """Detect accounts with impossible balances."""
        from accounting.models import Account, JournalEntryLine

        issues = []

        asset_accounts = Account.objects.filter(
            account_type='ASSET',
            is_active=True,
        )
        for account in asset_accounts:
            balance = self._get_account_balance(account)
            if balance < 0:
                issues.append(
                    f"Asset account {account.code} ({account.name}) "
                    f"has negative balance: {balance}"
                )

        liability_accounts = Account.objects.filter(
            account_type='LIABILITY',
            is_active=True,
        )
        for account in liability_accounts:
            balance = self._get_account_balance(account)
            if balance > 0:
                issues.append(
                    f"Liability account {account.code} ({account.name}) "
                    f"has positive balance: {balance}"
                )

        passed = len(issues) == 0

        if not passed:
            for issue in issues:
                self.warnings.append(f"Impossible accounting state: {issue}")

        self._add_scan(
            name='impossible_accounting_states',
            passed=passed,
            details='Account balances must match expected sign for account type',
            count=len(issues),
        )

    def _scan_inventory_accounting_mismatch(self):
        """Compare inventory value with accounting records."""
        from inventory.models import Product, Batch
        from accounting.models import Account

        issues = []

        total_inventory_value = Decimal('0.00')
        for batch in Batch.objects.filter(is_active=True):
            batch_value = batch.remaining_quantity * batch.unit_cost
            total_inventory_value += batch_value

        inventory_account = Account.objects.filter(
            code='1200',
            is_active=True,
        ).first()

        if inventory_account:
            ledger_balance = self._get_account_balance(inventory_account)
            diff = abs(ledger_balance - total_inventory_value)

            if diff > Decimal('1.00'):
                issues.append(
                    f"Inventory value mismatch: ledger={ledger_balance}, "
                    f"calculated={total_inventory_value}, diff={diff}"
                )

        passed = len(issues) == 0

        if not passed:
            for issue in issues:
                self.warnings.append(f"Inventory-accounting mismatch: {issue}")

        self._add_scan(
            name='inventory_accounting_mismatch',
            passed=passed,
            details='Inventory ledger balance should match calculated stock value',
            count=len(issues),
        )

    def _get_account_balance(self, account) -> Decimal:
        """Calculate account balance from journal entry lines."""
        from accounting.models import JournalEntryLine

        totals = JournalEntryLine.objects.filter(
            account=account,
            entry__is_posted=True,
            entry__is_active=True,
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )

        total_debit = totals['total_debit'] or Decimal('0.00')
        total_credit = totals['total_credit'] or Decimal('0.00')

        if account.account_type in ('ASSET', 'EXPENSE'):
            return total_debit - total_credit
        else:
            return total_credit - total_debit

    def _resolve_model(self, model_path: str):
        """Resolve a dotted model path to a Django model class."""
        try:
            app_label, model_name = model_path.split('.')
            from django.apps import apps
            return apps.get_model(app_label, model_name)
        except Exception:
            return None
