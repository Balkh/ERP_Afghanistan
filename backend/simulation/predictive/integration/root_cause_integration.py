import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.integration.root_cause')

WORKFLOW_MODULES = ['sales', 'purchase', 'inventory', 'return', 'hr']


class RootCauseIntegration:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._integration_history: deque = deque(maxlen=max_history)

    def integrate(self, drift_history: List[Dict[str, Any]],
                  root_cause_data: List[Dict[str, Any]],
                  patterns: List[Any],
                  workflow_completions: Dict[str, int]) -> Dict[str, Any]:
        recurrence = self._calculate_root_cause_recurrence(root_cause_data)
        affected_workflows = self._identify_affected_workflows(drift_history)
        pattern_impacts = self._assess_pattern_impacts(patterns)
        workflow_risk_factors = self._calculate_workflow_risk_factors(
            drift_history, root_cause_data, workflow_completions,
        )
        integration = {
            'root_cause_recurrence': recurrence,
            'affected_workflows': affected_workflows,
            'pattern_impacts': pattern_impacts,
            'workflow_risk_factors': workflow_risk_factors,
            'total_root_causes': len(root_cause_data),
            'total_patterns': len(patterns) if patterns else 0,
        }
        self._integration_history.append(integration)
        return integration

    def _calculate_root_cause_recurrence(self,
                                         root_cause_data: List[Dict]) -> Dict[str, int]:
        recurrence: Dict[str, int] = {}
        for rc in root_cause_data:
            primary = rc.get('root_cause', {}).get('primary_type', 'unknown')
            recurrence[primary] = recurrence.get(primary, 0) + 1
        return recurrence

    def _identify_affected_workflows(self,
                                     drift_history: List[Dict]) -> Dict[str, int]:
        affected: Dict[str, int] = {}
        for d in drift_history:
            module = d.get('mismatch', {}).get('affected_module', '')
            if module in WORKFLOW_MODULES:
                affected[module] = affected.get(module, 0) + 1
        return affected

    def _assess_pattern_impacts(self, patterns: List[Any]) -> List[Dict[str, Any]]:
        impacts: List[Dict[str, Any]] = []
        if not patterns:
            return impacts
        for p in patterns:
            if hasattr(p, 'to_dict'):
                pd = p.to_dict()
            elif isinstance(p, dict):
                pd = p
            else:
                continue
            impacts.append({
                'pattern_type': pd.get('pattern_type', 'unknown'),
                'frequency': pd.get('frequency', 0),
                'affected_module': pd.get('affected_module', 'unknown'),
            })
        return impacts

    def _calculate_workflow_risk_factors(self, drift_history: List[Dict],
                                         root_cause_data: List[Dict],
                                         workflow_completions: Dict[str, int]) -> Dict[str, float]:
        factors: Dict[str, float] = {}
        for module in WORKFLOW_MODULES:
            module_drifts = [d for d in drift_history
                             if d.get('mismatch', {}).get('affected_module', '') == module]
            module_causes = [rc for rc in root_cause_data
                             if module in str(rc.get('mismatch_id', ''))]
            drift_factor = len(module_drifts) * 5
            cause_factor = len(module_causes) * 10
            completion = workflow_completions.get(module, 0)
            completion_factor = max(0, 100 - completion) * 0.5 if completion > 0 else 50
            factors[module] = round(min(drift_factor + cause_factor + completion_factor, 100.0), 2)
        return factors

    @property
    def record_count(self) -> int:
        return len(self._integration_history)

    def get_latest_integration(self) -> Optional[Dict[str, Any]]:
        if self._integration_history:
            return self._integration_history[-1]
        return None

    def clear(self):
        self._integration_history.clear()
