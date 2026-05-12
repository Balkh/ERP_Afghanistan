"""SLA monitoring engine for digital twin operations."""

from collections import deque
from typing import Any, Dict, List, Optional


_DEFAULT_SLAS: Dict[str, int] = {
    "invoice_processing": 2,
    "workflow_execution": 10,
    "reconciliation": 30,
    "payment_processing": 3,
}


class SLAMonitor:
    """Tracks SLA compliance and records violations for time-pressured operations.

    All public methods are exception-safe. Violation history is bounded.
    """

    def __init__(
        self,
        slas: Optional[Dict[str, int]] = None,
        max_violations: int = 500,
    ) -> None:
        self._slas: Dict[str, int] = {**_DEFAULT_SLAS, **(slas or {})}
        self._max_violations = max_violations
        self._violations: deque = deque(maxlen=max_violations)
        self._total_checks: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_operation(
        self, operation: str, elapsed_ticks: int
    ) -> Dict[str, Any]:
        """Check if *elapsed_ticks* satisfies the configured SLA for *operation*.

        If the operation is not in the SLA table it is treated as within_sla
        and no violation is recorded.

        Returns:
            Dict with keys: operation, elapsed, sla_target, within_sla, breach_ratio.
        """
        try:
            self._total_checks += 1
            sla_target = self._slas.get(operation)

            if sla_target is None:
                return {
                    "operation": operation,
                    "elapsed": elapsed_ticks,
                    "sla_target": None,
                    "within_sla": True,
                    "breach_ratio": 0.0,
                }

            within_sla = elapsed_ticks <= sla_target
            breach_ratio = (
                max(0.0, elapsed_ticks - sla_target) / sla_target
                if sla_target > 0
                else 0.0
            )

            if not within_sla:
                self.record_violation(operation, elapsed_ticks, self._total_checks)

            return {
                "operation": operation,
                "elapsed": elapsed_ticks,
                "sla_target": sla_target,
                "within_sla": within_sla,
                "breach_ratio": round(breach_ratio, 4),
            }
        except Exception:
            return {
                "operation": operation,
                "elapsed": elapsed_ticks,
                "sla_target": None,
                "within_sla": True,
                "breach_ratio": 0.0,
            }

    def record_violation(
        self, operation: str, elapsed: int, tick: int
    ) -> Dict[str, Any]:
        """Manually record an SLA violation.

        Returns:
            The violation record dict.
        """
        try:
            record: Dict[str, Any] = {
                "operation": operation,
                "elapsed": elapsed,
                "tick": tick,
            }
            self._violations.append(record)
            return record
        except Exception:
            return {"operation": operation, "elapsed": elapsed, "tick": tick}

    def get_violations(
        self, operation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return violation records, optionally filtered by *operation*."""
        try:
            if operation is None:
                return list(self._violations)
            return [v for v in self._violations if v["operation"] == operation]
        except Exception:
            return []

    def get_violation_count(self) -> int:
        """Return total number of recorded violations."""
        try:
            return len(self._violations)
        except Exception:
            return 0

    def get_breach_rate(self) -> float:
        """Ratio of violations to total checks.

        Returns 0.0 if no checks have been performed.
        """
        try:
            if self._total_checks == 0:
                return 0.0
            return round(len(self._violations) / self._total_checks, 4)
        except Exception:
            return 0.0

    def get_total_checks(self) -> int:
        """Return total number of check_operation calls."""
        try:
            return self._total_checks
        except Exception:
            return 0

    def clear(self) -> None:
        """Reset all state — violations and check counter."""
        try:
            self._violations.clear()
            self._total_checks = 0
        except Exception:
            pass
