"""Replay validator — validates replay sessions and results."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayStatus, ReplayIntegrityReport, ReplayDivergence


class ReplayValidator:
    def __init__(self, max_history: int = 100):
        self._validation_history: deque = deque(maxlen=max_history)

    def validate_session(self, session: Dict[str, Any],
                         events: List[Dict[str, Any]]) -> Dict[str, Any]:
        has_events = len(events) > 0
        has_valid_range = session.get('end_tick', 0) >= session.get('start_tick', 0)
        is_valid_status = session.get('status') in ('completed', 'idle', 'running')
        is_valid = has_events and has_valid_range and is_valid_status
        issues = []
        if not has_events:
            issues.append('No events to replay')
        if not has_valid_range:
            issues.append('Invalid tick range')
        if not is_valid_status:
            issues.append(f"Invalid status: {session.get('status')}")
        self._validation_history.append({
            'is_valid': is_valid, 'issues_found': len(issues),
        })
        return {'is_valid': is_valid, 'issues': issues}

    def validate_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        was_executed = result.get('executed', False)
        has_session = result.get('session_id') is not None
        is_valid = was_executed and has_session
        self._validation_history.append({
            'is_valid': is_valid, 'result_keys': list(result.keys()),
        })
        return {'is_valid': is_valid, 'executed': was_executed,
                'has_session_id': has_session}

    def clear(self):
        self._validation_history.clear()
