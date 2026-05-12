"""Divergence detector — detects replay divergence from expected behavior."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import ReplayDivergence, DivergenceType, ForensicSeverity


class DivergenceDetector:
    def __init__(self, max_history: int = 100):
        self._divergences: deque = deque(maxlen=max_history)
        self._divergence_count: int = 0

    def detect_state_mismatch(self, tick: int, expected: Dict[str, Any],
                               actual: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mismatches = []
        for key in set(list(expected.keys()) + list(actual.keys())):
            exp_val = expected.get(key)
            act_val = actual.get(key)
            if exp_val != act_val:
                mismatches.append({'key': key, 'expected': str(exp_val), 'actual': str(act_val)})
        if not mismatches:
            return None
        return self._create_divergence(tick, DivergenceType.STATE_MISMATCH,
                                        str(mismatches[:3]), 'State mismatch detected',
                                        ForensicSeverity.HIGH, {'mismatches': mismatches})

    def detect_event_mismatch(self, tick: int, expected_event: Optional[Dict[str, Any]],
                               actual_event: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if expected_event == actual_event:
            return None
        return self._create_divergence(tick, DivergenceType.EVENT_MISMATCH,
                                        str(expected_event), str(actual_event),
                                        ForensicSeverity.HIGH)

    def detect_order_mismatch(self, tick: int, expected_order: List[str],
                               actual_order: List[str]) -> Optional[Dict[str, Any]]:
        if expected_order == actual_order:
            return None
        return self._create_divergence(tick, DivergenceType.ORDER_MISMATCH,
                                        str(expected_order[:3]), str(actual_order[:3]),
                                        ForensicSeverity.MEDIUM,
                                        {'expected': expected_order, 'actual': actual_order})

    def _create_divergence(self, tick: int, dtype: DivergenceType,
                           expected: str, actual: str,
                           severity: ForensicSeverity,
                           details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._divergence_count += 1
        div = ReplayDivergence(
            divergence_id=f"div_{self._divergence_count}",
            divergence_type=dtype, tick=tick,
            expected=expected, actual=actual,
            severity=severity, details=details or {},
        )
        self._divergences.append(div)
        return {'divergence_id': div.divergence_id,
                'type': dtype.value, 'tick': tick,
                'severity': severity.value,
                'expected': expected, 'actual': actual}

    def get_divergence_count(self) -> int:
        return self._divergence_count

    def clear(self):
        self._divergences.clear()
        self._divergence_count = 0
