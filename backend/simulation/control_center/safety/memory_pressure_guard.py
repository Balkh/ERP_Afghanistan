"""Memory pressure safety guard for orchestration safety monitoring."""
from collections import deque
from typing import Any, Dict, List


class MemoryPressureGuard:
    """Monitors memory pressure across bounded containers."""

    def __init__(self, max_pressure_threshold: float = 0.9, max_history: int = 200):
        self._threshold = max_pressure_threshold
        self._history: deque = deque(maxlen=max_history)

    def check_pressure(
        self,
        container_sizes: Dict[str, int],
        container_maxlens: Dict[str, int],
    ) -> Dict[str, Any]:
        try:
            per_container: Dict[str, float] = {}
            violations: List[str] = []
            total_pressure = 0.0
            count = 0

            for name, maxlen in container_maxlens.items():
                size = container_sizes.get(name, 0)
                if maxlen > 0:
                    pressure = size / maxlen
                else:
                    pressure = 1.0 if size > 0 else 0.0
                per_container[name] = round(pressure, 6)
                total_pressure += pressure
                count += 1
                if pressure > self._threshold:
                    violations.append(
                        f"{name} pressure {pressure:.4f} exceeds threshold {self._threshold}"
                    )

            average_pressure = round(total_pressure / count, 6) if count > 0 else 0.0

            result = {
                "safe": len(violations) == 0,
                "pressure": average_pressure,
                "threshold": self._threshold,
                "per_container": per_container,
                "violations": violations,
            }
            self._history.append(result)
            return dict(result)
        except Exception:
            return {
                "safe": False,
                "pressure": 1.0,
                "threshold": self._threshold,
                "per_container": {},
                "violations": ["check_pressure failed with unexpected error"],
            }

    def get_pressure_history(self) -> List[Dict[str, Any]]:
        try:
            return list(self._history)
        except Exception:
            return []

    def get_current_pressure(self) -> float:
        try:
            if self._history:
                return self._history[-1].get("pressure", 0.0)
            return 0.0
        except Exception:
            return 0.0

    def get_check_count(self) -> int:
        try:
            return len(self._history)
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self._history.clear()
        except Exception:
            pass
