"""
Task B: GraphComplexityAnalyzer — measures graph depth, branching, causal density.
"""
import logging
from typing import Any, Dict, List

from simulation.truth_engine.root_cause.models import CausalGraph

logger = logging.getLogger('erp.simulation.audit.graph.analyzer')


class GraphComplexityAnalyzer:
    def analyze(self, graph: CausalGraph) -> Dict[str, Any]:
        nodes = graph.nodes
        edges = list(graph.edges.values())
        depth = self._compute_depth(edges)
        branching = self._compute_branching(edges)
        density = len(edges) / max(len(nodes), 1)
        traversal_cost = len(nodes) + len(edges)
        return {
            'graph_depth': depth,
            'branching_factor': round(branching, 2),
            'causal_density': round(density, 4),
            'traversal_cost': traversal_cost,
            'depth_warning': depth > 20,
            'branching_warning': branching > 10,
            'density_warning': density > 5.0,
        }

    def _compute_depth(self, edges: List) -> int:
        if not edges:
            return 0
        adj = {}
        for e in edges:
            adj.setdefault(e.source_id, []).append(e.target_id)
        longest = 0
        visited = {}
        def dfs(node, path_len):
            nonlocal longest
            if node in visited and visited[node] >= path_len:
                return
            visited[node] = path_len
            if path_len > longest:
                longest = path_len
            for neighbor in adj.get(node, []):
                dfs(neighbor, path_len + 1)
        for src in list(adj.keys()):
            dfs(src, 1)
        return longest

    def _compute_branching(self, edges: List) -> float:
        if not edges:
            return 0.0
        out_degree = {}
        for e in edges:
            out_degree[e.source_id] = out_degree.get(e.source_id, 0) + 1
        if not out_degree:
            return 0.0
        return sum(out_degree.values()) / len(out_degree)
