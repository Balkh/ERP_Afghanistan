from collections import deque
from typing import Any, Dict, List, Optional
from simulation.control_center.models import OperationalPriority


class OperationalPriorityEngine:
    def __init__(self, max_history: int = 200):
        self._priority_history: deque = deque(maxlen=max_history)

    def compute_priority(self, severity_score: float, critical_count: int,
                         incident_count: int, source_count: int,
                         cascading_risk: bool) -> Dict[str, Any]:
        priority = self._resolve_priority(
            severity_score, critical_count, incident_count, cascading_risk)
        priority_value = priority.value if isinstance(priority, OperationalPriority) else priority
        self._priority_history.append({
            'priority': priority_value,
            'severity_score': severity_score,
            'critical_count': critical_count,
            'cascading': cascading_risk,
        })
        return {'priority': priority_value, 'label': priority.name}

    def _resolve_priority(self, score: float, critical_count: int,
                          incident_count: int,
                          cascading: bool) -> OperationalPriority:
        if cascading or critical_count > 5:
            return OperationalPriority.CRITICAL
        if score >= 0.7 or critical_count > 2:
            return OperationalPriority.HIGH
        if score >= 0.4 or incident_count > 3:
            return OperationalPriority.MEDIUM
        if score > 0 or incident_count > 0:
            return OperationalPriority.LOW
        return OperationalPriority.LOWEST

    def identify_critical_incidents(self,
                                    signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [s for s in signals
                if s.get('severity', '') in ('critical', 'high')
                and s.get('signal_type') != 'info']

    def prioritize_risks(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        return sorted(risks, key=lambda r: severity_order.get(r.get('severity', 'info'), 99))

    def clear(self):
        self._priority_history.clear()
