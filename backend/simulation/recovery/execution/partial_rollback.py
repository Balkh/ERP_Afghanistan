from collections import deque
from typing import Any, Dict, List


class PartialRollbackEngine:
    def __init__(self, max_history: int = 200):
        self._history: deque = deque(maxlen=max_history)

    def detect_affected(self, incident: Dict, state: Dict) -> Dict:
        try:
            affected_components = incident.get('affected_components', [])
            affected: Dict[str, Any] = {}
            unaffected: Dict[str, Any] = {}
            for key, value in state.items():
                if key in affected_components:
                    affected[key] = value
                else:
                    unaffected[key] = value
            result = {
                'affected': affected,
                'unaffected': unaffected,
                'component_count': len(affected),
            }
            self._history.append({
                'action': 'detect_affected',
                'affected_count': len(affected),
                'unaffected_count': len(unaffected),
            })
            return result
        except Exception:
            return {'affected': {}, 'unaffected': {}, 'component_count': 0}

    def execute_rollback(self, segment: Dict, rollback_map: Dict) -> Dict:
        try:
            affected = segment.get('affected', {})
            items = list(affected.keys())
            actions = [f"rollback_{item}" for item in items]
            actions.append(f"applied_map_{rollback_map.get('strategy', 'default')}")
            result = {
                'success': True,
                'items_rolled_back': len(items),
                'actions': actions,
            }
            self._history.append({
                'action': 'execute_rollback',
                'items_rolled_back': len(items),
                'actions_count': len(actions),
            })
            return result
        except Exception:
            return {'success': False, 'items_rolled_back': 0, 'actions': []}

    def merge_clean(self, segment: Dict, state: Dict) -> Dict:
        try:
            unaffected = segment.get('unaffected', {})
            merged_count = 0
            for key, value in unaffected.items():
                if key in state:
                    merged_count += 1
            result = {
                'success': True,
                'merged_items': merged_count,
            }
            self._history.append({
                'action': 'merge_clean',
                'merged_items': merged_count,
            })
            return result
        except Exception:
            return {'success': False, 'merged_items': 0}

    def verify(self, segment: Dict) -> Dict:
        try:
            affected = segment.get('affected', {})
            unaffected = segment.get('unaffected', {})
            issues: List[str] = []
            total = len(affected) + len(unaffected)
            if total == 0:
                issues.append('No components in segment')
            if not affected and not unaffected:
                issues.append('Both affected and unaffected are empty')
            passed = len(issues) == 0
            result = {
                'passed': passed,
                'issues': issues,
            }
            self._history.append({
                'action': 'verify',
                'passed': passed,
                'issues_count': len(issues),
            })
            return result
        except Exception:
            return {'passed': False, 'issues': ['verification_error']}

    def clear(self):
        self._history.clear()
