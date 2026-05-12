"""Recursion depth safety guard for orchestration safety monitoring."""
from collections import deque
from typing import Any, Dict


class RecursionGuard:
    """Monitors and guards against excessive recursion depth."""

    def __init__(self, max_depth: int = 100, max_history: int = 500):
        self._max_depth = max_depth
        self._history: deque = deque(maxlen=max_history)

    def check_depth(self, current_depth: int, context: str = "") -> Dict[str, Any]:
        try:
            violation = current_depth > self._max_depth
            return {
                "safe": not violation,
                "depth": current_depth,
                "max_depth": self._max_depth,
                "context": context,
                "violation": violation,
            }
        except Exception:
            return {
                "safe": False,
                "depth": current_depth,
                "max_depth": self._max_depth,
                "context": context,
                "violation": True,
            }

    def record_call(self, caller: str, depth: int) -> Dict[str, Any]:
        try:
            record = {"caller": caller, "depth": depth}
            self._history.append(record)
            return dict(record)
        except Exception:
            return {"caller": caller, "depth": depth, "error": True}

    def get_call_count(self) -> int:
        try:
            return len(self._history)
        except Exception:
            return 0

    def get_max_depth(self) -> int:
        try:
            return self._max_depth
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self._history.clear()
        except Exception:
            pass
