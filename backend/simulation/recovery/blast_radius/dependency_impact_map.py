"""Dependency impact mapping — maps dependency chains and estimates module-level impact."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import DependencyImpact


class DependencyImpactMap:
    def __init__(self, max_history: int = 100):
        self._impact_maps: deque = deque(maxlen=max_history)

    def build_impact_map(self, modules: List[str],
                         dependency_graph: Optional[Dict[str, List[str]]] = None,
                         critical_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        dependency_graph = dependency_graph or {}
        critical_paths = critical_paths or []
        impacts: Dict[str, Dict[str, Any]] = {}
        for mod in modules:
            downstream = dependency_graph.get(mod, [])
            depth = self._calculate_depth(mod, dependency_graph)
            is_critical = mod in critical_paths
            score = min(100.0, depth * 10 + len(downstream) * 5 + (20 if is_critical else 0))
            impacts[mod] = {
                'module_name': mod, 'impact_score': score,
                'dependency_depth': depth,
                'affected_downstream': downstream,
                'is_critical_path': is_critical,
            }
        self._impact_maps.append({
            'modules_mapped': len(modules), 'total_edges': sum(len(v) for v in dependency_graph.values()),
        })
        return impacts

    def _calculate_depth(self, module: str, graph: Dict[str, List[str]],
                         visited: Optional[set] = None, depth: int = 0) -> int:
        if visited is None:
            visited = set()
        if module in visited or depth > 50:
            return depth
        visited.add(module)
        max_depth = depth
        for dep in graph.get(module, []):
            d = self._calculate_depth(dep, graph, visited, depth + 1)
            max_depth = max(max_depth, d)
        return max_depth

    def clear(self):
        self._impact_maps.clear()
