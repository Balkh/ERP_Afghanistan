from collections import deque
from typing import Any, Dict, List
from datetime import datetime


class RecoveryExecutionEngine:
    def __init__(self, max_history: int = 200):
        self._history: deque = deque(maxlen=max_history)
        self._stages_completed: int = 0
        self._last_execution_tick: int = -1
        self._in_progress: bool = False

    def execute(self, containment_result: Dict, approval: Dict, tick: int) -> Dict:
        try:
            self._in_progress = True
            stages: List[Dict] = []

            stage1 = self._manual_approval(approval)
            stages.append(stage1)
            if not stage1.get('success', False):
                self._in_progress = False
                result = self._build_result(False, stages, tick, containment_result)
                self._history.append(result)
                return result

            stage2 = self._execute_action(containment_result)
            stages.append(stage2)

            stage3 = self._simulate_rollback(containment_result)
            stages.append(stage3)

            stage4 = self._simulate_reconciliation()
            stages.append(stage4)

            self._stages_completed = 4
            self._last_execution_tick = tick
            self._in_progress = False
            result = self._build_result(True, stages, tick, containment_result)
            self._history.append(result)
            return result
        except Exception:
            self._in_progress = False
            return self._build_result(False, [{'stage': 'error', 'success': False}], tick, containment_result)

    def _manual_approval(self, approval: Dict) -> Dict:
        if not approval.get('approved'):
            return {
                'stage': 'manual_approval',
                'success': False,
                'approved': False,
                'error': 'Approval required but not granted',
            }
        if not approval.get('approved_by'):
            return {
                'stage': 'manual_approval',
                'success': False,
                'approved': False,
                'error': 'Approval missing approved_by field',
            }
        return {
            'stage': 'manual_approval',
            'success': True,
            'approved': True,
            'approved_by': approval['approved_by'],
        }

    def _execute_action(self, containment_result: Dict) -> Dict:
        action = containment_result.get('action', 'unknown')
        return {
            'stage': 'execution',
            'success': True,
            'action': action,
            'containment_id': containment_result.get('containment_id', ''),
        }

    def _simulate_rollback(self, containment_result: Dict) -> Dict:
        return {
            'stage': 'rollback',
            'success': True,
            'rolled_back_items': 3,
            'details': 'Partial rollback completed successfully',
        }

    def _simulate_reconciliation(self) -> Dict:
        return {
            'stage': 'reconciliation',
            'success': True,
            'matched': 5,
            'unmatched': 0,
        }

    def _build_result(self, success: bool, stages: List[Dict], tick: int, containment_result: Dict) -> Dict:
        return {
            'success': success,
            'stages': stages,
            'tick': tick,
            'containment_id': containment_result.get('containment_id', ''),
        }

    def get_execution_status(self) -> Dict:
        return {
            'stages_completed': self._stages_completed,
            'total_stages': 4,
            'last_execution_tick': self._last_execution_tick,
            'in_progress': self._in_progress,
        }

    def get_execution_history(self) -> List[Dict]:
        return list(self._history)

    def get_execution_count(self) -> int:
        return len(self._history)

    def clear(self):
        self._history.clear()
        self._stages_completed = 0
        self._last_execution_tick = -1
        self._in_progress = False
