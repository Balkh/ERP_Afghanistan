"""Causal forensics — traces causal chains for forensic analysis."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ForensicSeverity


class CausalForensics:
    def __init__(self, max_history: int = 100):
        self._forensic_history: deque = deque(maxlen=max_history)

    def trace_causal_chain(self, events: List[Dict[str, Any]],
                           start_event_id: str) -> Dict[str, Any]:
        event_map = {e.get('event_id', ''): e for e in events}
        chain = []
        current = start_event_id
        visited = set()
        while current and current in event_map and current not in visited:
            visited.add(current)
            chain.append(event_map[current])
            parent = event_map[current].get('causal_parent')
            current = parent if parent and parent not in visited else None
            if len(chain) > 100:
                break
        depth = len(chain)
        severity = (ForensicSeverity.CRITICAL if depth > 20
                    else ForensicSeverity.HIGH if depth > 10
                    else ForensicSeverity.MEDIUM if depth > 3
                    else ForensicSeverity.INFO)
        self._forensic_history.append({
            'start_event': start_event_id, 'chain_depth': depth,
            'severity': severity.value,
        })
        return {
            'causal_chain': chain, 'depth': depth,
            'severity': severity.value,
            'start_event': start_event_id,
        }

    def find_root_cause(self, events: List[Dict[str, Any]],
                         event_id: str) -> Dict[str, Any]:
        event_map = {e.get('event_id', ''): e for e in events}
        current = event_id
        visited = set()
        while current and current in event_map and current not in visited:
            visited.add(current)
            parent = event_map[current].get('causal_parent')
            if not parent or parent in visited:
                break
            current = parent
            if len(visited) > 100:
                break
        root_event = event_map.get(current, {})
        return {
            'root_cause_event': root_event,
            'root_event_id': current,
            'trace_length': len(visited),
            'trace': list(visited),
        }

    def clear(self):
        self._forensic_history.clear()
