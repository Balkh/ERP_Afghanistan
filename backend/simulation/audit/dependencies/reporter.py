"""
Task D: CouplingRiskReport — generates dependency graph and coupling warnings.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger('erp.simulation.audit.dependencies.reporter')


class CouplingRiskReporter:
    def generate(self, dep_analysis: Dict[str, Any],
                 layer_validation: Dict[str, Any]) -> Dict[str, Any]:
        prod_violations = dep_analysis.get('production_violation_count', 0)
        layer_violations = layer_validation.get('violation_count', 0)
        cross = dep_analysis.get('cross_layer_count', 0)
        risk_level = 'LOW'
        if prod_violations > 0 or layer_violations > 5:
            risk_level = 'HIGH'
        elif layer_violations > 0 or cross > 0:
            risk_level = 'MEDIUM'
        return {
            'dependency_health': {
                'production_coupling_violations': prod_violations,
                'layer_isolation_violations': layer_violations,
                'cross_layer_imports': cross,
            },
            'risk_level': risk_level,
            'recommendations': self._recommendations(risk_level),
        }

    def _recommendations(self, risk_level: str) -> List[str]:
        recs = []
        if risk_level == 'HIGH':
            recs.append("Remove production domain imports from simulation layer")
            recs.append("Enforce strict layer boundary through import validation")
        if risk_level in ('HIGH', 'MEDIUM'):
            recs.append("Review cross-layer imports for circular dependency risk")
            recs.append("Consider isolating truth_engine further from workflows")
        return recs
