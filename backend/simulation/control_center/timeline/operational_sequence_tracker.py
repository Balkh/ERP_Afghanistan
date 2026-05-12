from collections import deque
from typing import Any, Dict, List, Optional

from simulation.control_center.models import UnifiedTimelineEvent


class OperationalSequenceTracker:
    def __init__(self, max_sequences: int = 200, max_events_per_sequence: int = 50):
        self._sequences: Dict[str, Dict[str, Any]] = {}
        self._order: deque = deque(maxlen=max_sequences)
        self._max_events = max_events_per_sequence
        self._max_sequences = max_sequences

    def start_sequence(
        self, sequence_id: str, tick: int, description: str
    ) -> Dict[str, Any]:
        if len(self._sequences) >= self._max_sequences:
            oldest = self._order[0] if self._order else None
            if oldest and oldest in self._sequences:
                del self._sequences[oldest]
        sequence = {
            'sequence_id': sequence_id,
            'tick_start': tick,
            'tick_end': tick,
            'description': description,
            'event_count': 0,
            'events': [],
            'active': True,
        }
        self._sequences[sequence_id] = sequence
        self._order.append(sequence_id)
        return dict(sequence)

    def add_to_sequence(
        self, sequence_id: str, event: UnifiedTimelineEvent
    ) -> bool:
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return False
        if len(sequence['events']) >= self._max_events:
            return False
        sequence['events'].append({
            'event_id': event.event_id,
            'tick': event.tick,
            'event_type': event.event_type,
            'description': event.description,
            'severity': event.severity.value,
        })
        sequence['event_count'] = len(sequence['events'])
        if event.tick > sequence['tick_end']:
            sequence['tick_end'] = event.tick
        return True

    def get_sequence(self, sequence_id: str) -> Optional[Dict[str, Any]]:
        raw = self._sequences.get(sequence_id)
        if raw is None:
            return None
        return dict(raw)

    def get_all_sequences(self) -> List[Dict[str, Any]]:
        return [dict(s) for s in self._sequences.values()]

    def get_sequence_count(self) -> int:
        return len(self._sequences)

    def clear(self):
        self._sequences.clear()
        self._order.clear()
