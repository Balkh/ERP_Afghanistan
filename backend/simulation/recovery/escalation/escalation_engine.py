"""Escalation engine — orchestrates severity classification, policy evaluation, and notification."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import EscalationRecord, IntegritySeverity, EscalationPriority
from simulation.recovery.escalation.severity_classifier import SeverityClassifier
from simulation.recovery.escalation.escalation_policy import EscalationPolicyEngine
from simulation.recovery.escalation.notification_priority import NotificationPriorityMapper


class EscalationEngine:
    def __init__(self, max_history: int = 200):
        self._classifier = SeverityClassifier()
        self._policy_engine = EscalationPolicyEngine()
        self._notification_mapper = NotificationPriorityMapper()
        self._escalation_history: deque = deque(maxlen=max_history)
        self._escalation_count: int = 0

    @property
    def classifier(self) -> SeverityClassifier:
        return self._classifier

    @property
    def policy_engine(self) -> EscalationPolicyEngine:
        return self._policy_engine

    @property
    def notification_mapper(self) -> NotificationPriorityMapper:
        return self._notification_mapper

    def evaluate(self, context: Dict[str, Any],
                 affected_workflows: Optional[List[str]] = None) -> Dict[str, Any]:
        affected_workflows = affected_workflows or []
        severity_result = self._classifier.classify(
            risk_score=context.get('risk_score', 0),
            has_conflicts=context.get('has_conflicts', False),
            has_irreversible=context.get('has_irreversible', False),
            containment_active=context.get('containment_active', False),
            workflows_affected=len(affected_workflows),
        )
        policy_results = self._policy_engine.evaluate({
            **context, 'severity': severity_result['severity'],
            'workflows_affected': len(affected_workflows),
        })
        _priority_order = {e.value: i for i, e in enumerate(EscalationPriority)}
        highest_priority = EscalationPriority.LOW
        for pr in policy_results:
            try:
                p = EscalationPriority(pr['priority'])
                if _priority_order.get(p.value, 0) > _priority_order.get(highest_priority.value, 0):
                    highest_priority = p
            except (ValueError, KeyError):
                pass
        notification = self._notification_mapper.map_priority(highest_priority)
        self._escalation_count += 1
        escalation_id = f"esc_{self._escalation_count}"
        record = EscalationRecord(
            escalation_id=escalation_id, priority=highest_priority,
            source_module=context.get('source_module', 'unknown'),
            reason=context.get('reason', 'No reason provided'),
            severity=IntegritySeverity(severity_result['severity']),
            generated_at_tick=context.get('tick', 0),
            affected_workflows=affected_workflows,
            recommendations=[pr['name'] for pr in policy_results],
            requires_immediate_action=highest_priority == EscalationPriority.IMMEDIATE,
        )
        self._escalation_history.append({
            'escalation_id': escalation_id,
            'priority': highest_priority.value,
            'policy_count': len(policy_results),
        })
        return {
            'escalation_id': escalation_id,
            'priority': highest_priority.value,
            'severity': severity_result['severity'],
            'requires_immediate_action': record.requires_immediate_action,
            'triggered_policies': policy_results,
            'notification': notification,
            'recommendations': record.recommendations,
        }

    def get_escalation_count(self) -> int:
        return self._escalation_count

    def clear(self):
        self._classifier.clear()
        self._policy_engine.clear()
        self._notification_mapper.clear()
        self._escalation_history.clear()
        self._escalation_count = 0
