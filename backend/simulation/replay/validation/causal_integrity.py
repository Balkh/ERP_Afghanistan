"""Causal integrity — validates causal chains for completeness."""
from collections import deque
from typing import Any, Dict, List, Optional


class CausalIntegrity:
    def __init__(self, max_history: int = 100):
        self._integrity_history: deque = deque(maxlen=max_history)

    def check_chain_integrity(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        event_ids = {e.get('event_id', '') for e in events}
        broken_links = []
        orphans = []
        for e in events:
            parent = e.get('causal_parent')
            if parent and parent not in event_ids:
                broken_links.append({
                    'event_id': e.get('event_id', ''),
                    'missing_parent': parent,
                })
        parents_with_children = set()
        for e in events:
            p = e.get('causal_parent')
            if p:
                parents_with_children.add(p)
        for e in events:
            eid = e.get('event_id', '')
            if eid not in parents_with_children and e.get('causal_parent') is None:
                pass
            elif eid not in parents_with_children and e.get('causal_parent'):
                pass
        self._integrity_history.append({
            'check': 'causal_integrity',
            'passed': len(broken_links) == 0,
            'broken_links': len(broken_links),
            'events_checked': len(events),
        })
        return {'chain_integrity': len(broken_links) == 0,
                'broken_links': broken_links,
                'total_events': len(events)}

    def verify_chain_completeness(self, events: List[Dict[str, Any]],
                                    root_event_id: str) -> Dict[str, Any]:
        event_map = {e.get('event_id', ''): e for e in events}
        visited = set()
        queue = [root_event_id]
        while queue and len(visited) < 100:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for e in events:
                if e.get('causal_parent') == current and e.get('event_id', '') not in visited:
                    queue.append(e.get('event_id', ''))
        all_in_chain = all(eid in event_map for eid in visited)
        self._integrity_history.append({
            'check': 'chain_completeness', 'passed': all_in_chain,
            'events_in_chain': len(visited),
        })
        return {'is_complete': all_in_chain,
                'events_in_chain': len(visited),
                'root_event_id': root_event_id}

    def clear(self):
        self._integrity_history.clear()
