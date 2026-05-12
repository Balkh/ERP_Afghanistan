"""Degradation levels — defines system operation levels during failure."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import DegradationLevel, IntegritySeverity


class DegradationLevels:
    LEVEL_DEFINITIONS = {
        DegradationLevel.FULL: {
            'name': 'Full Operation', 'description': 'All systems operating normally',
            'max_workflows': 100, 'max_journal_entries': 1000,
            'allow_new_workflows': True, 'allow_writes': True,
        },
        DegradationLevel.REDUCED: {
            'name': 'Reduced Operation', 'description': 'Non-critical operations restricted',
            'max_workflows': 50, 'max_journal_entries': 500,
            'allow_new_workflows': True, 'allow_writes': True,
        },
        DegradationLevel.MINIMUM: {
            'name': 'Minimum Operation', 'description': 'Only critical workflows allowed',
            'max_workflows': 10, 'max_journal_entries': 100,
            'allow_new_workflows': False, 'allow_writes': False,
        },
        DegradationLevel.EMERGENCY: {
            'name': 'Emergency Only', 'description': 'Only read operations and manual intervention',
            'max_workflows': 0, 'max_journal_entries': 0,
            'allow_new_workflows': False, 'allow_writes': False,
        },
    }

    def __init__(self):
        self._current_level = DegradationLevel.FULL
        self._level_history: deque = deque(maxlen=100)

    @property
    def current(self) -> DegradationLevel:
        return self._current_level

    def get_level(self, level: DegradationLevel) -> Dict[str, Any]:
        return dict(self.LEVEL_DEFINITIONS.get(level, self.LEVEL_DEFINITIONS[DegradationLevel.FULL]))

    def set_level(self, level: DegradationLevel, reason: str = "") -> Dict[str, Any]:
        previous = self._current_level
        self._current_level = level
        self._level_history.append({
            'from': previous.value, 'to': level.value, 'reason': reason,
        })
        return {
            'previous_level': previous.value, 'current_level': level.value,
            'definition': self.get_level(level), 'reason': reason,
        }

    def select_level(self, severity: IntegritySeverity,
                     has_irreversible: bool = False,
                     containment_active: bool = False) -> DegradationLevel:
        if severity == IntegritySeverity.CRITICAL or has_irreversible:
            return DegradationLevel.EMERGENCY
        elif severity == IntegritySeverity.HIGH:
            return DegradationLevel.MINIMUM
        elif severity == IntegritySeverity.MEDIUM or containment_active:
            return DegradationLevel.REDUCED
        return DegradationLevel.FULL

    def clear(self):
        self._current_level = DegradationLevel.FULL
        self._level_history.clear()
