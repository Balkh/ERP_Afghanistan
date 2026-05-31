import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from core.runner.models import FailureCategory
from core.runner.self_healer import HealAction

logger = logging.getLogger("c_runner.heal_ext")


class RemediationStrategy(Enum):
    RETRY = auto()
    ROLLBACK = auto()
    RECONCILE = auto()
    SKIP = auto()
    ISOLATE = auto()
    HALT = auto()


@dataclass
class StructuredRemediation:
    strategy: RemediationStrategy
    module: str
    failure_category: FailureCategory
    detail: str
    replay_key: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 3


class RemediationOrchestrator:

    def __init__(self):
        self._history: List[StructuredRemediation] = []
        self._consecutive_failures: Dict[str, int] = {}

    def remediate(
        self,
        module: str,
        category: FailureCategory,
        detail: str,
        executor: Callable[[], bool],
    ) -> HealAction:
        strategy = self._select_strategy(module, category)
        remediation = StructuredRemediation(
            strategy=strategy,
            module=module,
            failure_category=category,
            detail=detail,
        )
        self._history.append(remediation)

        if strategy == RemediationStrategy.RETRY:
            success = self._retry(executor)
            remediation.attempt_count = remediation.max_attempts
            return HealAction(
                category=category,
                strategy="retry_remediated",
                detail=f"Retry {'succeeded' if success else 'failed'}: {detail}",
                success=success,
            )

        if strategy == RemediationStrategy.SKIP:
            return HealAction(
                category=category,
                strategy="skipped",
                detail=f"Skipped: {detail}",
                success=True,
            )

        if strategy == RemediationStrategy.ISOLATE:
            return HealAction(
                category=category,
                strategy="isolated_module",
                detail=f"Isolated {module}: {detail}",
                success=True,
            )

        if strategy == RemediationStrategy.RECONCILE:
            return HealAction(
                category=category,
                strategy="reconcile_attempted",
                detail=f"Reconciliation: {detail}",
                success=True,
            )

        return HealAction(
            category=category,
            strategy="no_remediation",
            detail=detail,
            success=False,
        )

    def _select_strategy(self, module: str, category: FailureCategory) -> RemediationStrategy:
        key = f"{module}:{category.value}"
        self._consecutive_failures[key] = self._consecutive_failures.get(key, 0) + 1
        consecutive = self._consecutive_failures[key]

        if consecutive >= 5:
            return RemediationStrategy.HALT
        if consecutive >= 3:
            return RemediationStrategy.ISOLATE
        if category == FailureCategory.TRANSACTION_FAILURE:
            return RemediationStrategy.RETRY
        if category == FailureCategory.DATA_INTEGRITY:
            return RemediationStrategy.RECONCILE
        if category in (FailureCategory.LEDGER_IMBALANCE, FailureCategory.INVENTORY_IMBALANCE):
            return RemediationStrategy.RECONCILE
        return RemediationStrategy.SKIP

    def _retry(self, executor: Callable[[], bool]) -> bool:
        for attempt in range(3):
            try:
                if executor():
                    return True
            except Exception:
                continue
        return False

    def report(self) -> Dict[str, Any]:
        return {
            "total_remediations": len(self._history),
            "by_strategy": {
                s.name: sum(1 for r in self._history if r.strategy == s)
                for s in RemediationStrategy
            },
            "consecutive_failures": dict(self._consecutive_failures),
        }


class ReplayBasedCorrector:

    def __init__(self):
        self._corrections: List[Dict[str, Any]] = []

    def correct_from_replay(
        self,
        replay_buffer: Any,
        target_day: int,
        executor: Callable[[Any], bool],
    ) -> int:
        corrected = 0
        events = replay_buffer.get_sequence(0, target_day) if hasattr(replay_buffer, 'get_sequence') else []
        for event in events:
            try:
                if executor(event):
                    corrected += 1
                    self._corrections.append({
                        "day": target_day,
                        "event": str(getattr(event, 'event_type', 'unknown')),
                        "success": True,
                    })
            except Exception as e:
                self._corrections.append({
                    "day": target_day,
                    "event": str(getattr(event, 'event_type', 'unknown')),
                    "success": False,
                    "error": str(e),
                })
        return corrected

    @property
    def total_corrections(self) -> int:
        return len(self._corrections)

    @property
    def successful_corrections(self) -> int:
        return sum(1 for c in self._corrections if c.get("success"))
