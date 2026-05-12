"""Integrity guard — monitors and validates system integrity."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegrityViolation, IntegritySeverity, CorruptionType


class IntegrityGuard:
    def __init__(self, max_history: int = 500):
        self._violations: deque = deque(maxlen=max_history)
        self._violation_count: int = 0
        self._active_violations: List[IntegrityViolation] = []

    def record_violation(self, violation_type: CorruptionType, severity: IntegritySeverity,
                         source_module: str, description: str, tick: int,
                         affected_entities: Optional[List[str]] = None) -> Dict[str, Any]:
        self._violation_count += 1
        violation_id = f"vio_{self._violation_count}"
        violation = IntegrityViolation(
            violation_id=violation_id, violation_type=violation_type,
            severity=severity, source_module=source_module,
            description=description, detected_at_tick=tick,
            affected_entities=affected_entities or [],
        )
        self._violations.append(violation)
        if severity in (IntegritySeverity.HIGH, IntegritySeverity.CRITICAL):
            self._active_violations.append(violation)
        return {
            'violation_id': violation_id, 'type': violation_type.value,
            'severity': severity.value, 'description': description,
            'tick': tick,
        }

    def get_active_violations(self) -> List[Dict[str, Any]]:
        return [{'violation_id': v.violation_id, 'type': v.violation_type.value,
                 'severity': v.severity.value, 'description': v.description,
                 'module': v.source_module, 'tick': v.detected_at_tick}
                for v in self._active_violations]

    def get_violation_count(self) -> int:
        return self._violation_count

    def clear(self):
        self._violations.clear()
        self._active_violations.clear()
        self._violation_count = 0
