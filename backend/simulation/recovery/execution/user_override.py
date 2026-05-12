from collections import deque
from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime, timezone


class UserOverrideHandler:
    RISKY_TARGETS = {'critical', 'financial', 'inventory', 'production', 'database'}

    def __init__(self, max_history: int = 200):
        self._history: deque = deque(maxlen=max_history)

    def validate(self, request: Dict) -> Dict:
        try:
            required = ['override_id', 'reason', 'requested_by', 'target']
            missing: List[str] = [f for f in required if f not in request or not request[f]]
            warnings: List[str] = []
            if len(request.get('reason', '')) < 10:
                warnings.append('Reason is too short (minimum 10 characters)')
            if request.get('target', '').lower() in self.RISKY_TARGETS:
                warnings.append(f"Target '{request['target']}' is a high-risk area")
            valid = len(missing) == 0
            result = {
                'valid': valid,
                'missing_fields': missing,
                'warnings': warnings,
            }
            self._history.append({
                'action': 'validate',
                'valid': valid,
                'missing_count': len(missing),
                'warning_count': len(warnings),
            })
            return result
        except Exception:
            return {'valid': False, 'missing_fields': ['validation_error'], 'warnings': []}

    def score_risk(self, request: Dict) -> Dict:
        try:
            target = request.get('target', '').lower()
            reason_len = len(request.get('reason', ''))
            risk_score = 0.0
            if target in self.RISKY_TARGETS:
                risk_score += 40.0
            if reason_len < 10:
                risk_score += 20.0
            elif reason_len < 30:
                risk_score += 10.0
            risk_score = min(100.0, risk_score)
            level = 'critical' if risk_score >= 80 else 'high' if risk_score >= 60 else 'medium' if risk_score >= 30 else 'low'
            result = {
                'risk_score': risk_score,
                'level': level,
            }
            self._history.append({
                'action': 'score_risk',
                'risk_score': risk_score,
                'level': level,
            })
            return result
        except Exception:
            return {'risk_score': 100.0, 'level': 'critical'}

    def audit_lock(self, request: Dict) -> Dict:
        try:
            audit_id = str(uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            result = {
                'locked': True,
                'audit_id': audit_id,
                'timestamp': timestamp,
            }
            self._history.append({
                'action': 'audit_lock',
                'audit_id': audit_id,
                'override_id': request.get('override_id', ''),
                'timestamp': timestamp,
            })
            return result
        except Exception:
            return {'locked': False, 'audit_id': '', 'timestamp': ''}

    def controlled_execute(self, request: Dict, risk_score: Dict) -> Dict:
        try:
            execution_id = str(uuid4())
            risk_level = risk_score.get('level', 'unknown')
            result = {
                'success': True,
                'execution_id': execution_id,
                'risk_level': risk_level,
                'monitored': True,
            }
            self._history.append({
                'action': 'controlled_execute',
                'execution_id': execution_id,
                'risk_level': risk_level,
                'override_id': request.get('override_id', ''),
            })
            return result
        except Exception:
            return {'success': False, 'execution_id': '', 'risk_level': 'unknown', 'monitored': False}

    def get_override_history(self) -> List[Dict]:
        return list(self._history)

    def clear(self):
        self._history.clear()
