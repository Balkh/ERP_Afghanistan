"""
Task 6: CausalGraphBuilder — Builds a directed causal DAG.
Nodes: Event, Workflow, Agent, Mismatch.
Edges: triggers, causes, correlates_with.
No inferred edges without evidence.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import (
    CausalGraph, CausalLink, NodeType, EdgeType, RootCause,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.graph')


class CausalGraphBuilder:
    """
    Builds a Directed Acyclic Graph (DAG) from causal analysis data.
    Read-only structure. No inferred edges.
    """

    def __init__(self):
        self._graphs: Dict[str, CausalGraph] = {}

    def build(
        self,
        graph_id: str,
        mismatches: List[Dict[str, Any]],
        chains: List[CausalLink],
        root_causes: List[RootCause],
        agent_executions: Dict[str, int],
        workflow_completions: Dict[str, int],
    ) -> CausalGraph:
        graph = CausalGraph()
        for agent_id, count in agent_executions.items():
            if count > 0:
                graph.add_node(
                    node_id=f"agent:{agent_id}",
                    node_type=NodeType.AGENT,
                    label=f"Agent {agent_id}",
                    metadata={'execution_count': count},
                )
        for wf_id, count in workflow_completions.items():
            if count > 0:
                graph.add_node(
                    node_id=f"workflow:{wf_id}",
                    node_type=NodeType.WORKFLOW,
                    label=f"Workflow {wf_id}",
                    metadata={'completion_count': count},
                )
        for m in mismatches:
            graph.add_node(
                node_id=m.get('mismatch_id', 'unknown'),
                node_type=NodeType.MISMATCH,
                label=m.get('description', 'Mismatch'),
                metadata={'type': m.get('mismatch_type', '')},
            )
        for link in chains:
            graph.add_edge(link)
        for cause in root_causes:
            graph.add_node(
                node_id=f"cause:{cause.cause_id}",
                node_type=NodeType.SYSTEM_STATE,
                label=f"Root cause: {cause.primary_type.value}",
                metadata={
                    'confidence': cause.confidence,
                    'mismatch_id': cause.mismatch_id,
                },
            )
        self._graphs[graph_id] = graph
        return graph

    def get_graph(self, graph_id: str) -> Optional[CausalGraph]:
        return self._graphs.get(graph_id)

    @property
    def graph_count(self) -> int:
        return len(self._graphs)
