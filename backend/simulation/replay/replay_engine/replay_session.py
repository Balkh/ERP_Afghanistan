"""Replay session — manages a single replay session lifecycle."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplaySession, ReplayStatus, ReplayMode


class ReplaySessionManager:
    def __init__(self, max_sessions: int = 50):
        self._sessions: Dict[str, ReplaySession] = {}
        self._session_history: deque = deque(maxlen=max_sessions)

    def create_session(self, session_id: str, mode: ReplayMode = ReplayMode.FULL,
                       start_tick: int = 0, end_tick: int = 100) -> Dict[str, Any]:
        session = ReplaySession(
            session_id=session_id, status=ReplayStatus.IDLE,
            mode=mode, start_tick=start_tick,
            current_tick=start_tick, end_tick=end_tick,
        )
        self._sessions[session_id] = session
        self._session_history.append(session_id)
        return {'session_id': session_id, 'status': 'idle',
                'mode': mode.value, 'start_tick': start_tick, 'end_tick': end_tick}

    def start_session(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {'started': False, 'reason': 'Session not found'}
        session.status = ReplayStatus.RUNNING
        session.current_tick = session.start_tick
        return {'started': True, 'session_id': session_id,
                'current_tick': session.current_tick}

    def pause_session(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {'paused': False, 'reason': 'Session not found'}
        session.status = ReplayStatus.PAUSED
        session.is_paused = True
        return {'paused': True, 'session_id': session_id,
                'current_tick': session.current_tick}

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {'resumed': False, 'reason': 'Session not found'}
        session.status = ReplayStatus.RUNNING
        session.is_paused = False
        return {'resumed': True, 'session_id': session_id}

    def complete_session(self, session_id: str) -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {'completed': False, 'reason': 'Session not found'}
        session.status = ReplayStatus.COMPLETED
        return {'completed': True, 'session_id': session_id}

    def fail_session(self, session_id: str, reason: str = "") -> Dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            return {'failed': False, 'reason': 'Session not found'}
        session.status = ReplayStatus.FAILED
        return {'failed': True, 'session_id': session_id, 'error': reason}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        s = self._sessions.get(session_id)
        if s is None:
            return None
        return {'session_id': s.session_id, 'status': s.status.value,
                'mode': s.mode.value, 'current_tick': s.current_tick,
                'start_tick': s.start_tick, 'end_tick': s.end_tick,
                'events_replayed': s.events_replayed, 'is_paused': s.is_paused}

    def clear(self):
        self._sessions.clear()
        self._session_history.clear()
