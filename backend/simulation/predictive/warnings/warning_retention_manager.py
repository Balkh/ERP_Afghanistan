import logging
from collections import deque
from typing import Any, Dict, List, Optional

from simulation.predictive.models import EarlyWarning, WarningSeverity

logger = logging.getLogger('erp.simulation.predictive.warnings.retention')


class WarningRetentionManager:
    def __init__(self, max_warnings: int = 500, retention_ticks: int = 100):
        self._max_warnings = max_warnings
        self._retention_ticks = retention_ticks
        self._active_warnings: deque = deque(maxlen=max_warnings)
        self._archived_warnings: List[EarlyWarning] = []

    def retain(self, warnings: List[EarlyWarning]) -> List[EarlyWarning]:
        retained: List[EarlyWarning] = []
        for w in warnings:
            if len(self._active_warnings) >= self._max_warnings:
                self._archive_oldest()
            self._active_warnings.append(w)
            retained.append(w)
        return retained

    def _archive_oldest(self):
        if self._active_warnings:
            oldest = self._active_warnings.popleft()
            self._archived_warnings.append(oldest)

    def get_active_warnings(self) -> List[EarlyWarning]:
        return list(self._active_warnings)

    def get_archived_warnings(self) -> List[EarlyWarning]:
        return list(self._archived_warnings)

    def get_warnings_by_severity(self,
                                 severity: WarningSeverity) -> List[EarlyWarning]:
        return [w for w in self._active_warnings if w.severity == severity]

    def get_critical_warnings(self) -> List[EarlyWarning]:
        return self.get_warnings_by_severity(WarningSeverity.CRITICAL)

    def get_high_warnings(self) -> List[EarlyWarning]:
        return self.get_warnings_by_severity(WarningSeverity.HIGH)

    @property
    def active_count(self) -> int:
        return len(self._active_warnings)

    @property
    def archived_count(self) -> int:
        return len(self._archived_warnings)

    def clear(self):
        self._active_warnings.clear()
        self._archived_warnings.clear()
