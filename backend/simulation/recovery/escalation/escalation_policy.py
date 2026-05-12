"""Escalation policies — defines when and how to escalate incidents."""
from collections import deque
from typing import Any, Dict, List, Optional, Callable
from simulation.recovery.models import IntegritySeverity, EscalationPriority


EscalationCondition = Callable[[Dict[str, Any]], bool]


class EscalationPolicy:
    def __init__(self, policy_id: str, name: str,
                 condition: EscalationCondition, priority: EscalationPriority,
                 description: str = ""):
        self.policy_id = policy_id
        self.name = name
        self.condition = condition
        self.priority = priority
        self.description = description


class EscalationPolicyEngine:
    DEFAULT_POLICIES = {
        'critical_severity': EscalationPolicy(
            policy_id='esc_001', name='Critical Severity',
            condition=lambda ctx: ctx.get('severity', '') == IntegritySeverity.CRITICAL.value,
            priority=EscalationPriority.IMMEDIATE,
            description='Any critical severity incident triggers immediate escalation',
        ),
        'high_risk_score': EscalationPolicy(
            policy_id='esc_002', name='High Risk Score',
            condition=lambda ctx: ctx.get('risk_score', 0) >= 70,
            priority=EscalationPriority.HIGH,
            description='Risk score >= 70 triggers high priority escalation',
        ),
        'multiple_workflows': EscalationPolicy(
            policy_id='esc_003', name='Multiple Workflows Affected',
            condition=lambda ctx: ctx.get('workflows_affected', 0) >= 3,
            priority=EscalationPriority.HIGH,
            description='3+ affected workflows triggers escalation',
        ),
        'irreversible_operations': EscalationPolicy(
            policy_id='esc_004', name='Irreversible Operations',
            condition=lambda ctx: ctx.get('has_irreversible', False),
            priority=EscalationPriority.IMMEDIATE,
            description='Irreversible operations require immediate escalation',
        ),
        'containment_failure': EscalationPolicy(
            policy_id='esc_005', name='Containment Failure',
            condition=lambda ctx: ctx.get('containment_failed', False),
            priority=EscalationPriority.IMMEDIATE,
            description='Containment failure requires immediate escalation',
        ),
    }

    def __init__(self):
        self._custom_policies: Dict[str, EscalationPolicy] = {}
        self._evaluation_history: deque = deque(maxlen=200)

    def add_policy(self, policy: EscalationPolicy):
        self._custom_policies[policy.policy_id] = policy

    def evaluate(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        triggered = []
        all_policies = {**self.DEFAULT_POLICIES, **self._custom_policies}
        for key, policy in all_policies.items():
            try:
                if policy.condition(context):
                    triggered.append({
                        'policy_id': policy.policy_id,
                        'name': policy.name,
                        'priority': policy.priority.value,
                        'description': policy.description,
                    })
            except Exception:
                pass
        self._evaluation_history.append({
            'context_summary': {k: v for k, v in context.items()
                              if not isinstance(v, (dict, list)) or len(str(v)) < 100},
            'triggered_count': len(triggered),
        })
        return triggered

    def clear(self):
        self._custom_policies.clear()
        self._evaluation_history.clear()
