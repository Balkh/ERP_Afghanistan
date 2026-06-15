"""
Recovery validation services for backup/restore system.

Provides read-only validators that check data integrity after a restore operation.
These validators NEVER mutate data — they only read and report.
"""

import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q, F

logger = logging.getLogger('erp.backup.recovery')


class AccountingRecoveryValidator:
    """Validates accounting data integrity after restore.

    Checks performed (all read-only):
    - Journal entry balance (debits == credits per entry)
    - Debit/credit equality across all entries
    - Invoice-payment consistency
    - Ledger integrity
    - Orphaned transaction detection
    - Duplicate posting detection
    - Account hierarchy integrity

    Returns a dict with:
        {
            'valid': bool,
            'checks': [{'name': str, 'passed': bool, 'details': str, 'count': int}],
            'errors': [str],
            'warnings': [str],
        }
    """

    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []

    def validate(self) -> dict:
        """Run all accounting recovery checks and return results."""
        self._check_journal_entry_balance()
        self._check_debit_credit_equality()
        self._check_invoice_payment_consistency()
        self._check_ledger_integrity()
        self._check_orphaned_transactions()
        self._check_duplicate_posting()
        self._check_account_hierarchy()

        return {
            'valid': len(self.errors) == 0,
            'checks': self.checks,
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def _add_check(self, name: str, passed: bool, details: str, count: int = 0):
        self.checks.append({
            'name': name,
            'passed': passed,
            'details': details,
            'count': count,
        })

    def _check_journal_entry_balance(self):
        """Verify each posted journal entry has debits == credits."""
        from accounting.models import JournalEntry, JournalEntryLine

        unbalanced = []
        posted_entries = JournalEntry.objects.filter(is_posted=True, is_active=True)

        for entry in posted_entries:
            totals = entry.lines.aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit'),
            )
            total_debit = totals['total_debit'] or Decimal('0.00')
            total_credit = totals['total_credit'] or Decimal('0.00')
            if total_debit != total_credit:
                unbalanced.append(entry.entry_number)

        passed = len(unbalanced) == 0
        if not passed:
            self.errors.append(
                f"Found {len(unbalanced)} unbalanced journal entries: "
                f"{', '.join(unbalanced[:5])}"
                f"{'...' if len(unbalanced) > 5 else ''}"
            )

        self._add_check(
            name='journal_entry_balance',
            passed=passed,
            details='Each posted journal entry must have equal debits and credits',
            count=len(unbalanced),
        )

    def _check_debit_credit_equality(self):
        """Verify total debits == total credits across ALL journal entries."""
        from accounting.models import JournalEntryLine

        totals = JournalEntryLine.objects.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        total_debit = totals['total_debit'] or Decimal('0.00')
        total_credit = totals['total_credit'] or Decimal('0.00')
        diff = abs(total_debit - total_credit)

        passed = diff == Decimal('0.00')
        if not passed:
            self.errors.append(
                f"Global debit/credit mismatch: debits={total_debit}, "
                f"credits={total_credit}, difference={diff}"
            )

        self._add_check(
            name='debit_credit_equality',
            passed=passed,
            details='Sum of all debits must equal sum of all credits',
            count=1 if not passed else 0,
        )

    def _check_invoice_payment_consistency(self):
        """Verify sales/purchase invoice paid_amount matches sum of payments."""
        from sales.models import SalesInvoice, CustomerPayment
        from purchases.models import PurchaseInvoice, SupplierPayment

        inconsistencies = []

        # Check sales invoices
        for invoice in SalesInvoice.objects.filter(
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ):
            total_payments = CustomerPayment.objects.filter(
                invoice=invoice,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            if invoice.paid_amount != total_payments:
                inconsistencies.append(
                    f"Sales invoice {invoice.invoice_number}: "
                    f"paid_amount={invoice.paid_amount}, "
                    f"sum_payments={total_payments}"
                )

        # Check purchase invoices
        for invoice in PurchaseInvoice.objects.filter(
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID'],
            is_active=True,
        ):
            total_payments = SupplierPayment.objects.filter(
                invoice=invoice,
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            if invoice.paid_amount != total_payments:
                inconsistencies.append(
                    f"Purchase invoice {invoice.invoice_number}: "
                    f"paid_amount={invoice.paid_amount}, "
                    f"sum_payments={total_payments}"
                )

        passed = len(inconsistencies) == 0
        if not passed:
            self.errors.append(
                f"Found {len(inconsistencies)} invoice-payment inconsistencies: "
                f"{', '.join(inconsistencies[:5])}"
                f"{'...' if len(inconsistencies) > 5 else ''}"
            )

        self._add_check(
            name='invoice_payment_consistency',
            passed=passed,
            details='Invoice paid_amount must match sum of related payment records',
            count=len(inconsistencies),
        )

    def _check_ledger_integrity(self):
        """Verify every journal entry line references a valid active account."""
        from accounting.models import JournalEntryLine

        orphaned_lines = JournalEntryLine.objects.filter(
            Q(account__isnull=True) | Q(account__is_active=False)
        ).count()

        # Check for lines referencing non-existent accounts via raw count
        total_lines = JournalEntryLine.objects.count()
        valid_lines = JournalEntryLine.objects.filter(
            account__is_active=True,
        ).count()

        passed = orphaned_lines == 0
        if not passed:
            self.errors.append(
                f"Found {orphaned_lines} journal entry lines referencing "
                f"inactive or missing accounts"
            )

        self._add_check(
            name='ledger_integrity',
            passed=passed,
            details='All journal entry lines must reference valid active accounts',
            count=orphaned_lines,
        )

    def _check_orphaned_transactions(self):
        """Detect financial transactions with no valid invoice or party linkage."""
        from payments.models import FinancialTransaction

        # Transactions with party_type set but no party_id
        orphaned_party = FinancialTransaction.objects.filter(
            party_type__in=['CUSTOMER', 'SUPPLIER', 'EMPLOYEE'],
            party_id__isnull=True,
            is_active=True,
        ).count()

        # Transactions with invoice_type set but no invoice_id
        orphaned_invoice = FinancialTransaction.objects.filter(
            invoice_type__in=['SALES', 'PURCHASE'],
            invoice_id__isnull=True,
            is_active=True,
        ).count()

        total_orphaned = orphaned_party + orphaned_invoice
        passed = total_orphaned == 0

        if not passed:
            self.errors.append(
                f"Found {total_orphaned} orphaned financial transactions "
                f"({orphaned_party} missing party, {orphaned_invoice} missing invoice)"
            )
        elif orphaned_party > 0 or orphaned_invoice > 0:
            self.warnings.append(
                f"{total_orphaned} transactions have incomplete linkage "
                f"(may be intentional for adjustments)"
            )

        self._add_check(
            name='orphaned_transactions',
            passed=passed,
            details='Financial transactions should have valid party/invoice references',
            count=total_orphaned,
        )

    def _check_duplicate_posting(self):
        """Detect journal entries with duplicate entry_numbers."""
        from accounting.models import JournalEntry

        duplicates = (
            JournalEntry.objects.values('entry_number')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        dup_count = duplicates.count()
        passed = dup_count == 0

        if not passed:
            dup_numbers = [d['entry_number'] for d in duplicates[:10]]
            self.errors.append(
                f"Found {dup_count} duplicate journal entry numbers: "
                f"{', '.join(dup_numbers)}"
            )

        self._add_check(
            name='duplicate_posting',
            passed=passed,
            details='No duplicate journal entry numbers should exist',
            count=dup_count,
        )

    def _check_account_hierarchy(self):
        """Verify account parent references have no circular references."""
        from accounting.models import Account

        circular = []
        accounts_with_parent = Account.objects.filter(parent__isnull=False)

        for account in accounts_with_parent:
            visited = set()
            current = account
            has_cycle = False
            while current.parent is not None:
                if current.id in visited:
                    has_cycle = True
                    break
                visited.add(current.id)
                current = current.parent
            if has_cycle:
                circular.append(account.code)

        passed = len(circular) == 0
        if not passed:
            self.errors.append(
                f"Found {len(circular)} accounts with circular parent references: "
                f"{', '.join(circular[:5])}"
                f"{'...' if len(circular) > 5 else ''}"
            )

        # Also check for orphaned parent references
        orphaned_parents = Account.objects.filter(
            parent__isnull=False,
        ).exclude(
            parent__in=Account.objects.all()
        ).count()

        if orphaned_parents > 0:
            self.warnings.append(
                f"{orphaned_parents} accounts reference non-existent parent accounts"
            )

        self._add_check(
            name='account_hierarchy',
            passed=passed,
            details='Account parent chain must have no circular references',
            count=len(circular),
        )


class InventoryRecoveryValidator:
    """Validates inventory data integrity after restore.

    Checks performed (all read-only):
    - Stock quantity consistency (sum of movements matches current stock)
    - Batch integrity (no negative quantities)
    - Warehouse totals consistency
    - Movement chain continuity
    - Negative stock detection
    - Orphaned batch detection
    - Product-batch relationship integrity

    Returns a dict with:
        {
            'valid': bool,
            'checks': [{'name': str, 'passed': bool, 'details': str, 'count': int}],
            'errors': [str],
            'warnings': [str],
        }
    """

    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []

    def validate(self) -> dict:
        """Run all inventory recovery checks and return results."""
        self._check_stock_quantity_consistency()
        self._check_batch_integrity()
        self._check_warehouse_totals()
        self._check_movement_chain_continuity()
        self._check_negative_stock()
        self._check_orphaned_batches()
        self._check_product_batch_relationship()

        return {
            'valid': len(self.errors) == 0,
            'checks': self.checks,
            'errors': self.errors,
            'warnings': self.warnings,
        }

    def _add_check(self, name: str, passed: bool, details: str, count: int = 0):
        self.checks.append({
            'name': name,
            'passed': passed,
            'details': details,
            'count': count,
        })

    def _check_stock_quantity_consistency(self):
        """Verify batch remaining_quantity matches sum of stock movements."""
        from inventory.models import Batch, StockMovement

        inconsistencies = []

        batches = Batch.objects.filter(is_active=True)
        for batch in batches:
            # Sum all non-TRANSFER movements for this batch
            movement_total = StockMovement.objects.filter(
                batch=batch,
                is_active=True,
            ).exclude(
                movement_type='TRANSFER'
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

            if batch.remaining_quantity != movement_total:
                inconsistencies.append(
                    f"Batch {batch.batch_number}: "
                    f"remaining={batch.remaining_quantity}, "
                    f"movements_sum={movement_total}"
                )

        passed = len(inconsistencies) == 0
        if not passed:
            self.errors.append(
                f"Found {len(inconsistencies)} batches with quantity mismatches: "
                f"{', '.join(inconsistencies[:5])}"
                f"{'...' if len(inconsistencies) > 5 else ''}"
            )

        self._add_check(
            name='stock_quantity_consistency',
            passed=passed,
            details='Batch remaining_quantity must equal sum of stock movements',
            count=len(inconsistencies),
        )

    def _check_batch_integrity(self):
        """Verify no batch has negative quantity or remaining_quantity."""
        from inventory.models import Batch

        negative_quantity = Batch.objects.filter(
            Q(quantity__lt=0) | Q(remaining_quantity__lt=0),
        ).count()

        passed = negative_quantity == 0
        if not passed:
            self.errors.append(
                f"Found {negative_quantity} batches with negative quantities"
            )

        self._add_check(
            name='batch_integrity',
            passed=passed,
            details='No batch should have negative quantity or remaining_quantity',
            count=negative_quantity,
        )

    def _check_warehouse_totals(self):
        """Verify warehouse stock totals are consistent with movements."""
        from inventory.models import Warehouse, StockMovement, Batch

        inconsistencies = []

        warehouses = Warehouse.objects.filter(is_active=True)
        for warehouse in warehouses:
            # Sum all movements for this warehouse
            movement_total = StockMovement.objects.filter(
                warehouse=warehouse,
                is_active=True,
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

            # Sum batch remaining quantities for batches linked to movements in this warehouse
            batch_ids = StockMovement.objects.filter(
                warehouse=warehouse,
                batch__isnull=False,
            ).values_list('batch_id', flat=True).distinct()

            batch_total = Batch.objects.filter(
                id__in=batch_ids,
                is_active=True,
            ).aggregate(total=Sum('remaining_quantity'))['total'] or Decimal('0.00')

            # These won't always match exactly (batches may span warehouses via transfers),
            # so this is a warning, not an error
            diff = abs(movement_total - batch_total)
            if diff > Decimal('0.01'):
                inconsistencies.append(
                    f"Warehouse {warehouse.name}: "
                    f"movements={movement_total}, "
                    f"batch_total={batch_total}"
                )

        passed = len(inconsistencies) == 0
        if not passed:
            self.warnings.append(
                f"Found {len(inconsistencies)} warehouses with quantity discrepancies: "
                f"{', '.join(inconsistencies[:5])}"
                f"{'...' if len(inconsistencies) > 5 else ''}"
            )

        self._add_check(
            name='warehouse_totals',
            passed=passed,
            details='Warehouse movement totals should align with batch quantities',
            count=len(inconsistencies),
        )

    def _check_movement_chain_continuity(self):
        """Verify stock movements reference valid products, batches, and warehouses."""
        from inventory.models import StockMovement, Product, Batch, Warehouse

        # Movements referencing non-existent products
        invalid_products = StockMovement.objects.filter(
            is_active=True,
        ).exclude(
            product__in=Product.objects.all()
        ).count()

        # Movements referencing non-existent warehouses
        invalid_warehouses = StockMovement.objects.filter(
            is_active=True,
        ).exclude(
            warehouse__in=Warehouse.objects.all()
        ).count()

        # Movements with batch that doesn't exist (batch is nullable, so only check non-null)
        invalid_batches = StockMovement.objects.filter(
            is_active=True,
            batch__isnull=False,
        ).exclude(
            batch__in=Batch.objects.all()
        ).count()

        total_invalid = invalid_products + invalid_warehouses + invalid_batches
        passed = total_invalid == 0

        if not passed:
            self.errors.append(
                f"Found {total_invalid} movements with broken references: "
                f"{invalid_products} invalid products, "
                f"{invalid_warehouses} invalid warehouses, "
                f"{invalid_batches} invalid batches"
            )

        self._add_check(
            name='movement_chain_continuity',
            passed=passed,
            details='All stock movements must reference valid products, batches, and warehouses',
            count=total_invalid,
        )

    def _check_negative_stock(self):
        """Detect products with negative total stock across all warehouses."""
        from inventory.models import Product, StockMovement

        negative_products = []

        products = Product.objects.filter(is_active=True)
        for product in products:
            total_stock = StockMovement.objects.filter(
                product=product,
                is_active=True,
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

            if total_stock < 0:
                negative_products.append(
                    f"{product.name} (stock={total_stock})"
                )

        passed = len(negative_products) == 0
        if not passed:
            self.errors.append(
                f"Found {len(negative_products)} products with negative stock: "
                f"{', '.join(negative_products[:5])}"
                f"{'...' if len(negative_products) > 5 else ''}"
            )

        self._add_check(
            name='negative_stock',
            passed=passed,
            details='No product should have negative total stock',
            count=len(negative_products),
        )

    def _check_orphaned_batches(self):
        """Detect batches that reference non-existent products."""
        from inventory.models import Batch, Product

        orphaned = Batch.objects.filter(
            is_active=True,
        ).exclude(
            product__in=Product.objects.all()
        ).count()

        passed = orphaned == 0
        if not passed:
            self.errors.append(
                f"Found {orphaned} batches referencing non-existent products"
            )

        self._add_check(
            name='orphaned_batches',
            passed=passed,
            details='All batches must reference valid products',
            count=orphaned,
        )

    def _check_product_batch_relationship(self):
        """Verify product-batch relationships are consistent."""
        from inventory.models import Product, Batch, StockMovement

        issues = []

        # Batches with remaining_quantity > original quantity
        overdrawn = Batch.objects.filter(
            is_active=True,
            remaining_quantity__gt=F('quantity'),
        ).count()

        if overdrawn > 0:
            issues.append(f"{overdrawn} batches have remaining_quantity > quantity")

        # Products with batches but no movements
        products_with_batches_no_movements = Product.objects.filter(
            is_active=True,
            batch__isnull=False,
        ).exclude(
            stockmovement__isnull=False,
        ).distinct().count()

        if products_with_batches_no_movements > 0:
            issues.append(
                f"{products_with_batches_no_movements} products have batches "
                f"but no stock movements"
            )

        # Movements with batch that doesn't belong to the product
        mismatched = StockMovement.objects.filter(
            is_active=True,
            batch__isnull=False,
        ).exclude(
            batch__product=F('product'),
        ).count()

        if mismatched > 0:
            issues.append(
                f"{mismatched} movements have batch-product mismatch"
            )

        passed = len(issues) == 0
        if not passed:
            for issue in issues:
                self.errors.append(issue)

        self._add_check(
            name='product_batch_relationship',
            passed=passed,
            details='Product-batch relationships must be consistent and valid',
            count=len(issues),
        )
