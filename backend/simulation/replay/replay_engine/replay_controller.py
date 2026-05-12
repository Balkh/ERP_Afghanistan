"""Replay controller — controls replay execution (start/stop/step)."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayMode, ReplayStatus


class ReplayController:
    def __init__(self, max_history: int = 200):
        self._control_history: deque = deque(maxlen=max_history)
        self._control_count: int = 0

    def start(self, session_id: str, mode: ReplayMode = ReplayMode.FULL) -> Dict[str, Any]:
        self._control_count += 1
        self._control_history.append({
            'action': 'start', 'session_id': session_id, 'mode': mode.value,
        })
        return {'started': True, 'session_id': session_id, 'mode': mode.value}

    def stop(self, session_id: str) -> Dict[str, Any]:
        self._control_history.append({
            'action': 'stop', 'session_id': session_id,
        })
        return {'stopped': True, 'session_id': session_id}

    def pause(self, session_id: str) -> Dict[str, Any]:
        self._control_history.append({
            'action': 'pause', 'session_id': session_id,
        })
        return {'paused': True, 'session_id': session_id}

    def resume(self, session_id: str) -> Dict[str, Any]:
        self._control_history.append({
            'action': 'resume', 'session_id': session_id,
        })
        return {'resumed': True, 'session_id': session_id}

    def step_forward(self, session_id: str) -> Dict[str, Any]:
        self._control_history.append({
            'action': 'step_forward', 'session_id': session_id,
        })
        return {'stepped': True, 'session_id': session_id, 'direction': 'forward'}

    def step_backward(self, session_id: str) -> Dict[str, Any]:
        self._control_history.append({
            'action': 'step_backward', 'session_id': session_id,
        })
        return {'stepped': True, 'session_id': session_id, 'direction': 'backward'}

    def clear(self):
        self._control_history.clear()
        self._control_count = 0
