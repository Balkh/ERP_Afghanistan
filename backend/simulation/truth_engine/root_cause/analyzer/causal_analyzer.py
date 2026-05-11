"""
Task 3: CausalAnalyzer — Full dependency chain analysis.
Maps Agent -> Workflow -> Event -> System State -> Mismatch.
Read-only analysis. No execution. No inference without evidence.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import (
    CausalChain, CausalLink, NodeType, EdgeType, RootCause,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.analyzer')


class CausalAnalyzer:
    """
    Analyzes the full dependency chain between events, agents,
    workflows, and mismatches.
    """

    def __init__(self):
        self._analyses: Dict[str, Dict[str, Any]] = {}

    def analyze(
        self,
        chain: CausalChain,
        root_cause: RootCause,
        agent_executions: Dict[str, int],
        workflow_completions: Dict[str, int],
    ) -> Dict[str, Any]:
        analysis = {
            'chain_id': chain.chain_id,
            'mismatch_id': chain.mismatch_id,
            'tick': chain.tick,
            'root_cause': root_cause.to_dict(),
            'dependency_chain': self._build_dependency_chain(
                chain, root_cause
            ),
            'agent_workflow_map': self._map_agent_workflow(
                root_cause, agent_executions, workflow_completions
            ),
            'event_sequence': self._extract_event_sequence(chain),
        }
        self._analyses[chain.chain_id] = analysis
        return analysis

    def _build_dependency_chain(
        self, chain: CausalChain, root_cause: RootCause,
    ) -> List[Dict[str, Any]]:
        deps = []
        for link in chain.links:
            deps.append({
                'step': f"{link.source_type.value} -> "
                        f"{link.target_type.value}",
                'source': link.source_id,
                'target': link.target_id,
                'relation': link.edge_type.value,
                'confidence': link.confidence,
            })
        return deps

    def _map_agent_workflow(
        self, root_cause: RootCause,
        agent_executions: Dict[str, int],
        workflow_completions: Dict[str, int],
    ) -> Dict[str, Any]:
        return {
            'agent_activity': dict(agent_executions),
            'workflow_completions': dict(workflow_completions),
            'primary_type': root_cause.primary_type.value,
        }

    def _extract_event_sequence(
        self, chain: CausalChain,
    ) -> List[Dict[str, Any]]:
        return [
            {
                'link_id': link.link_id,
                'source': link.source_id,
                'target': link.target_id,
                'edge': link.edge_type.value,
            }
            for link in chain.links
        ]

    def get_analysis(self, chain_id: str) -> Optional[Dict[str, Any]]:
        return self._analyses.get(chain_id)

    @property
    def analysis_count(self) -> int:
        return len(self._analyses)
