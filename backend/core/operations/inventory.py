"""
Inventory Integrity Monitor.
Validates stock data consistency and detects anomalies.
"""
from decimal import Decimal
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta
from inventory.models import Product, Batch, StockMovement, Warehouse


class InventoryIntegrityMonitor:
    """Monitor inventory integrity."""

    @staticmethod
    def check_negative_stock() -> dict:
        """Detect negative stock quantities."""
        result = {
            'status': 'ok',
            'issues': [],
            'negative_count': 0
        }

        try:
            batches = Batch.objects.filter(remaining_quantity__lt=0)
            result['negative_count'] = batches.count()

            if result['negative_count'] > 0:
                result['status'] = 'error'
                result['issues'] = [
                    {
                        'batch_id': str(b.id),
                        'product_name': b.product.name if b.product else 'Unknown',
                        'warehouse_name': b.warehouse.name if b.warehouse else 'Unknown',
                        'remaining_quantity': str(b.remaining_quantity)
                    }
                    for b in batches[:50]
                ]
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_duplicate_deductions() -> dict:
        """Detect duplicate stock deductions."""
        result = {
            'status': 'ok',
            'issues': [],
            'duplicates_found': 0
        }

        try:
            duplicates = StockMovement.objects.values(
                'product_id', 'batch_id', 'movement_type', 'quantity',
                'created_at__date'
            ).annotate(
                count=Sum('id')
            ).filter(
                count__gt=1,
                movement_type='OUT'
            )

            result['duplicates_found'] = len(duplicates)
            if result['duplicates_found'] > 0:
                result['status'] = 'warning'
                result['issues'] = list(duplicates[:10])
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_batch_consistency() -> dict:
        """Validate batch consistency."""
        result = {
            'status': 'ok',
            'batches_checked': 0,
            'issues': []
        }

        try:
            batches = Batch.objects.all()
            result['batches_checked'] = batches.count()

            for batch in batches:
                if batch.expiry_date and batch.expiry_date < timezone.now().date():
                    if batch.remaining_quantity > 0:
                        result['issues'].append({
                            'batch_id': str(batch.id),
                            'status': 'expired_with_stock',
                            'expiry_date': str(batch.expiry_date),
                            'remaining_quantity': str(batch.remaining_quantity)
                        })
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_warehouse_consistency() -> dict:
        """Validate warehouse-level stock consistency."""
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

                expected_balance = total_in - total_out

                batches = Batch.objects.filter(warehouse=warehouse)
                actual_balance = sum(b.remaining_quantity for b in batches)

                if abs(expected_balance - actual_balance) > Decimal('0.01'):
                    result['issues'].append({
                        'warehouse_id': str(warehouse.id),
                        'warehouse_name': warehouse.name,
                        'expected_balance': str(expected_balance),
                        'actual_balance': str(actual_balance),
                        'difference': str(expected_balance - actual_balance)
                    })

            if result['issues']:
                result['status'] = 'warning'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_stock_movement_consistency() -> dict:
        """Validate stock movement chain consistency."""
        result = {
            'status': 'ok',
            'movements_checked': 0,
            'issues': []
        }

        try:
            movements = StockMovement.objects.all()
            result['movements_checked'] = movements.count()

            for movement in movements:
                if movement.movement_type == 'OUT' and movement.batch:
                    if movement.quantity > movement.batch.remaining_quantity:
                        result['issues'].append({
                            'movement_id': str(movement.id),
                            'batch_id': str(movement.batch.id),
                            'quantity_requested': str(movement.quantity),
                            'batch_available': str(movement.batch.remaining_quantity)
                        })

            if result['issues']:
                result['status'] = 'warning'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def run_full_audit() -> dict:
        """Run complete inventory integrity audit."""
        return {
            'negative_stock': InventoryIntegrityMonitor.check_negative_stock(),
            'duplicate_deductions': InventoryIntegrityMonitor.check_duplicate_deductions(),
            'batch_consistency': InventoryIntegrityMonitor.check_batch_consistency(),
            'warehouse_consistency': InventoryIntegrityMonitor.check_warehouse_consistency(),
            'movement_consistency': InventoryIntegrityMonitor.check_stock_movement_consistency()
        }