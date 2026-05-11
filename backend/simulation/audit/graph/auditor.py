"""
Task B: GraphMemoryAuditor — verifies bounded node/edge storage and cleanup.
"""
import logging
from typing import Any, Dict, Optional

from simulation.truth_engine.root_cause.graph.causal_graph_builder import (
    CausalGraphBuilder,
)

logger = logging.getLogger('erp.simulation.audit.graph.auditor')


class GraphMemoryAuditor:
    def audit(self, builder: CausalGraphBuilder,
              max_nodes: int = 1000,
              max_edges: int = 5000) -> Dict[str, Any]:
        graphs = builder._graphs if hasattr(builder, '_graphs') else {}
        total_nodes = 0
        total_edges = 0
        for gid, g in graphs.items():
            total_nodes += len(g.nodes) if hasattr(g, 'nodes') else 0
            total_edges += len(g.edges) if hasattr(g, 'edges') else 0
        return {
            'builder_instance': builder.graph_count,
            'total_graphs': len(graphs),
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'node_exceeds_max': total_nodes > max_nodes,
            'edge_exceeds_max': total_edges > max_edges,
            'max_node_limit': max_nodes,
            'max_edge_limit': max_edges,
        }
