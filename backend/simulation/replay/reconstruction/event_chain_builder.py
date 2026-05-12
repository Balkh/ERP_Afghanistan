"""Event chain builder — builds causal chains from event sequences."""
from collections import deque
from typing import Any, Dict, List, Optional


class EventChainBuilder:
    def __init__(self, max_chains: int = 100):
        self._chains: deque = deque(maxlen=max_chains)

    def build_chain(self, events: List[Dict[str, Any]],
                    start_event_id: Optional[str] = None) -> Dict[str, Any]:
        if not events:
            return {'chain': [], 'length': 0}
        event_map = {e.get('event_id', ''): e for e in events}
        if start_event_id and start_event_id in event_map:
            start = start_event_id
        else:
            start = events[0].get('event_id', '')
        chain = []
        current = start
        visited = set()
        while current and current in event_map and current not in visited:
            visited.add(current)
            chain.append(event_map[current])
            parent = event_map[current].get('causal_parent')
            current = parent if parent and parent not in visited else None
            if len(chain) > 100:
                break
        self._chains.append({
            'start_event': start, 'chain_length': len(chain),
        })
        return {'chain': chain, 'length': len(chain), 'start_event': start}

    def build_downstream_chain(self, events: List[Dict[str, Any]],
                                start_event_id: str) -> Dict[str, Any]:
        children: Dict[str, List[str]] = {}
        for e in events:
            parent = e.get('causal_parent')
            if parent:
                if parent not in children:
                    children[parent] = []
                children[parent].append(e.get('event_id', ''))
        chain = []
        queue = [start_event_id]
        visited = set()
        while queue and len(chain) < 100:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            event = next((e for e in events if e.get('event_id') == current), None)
            if event:
                chain.append(event)
            for child in children.get(current, []):
                if child not in visited:
                    queue.append(child)
        return {'chain': chain, 'length': len(chain), 'start_event': start_event_id}

    def clear(self):
        self._chains.clear()
