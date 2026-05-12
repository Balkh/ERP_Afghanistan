"""Queue backlog simulator for digital twin pressure scenarios."""

from collections import deque
from typing import Any, Dict, List


class QueueBacklogSimulator:
    """Deterministic queue backlog simulation with configurable pressure thresholds.

    Arrivals are deterministic (not random) using tick parity for variation.
    History is bounded. All public methods are exception-safe.
    """

    def __init__(
        self,
        arrival_rate: float = 2.0,
        processing_rate: float = 1.5,
        warning_threshold: int = 100,
        critical_threshold: int = 500,
        max_history: int = 500,
    ) -> None:
        self._arrival_rate = arrival_rate
        self._processing_rate = processing_rate
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold
        self._max_history = max_history
        self._backlog: int = 0
        self._tick_counter: int = 0
        self._history: deque = deque(maxlen=max_history)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_tick(self) -> Dict[str, Any]:
        """Advance one tick — deterministic arrivals and processing.

        Arrivals = floor(arrival_rate) + (1 if tick % 2 == 0 else 0).
        Processed = max(0, min(backlog, int(processing_rate))).

        Returns:
            Dict with keys: backlog_size, arrivals, processed,
            is_starved, pressure_level.
        """
        try:
            self._tick_counter += 1

            arrivals = int(self._arrival_rate) + (
                1 if self._tick_counter % 2 == 0 else 0
            )
            processed = max(0, min(self._backlog, int(self._processing_rate)))

            self._backlog += arrivals - processed

            is_starved = self._backlog > self._critical_threshold
            pressure_level = self._get_pressure_level()

            record: Dict[str, Any] = {
                "tick": self._tick_counter,
                "backlog_size": self._backlog,
                "arrivals": arrivals,
                "processed": processed,
                "is_starved": is_starved,
                "pressure_level": pressure_level,
            }
            self._history.append(record)

            return {
                "backlog_size": self._backlog,
                "arrivals": arrivals,
                "processed": processed,
                "is_starved": is_starved,
                "pressure_level": pressure_level,
            }
        except Exception:
            return {
                "backlog_size": self._backlog,
                "arrivals": 0,
                "processed": 0,
                "is_starved": False,
                "pressure_level": "normal",
            }

    def push_events(self, count: int = 1) -> None:
        """Manually inject extra events into the backlog."""
        try:
            self._backlog += max(1, count)
        except Exception:
            pass

    def get_backlog_history(self) -> List[Dict[str, Any]]:
        """Return all recorded backlog snapshots."""
        try:
            return list(self._history)
        except Exception:
            return []

    def get_current_backlog(self) -> int:
        """Return the current backlog size."""
        try:
            return self._backlog
        except Exception:
            return 0

    def is_starved(self) -> bool:
        """Return True if backlog exceeds the critical threshold."""
        try:
            return self._backlog > self._critical_threshold
        except Exception:
            return False

    def clear(self) -> None:
        """Reset backlog and clear recorded history."""
        try:
            self._backlog = 0
            self._tick_counter = 0
            self._history.clear()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_pressure_level(self) -> str:
        if self._backlog >= self._critical_threshold:
            return "critical"
        if self._backlog >= self._warning_threshold:
            return "warning"
        return "normal"
