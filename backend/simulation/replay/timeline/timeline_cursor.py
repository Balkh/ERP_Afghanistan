"""Timeline cursor — navigates timeline with direction-aware stepping."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import TimelineCursor, TimelineDirection


class TimelineCursorManager:
    def __init__(self, max_cursors: int = 50):
        self._cursors: Dict[str, TimelineCursor] = {}
        self._cursor_history: deque = deque(maxlen=max_cursors)

    def create_cursor(self, cursor_id: str, start_tick: int = 0,
                      direction: TimelineDirection = TimelineDirection.FORWARD,
                      total_events: int = 0) -> Dict[str, Any]:
        cursor = TimelineCursor(
            cursor_id=cursor_id, current_tick=start_tick,
            direction=direction, position=0, total_events=total_events,
        )
        self._cursors[cursor_id] = cursor
        self._cursor_history.append(cursor_id)
        return {'cursor_id': cursor_id, 'current_tick': start_tick,
                'direction': direction.value, 'position': 0}

    def advance(self, cursor_id: str, steps: int = 1) -> Dict[str, Any]:
        cursor = self._cursors.get(cursor_id)
        if cursor is None:
            return {'advanced': False, 'reason': 'Cursor not found'}
        if cursor.direction == TimelineDirection.FORWARD:
            cursor.current_tick += steps
        else:
            cursor.current_tick = max(0, cursor.current_tick - steps)
        cursor.position += 1
        return {'advanced': True, 'cursor_id': cursor_id,
                'current_tick': cursor.current_tick, 'position': cursor.position}

    def get_cursor(self, cursor_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._cursors.get(cursor_id)
        if cursor is None:
            return None
        return {'cursor_id': cursor.cursor_id, 'current_tick': cursor.current_tick,
                'direction': cursor.direction.value, 'position': cursor.position}

    def delete_cursor(self, cursor_id: str) -> bool:
        if cursor_id in self._cursors:
            del self._cursors[cursor_id]
            return True
        return False

    def clear(self):
        self._cursors.clear()
        self._cursor_history.clear()
