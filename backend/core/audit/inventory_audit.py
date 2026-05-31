import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.db.models import Sum
from core.audit.models import (
    AuditModule, AuditSeverity, AuditFinding, ModuleResult,
)

logger = logging.getLogger("audit.inventory")


class InventoryAuditEngine:

    def __init__(self):
        self.module = AuditModule.INVENTORY

    def audit(self, existing_data: Optional[Dict[str, Any]] = None) -> ModuleResult:
        existing_data = existing_data or {}
        findings: List[AuditFinding] = []
        module = self.module

        total_batches = 0
        negative_batches = 0
        mismatched_batches = 0
        total_movements = 0

        try:
            from inventory.models import Batch, StockMovement, Product

            batches = Batch.objects.all()
            total_batches = batches.count()

            neg_qty = Batch.objects.filter(remaining_quantity__lt=0).count()
            negative_batches = neg_qty
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="negative_stock",
                passed=neg_qty == 0,
                detail=f"Batches with negative remaining quantity: {neg_qty}/{total_batches}",
                evidence={"negative_batches": neg_qty, "total_batches": total_batches},
            ))

            zero_qty = Batch.objects.filter(remaining_quantity=0).count()
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.LOW,
                check_name="zero_stock_batches",
                passed=True,
                detail=f"Zero-quantity batches: {zero_qty}/{total_batches}",
                evidence={"zero_batches": zero_qty},
            ))

            movements = StockMovement.objects.filter(is_active=True)
            total_movements = movements.count()

            movement_type_counts = {}
            for mt in StockMovement.MOVEMENT_TYPES:
                code = mt[0]
                count = movements.filter(movement_type=code).count()
                if count > 0:
                    movement_type_counts[code] = count
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.LOW,
                check_name="movement_type_distribution",
                passed=True,
                detail=f"Movements by type: {movement_type_counts}",
                evidence={"movement_counts": movement_type_counts},
            ))

            orphan_movements = StockMovement.objects.filter(
                is_active=True, batch__isnull=True
            ).count()
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.MEDIUM,
                check_name="movements_without_batch",
                passed=orphan_movements == 0,
                detail=f"Movements without batch assignment: {orphan_movements}",
                evidence={"orphan_movements": orphan_movements},
            ))

            for batch in batches:
                net = StockMovement.objects.filter(
                    batch=batch, is_active=True
                ).exclude(movement_type="TRANSFER").aggregate(
                    total=Sum("quantity")
                )["total"] or Decimal("0.00")

                expected = net
                actual = batch.remaining_quantity
                if expected != actual:
                    mismatched_batches += 1
                    findings.append(AuditFinding(
                        module=module,
                        severity=AuditSeverity.HIGH,
                        check_name="batch_quantity_mismatch",
                        passed=False,
                        detail=(
                            f"Batch {batch.batch_number} (product={batch.product.name}): "
                            f"expected={expected}, actual={actual}, diff={expected - actual}"
                        ),
                        evidence={
                            "batch_number": batch.batch_number,
                            "product": batch.product.name,
                            "expected": str(expected),
                            "actual": str(actual),
                            "difference": str(expected - actual),
                        },
                    ))

            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.MEDIUM,
                check_name="batch_quantity_reconciliation",
                passed=mismatched_batches == 0,
                detail=(
                    f"Batches with quantity mismatch: {mismatched_batches}/{total_batches}"
                ),
                evidence={
                    "mismatched": mismatched_batches,
                    "total": total_batches,
                },
            ))

        except Exception as e:
            findings.append(AuditFinding(
                module=module,
                severity=AuditSeverity.HIGH,
                check_name="audit_execution",
                passed=False,
                detail=f"Inventory audit failed: {e}",
            ))
            logger.error("Inventory audit error: %s", e, exc_info=True)

        passed = all(
            f.passed for f in findings
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH)
        )

        return ModuleResult(
            module=module,
            passed=passed,
            findings=findings,
            summary=(
                f"Batches={total_batches}, Movements={total_movements}, "
                f"Negative={negative_batches}, Mismatched={mismatched_batches}, "
                f"Issues={sum(1 for f in findings if not f.passed)}"
            ),
        )
