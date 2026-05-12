"""Timeline builder — constructs immutable event timelines."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import TimelineEvent


class TimelineBuilder:
    def __init__(self, max_events: int = 1000):
        self._events: deque = deque(maxlen=max_events)
        self._event_count: int = 0

    def add_event(self, tick: int, event_type: str, source: str,
                  description: str = "",
                  payload: Optional[Dict[str, Any]] = None,
                  causal_parent: Optional[str] = None) -> str:
        self._event_count += 1
        event_id = f"ev_{self._event_count}_{tick}"
        event = TimelineEvent(
            event_id=event_id, tick=tick, event_type=event_type,
            source=source, description=description,
            payload=payload or {}, causal_parent=causal_parent,
        )
        self._events.append(event)
        return event_id

    def get_events(self, since_tick: int = 0, until_tick: Optional[int] = None) -> List[Dict[str, Any]]:
        result = []
        for e in self._events:
            if e.tick >= since_tick:
                if until_tick is None or e.tick <= until_tick:
                    result.append({
                        'event_id': e.event_id, 'tick': e.tick,
                        'event_type': e.event_type, 'source': e.source,
                        'description': e.description, 'payload': e.payload,
                        'causal_parent': e.causal_parent,
                    })
        return result

    def get_event_count(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()
        self._event_count = 0
