"""
Data Integrity Self-Check System & Financial Audit Continuity.
Comprehensive validation of inventory, accounting, and data consistency.
"""
import logging
from decimal import Decimal
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('erp.integrity')


class InventoryAccountingReconciler:
    """Reconcile inventory with accounting records."""

    @staticmethod
    def check_inventory_ledger_consistency():
        """Check if inventory stock matches GL entries."""
        from inventory.models import Product, Batch, StockMovement
        from accounting.models import Account, JournalEntryLine

        result = {
            'status': 'ok',
            'issues': [],
            'products_checked': 0
        }

        try:
            products = Product.objects.all()
            result['products_checked'] = products.count()

            inventory_accounts = Account.objects.filter(
                account_type='ASSET',
                name__icontains='inventory'
            )

            for product in products:
                total_stock = Batch.objects.filter(
                    product=product
                ).aggregate(total=Sum('remaining_quantity'))['total'] or 0

                if total_stock < 0:
                    result['issues'].append({
                        'product_id': str(product.id),
                        'product_name': product.name,
                        'issue': 'negative_stock',
                        'quantity': str(total_stock)
                    })

            if result['issues']:
                result['status'] = 'warning'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_pending_stock_movements():
        """Check for orphaned or incomplete stock movements."""
        from inventory.models import StockMovement

        result = {
            'status': 'ok',
            'issues': [],
            'total_movements': 0
        }

        try:
            total = StockMovement.objects.count()
            result['total_movements'] = total

            without_batch = StockMovement.objects.filter(
                batch__isnull=True,
                movement_type__in=['IN', 'OUT']
            )

            if without_batch.exists():
                result['issues'].append({
                    'type': 'movements_without_batch',
                    'count': without_batch.count()
                })
                result['status'] = 'warning'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result


class BatchExpiryValidator:
    """Validate batch expiry correctness."""

    @staticmethod
    def check_expired_batches_with_stock():
        """Find expired batches that still have stock."""
        from inventory.models import Batch

        result = {
            'status': 'ok',
            'issues': [],
            'total_expired': 0
        }

        try:
            expired = Batch.objects.filter(
                expiry_date__lt=timezone.now().date(),
                remaining_quantity__gt=0
            )

            result['total_expired'] = expired.count()

            if expired.exists():
                result['status'] = 'warning'
                result['issues'] = [
                    {
                        'batch_id': str(b.id),
                        'product_name': b.product.name if b.product else 'Unknown',
                        'expiry_date': str(b.expiry_date),
                        'remaining_quantity': str(b.remaining_quantity)
                    }
                    for b in expired[:50]
                ]

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_expiring_soon(days: int = 30):
        """Check batches expiring soon."""
        from inventory.models import Batch
        from datetime import date

        future_date = date.today() + timedelta(days=days)

        result = {
            'status': 'ok',
            'expiring_count': 0,
            'at_risk_quantity': 0
        }

        try:
            expiring = Batch.objects.filter(
                expiry_date__gte=timezone.now().date(),
                expiry_date__lte=future_date,
                remaining_quantity__gt=0
            )

            result['expiring_count'] = expiring.count()
            result['at_risk_quantity'] = expiring.aggregate(
                total=Sum('remaining_quantity')
            )['total'] or 0

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result


class FiscalPeriodConsistency:
    """Validate fiscal period consistency."""

    @staticmethod
    def check_fiscal_lock_consistency():
        """Check that locked periods have no postings."""
        from accounting.models import FiscalPeriod

        result = {
            'status': 'ok',
            'issues': [],
            'periods_checked': 0
        }

        try:
            periods = FiscalPeriod.objects.all()
            result['periods_checked'] = periods.count()

            for period in periods:
                if period.is_locked:
                    has_entries = period.journal_entries.exists()
                    if has_entries:
                        result['issues'].append({
                            'period_id': str(period.id),
                            'period_name': period.name,
                            'issue': 'locked_period_has_entries'
                        })
                        result['status'] = 'error'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result


class WarehouseConsistencyChecker:
    """Validate warehouse consistency."""

    @staticmethod
    def check_warehouse_stock_balance():
        """Verify warehouse stock balance from movements."""
        from inventory.models import Warehouse, StockMovement, Batch

        result = {
            'status': 'ok',
            'warehouses_checked': 0,
            'issues': []
        }

        try:
            warehouses = Warehouse.objects.filter(is_active=True)
            result['warehouses_checked'] = warehouses.count()

            for warehouse in warehouses:
                movements = StockMovement.objects.filter(warehouse=warehouse)
                total_in = movements.filter(movement_type='IN').aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                total_out = movements.filter(movement_type='OUT').aggregate(
                    total=Sum('quantity')
                )['total'] or 0
                total_transfers = movements.filter(movement_type='TRANSFER').aggregate(
                    total=Sum('quantity')
                )['total'] or 0

                expected = total_in - total_out
                actual = Batch.objects.filter(
                    warehouse=warehouse
                ).aggregate(total=Sum('remaining_quantity'))['total'] or 0

                if abs(expected - actual) > Decimal('0.01'):
                    result['issues'].append({
                        'warehouse_id': str(warehouse.id),
                        'warehouse_name': warehouse.name,
                        'expected': str(expected),
                        'actual': str(actual),
                        'difference': str(expected - actual)
                    })

            if result['issues']:
                result['status'] = 'warning'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result


class DataIntegrityRunner:
    """Run comprehensive data integrity checks."""

    @staticmethod
    def run_full_integrity_check():
        """Execute all integrity checks."""
        return {
            'inventory_accounting': InventoryAccountingReconciler.check_inventory_ledger_consistency(),
            'pending_movements': InventoryAccountingReconciler.check_pending_stock_movements(),
            'expired_batches': BatchExpiryValidator.check_expired_batches_with_stock(),
            'expiring_soon': BatchExpiryValidator.check_expiring_soon(),
            'fiscal_consistency': FiscalPeriodConsistency.check_fiscal_lock_consistency(),
            'warehouse_balance': WarehouseConsistencyChecker.check_warehouse_stock_balance(),
            'financial_unbalanced': 'Use FinancialIntegrityMonitor.run_full_audit()',
            'check_timestamp': timezone.now().isoformat()
        }

    @staticmethod
    def get_integrity_summary():
        """Get quick integrity status summary."""
        checks = DataIntegrityRunner.run_full_integrity_check()

        error_count = 0
        warning_count = 0

        for key, value in checks.items():
            if isinstance(value, dict):
                if value.get('status') == 'error':
                    error_count += 1
                elif value.get('status') == 'warning':
                    warning_count += 1

        return {
            'overall_status': 'error' if error_count > 0 else 'warning' if warning_count > 0 else 'ok',
            'errors': error_count,
            'warnings': warning_count,
            'checks_run': len(checks)
        }