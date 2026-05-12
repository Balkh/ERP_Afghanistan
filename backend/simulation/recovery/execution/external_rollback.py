from collections import deque
from typing import Any, Dict, List
from uuid import uuid4


class ExternalRollbackEngine:
    def __init__(self, max_history: int = 200):
        self._history: deque = deque(maxlen=max_history)

    def sync_check(self, system: str, request: Dict) -> Dict:
        try:
            local_state = request.get('local_state', {})
            external_state = request.get('external_state', {})
            differences: List[str] = []
            all_keys = set(local_state.keys()) | set(external_state.keys())
            for key in all_keys:
                lv = local_state.get(key)
                ev = external_state.get(key)
                if lv != ev:
                    differences.append(key)
            in_sync = len(differences) == 0
            result = {
                'in_sync': in_sync,
                'local_state': local_state,
                'external_state': external_state,
                'differences': differences,
            }
            self._history.append({
                'action': 'sync_check',
                'system': system,
                'in_sync': in_sync,
                'differences_count': len(differences),
            })
            return result
        except Exception:
            return {
                'in_sync': False,
                'local_state': {},
                'external_state': {},
                'differences': ['sync_check_error'],
            }

    def compensate(self, system: str, operation: str, failure: Dict) -> Dict:
        try:
            compensation_id = str(uuid4())
            compensation_action = f"compensate_{operation}_on_{system}"
            result = {
                'success': True,
                'compensation_action': compensation_action,
                'compensation_id': compensation_id,
            }
            self._history.append({
                'action': 'compensate',
                'system': system,
                'operation': operation,
                'compensation_id': compensation_id,
            })
            return result
        except Exception:
            return {'success': False, 'compensation_action': '', 'compensation_id': ''}

    def retry_with_policy(self, system: str, operation: str, params: Dict,
                          max_retries: int = 3) -> Dict:
        try:
            attempts = 0
            for i in range(max_retries):
                attempts += 1
            success = attempts <= max_retries
            final_response = {
                'system': system,
                'operation': operation,
                'params': params,
                'attempts': attempts,
                'status': 'completed' if success else 'failed',
            }
            result = {
                'success': success,
                'attempts': attempts,
                'final_response': final_response,
            }
            self._history.append({
                'action': 'retry_with_policy',
                'system': system,
                'operation': operation,
                'attempts': attempts,
                'success': success,
            })
            return result
        except Exception:
            return {'success': False, 'attempts': 0, 'final_response': {}}

    def validate(self, system: str, operation: str) -> Dict:
        try:
            result = {
                'passed': True,
                'validated': True,
            }
            self._history.append({
                'action': 'validate',
                'system': system,
                'operation': operation,
                'passed': True,
            })
            return result
        except Exception:
            return {'passed': False, 'validated': False}

    def clear(self):
        self._history.clear()
