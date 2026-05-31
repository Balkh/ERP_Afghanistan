"""
Transition Provenance — tracks all state transitions with audit evidence.

Every state mutation (APPROVED -> COMPLETED, PENDING -> APPROVED, etc.)
MUST declare:
  - source: what triggered the transition
  - reason: why the transition occurred
  - condition: what condition was met

This prevents hidden automatic workflow transitions from mutating state
without leaving an evidence trail.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger('erp.transition_provenance')


class ProvenanceRecord:
    """A single state transition record with full provenance."""

    def __init__(
        self,
        model_name: str,
        instance_id: str,
        from_status: str,
        to_status: str,
        source: str,
        reason: str,
        condition: str,
        timestamp: Optional[datetime] = None,
    ):
        self.model_name = model_name
        self.instance_id = instance_id
        self.from_status = from_status
        self.to_status = to_status
        self.source = source
        self.reason = reason
        self.condition = condition
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'model': self.model_name,
            'instance_id': self.instance_id,
            'from': self.from_status,
            'to': self.to_status,
            'source': self.source,
            'reason': self.reason,
            'condition': self.condition,
            'timestamp': self.timestamp.isoformat(),
        }


class TransitionJournal:
    """In-memory journal of all state transitions during a session.

    In production, this feeds into the audit system. In tests,
    it provides replayable evidence of every state mutation.
    """

    def __init__(self):
        self._records: list = []
        self._by_model: Dict[str, list] = defaultdict(list)

    def record(
        self,
        model_name: str,
        instance_id: str,
        from_status: str,
        to_status: str,
        source: str,
        reason: str,
        condition: str = '',
    ):
        rec = ProvenanceRecord(
            model_name=model_name,
            instance_id=instance_id,
            from_status=from_status,
            to_status=to_status,
            source=source,
            reason=reason,
            condition=condition,
        )
        self._records.append(rec)
        self._by_model[model_name].append(rec)
        logger.debug(
            f"[PROVENANCE] {model_name}.{instance_id[:8]}: "
            f"{from_status} -> {to_status} via {source} ({reason})"
        )
        return rec

    def get_by_model(self, model_name: str) -> list:
        return list(self._by_model.get(model_name, []))

    def get_all(self) -> list:
        return list(self._records)

    def find_auto_transitions(self, model_name: str = '') -> list:
        """Return all transitions triggered by signals or automation."""
        results = []
        for rec in self._records:
            if model_name and rec.model_name != model_name:
                continue
            if rec.source in ('signal', 'auto', 'system'):
                results.append(rec)
        return results

    def validate_all_have_provenance(self) -> list:
        """Check that every transition has complete provenance.

        Returns list of issues (empty if all clean).
        """
        issues = []
        for rec in self._records:
            if not rec.source:
                issues.append(
                    f"Missing source: {rec.model_name}.{rec.instance_id[:8]} "
                    f"{rec.from_status} -> {rec.to_status}"
                )
            if not rec.reason:
                issues.append(
                    f"Missing reason: {rec.model_name}.{rec.instance_id[:8]} "
                    f"{rec.from_status} -> {rec.to_status}"
                )
        return issues

    def clear(self):
        self._records.clear()
        self._by_model.clear()


# Session-level journal
_journal = TransitionJournal()


def get_journal() -> TransitionJournal:
    return _journal


def record_transition(
    model_name: str,
    instance_id: str,
    from_status: str,
    to_status: str,
    source: str,
    reason: str,
    condition: str = '',
):
    """Record a state transition in the session journal."""
    return _journal.record(
        model_name=model_name,
        instance_id=instance_id,
        from_status=from_status,
        to_status=to_status,
        source=source,
        reason=reason,
        condition=condition,
    )


def provenance_decorator(source: str = ''):
    """Decorator that records state transitions for a model's save() method.

    Usage:
        @provenance_decorator(source='approve')
        def approve(self, employee):
            self.status = 'APPROVED'
            self.save()

    The decorator detects status changes before/after save and records them.
    """
    def decorator(func):
        def wrapper(instance, *args, **kwargs):
            model_name = instance.__class__.__name__
            old_status = getattr(instance, 'status', '')

            result = func(instance, *args, **kwargs)

            new_status = getattr(instance, 'status', '')
            if old_status != new_status:
                record_transition(
                    model_name=model_name,
                    instance_id=str(instance.id),
                    from_status=old_status,
                    to_status=new_status,
                    source=source or func.__name__,
                    reason=f'{func.__name__} changed status',
                )
            return result
        return wrapper
    return decorator
