"""
Task A: EventRetentionValidator — verifies bounded history enforcement.
Ensures event cleanup works correctly, detects retention leaks.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.audit.event_lifecycle.validator')


class EventRetentionValidator:
    def validate(self, event_bus: Any, max_history: int) -> Dict[str, Any]:
        history = getattr(event_bus, 'history', [])
        if callable(history):
            history = history()
        if hasattr(history, '_history'):
            history_list = list(history._history)
        elif isinstance(history, list):
            history_list = history
        else:
            history_list = list(history) if history else []
        actual_count = len(history_list)
        retention_leak = actual_count > max_history
        history_obj = getattr(event_bus, '_history', None)
        if history_obj is None or not hasattr(history_obj, 'maxlen'):
            history_obj = getattr(event_bus, 'history', None)
        maxlen = None
        if hasattr(history_obj, 'maxlen'):
            maxlen = history_obj.maxlen
        return {
            'max_history_setting': max_history,
            'actual_event_count': actual_count,
            'retention_leak_detected': retention_leak,
            'overflow_amount': max(0, actual_count - max_history),
            'maxlen_property': maxlen,
            'retention_compliant': not retention_leak and maxlen is not None,
            'maxlen_set_correctly': maxlen == max_history,
        }
