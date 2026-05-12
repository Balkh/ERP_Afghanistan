"""Timeline integrity — validates timeline integrity and ordering."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import TimelineDirection


class TimelineIntegrity:
    def __init__(self, max_history: int = 200):
        self._integrity_history: deque = deque(maxlen=max_history)

    def check_ordering(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        ticks = [e.get('tick', -1) for e in events]
        is_ordered = all(ticks[i] <= ticks[i + 1] for i in range(len(ticks) - 1))
        has_no_negative = all(t >= 0 for t in ticks)
        self._integrity_history.append({
            'check': 'ordering', 'passed': is_ordered and has_no_negative,
            'events': len(events),
        })
        return {'is_ordered': is_ordered, 'has_no_negative_ticks': has_no_negative,
                'events_checked': len(events)}

    def check_contiguity(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not events:
            return {'is_contiguous': True, 'gaps': []}
        ticks = sorted(set(e.get('tick', 0) for e in events))
        gaps = []
        for i in range(len(ticks) - 1):
            if ticks[i + 1] - ticks[i] > 1:
                gaps.append({'from': ticks[i], 'to': ticks[i + 1]})
        self._integrity_history.append({
            'check': 'contiguity', 'passed': len(gaps) == 0,
            'gaps_found': len(gaps),
        })
        return {'is_contiguous': len(gaps) == 0, 'gaps': gaps}

    def check_direction(self, events: List[Dict[str, Any]],
                         direction: TimelineDirection) -> Dict[str, Any]:
        if len(events) < 2:
            return {'is_correct_direction': True, 'events_checked': len(events)}
        ticks = [e.get('tick', 0) for e in events]
        if direction == TimelineDirection.FORWARD:
            correct = all(ticks[i] <= ticks[i + 1] for i in range(len(ticks) - 1))
        else:
            correct = all(ticks[i] >= ticks[i + 1] for i in range(len(ticks) - 1))
        self._integrity_history.append({
            'check': 'direction', 'passed': correct,
            'direction': direction.value,
        })
        return {'is_correct_direction': correct, 'direction': direction.value}

    def clear(self):
        self._integrity_history.clear()
