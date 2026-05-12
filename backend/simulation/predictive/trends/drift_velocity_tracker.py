import logging
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.predictive.models import DriftVelocity

logger = logging.getLogger('erp.simulation.predictive.trends.velocity')

WORKFLOW_MODULES = ['sales', 'purchase', 'inventory', 'return', 'hr']


class DriftVelocityTracker:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._velocity_history: deque = deque(maxlen=max_history)

    def measure(self, drift_history: List[Dict[str, Any]],
                current_tick: int) -> List[DriftVelocity]:
        results: List[DriftVelocity] = []
        for module in WORKFLOW_MODULES:
            module_drifts = [d for d in drift_history
                             if d.get('mismatch', {}).get('affected_module', '') == module]
            velocity = self._measure_module(module, module_drifts, current_tick)
            if velocity:
                results.append(velocity)
        return results

    def _measure_module(self, module: str,
                        drifts: List[Dict[str, Any]],
                        current_tick: int) -> Optional[DriftVelocity]:
        if len(drifts) < 2:
            return None
        acceleration = self._calc_acceleration(drifts)
        recurrence_velocity = self._calc_recurrence_velocity(drifts)
        momentum = self._calc_momentum(drifts)
        escalation_speed = self._calc_escalation_speed(drifts)
        entry = DriftVelocity(
            module=module,
            acceleration=round(acceleration, 4),
            recurrence_velocity=round(recurrence_velocity, 4),
            instability_momentum=round(momentum, 4),
            escalation_speed=round(escalation_speed, 4),
            details={
                'total_drifts': len(drifts),
                'drift_rate': round(len(drifts) / max(current_tick, 1), 4),
                'recent_trend': self._recent_trend(drifts),
            },
        )
        self._velocity_history.append({
            'module': module,
            'velocity': entry,
            'tick': current_tick,
        })
        return entry

    def _calc_acceleration(self, drifts: List[Dict]) -> float:
        if len(drifts) < 4:
            return 0.0
        half = len(drifts) // 2
        first = drifts[:half]
        second = drifts[half:]
        first_count = len(first)
        second_count = len(second)
        if first_count == 0:
            return 0.0
        return (second_count - first_count) / first_count

    def _calc_recurrence_velocity(self, drifts: List[Dict]) -> float:
        if len(drifts) < 3:
            return 0.0
        same_type_count = 0
        total_pairs = 0
        for i in range(1, len(drifts)):
            prev_type = drifts[i - 1].get('mismatch', {}).get('mismatch_type', '')
            curr_type = drifts[i].get('mismatch', {}).get('mismatch_type', '')
            if prev_type and curr_type == prev_type:
                same_type_count += 1
            total_pairs += 1
        return same_type_count / max(total_pairs, 1)

    def _calc_momentum(self, drifts: List[Dict]) -> float:
        if len(drifts) < 2:
            return 0.0
        severity_values = []
        for d in drifts:
            sev = d.get('mismatch', {}).get('severity', 'info')
            severity_values.append({'info': 0, 'low': 1, 'medium': 2,
                                    'high': 3, 'critical': 4}.get(sev, 0))
        if not severity_values:
            return 0.0
        trend = 0.0
        for i in range(1, len(severity_values)):
            trend += (severity_values[i] - severity_values[i - 1])
        return trend / len(severity_values)

    def _calc_escalation_speed(self, drifts: List[Dict]) -> float:
        if len(drifts) < 3:
            return 0.0
        first_sev = drifts[0].get('mismatch', {}).get('severity', 'info')
        last_sev = drifts[-1].get('mismatch', {}).get('severity', 'info')
        sev_map = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        diff = sev_map.get(last_sev, 0) - sev_map.get(first_sev, 0)
        return diff / max(len(drifts), 1)

    def _recent_trend(self, drifts: List[Dict]) -> str:
        if len(drifts) < 3:
            return 'insufficient_data'
        recent = drifts[-3:]
        severities = [d.get('mismatch', {}).get('severity', 'info') for d in recent]
        sev_map = {'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        values = [sev_map.get(s, 0) for s in severities]
        if all(v >= 3 for v in values):
            return 'escalating'
        if values[-1] > values[0]:
            return 'increasing'
        if values[-1] < values[0]:
            return 'decreasing'
        return 'stable'

    @property
    def record_count(self) -> int:
        return len(self._velocity_history)

    def clear(self):
        self._velocity_history.clear()
