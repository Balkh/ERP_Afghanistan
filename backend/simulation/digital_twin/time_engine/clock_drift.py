"""Clock drift simulator for digital twin desynchronization scenarios."""

from collections import deque
from typing import Any, Dict, List


class ClockDriftSimulator:
    """Simulates cumulative clock drift between internal and external time sources.

    Drift accumulates by *drift_rate* per simulated tick. When total drift
    exceeds 1.0 the clock is considered desynchronised. All history is bounded.
    All public methods are exception-safe.
    """

    def __init__(self, drift_rate: float = 0.05, max_history: int = 200) -> None:
        self._drift_rate = drift_rate
        self._max_history = max_history
        self._total_drift: float = 0.0
        self._tick_counter: int = 0
        self._history: deque = deque(maxlen=max_history)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def simulate_tick(self) -> Dict[str, Any]:
        """Advance one tick — accumulates drift by *drift_rate*.

        Returns:
            Dict with keys: drift_amount, desynced, source, target.
        """
        try:
            self._tick_counter += 1
            drift_amount = self._drift_rate
            self._total_drift += drift_amount
            desynced = self._total_drift > 1.0

            record: Dict[str, Any] = {
                "drift_amount": drift_amount,
                "total_drift": round(self._total_drift, 6),
                "desynced": desynced,
                "source": "internal",
                "target": "external",
                "tick": self._tick_counter,
            }
            self._history.append(record)
            return {
                "drift_amount": drift_amount,
                "desynced": desynced,
                "source": "internal",
                "target": "external",
            }
        except Exception:
            return {
                "drift_amount": 0.0,
                "desynced": False,
                "source": "internal",
                "target": "external",
            }

    def get_drift_history(self) -> List[Dict[str, Any]]:
        """Return all recorded drift events."""
        try:
            return list(self._history)
        except Exception:
            return []

    def get_total_drift(self) -> float:
        """Return the cumulative drift amount."""
        try:
            return round(self._total_drift, 6)
        except Exception:
            return 0.0

    def reset(self) -> None:
        """Reset cumulative drift to zero without clearing history."""
        try:
            self._total_drift = 0.0
            self._tick_counter = 0
        except Exception:
            pass

    def clear(self) -> None:
        """Reset cumulative drift AND clear recorded history."""
        try:
            self._total_drift = 0.0
            self._tick_counter = 0
            self._history.clear()
        except Exception:
            pass
