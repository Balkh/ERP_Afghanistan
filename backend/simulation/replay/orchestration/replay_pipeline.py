"""Replay pipeline — defines execution pipeline for replay operations."""
from collections import deque
from typing import Any, Dict, List, Optional


class ReplayPipeline:
    def __init__(self, pipeline_id: str, steps: Optional[List[str]] = None):
        self._pipeline_id = pipeline_id
        self._steps = list(steps or [])
        self._current_step: int = 0
        self._is_running: bool = False
        self._is_complete: bool = False
        self._has_failed: bool = False
        self._error_message: str = ""
        self._execution_history: List[Dict[str, Any]] = []

    @property
    def pipeline_id(self) -> str:
        return self._pipeline_id

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @property
    def has_failed(self) -> bool:
        return self._has_failed

    def start(self) -> Dict[str, Any]:
        if not self._steps:
            return {'started': False, 'reason': 'No steps defined'}
        self._is_running = True
        self._current_step = 0
        self._is_complete = False
        self._has_failed = False
        self._execution_history.append({'action': 'start', 'step': 0})
        return {'started': True, 'pipeline_id': self._pipeline_id,
                'total_steps': len(self._steps)}

    def advance(self) -> Dict[str, Any]:
        if not self._is_running:
            return {'advanced': False, 'reason': 'Pipeline not running'}
        if self._current_step >= len(self._steps):
            self._is_running = False
            self._is_complete = True
            return {'advanced': False, 'reason': 'All steps complete', 'complete': True}
        step_name = self._steps[self._current_step]
        self._execution_history.append({'action': 'advance', 'step_name': step_name})
        self._current_step += 1
        if self._current_step >= len(self._steps):
            self._is_running = False
            self._is_complete = True
        return {'advanced': True, 'step_name': step_name,
                'step_index': self._current_step - 1,
                'remaining': len(self._steps) - self._current_step,
                'complete': self._is_complete}

    def fail(self, error: str) -> Dict[str, Any]:
        self._is_running = False
        self._has_failed = True
        self._error_message = error
        self._execution_history.append({'action': 'fail', 'error': error})
        return {'failed': True, 'error': error}

    def reset(self) -> Dict[str, Any]:
        self._current_step = 0
        self._is_running = False
        self._is_complete = False
        self._has_failed = False
        self._error_message = ""
        self._execution_history.clear()
        return {'reset': True}

    def get_status(self) -> Dict[str, Any]:
        return {'pipeline_id': self._pipeline_id,
                'current_step': self._current_step,
                'total_steps': len(self._steps),
                'is_running': self._is_running,
                'is_complete': self._is_complete,
                'has_failed': self._has_failed,
                'error': self._error_message}
