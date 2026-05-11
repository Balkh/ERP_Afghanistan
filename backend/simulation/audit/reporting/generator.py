"""
Task F: IntelligenceHealthReportGenerator — unified system health report.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger('erp.simulation.audit.reporting.generator')


class IntelligenceHealthReportGenerator:
    def generate(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        e2e = audit_data.get('event_lifecycle', {})
        graph = audit_data.get('graph', {})
        memory = audit_data.get('memory', {})
        deps = audit_data.get('dependencies', {})
        perf = audit_data.get('performance', {})
        ev_health = e2e.get('health_summary', 'UNKNOWN')
        graph_dag = graph.get('dag_integrity', False)
        mem_bounded = memory.get('all_bounded', False)
        deps_clean = deps.get('layers_isolated', False)
        perf_warnings = perf.get('warning_count', 0)
        scores = {
            'event_lifecycle_score': self._score_event(e2e),
            'graph_integrity_score': self._score_graph(graph),
            'memory_safety_score': 100.0 if mem_bounded else 50.0,
            'dependency_cleanliness_score': self._score_deps(deps),
            'performance_stability_score': self._score_perf(perf),
        }
        scores['overall_stability_score'] = round(
            sum(scores.values()) / len(scores), 2
        )
        return {
            'overall_stability_score': scores['overall_stability_score'],
            'scores': scores,
            'health_summary': {
                'event_lifecycle': ev_health,
                'graph_integrity': 'PASS' if graph_dag else 'FAIL',
                'memory_bounds': 'PASS' if mem_bounded else 'FAIL',
                'dependency_isolation': 'PASS' if deps_clean else 'FAIL',
                'performance_stability': 'PASS' if perf_warnings == 0
                else 'WARNING',
            },
            'architectural_entropy': self._compute_entropy(scores),
        }

    def _score_event(self, data: Dict) -> float:
        health = data.get('health_summary', 'UNKNOWN')
        mapping = {'HEALTHY': 100.0, 'WARNING': 70.0, 'CRITICAL': 30.0}
        return mapping.get(health, 50.0)

    def _score_graph(self, data: Dict) -> float:
        dag = data.get('dag_integrity', False)
        density_warn = data.get('density_warning', False)
        orphans = len(data.get('orphan_nodes', []))
        if not dag:
            return 0.0
        score = 100.0
        if density_warn:
            score -= 30.0
        score -= orphans * 5.0
        return max(0.0, score)

    def _score_deps(self, data: Dict) -> float:
        violations = data.get('violation_count', 0)
        return max(0.0, 100.0 - violations * 20.0)

    def _score_perf(self, data: Dict) -> float:
        warnings = data.get('warning_count', 0)
        return max(0.0, 100.0 - warnings * 30.0)

    def _compute_entropy(self, scores: Dict[str, float]) -> float:
        values = [v / 100.0 for v in scores.values() if v > 0]
        if not values:
            return 0.0
        import math
        entropy = 0.0
        for v in values:
            if v > 0:
                entropy -= v * math.log2(v)
        return round(entropy, 4)
