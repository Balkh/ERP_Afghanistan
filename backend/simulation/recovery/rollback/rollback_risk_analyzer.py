"""Rollback risk analysis — evaluates risk of rolling back workflows."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import RollbackRisk, IntegritySeverity


class RollbackRiskAnalyzer:
    def __init__(self, max_history: int = 100):
        self._risk_history: deque = deque(maxlen=max_history)

    def analyze_risk(self, simulation_result: Dict[str, Any],
                     dependency_chain_length: int = 0) -> Dict[str, Any]:
        risk_score = simulation_result.get('estimated_risk_score', 0)
        has_conflicts = simulation_result.get('has_conflicts', False)
        conflicting = simulation_result.get('conflicts', [])
        has_irreversible = has_conflicts
        if risk_score >= 70 or has_conflicts:
            severity = IntegritySeverity.CRITICAL
        elif risk_score >= 40:
            severity = IntegritySeverity.HIGH
        elif risk_score >= 20:
            severity = IntegritySeverity.MEDIUM
        elif risk_score >= 5:
            severity = IntegritySeverity.LOW
        else:
            severity = IntegritySeverity.INFO
        risk = RollbackRisk(
            risk_score=risk_score, severity=severity,
            conflicting_transactions=conflicting,
            dependency_chain_length=dependency_chain_length,
            has_irreversible_operations=has_irreversible,
        )
        self._risk_history.append({
            'risk_score': risk_score, 'severity': severity.value,
            'has_irreversible': has_irreversible,
        })
        return {
            'risk_score': risk_score, 'severity': severity.value,
            'conflicting_transactions': conflicting,
            'dependency_chain_length': dependency_chain_length,
            'has_irreversible_operations': has_irreversible,
        }

    def get_average_risk_score(self) -> float:
        if not self._risk_history:
            return 0.0
        return sum(r['risk_score'] for r in self._risk_history) / len(self._risk_history)

    def clear(self):
        self._risk_history.clear()
