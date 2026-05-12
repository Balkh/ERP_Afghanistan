"""Remediation priority — assigns priority levels to recovery recommendations."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegritySeverity, RecoveryPathType


class RemediationPriority:
    def __init__(self, max_history: int = 100):
        self._priority_history: deque = deque(maxlen=max_history)

    def calculate_priority(self, severity: IntegritySeverity,
                           blast_radius_score: float = 0.0,
                           has_irreversible: bool = False,
                           workflows_blocked: int = 0) -> Dict[str, Any]:
        base_priority = {
            IntegritySeverity.CRITICAL: 100,
            IntegritySeverity.HIGH: 75,
            IntegritySeverity.MEDIUM: 50,
            IntegritySeverity.LOW: 25,
            IntegritySeverity.INFO: 5,
        }.get(severity, 0)
        bonus = (blast_radius_score * 0.2) + (30 if has_irreversible else 0) + (workflows_blocked * 10)
        priority = min(100, base_priority + bonus)
        level = ('critical' if priority >= 80 else 'high' if priority >= 55
                 else 'medium' if priority >= 30 else 'low')
        self._priority_history.append({
            'priority_score': priority, 'level': level,
        })
        return {'priority_score': priority, 'priority_level': level,
                'base_priority': base_priority, 'bonus': bonus}

    def clear(self):
        self._priority_history.clear()
