import logging
from collections import deque
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger('erp.simulation.predictive.safety.failure_isolation')

T = TypeVar('T')


class PredictionFailureIsolation:
    def __init__(self, max_error_history: int = 100):
        self._max_error_history = max_error_history
        self._error_history: deque = deque(maxlen=max_error_history)
        self._degraded_mode = False

    def safe_call(self, fn: Callable[..., T], *args: Any,
                  default_return: T = None,
                  **kwargs: Any) -> T:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self._record_error(fn.__name__, str(e))
            logger.warning('Prediction failure in %s: %s (degraded mode: %s)',
                           fn.__name__, e, self._degraded_mode)
            return default_return

    def _record_error(self, operation: str, error: str):
        self._error_history.append({
            'operation': operation,
            'error': error,
        })
        if self._error_count >= 5:
            self._degraded_mode = True

    @property
    def _error_count(self) -> int:
        return len(self._error_history)

    @property
    def is_degraded(self) -> bool:
        return self._degraded_mode

    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        recent = list(self._error_history)[-count:]
        return recent

    def reset_degraded_mode(self):
        self._degraded_mode = False

    def get_error_summary(self) -> Dict[str, Any]:
        operations: Dict[str, int] = {}
        for err in self._error_history:
            op = err['operation']
            operations[op] = operations.get(op, 0) + 1
        return {
            'total_errors': len(self._error_history),
            'degraded_mode': self._degraded_mode,
            'operation_counts': operations,
        }

    def clear(self):
        self._error_history.clear()
        self._degraded_mode = False
