"""Dependency rollback map — builds dependency chains for rollback analysis."""
from collections import deque
from typing import Any, Dict, List, Optional


class DependencyRollbackMap:
    def __init__(self, max_history: int = 100):
        self._dependency_maps: deque = deque(maxlen=max_history)

    def build_dependency_map(self, workflows: List[Dict[str, Any]],
                             links: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        links = links or []
        dependency_map: Dict[str, List[str]] = {}
        dependent_map: Dict[str, List[str]] = {}
        for w in workflows:
            wf_id = w.get('workflow_id', '')
            dependency_map[wf_id] = []
            dependent_map[wf_id] = []
        for link in links:
            source = link.get('source', '')
            target = link.get('target', '')
            if source in dependency_map:
                dependency_map[source].append(target)
            if target in dependent_map:
                dependent_map[target].append(source)
        chain_lengths = {}
        for wf_id in dependency_map:
            visited = set()
            stack = [wf_id]
            depth = 0
            while stack and depth < 100:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                for dep in dependency_map.get(current, []):
                    if dep not in visited:
                        stack.append(dep)
                depth += 1
            chain_lengths[wf_id] = depth
        self._dependency_maps.append({
            'workflow_count': len(workflows),
            'link_count': len(links),
            'max_chain_length': max(chain_lengths.values()) if chain_lengths else 0,
        })
        return {
            'dependency_map': dependency_map,
            'dependent_map': dependent_map,
            'chain_lengths': chain_lengths,
            'max_depth': max(chain_lengths.values()) if chain_lengths else 0,
        }

    def clear(self):
        self._dependency_maps.clear()
