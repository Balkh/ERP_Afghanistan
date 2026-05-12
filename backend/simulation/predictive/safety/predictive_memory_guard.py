import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.safety.memory_guard')


class PredictiveMemoryGuard:
    def __init__(self):
        self._violations: List[Dict[str, Any]] = []

    def check_bounds(self, component_name: str, current_size: int,
                     max_size: int) -> bool:
        if current_size > max_size:
            self._violations.append({
                'component': component_name,
                'current_size': current_size,
                'max_size': max_size,
                'violation': 'memory_overrun',
            })
            return False
        return True

    def check_all_bounded(self, components: Dict[str, int],
                          limits: Dict[str, int]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for name, size in components.items():
            limit = limits.get(name, float('inf'))
            if limit != float('inf') and size > limit:
                violation = {
                    'component': name,
                    'current_size': size,
                    'max_size': limit,
                    'violation': 'memory_overrun',
                }
                self._violations.append(violation)
                results.append(violation)
            else:
                results.append({
                    'component': name,
                    'current_size': size,
                    'max_size': limit,
                    'violation': None,
                })
        return results

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    @property
    def has_violations(self) -> bool:
        return len(self._violations) > 0

    def get_violations(self) -> List[Dict[str, Any]]:
        return list(self._violations)

    def clear(self):
        self._violations.clear()
