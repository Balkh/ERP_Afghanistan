"""Rollback validation — validates that a rollback simulation is safe."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegritySeverity


class RollbackValidator:
    def __init__(self, max_history: int = 100):
        self._validation_history: deque = deque(maxlen=max_history)

    def validate_rollback(self, simulation_result: Dict[str, Any],
                          risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        has_conflicts = simulation_result.get('has_conflicts', False)
        has_irreversible = risk_analysis.get('has_irreversible_operations', False)
        risk_score = risk_analysis.get('risk_score', 0)
        is_safe = not has_conflicts and not has_irreversible and risk_score < 50
        warnings = []
        if has_conflicts:
            warnings.append('Rollback has conflicting posted transactions')
        if has_irreversible:
            warnings.append('Rollback includes irreversible operations')
        if risk_score >= 50:
            warnings.append(f'High risk score ({risk_score})')
        if risk_score >= 70:
            severity = IntegritySeverity.CRITICAL
        elif risk_score >= 40:
            severity = IntegritySeverity.HIGH
        else:
            severity = IntegritySeverity.INFO if is_safe else IntegritySeverity.MEDIUM
        self._validation_history.append({
            'is_safe': is_safe, 'risk_score': risk_score,
            'warnings_count': len(warnings),
        })
        return {
            'is_safe': is_safe, 'severity': severity.value,
            'warnings': warnings, 'risk_score': risk_score,
            'blockers': ['has_conflicts'] if has_conflicts else [],
        }

    def get_validation_count(self) -> int:
        return len(self._validation_history)

    def clear(self):
        self._validation_history.clear()
