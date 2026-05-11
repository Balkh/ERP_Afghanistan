"""
Task 7: DriftMemoryStore — Historical drift pattern storage.
No ML or predictive models. Only statistical aggregation.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import (
    DriftPattern, RootCause,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.history')


class DriftMemoryStore:
    """
    Stores historical patterns of system drift.
    Read-only analysis. Statistical aggregation only.
    """

    def __init__(self):
        self._drift_history: List[Dict[str, Any]] = []
        self._pattern_history: Dict[str, List[DriftPattern]] = {}

    def record_drift(
        self,
        tick: int,
        mismatch_data: Dict[str, Any],
        root_cause: Optional[RootCause] = None,
    ):
        entry = {
            'tick': tick,
            'mismatch': dict(mismatch_data),
            'root_cause': root_cause.to_dict() if root_cause else None,
        }
        self._drift_history.append(entry)

    def record_patterns(self, run_id: str, patterns: List[DriftPattern]):
        self._pattern_history[run_id] = patterns

    def get_drift_history(
        self, since_tick: int = 0,
    ) -> List[Dict[str, Any]]:
        return [
            e for e in self._drift_history
            if e.get('tick', 0) >= since_tick
        ]

    def get_pattern_history(
        self, run_id: str,
    ) -> List[DriftPattern]:
        return list(self._pattern_history.get(run_id, []))

    def get_high_risk_workflows(
        self, min_frequency: int = 2,
    ) -> Dict[str, int]:
        workflow_counts: Dict[str, int] = {}
        for entry in self._drift_history:
            rc = entry.get('root_cause')
            if rc and rc.get('primary_type') in (
                'workflow_design_flaw', 'missing_mapping'
            ):
                mm = entry.get('mismatch', {})
                module = mm.get('affected_module', 'unknown')
                workflow_counts[module] = workflow_counts.get(module, 0) + 1
        return {
            wf: count for wf, count in workflow_counts.items()
            if count >= min_frequency
        }

    def get_frequently_failing_agents(
        self, min_failures: int = 2,
    ) -> Dict[str, int]:
        agent_counts: Dict[str, int] = {}
        for entry in self._drift_history:
            mm = entry.get('mismatch', {})
            module = mm.get('affected_module', '')
            if module:
                agent_counts[module] = agent_counts.get(module, 0) + 1
        return {
            agent: count for agent, count in agent_counts.items()
            if count >= min_failures
        }

    def get_drift_count(self) -> int:
        return len(self._drift_history)

    def clear(self):
        self._drift_history.clear()
        self._pattern_history.clear()
