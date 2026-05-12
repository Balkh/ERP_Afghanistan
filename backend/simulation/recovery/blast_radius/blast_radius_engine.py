"""Blast radius engine — estimates the impact scope of detected corruption."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import BlastRadiusResult


class BlastRadiusEngine:
    def __init__(self, max_history: int = 100):
        self._analyses: deque = deque(maxlen=max_history)

    def analyze(self, corruption: Dict[str, Any],
                affected_workflows: Optional[List[str]] = None,
                affected_modules: Optional[List[str]] = None,
                dependency_impact: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        affected_workflows = affected_workflows or []
        affected_modules = affected_modules or []
        wf_count = len(affected_workflows)
        mod_count = len(affected_modules)
        blast_radius = corruption.get('estimated_blast_radius', 0)
        financial_exposure = 0.0
        inv_items = 0
        if dependency_impact:
            for mod, impact in dependency_impact.items() if isinstance(dependency_impact, dict) else []:
                if isinstance(impact, dict):
                    financial_exposure += impact.get('financial_exposure', 0)
                    inv_items += impact.get('inventory_items_affected', 0)
        total_deps = wf_count + mod_count
        critical_count = sum(1 for w in affected_workflows if 'critical' in w.lower()) if affected_workflows else 0
        impact_score = min(100.0, blast_radius * 10 + wf_count * 5 + mod_count * 3 + critical_count * 10)
        result = BlastRadiusResult(
            estimated_impact_score=impact_score,
            affected_workflows=affected_workflows,
            affected_modules=affected_modules,
            financial_exposure=financial_exposure,
            inventory_items_affected=inv_items,
            total_dependencies=total_deps,
            critical_path_count=critical_count,
        )
        self._analyses.append({
            'impact_score': impact_score, 'workflows': wf_count,
            'modules': mod_count, 'critical_paths': critical_count,
        })
        return {
            'estimated_impact_score': impact_score,
            'affected_workflows': affected_workflows,
            'affected_modules': affected_modules,
            'financial_exposure': financial_exposure,
            'inventory_items_affected': inv_items,
            'total_dependencies': total_deps,
            'critical_path_count': critical_count,
        }

    def get_analysis_count(self) -> int:
        return len(self._analyses)

    def clear(self):
        self._analyses.clear()
