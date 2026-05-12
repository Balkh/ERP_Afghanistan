import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set

from simulation.predictive.models import EarlyWarning, WarningSeverity

logger = logging.getLogger('erp.simulation.predictive.warnings.deduplicator')


class WarningDeduplicator:
    def __init__(self, max_history: int = 500):
        self._max_history = max_history
        self._seen_warnings: deque = deque(maxlen=max_history)

    def deduplicate(self, warnings: List[EarlyWarning]) -> List[EarlyWarning]:
        deduplicated: List[EarlyWarning] = []
        for w in warnings:
            if not self._is_duplicate(w):
                deduplicated.append(w)
                self._seen_warnings.append(self._make_key(w))
        return deduplicated

    def _is_duplicate(self, warning: EarlyWarning) -> bool:
        key = self._make_key(warning)
        return key in self._seen_warnings

    def _make_key(self, warning: EarlyWarning) -> str:
        return f'{warning.source_module}:{warning.title}:{warning.severity.value}'

    @property
    def history_count(self) -> int:
        return len(self._seen_warnings)

    def clear(self):
        self._seen_warnings.clear()
