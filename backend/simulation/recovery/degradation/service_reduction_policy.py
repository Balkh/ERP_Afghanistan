"""Service reduction policy — defines which services to reduce/preserve at each degradation level."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import DegradationLevel


class ServiceReductionPolicy:
    REDUCTION_PLANS = {
        DegradationLevel.FULL: {
            'services_to_reduce': [],
            'services_to_preserve': ['all'],
            'description': 'No reduction needed',
        },
        DegradationLevel.REDUCED: {
            'services_to_reduce': ['reporting', 'analytics', 'notification'],
            'services_to_preserve': ['accounting', 'inventory', 'sales', 'purchases'],
            'description': 'Non-critical services reduced',
        },
        DegradationLevel.MINIMUM: {
            'services_to_reduce': ['reporting', 'analytics', 'notification', 'sales', 'purchases'],
            'services_to_preserve': ['accounting', 'inventory'],
            'description': 'Only core accounting and inventory preserved',
        },
        DegradationLevel.EMERGENCY: {
            'services_to_reduce': ['reporting', 'analytics', 'notification', 'sales',
                                    'purchases', 'inventory'],
            'services_to_preserve': ['accounting_readonly'],
            'description': 'Only read-only accounting available',
        },
    }

    def __init__(self):
        self._reduction_history: deque = deque(maxlen=100)

    def get_plan(self, level: DegradationLevel) -> Dict[str, Any]:
        return dict(self.REDUCTION_PLANS.get(level, self.REDUCTION_PLANS[DegradationLevel.FULL]))

    def apply_reduction(self, level: DegradationLevel) -> Dict[str, Any]:
        plan = self.get_plan(level)
        self._reduction_history.append({
            'level': level.value, 'reduced_count': len(plan['services_to_reduce']),
        })
        return {
            'degradation_level': level.value,
            'services_to_reduce': plan['services_to_reduce'],
            'services_to_preserve': plan['services_to_preserve'],
            'description': plan['description'],
        }

    def clear(self):
        self._reduction_history.clear()
