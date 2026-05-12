"""Graph explosion safety guard for orchestration safety monitoring."""
from collections import deque
from typing import Any, Dict, List


class GraphExplosionGuard:
    """Monitors and guards against graph node/edge explosion and cycles."""

    def __init__(self, max_nodes: int = 1000, max_edges: int = 5000, max_history: int = 200):
        self._max_nodes = max_nodes
        self._max_edges = max_edges
        self._history: deque = deque(maxlen=max_history)

    def check_graph_size(self, node_count: int, edge_count: int, context: str = "") -> Dict[str, Any]:
        try:
            violations: List[str] = []
            if node_count > self._max_nodes:
                violations.append(
                    f"node_count {node_count} exceeds max {self._max_nodes}"
                )
            if edge_count > self._max_edges:
                violations.append(
                    f"edge_count {edge_count} exceeds max {self._max_edges}"
                )
            return {
                "safe": len(violations) == 0,
                "node_count": node_count,
                "edge_count": edge_count,
                "max_nodes": self._max_nodes,
                "max_edges": self._max_edges,
                "violations": violations,
                "context": context,
            }
        except Exception:
            return {
                "safe": False,
                "node_count": node_count,
                "edge_count": edge_count,
                "max_nodes": self._max_nodes,
                "max_edges": self._max_edges,
                "violations": ["check_graph_size failed with unexpected error"],
                "context": context,
            }

    def detect_cycle(
        self, adjacency: Dict[str, List[str]], max_traversal: int = 1000
    ) -> Dict[str, Any]:
        try:
            visited: set = set()
            rec_stack: set = set()
            cycle_path: List[str] = []
            traversal_count = 0

            def dfs(node: str) -> bool:
                nonlocal traversal_count
                if traversal_count > max_traversal:
                    return False
                visited.add(node)
                rec_stack.add(node)
                cycle_path.append(node)
                traversal_count += 1
                for neighbor in adjacency.get(node, []):
                    if traversal_count > max_traversal:
                        return False
                    traversal_count += 1
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        cycle_path.append(neighbor)
                        return True
                cycle_path.pop()
                rec_stack.discard(node)
                return False

            for node in adjacency:
                if node not in visited:
                    if dfs(node):
                        break
                if traversal_count > max_traversal:
                    break

            aborted = traversal_count > max_traversal
            if aborted:
                return {
                    "has_cycle": False,
                    "cycle_path": [],
                    "traversal_count": traversal_count,
                    "max_traversal": max_traversal,
                    "aborted": True,
                }

            return {
                "has_cycle": len(cycle_path) > 0,
                "cycle_path": list(cycle_path),
                "traversal_count": traversal_count,
                "max_traversal": max_traversal,
                "aborted": False,
            }
        except Exception:
            return {
                "has_cycle": False,
                "cycle_path": [],
                "traversal_count": 0,
                "max_traversal": max_traversal,
                "aborted": True,
            }

    def record_graph_check(self, node_count: int, edge_count: int, is_safe: bool) -> Dict[str, Any]:
        try:
            record = {
                "node_count": node_count,
                "edge_count": edge_count,
                "is_safe": is_safe,
            }
            self._history.append(record)
            return dict(record)
        except Exception:
            return {
                "node_count": node_count,
                "edge_count": edge_count,
                "is_safe": is_safe,
                "error": True,
            }

    def get_check_count(self) -> int:
        try:
            return len(self._history)
        except Exception:
            return 0

    def clear(self) -> None:
        try:
            self._history.clear()
        except Exception:
            pass
