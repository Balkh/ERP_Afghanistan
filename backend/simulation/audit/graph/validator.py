"""
Task B: GraphIntegrityValidator — validates DAG integrity, cycles, orphans, density.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import CausalGraph

logger = logging.getLogger('erp.simulation.audit.graph.validator')


class GraphIntegrityValidator:
    def validate(self, graph: CausalGraph) -> Dict[str, Any]:
        nodes = graph.nodes
        edges = graph.edges
        node_ids = set(nodes.keys())
        edge_list = list(edges.values())
        has_cycle = self._detect_cycle(edge_list)
        orphans = self._detect_orphans(nodes, edge_list)
        disconnected = self._detect_disconnected(nodes, edge_list)
        edge_count = len(edge_list)
        node_count = len(node_ids)
        density = (2.0 * edge_count) / (node_count * (node_count - 1)) \
            if node_count > 1 else 0.0
        return {
            'node_count': node_count,
            'edge_count': edge_count,
            'has_cycle': has_cycle,
            'orphan_nodes': orphans,
            'disconnected_chains': disconnected,
            'edge_density': round(density, 4),
            'dag_integrity': not has_cycle,
            'density_warning': density > 0.5,
        }

    def _detect_cycle(self, edges: List) -> bool:
        adj = {}
        for e in edges:
            src = e.source_id
            tgt = e.target_id
            adj.setdefault(src, []).append(tgt)
        visited = set()
        rec_stack = set()
        def dfs(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if dfs(neighbor):
                    return True
            rec_stack.discard(node)
            return False
        for node in list(adj.keys()):
            if dfs(node):
                return True
        return False

    def _detect_orphans(self, nodes: Dict, edges: List) -> List[str]:
        referenced = set()
        for e in edges:
            referenced.add(e.source_id)
            referenced.add(e.target_id)
        return [nid for nid in nodes if nid not in referenced]

    def _detect_disconnected(self, nodes: Dict, edges: List) -> int:
        if not edges:
            return len(nodes) if nodes else 0
        adj = {}
        for e in edges:
            adj.setdefault(e.source_id, set()).add(e.target_id)
            adj.setdefault(e.target_id, set()).add(e.source_id)
        visited = set()
        start = next(iter(adj.keys()), None)
        if not start:
            return len(nodes)
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    stack.append(neighbor)
        return sum(1 for nid in nodes if nid not in visited)
