"""Operational fallbacks — fallback strategies for degraded operations."""
from collections import deque
from typing import Any, Dict, List, Optional, Callable
from simulation.recovery.models import DegradationLevel


class OperationalFallbacks:
    FALLBACK_STRATEGIES = {
        DegradationLevel.FULL: {
            'on_write_failure': 'retry', 'on_read_failure': 'retry',
            'on_timeout': 'retry', 'on_validation_error': 'reject',
        },
        DegradationLevel.REDUCED: {
            'on_write_failure': 'queue', 'on_read_failure': 'retry',
            'on_timeout': 'warn', 'on_validation_error': 'reject',
        },
        DegradationLevel.MINIMUM: {
            'on_write_failure': 'reject', 'on_read_failure': 'cache',
            'on_timeout': 'default', 'on_validation_error': 'reject',
        },
        DegradationLevel.EMERGENCY: {
            'on_write_failure': 'reject', 'on_read_failure': 'reject',
            'on_timeout': 'reject', 'on_validation_error': 'reject',
        },
    }

    def __init__(self):
        self._fallback_history: deque = deque(maxlen=200)

    def get_strategy(self, level: DegradationLevel) -> Dict[str, str]:
        return dict(self.FALLBACK_STRATEGIES.get(level, self.FALLBACK_STRATEGIES[DegradationLevel.FULL]))

    def apply_fallback(self, level: DegradationLevel, operation: str,
                       error: str = "") -> Dict[str, Any]:
        strategy = self.get_strategy(level)
        action = strategy.get(operation, 'reject')
        self._fallback_history.append({
            'level': level.value, 'operation': operation,
            'action': action, 'error': error,
        })
        return {'operation': operation, 'action': action,
                'level': level.value, 'error': error}

    def clear(self):
        self._fallback_history.clear()
