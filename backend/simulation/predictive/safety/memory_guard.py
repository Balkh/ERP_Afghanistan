import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.safety.memory_guard')


class PredictiveMemoryGuard:
    def __init__(self):
        self._checks: Dict[str, Dict[str, Any]] = {}

    def register(self, component_name: str, current_count: int,
                 max_bound: int):
        self._checks[component_name] = {
            'current_count': current_count,
            'max_bound': max_bound,
            'utilization_pct': round((current_count / max(max_bound, 1)) * 100, 1),
            'within_bounds': current_count <= max_bound,
        }

    def audit_all(self) -> Dict[str, Any]:
        violations = {name: info for name, info in self._checks.items()
                      if not info['within_bounds']}
        return {
            'total_components_checked': len(self._checks),
            'violations_found': len(violations),
            'violations': violations,
            'all_healthy': len(violations) == 0,
            'component_details': dict(self._checks),
        }

    def get_utilization_report(self) -> Dict[str, float]:
        return {
            name: info['utilization_pct']
            for name, info in self._checks.items()
        }

    def clear(self):
        self._checks.clear()
