"""Deterministic performance timer for digital twin operations."""

from collections import deque
from typing import Any, Dict, Optional


class PerfTimer:
    """Bounded, deterministic tick-based timer for operation profiling.

    Uses an internal monotonic counter (not wall clock) so results are
    fully deterministic across runs. All public methods are exception-safe.
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._max_history = max_history
        self._runners: Dict[str, int] = {}
        self._history: deque = deque(maxlen=max_history)
        self._tick_counter: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, operation_id: str) -> None:
        """Start timing *operation_id*.

        Raises:
            ValueError: If *operation_id* is already running.
        """
        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("operation_id must be a non-empty string")

        if operation_id in self._runners:
            raise ValueError(
                f"Timer already running for '{operation_id}'"
            )

        try:
            self._tick_counter += 1
            self._runners[operation_id] = self._tick_counter
        except Exception:
            self._tick_counter -= 1
            raise

    def elapsed(self, operation_id: str) -> int:
        """Return ticks consumed since *operation_id* was started.

        Raises:
            ValueError: If *operation_id* is not running.
        """
        if operation_id not in self._runners:
            raise ValueError(
                f"No running timer for '{operation_id}'"
            )

        try:
            start = self._runners[operation_id]
            return self._tick_counter - start
        except Exception:
            raise

    def stop(self, operation_id: str) -> int:
        """Stop the timer for *operation_id* and record to history.

        Returns:
            Elapsed ticks.

        Raises:
            ValueError: If *operation_id* is not running.
        """
        if operation_id not in self._runners:
            raise ValueError(
                f"No running timer for '{operation_id}'"
            )

        try:
            start = self._runners.pop(operation_id)
            self._tick_counter += 1
            elapsed_val = self._tick_counter - start
            self._history.append({
                "operation_id": operation_id,
                "start_tick": start,
                "end_tick": self._tick_counter,
                "elapsed": elapsed_val,
            })
            return elapsed_val
        except Exception:
            raise

    def check_sla(self, operation_id: str, sla_ticks: int) -> Dict[str, Any]:
        """Check whether the running *operation_id* is within SLA.

        Does NOT stop the timer.

        Returns:
            Dict with keys: operation_id, elapsed, sla_ticks, within_sla, remaining.

        Raises:
            ValueError: If *operation_id* is not running.
        """
        if operation_id not in self._runners:
            raise ValueError(
                f"No running timer for '{operation_id}'"
            )

        try:
            elapsed_val = self.elapsed(operation_id)
            remaining = sla_ticks - elapsed_val
            return {
                "operation_id": operation_id,
                "elapsed": elapsed_val,
                "sla_ticks": sla_ticks,
                "within_sla": elapsed_val <= sla_ticks,
                "remaining": remaining,
            }
        except Exception:
            raise

    def is_running(self, operation_id: str) -> bool:
        """Return True if *operation_id* is currently being timed."""
        try:
            return operation_id in self._runners
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Compute aggregate statistics across completed timer records.

        Returns:
            Dict with keys: count, avg, max, min, running_count.
        """
        try:
            count = len(self._history)
            if count == 0:
                return {
                    "count": 0,
                    "avg": 0.0,
                    "max": 0,
                    "min": 0,
                    "running_count": len(self._runners),
                }

            elapsed_vals = [rec["elapsed"] for rec in self._history]
            return {
                "count": count,
                "avg": sum(elapsed_vals) / count,
                "max": max(elapsed_vals),
                "min": min(elapsed_vals),
                "running_count": len(self._runners),
            }
        except Exception:
            return {
                "count": 0, "avg": 0.0, "max": 0, "min": 0,
                "running_count": 0,
            }

    def clear(self) -> None:
        """Reset all state — running timers and history."""
        try:
            self._runners.clear()
            self._history.clear()
            self._tick_counter = 0
        except Exception:
            pass
