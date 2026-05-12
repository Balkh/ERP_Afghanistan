"""Timeline validator — validates timeline consistency and integrity."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import TimelineEvent


class TimelineValidator:
    def __init__(self, max_history: int = 200):
        self._validation_history: deque = deque(maxlen=max_history)

    def validate_ordering(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        ticks = [e.get('tick', -1) for e in events]
        is_ordered = all(ticks[i] <= ticks[i + 1] for i in range(len(ticks) - 1))
        gaps = []
        for i in range(len(ticks) - 1):
            if ticks[i + 1] - ticks[i] > 1:
                gaps.append({'from': ticks[i], 'to': ticks[i + 1], 'gap': ticks[i + 1] - ticks[i]})
        self._validation_history.append({
            'check': 'ordering', 'passed': is_ordered,
            'events_checked': len(events), 'gaps_found': len(gaps),
        })
        return {'is_ordered': is_ordered, 'gaps': gaps,
                'events_checked': len(events), 'gaps_found': len(gaps)}

    def validate_no_duplicates(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        seen = set()
        duplicates = []
        for e in events:
            eid = e.get('event_id', '')
            if eid in seen:
                duplicates.append(eid)
            seen.add(eid)
        self._validation_history.append({
            'check': 'duplicates', 'passed': len(duplicates) == 0,
            'duplicates_found': len(duplicates),
        })
        return {'no_duplicates': len(duplicates) == 0, 'duplicates': duplicates}

    def validate_causal_continuity(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        event_ids = {e.get('event_id', '') for e in events}
        broken_links = []
        for e in events:
            parent = e.get('causal_parent')
            if parent and parent not in event_ids:
                broken_links.append({'event_id': e.get('event_id', ''),
                                     'missing_parent': parent})
        self._validation_history.append({
            'check': 'causal_continuity', 'passed': len(broken_links) == 0,
            'broken_links': len(broken_links),
        })
        return {'causal_continuity': len(broken_links) == 0, 'broken_links': broken_links}

    def clear(self):
        self._validation_history.clear()
