from collections import deque
from typing import Any, Dict, List, Optional

from simulation.control_center.models import IntelligenceSeverity, UnifiedTimelineEvent


class UnifiedTimeline:
    def __init__(self, max_events: int = 1000):
        self._events: deque = deque(maxlen=max_events)

    def add_event(
        self,
        event_id: str,
        tick: int,
        source_phase: str,
        event_type: str,
        description: str,
        severity: IntelligenceSeverity,
        payload: Optional[Dict[str, Any]] = None,
        related_event_ids: Optional[List[str]] = None,
    ) -> UnifiedTimelineEvent:
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event_id must be a non-empty string")
        if tick < 0:
            raise ValueError("tick must be >= 0")
        event = UnifiedTimelineEvent(
            event_id=event_id,
            tick=tick,
            source_phase=source_phase,
            event_type=event_type,
            description=description,
            severity=severity,
            payload=payload or {},
            related_event_ids=related_event_ids or [],
        )
        self._events.append(event)
        return event

    def get_events(
        self,
        tick_start: Optional[int] = None,
        tick_end: Optional[int] = None,
        source_phase: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[IntelligenceSeverity] = None,
        limit: int = 100,
    ) -> List[UnifiedTimelineEvent]:
        result = []
        for e in self._events:
            if tick_start is not None and e.tick < tick_start:
                continue
            if tick_end is not None and e.tick > tick_end:
                continue
            if source_phase is not None and e.source_phase != source_phase:
                continue
            if event_type is not None and e.event_type != event_type:
                continue
            if severity is not None and e.severity != severity:
                continue
            result.append(e)
        result.sort(key=lambda x: x.tick)
        return result[:limit]

    def get_event_count(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()
