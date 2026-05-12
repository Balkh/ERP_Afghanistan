"""Replay engine — orchestrates sessions, controllers, and safety."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.replay_engine.replay_session import ReplaySessionManager
from simulation.replay.replay_engine.replay_controller import ReplayController
from simulation.replay.replay_engine.replay_safety_guard import ReplaySafetyGuard
from simulation.replay.models import ReplayMode


class ReplayEngine:
    def __init__(self, max_history: int = 200):
        self._sessions = ReplaySessionManager()
        self._controller = ReplayController()
        self._safety_guard = ReplaySafetyGuard()
        self._execution_history: deque = deque(maxlen=max_history)

    @property
    def sessions(self) -> ReplaySessionManager:
        return self._sessions

    @property
    def controller(self) -> ReplayController:
        return self._controller

    @property
    def safety_guard(self) -> ReplaySafetyGuard:
        return self._safety_guard

    def execute_replay(self, session_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        session = self._sessions.get_session(session_id)
        if session is None:
            return {'executed': False, 'reason': 'Session not found'}
        self._controller.start(session_id)
        self._sessions.start_session(session_id)
        for e in events:
            write_check = self._safety_guard.check_write_operation('replay')
            if not write_check['allowed']:
                self._sessions.fail_session(session_id, 'Write blocked during replay')
                self._execution_history.append({
                    'session_id': session_id, 'action': 'blocked',
                    'event_id': e.get('event_id', ''),
                })
                return {'executed': False, 'reason': 'Write blocked during replay'}
        self._sessions.complete_session(session_id)
        self._execution_history.append({
            'session_id': session_id, 'action': 'complete',
            'events_replayed': len(events),
        })
        return {'executed': True, 'session_id': session_id,
                'events_replayed': len(events)}

    def clear(self):
        self._sessions.clear()
        self._controller.clear()
        self._safety_guard.clear()
        self._execution_history.clear()
