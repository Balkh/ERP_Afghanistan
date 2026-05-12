"""Recovery paths — defines possible recovery path types and their characteristics."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import RecoveryPathType, IntegritySeverity


class RecoveryPathsRegistry:
    PATH_DEFINITIONS = {
        RecoveryPathType.ROLLBACK: {
            'name': 'Rollback', 'description': 'Roll back workflow to previous safe state',
            'requires_manual_review': True, 'automated_possible': False,
            'estimated_effort': 'high', 'risks': ['Data loss', 'Dependent workflow impact'],
        },
        RecoveryPathType.RECONCILE: {
            'name': 'Reconcile', 'description': 'Reconcile differences between expected and actual state',
            'requires_manual_review': False, 'automated_possible': True,
            'estimated_effort': 'medium', 'risks': ['May not resolve root cause'],
        },
        RecoveryPathType.REPROCESS: {
            'name': 'Reprocess', 'description': 'Reprocess the workflow from a known good state',
            'requires_manual_review': False, 'automated_possible': True,
            'estimated_effort': 'low', 'risks': ['Duplicate processing if not careful'],
        },
        RecoveryPathType.MANUAL_INTERVENTION: {
            'name': 'Manual Intervention', 'description': 'Requires human operator to resolve',
            'requires_manual_review': True, 'automated_possible': False,
            'estimated_effort': 'variable', 'risks': ['Delay in resolution', 'Human error'],
        },
        RecoveryPathType.IGNORE: {
            'name': 'Ignore', 'description': 'No action required — informational only',
            'requires_manual_review': False, 'automated_possible': True,
            'estimated_effort': 'none', 'risks': [],
        },
    }

    def __init__(self):
        self._access_history: deque = deque(maxlen=200)

    def get_path(self, path_type: RecoveryPathType) -> Dict[str, Any]:
        definition = dict(self.PATH_DEFINITIONS.get(path_type, self.PATH_DEFINITIONS[RecoveryPathType.IGNORE]))
        definition['path_type'] = path_type.value
        self._access_history.append(path_type.value)
        return definition

    def get_path_by_str(self, path_str: str) -> Dict[str, Any]:
        try:
            path_type = RecoveryPathType(path_str)
        except ValueError:
            path_type = RecoveryPathType.IGNORE
        return self.get_path(path_type)

    def clear(self):
        self._access_history.clear()
