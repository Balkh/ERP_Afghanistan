import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger('erp.simulation.predictive.warnings.retention')


class WarningRetentionManager:
    def __init__(self, max_warnings: int = 500):
        self._max_warnings = max_warnings
        self._warnings: deque = deque(maxlen=max_warnings)

    def add_warning(self, warning: Dict[str, Any]):
        self._warnings.append(dict(warning))

    def get_warnings(self, since_tick: int = 0,
                     level: Optional[str] = None,
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        results = [w for w in self._warnings if w.get('tick', 0) >= since_tick]
        if level:
            results = [w for w in results if w.get('severity') == level]
        if limit is not None:
            results = results[-limit:]
        return list(results)

    def get_warning_count(self, level: Optional[str] = None) -> int:
        if level:
            return sum(1 for w in self._warnings if w.get('severity') == level)
        return len(self._warnings)

    def get_critical_warnings(self, since_tick: int = 0) -> List[Dict[str, Any]]:
        return self.get_warnings(since_tick=since_tick, level='critical')

    def get_high_warnings(self, since_tick: int = 0) -> List[Dict[str, Any]]:
        return self.get_warnings(since_tick=since_tick, level='high')

    def clear(self):
        self._warnings.clear()

    @property
    def warning_count(self) -> int:
        return len(self._warnings)

    @property
    def max_warnings(self) -> int:
        return self._max_warnings
