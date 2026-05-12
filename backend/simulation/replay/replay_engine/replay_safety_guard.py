"""Replay safety guard — prevents unsafe replay operations."""
from collections import deque
from typing import Any, Dict, List, Optional, Callable


class ReplaySafetyGuard:
    def __init__(self, max_history: int = 100):
        self._safety_violations: deque = deque(maxlen=max_history)
        self._violation_count: int = 0

    def check_write_operation(self, operation: str) -> Dict[str, Any]:
        self._violation_count += 1
        self._safety_violations.append({
            'type': 'write_operation', 'operation': operation,
        })
        return {'allowed': False, 'reason': f'Write operation blocked: {operation}',
                'violation_id': f'sv_{self._violation_count}'}

    def check_business_logic(self, logic_name: str) -> Dict[str, Any]:
        self._violation_count += 1
        self._safety_violations.append({
            'type': 'business_logic', 'logic_name': logic_name,
        })
        return {'allowed': False, 'reason': f'Business logic blocked: {logic_name}',
                'violation_id': f'sv_{self._violation_count}'}

    def safe_call(self, fn: Callable, default_return: Any = None,
                  *args, **kwargs) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self._violation_count += 1
            self._safety_violations.append({
                'type': 'exception', 'error': str(e),
            })
            return default_return

    def get_violation_count(self) -> int:
        return self._violation_count

    def clear(self):
        self._safety_violations.clear()
        self._violation_count = 0
