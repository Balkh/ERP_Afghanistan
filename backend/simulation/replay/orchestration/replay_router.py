"""Replay router — routes replay requests to appropriate handlers."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayMode


class ReplayRouter:
    def __init__(self, max_history: int = 100):
        self._routing_history: deque = deque(maxlen=max_history)
        self._route_count: int = 0

    def route_replay(self, mode: ReplayMode, session_id: str,
                     events: List[Dict[str, Any]]) -> Dict[str, Any]:
        self._route_count += 1
        route_id = f"rr_{self._route_count}"
        strategy = {
            ReplayMode.FULL: 'process_all',
            ReplayMode.STEP: 'process_step',
            ReplayMode.WINDOW: 'process_window',
            ReplayMode.BOOKMARK: 'process_bookmark',
        }.get(mode, 'process_all')
        self._routing_history.append({
            'route_id': route_id, 'session_id': session_id,
            'mode': mode.value, 'strategy': strategy,
            'event_count': len(events),
        })
        return {'route_id': route_id, 'session_id': session_id,
                'mode': mode.value, 'strategy': strategy}

    def get_route_count(self) -> int:
        return self._route_count

    def clear(self):
        self._routing_history.clear()
        self._route_count = 0
