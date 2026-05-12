"""Incident reconstructor — reconstructs operational incidents from events."""
from collections import deque
from typing import Any, Dict, List, Optional


class IncidentReconstructor:
    def __init__(self, max_history: int = 100):
        self._reconstruction_history: deque = deque(maxlen=max_history)

    def reconstruct(self, incident_id: str, events: List[Dict[str, Any]],
                    trigger_event_id: Optional[str] = None) -> Dict[str, Any]:
        trigger = None
        related = []
        for e in events:
            if trigger_event_id and e.get('event_id') == trigger_event_id:
                trigger = e
            if e.get('event_type', '').startswith('error') or \
               e.get('event_type', '').startswith('failure') or \
               e.get('event_type', '').startswith('incident'):
                related.append(e)
        self._reconstruction_history.append({
            'incident_id': incident_id, 'events_analyzed': len(events),
            'related_events': len(related),
        })
        return {
            'incident_id': incident_id,
            'trigger_event': trigger,
            'related_events': related,
            'total_related': len(related),
        }

    def get_reconstruction_count(self) -> int:
        return len(self._reconstruction_history)

    def clear(self):
        self._reconstruction_history.clear()
