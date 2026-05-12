"""Graceful degradation — orchestrates degradation across all subsystems."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import DegradationLevel, DegradationAction, IntegritySeverity
from simulation.recovery.degradation.degradation_levels import DegradationLevels
from simulation.recovery.degradation.operational_fallbacks import OperationalFallbacks
from simulation.recovery.degradation.service_reduction_policy import ServiceReductionPolicy


class GracefulDegradation:
    def __init__(self, max_history: int = 200):
        self._levels = DegradationLevels()
        self._fallbacks = OperationalFallbacks()
        self._service_reduction = ServiceReductionPolicy()
        self._degradation_history: deque = deque(maxlen=max_history)
        self._degradation_actions: deque = deque(maxlen=max_history)

    @property
    def levels(self) -> DegradationLevels:
        return self._levels

    @property
    def fallbacks(self) -> OperationalFallbacks:
        return self._fallbacks

    @property
    def service_reduction(self) -> ServiceReductionPolicy:
        return self._service_reduction

    def degrade(self, severity: IntegritySeverity,
                has_irreversible: bool = False,
                containment_active: bool = False,
                reason: str = "") -> Dict[str, Any]:
        target_level = self._levels.select_level(severity, has_irreversible, containment_active)
        if target_level == self._levels.current:
            return {'degraded': False, 'reason': 'Already at appropriate level',
                    'current_level': target_level.value}
        level_result = self._levels.set_level(target_level, reason)
        fallback_strategy = self._fallbacks.get_strategy(target_level)
        reduction_plan = self._service_reduction.apply_reduction(target_level)
        action = DegradationAction(
            action_id=f"deg_{len(self._degradation_actions) + 1}",
            degradation_level=target_level,
            description=f"Degraded to {target_level.value}: {reason}",
            services_to_reduce=reduction_plan['services_to_reduce'],
            services_to_preserve=reduction_plan['services_to_preserve'],
            estimated_impact='high' if target_level in (DegradationLevel.MINIMUM, DegradationLevel.EMERGENCY) else 'medium',
        )
        self._degradation_actions.append(action)
        self._degradation_history.append({
            'from': level_result['previous_level'],
            'to': level_result['current_level'],
            'reason': reason,
        })
        return {
            'degraded': True,
            'previous_level': level_result['previous_level'],
            'current_level': level_result['current_level'],
            'fallback_strategy': fallback_strategy,
            'service_reduction': reduction_plan,
            'reason': reason,
        }

    def get_current_status(self) -> Dict[str, Any]:
        current = self._levels.current
        return {
            'current_level': current.value,
            'definition': self._levels.get_level(current),
            'fallback_strategy': self._fallbacks.get_strategy(current),
            'service_reduction': self._service_reduction.get_plan(current),
        }

    def clear(self):
        self._levels.clear()
        self._fallbacks.clear()
        self._service_reduction.clear()
        self._degradation_history.clear()
        self._degradation_actions.clear()
