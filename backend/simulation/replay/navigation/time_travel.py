"""Time travel — navigates timeline to specific ticks."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import TimelineDirection


class TimeTravel:
    def __init__(self, max_history: int = 100):
        self._travel_history: deque = deque(maxlen=max_history)

    def navigate_to(self, target_tick: int, current_tick: int,
                    events: List[Dict[str, Any]]) -> Dict[str, Any]:
        direction = (TimelineDirection.FORWARD if target_tick >= current_tick
                     else TimelineDirection.BACKWARD)
        ticks_to_travel = abs(target_tick - current_tick)
        events_in_range = [e for e in events
                           if min(current_tick, target_tick) <= e.get('tick', 0) <= max(current_tick, target_tick)]
        self._travel_history.append({
            'from_tick': current_tick, 'to_tick': target_tick,
            'ticks_traveled': ticks_to_travel, 'direction': direction.value,
            'events_found': len(events_in_range),
        })
        return {
            'target_tick': target_tick, 'previous_tick': current_tick,
            'ticks_traveled': ticks_to_travel,
            'direction': direction.value,
            'events_in_range': events_in_range,
            'events_found': len(events_in_range),
        }

    def navigate_to_start(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not events:
            return {'start_tick': 0, 'events_found': 0}
        start_tick = min(e.get('tick', 0) for e in events)
        return self.navigate_to(start_tick, 0, events)

    def navigate_to_end(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not events:
            return {'end_tick': 0, 'events_found': 0}
        end_tick = max(e.get('tick', 0) for e in events)
        return self.navigate_to(end_tick, 0, events)

    def clear(self):
        self._travel_history.clear()
