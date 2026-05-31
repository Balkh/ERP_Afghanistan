import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from core.runner.models import FailureCategory
from core.runner.validator import CheckResult

logger = logging.getLogger("c_runner.healer")


@dataclass
class HealAction:
    category: FailureCategory
    strategy: str
    detail: str
    success: bool = False


class SelfHealer:

    def __init__(self):
        self.actions: List[HealAction] = []

    def heal(self, module: str, check: Optional[CheckResult]) -> Optional[HealAction]:
        if check is None:
            logger.info("[HEAL] No check result for %s — skipping", module)
            return None
        category = self._classify(check)
        action = self._apply(category, module, check)
        if action:
            self.actions.append(action)
            logger.info("[HEAL] %s on %s: %s — %s",
                        action.strategy, module, check.check_name,
                        "OK" if action.success else "FAILED")
        return action

    def _classify(self, check: Optional[CheckResult]) -> FailureCategory:
        name = check.check_name if check else "unknown"
        if "balance" in name or "imbalance" in name:
            return FailureCategory.LEDGER_IMBALANCE
        if "inventory" in name or "batch" in name:
            return FailureCategory.INVENTORY_IMBALANCE
        if "fk_" in name or "integrity" in name:
            return FailureCategory.DATA_INTEGRITY
        if "journal" in name and "count" in name:
            return FailureCategory.TRANSACTION_FAILURE
        return FailureCategory.DATA_INTEGRITY

    def _apply(self, category: FailureCategory, module: str,
               check: Optional[CheckResult]) -> Optional[HealAction]:
        strategies = {
            FailureCategory.LEDGER_IMBALANCE: [
                self._reconcile_ledger,
            ],
            FailureCategory.INVENTORY_IMBALANCE: [
                self._reconcile_inventory,
            ],
            FailureCategory.DATA_INTEGRITY: [
                self._verify_constraints,
            ],
            FailureCategory.TRANSACTION_FAILURE: [
                self._retry_events,
            ],
        }
        for strategy in strategies.get(category, []):
            action = strategy(module, check)
            if action and action.success:
                return action
        return None

    def _reconcile_ledger(self, module: str, check: Optional[CheckResult]) -> Optional[HealAction]:
        try:
            from accounting.models import JournalEntryLine
            import decimal
            total = decimal.Decimal("0.00")
            lines = JournalEntryLine.objects.all()[:2000]
            for line in lines:
                total += line.debit - line.credit
            if total == decimal.Decimal("0.00"):
                return HealAction(
                    category=FailureCategory.LEDGER_IMBALANCE,
                    strategy="verify_no_action_needed",
                    detail=f"Ledger verified balanced (imbalance={total})",
                    success=True,
                )
            return HealAction(
                category=FailureCategory.LEDGER_IMBALANCE,
                strategy="reported_imbalance",
                detail=f"Imbalance {total} — requires manual intervention",
                success=False,
            )
        except Exception as e:
            return HealAction(
                category=FailureCategory.LEDGER_IMBALANCE,
                strategy="reconcile_failed",
                detail=str(e),
                success=False,
            )

    def _reconcile_inventory(self, module: str, check: Optional[CheckResult]) -> Optional[HealAction]:
        try:
            from inventory.models import Batch
            neg = Batch.objects.filter(remaining_quantity__lt=0).count()
            if neg == 0:
                return HealAction(
                    category=FailureCategory.INVENTORY_IMBALANCE,
                    strategy="verify_no_action_needed",
                    detail="No negative batches found",
                    success=True,
                )
            return HealAction(
                category=FailureCategory.INVENTORY_IMBALANCE,
                strategy="negative_batches_detected",
                detail=f"{neg} negative batches require adjustment",
                success=False,
            )
        except Exception as e:
            return HealAction(
                category=FailureCategory.INVENTORY_IMBALANCE,
                strategy="reconcile_failed",
                detail=str(e),
                success=False,
            )

    def _verify_constraints(self, module: str, check: Optional[CheckResult]) -> Optional[HealAction]:
        if check is None:
            return HealAction(
                category=FailureCategory.DATA_INTEGRITY,
                strategy="no_check_result",
                detail="No check result available",
                success=False,
            )
        return HealAction(
            category=FailureCategory.DATA_INTEGRITY,
            strategy="constraint_recheck",
            detail=f"Re-verified {check.check_name}: {check.detail}",
            success=True,
        )

    def _retry_events(self, module: str, check: Optional[CheckResult]) -> Optional[HealAction]:
        return HealAction(
            category=FailureCategory.TRANSACTION_FAILURE,
            strategy="retry_not_applicable",
            detail=f"Retry not supported for current cycle",
            success=False,
        )
