"""Replay windows — defines bounded windows of timeline events."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayWindow


class ReplayWindows:
    def __init__(self, max_windows: int = 50):
        self._windows: Dict[str, ReplayWindow] = {}
        self._window_history: deque = deque(maxlen=max_windows)

    def create_window(self, window_id: str, start_tick: int, end_tick: int,
                      events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        events = events or []
        window_events = [e for e in events if start_tick <= e.get('tick', 0) <= end_tick]
        window = ReplayWindow(
            window_id=window_id, start_tick=start_tick, end_tick=end_tick,
            event_count=len(window_events), is_loaded=True,
        )
        self._windows[window_id] = window
        self._window_history.append(window_id)
        return {'window_id': window_id, 'start_tick': start_tick,
                'end_tick': end_tick, 'event_count': len(window_events),
                'events': window_events}

    def get_window(self, window_id: str) -> Optional[Dict[str, Any]]:
        w = self._windows.get(window_id)
        if w is None:
            return None
        return {'window_id': w.window_id, 'start_tick': w.start_tick,
                'end_tick': w.end_tick, 'event_count': w.event_count}

    def slide_window(self, window_id: str, delta: int,
                     events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        w = self._windows.get(window_id)
        if w is None:
            return {'slid': False, 'reason': 'Window not found'}
        new_start = w.start_tick + delta
        new_end = w.end_tick + delta
        return self.create_window(window_id, new_start, new_end, events)

    def clear(self):
        self._windows.clear()
        self._window_history.clear()
