"""Replay navigation — step-based navigation through replayed events."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import TimelineDirection


class ReplayNavigation:
    def __init__(self, max_history: int = 100):
        self._navigation_history: deque = deque(maxlen=max_history)

    def next_event(self, current_index: int, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if current_index + 1 >= len(events):
            return {'navigated': False, 'reason': 'At end of timeline',
                    'current_index': current_index}
        next_idx = current_index + 1
        self._navigation_history.append({
            'action': 'next', 'from': current_index, 'to': next_idx,
        })
        return {'navigated': True, 'event': events[next_idx],
                'current_index': next_idx, 'new_tick': events[next_idx].get('tick', 0)}

    def previous_event(self, current_index: int, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if current_index <= 0:
            return {'navigated': False, 'reason': 'At start of timeline',
                    'current_index': current_index}
        prev_idx = current_index - 1
        self._navigation_history.append({
            'action': 'previous', 'from': current_index, 'to': prev_idx,
        })
        return {'navigated': True, 'event': events[prev_idx],
                'current_index': prev_idx, 'new_tick': events[prev_idx].get('tick', 0)}

    def skip_to_tick(self, target_tick: int, current_index: int,
                     events: List[Dict[str, Any]]) -> Dict[str, Any]:
        for i, e in enumerate(events):
            if e.get('tick', 0) >= target_tick:
                self._navigation_history.append({
                    'action': 'skip_to_tick', 'target': target_tick,
                    'from_index': current_index, 'to_index': i,
                })
                return {'navigated': True, 'event': e,
                        'current_index': i, 'new_tick': e.get('tick', 0)}
        return {'navigated': False, 'reason': 'Target tick not found'}

    def clear(self):
        self._navigation_history.clear()
