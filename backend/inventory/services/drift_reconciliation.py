"""
Stock Drift Reconciliation Service
====================================
Compares Batch.remaining_quantity against the aggregate of StockMovement
quantities for each batch to detect data inconsistencies (stock drift).

This is a READ-ONLY audit service. It never modifies data.
"""
import logging
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Optional

from django.db.models import Sum, Q

from inventory.models import Batch, StockMovement

logger = logging.getLogger('erp.inventory')


@dataclass
class BatchDrift:
    """Represents a drift discrepancy for a single batch."""
    batch_id: str
    batch_number: str
    product_name: str
    stored_quantity: Decimal
    computed_quantity: Decimal
    drift_amount: Decimal
    movement_count: int
    warehouse_name: str = ''


@dataclass
class DriftReconciliationResult:
    """Result of a full drift reconciliation scan."""
    total_batches_checked: int = 0
    batches_with_drift: int = 0
    batches_clean: int = 0
    total_drift_value: Decimal = field(default_factory=lambda: Decimal('0.00'))
    drifts: List[BatchDrift] = field(default_factory=list)
    truncated: bool = False

    @property
    def is_healthy(self) -> bool:
        return self.batches_with_drift == 0

    @property
    def health_score(self) -> float:
        if self.total_batches_checked == 0:
            return 100.0
        return round((self.batches_clean / self.total_batches_checked) * 100, 2)


class StockDriftReconciliation:
    """
    READ-ONLY audit service that compares stored Batch.remaining_quantity
    against the computed sum of StockMovement quantities for each batch.

    The expected remaining_quantity for a batch is:
        SUM(StockMovement.quantity WHERE batch=X AND is_active=True)
        excluding TRANSFER movements (which are managed separately).

    Drift is detected when |stored - computed| > tolerance.
    """

    @staticmethod
    def check_batch(
        batch: Batch,
        tolerance: Decimal = Decimal('0.00'),
    ) -> Optional[BatchDrift]:
        """
        Check a single batch for drift.

        Args:
            batch: Batch instance to check
            tolerance: Allowed difference before reporting drift (default: exact match)

        Returns:
            BatchDrift if drift detected, None if clean
        """
        computed = StockMovement.objects.filter(
            batch=batch,
            is_active=True,
        ).exclude(
            movement_type='TRANSFER',
        ).aggregate(
            total=Sum('quantity'),
        )['total'] or Decimal('0')

        stored = batch.remaining_quantity or Decimal('0')
        drift = stored - computed

        if abs(drift) <= tolerance:
            return None

        product_name = ''
        if hasattr(batch, 'product') and batch.product:
            product_name = str(batch.product)

        warehouse_name = getattr(batch, 'location', '') or ''

        movement_count = StockMovement.objects.filter(
            batch=batch,
            is_active=True,
        ).count()

        return BatchDrift(
            batch_id=str(batch.id),
            batch_number=batch.batch_number,
            product_name=product_name,
            stored_quantity=stored,
            computed_quantity=computed,
            drift_amount=drift,
            movement_count=movement_count,
            warehouse_name=warehouse_name,
        )

    @staticmethod
    def run_full_reconciliation(
        product_id=None,
        warehouse_id=None,
        tolerance: Decimal = Decimal('0.00'),
        only_positive_stock: bool = True,
        max_drifts: int = 0,
    ) -> DriftReconciliationResult:
        """
        Run a full reconciliation across all (or filtered) batches.

        Uses a single aggregate query for StockMovement instead of N+1.

        Args:
            product_id: Optional product UUID to filter by
            warehouse_id: Optional warehouse UUID to filter by
            tolerance: Allowed drift before reporting (default: exact match)
            only_positive_stock: If True, only check batches with remaining_quantity > 0
            max_drifts: If > 0, stop after finding this many drifts (early exit)

        Returns:
            DriftReconciliationResult with all detected drifts
        """
        result = DriftReconciliationResult()

        batch_qs = Batch.objects.filter(is_active=True).select_related(
            'product',
        )

        if product_id:
            batch_qs = batch_qs.filter(product_id=product_id)
        if warehouse_id:
            # Batch stores its warehouse as the warehouse UUID string in `location`.
            batch_qs = batch_qs.filter(location=str(warehouse_id))
        if only_positive_stock:
            batch_qs = batch_qs.filter(remaining_quantity__gt=0)

        # Single aggregate query: SUM(quantity) grouped by batch_id
        computed_map = dict(
            StockMovement.objects.filter(
                batch__in=batch_qs,
                is_active=True,
            ).exclude(
                movement_type='TRANSFER',
            ).values('batch_id').annotate(
                computed=Sum('quantity'),
            ).values_list('batch_id', 'computed'),
        )

        for batch in batch_qs.iterator():
            result.total_batches_checked += 1
            computed = computed_map.get(batch.id, Decimal('0'))
            stored = batch.remaining_quantity if batch.remaining_quantity is not None else Decimal('0')
            drift_amount = stored - computed

            if abs(drift_amount) <= tolerance:
                result.batches_clean += 1
                continue

            # Early exit if max_drifts reached
            if max_drifts > 0 and result.batches_with_drift >= max_drifts:
                result.truncated = True
                break

            result.batches_with_drift += 1
            movement_count = StockMovement.objects.filter(
                batch=batch, is_active=True,
            ).count()
            result.drifts.append(BatchDrift(
                batch_id=str(batch.id),
                batch_number=batch.batch_number,
                product_name=str(batch.product) if batch.product else '',
                stored_quantity=stored,
                computed_quantity=computed,
                drift_amount=drift_amount,
                movement_count=movement_count,
                warehouse_name=getattr(batch, 'location', '') or '',
            ))
            result.total_drift_value += abs(drift_amount)

        logger.info(
            "Stock drift reconciliation complete: "
            "%d/%d batches clean, %d with drift (total drift: %s)",
            result.batches_clean,
            result.total_batches_checked,
            result.batches_with_drift,
            result.total_drift_value,
        )

        return result

    @staticmethod
    def get_drift_summary(
        product_id=None,
        warehouse_id=None,
        tolerance: Decimal = Decimal('0.00'),
        only_positive_stock: bool = True,
        max_drifts: int = 0,
    ) -> dict:
        """
        Get a concise drift summary suitable for API responses or dashboards.

        Args:
            product_id: Optional product UUID to filter by
            warehouse_id: Optional warehouse UUID to filter by
            tolerance: Allowed drift before reporting
            only_positive_stock: If True, only check batches with remaining > 0
            max_drifts: If > 0, stop after this many drifts

        Returns:
            Dict with health status, counts, and drift details
        """
        result = StockDriftReconciliation.run_full_reconciliation(
            product_id=product_id,
            warehouse_id=warehouse_id,
            tolerance=tolerance,
            only_positive_stock=only_positive_stock,
            max_drifts=max_drifts,
        )

        return {
            'is_healthy': result.is_healthy,
            'health_score': result.health_score,
            'total_batches_checked': result.total_batches_checked,
            'batches_clean': result.batches_clean,
            'batches_with_drift': result.batches_with_drift,
            'total_drift_value': str(result.total_drift_value),
            'truncated': result.truncated,
            'drifts': [
                {
                    'batch_id': d.batch_id,
                    'batch_number': d.batch_number,
                    'product_name': d.product_name,
                    'stored_quantity': str(d.stored_quantity),
                    'computed_quantity': str(d.computed_quantity),
                    'drift_amount': str(d.drift_amount),
                    'movement_count': d.movement_count,
                    'warehouse_name': d.warehouse_name,
                }
                for d in result.drifts
            ],
        }
