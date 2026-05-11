import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.warnings.deduplicator')


class WarningDeduplicator:
    def __init__(self, dedup_window: int = 5):
        self._dedup_window = dedup_window
        self._recent_keys: deque = deque(maxlen=20)

    def is_duplicate(self, warning: Dict[str, Any]) -> bool:
        key = self._make_key(warning)
        if key in self._recent_keys:
            return True
        self._recent_keys.append(key)
        return False

    def _make_key(self, warning: Dict[str, Any]) -> str:
        wtype = warning.get('warning_type', '')
        wf = warning.get('workflow_type', '')
        module = warning.get('affected_module', '')
        sev = warning.get('severity', '')
        return f"{wtype}:{wf}:{module}:{sev}"

    def clear(self):
        self._recent_keys.clear()
