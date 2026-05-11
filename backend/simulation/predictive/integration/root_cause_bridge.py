import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.engine import RootCauseEngine

logger = logging.getLogger('erp.simulation.predictive.integration.bridge')


class RootCausePredictiveBridge:
    def __init__(self, root_cause_engine: Optional[RootCauseEngine] = None):
        self._engine = root_cause_engine

    @property
    def engine(self) -> Optional[RootCauseEngine]:
        return self._engine

    def bind(self, root_cause_engine: RootCauseEngine):
        self._engine = root_cause_engine

    def get_recurring_patterns(self) -> List[Dict[str, Any]]:
        if not self._engine:
            return []
        patterns = []
        drift_history = self._engine.get_drift_history()
        seen_patterns: Dict[str, int] = {}
        for entry in drift_history:
            mm = entry.get('mismatch', {})
            mtype = mm.get('mismatch_type', '')
            module = mm.get('affected_module', '')
            key = f"{mtype}:{module}"
            seen_patterns[key] = seen_patterns.get(key, 0) + 1
        for key, count in seen_patterns.items():
            if count >= 2:
                parts = key.split(':')
                patterns.append({
                    'pattern_key': key,
                    'mismatch_type': parts[0],
                    'affected_module': parts[1],
                    'recurrence_count': count,
                    'frequency': count / max(len(drift_history), 1),
                })
        return patterns

    def get_recurring_root_causes(self) -> Dict[str, int]:
        if not self._engine:
            return {}
        counts: Dict[str, int] = {}
        for entry in self._engine.get_drift_history():
            rc = entry.get('root_cause', {})
            if rc:
                ptype = rc.get('primary_type', 'unknown')
                counts[ptype] = counts.get(ptype, 0) + 1
        return counts

    def get_causal_chain_statistics(self) -> Dict[str, Any]:
        if not self._engine:
            return {'total_chains': 0, 'avg_length': 0.0, 'max_length': 0}
        chains = []
        for entry in self._engine.get_drift_history():
            mid = entry.get('mismatch', {}).get('mismatch_id', '')
            cid = f"chain_{mid}"
            chain = self._engine.correlator.get_chain(cid)
            if chain:
                chains.append(len(chain.links))
        return {
            'total_chains': len(chains),
            'avg_length': round(sum(chains) / max(len(chains), 1), 2),
            'max_length': max(chains) if chains else 0,
        }

    def get_dependency_chain_analysis(self) -> Dict[str, Any]:
        if not self._engine:
            return {'workflow_dependencies': {}, 'agent_dependencies': {}}
        agent_counts: Dict[str, int] = {}
        workflow_counts: Dict[str, int] = {}
        for entry in self._engine.get_drift_history():
            mm = entry.get('mismatch', {})
            module = mm.get('affected_module', '')
            if module:
                workflow_counts[module] = workflow_counts.get(module, 0) + 1
            mm_ctx = mm.get('context', {})
            agent = mm_ctx.get('agent_id', '')
            if agent:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        return {
            'workflow_dependencies': workflow_counts,
            'agent_dependencies': agent_counts,
        }
