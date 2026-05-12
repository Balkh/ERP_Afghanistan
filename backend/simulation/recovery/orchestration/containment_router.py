"""Containment router — routes containment events to appropriate handlers."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegritySeverity, CorruptionType
from simulation.recovery.containment.containment_engine import ContainmentEngine
from simulation.recovery.escalation.escalation_engine import EscalationEngine


class ContainmentRouter:
    def __init__(self, max_history: int = 200):
        self._routing_history: deque = deque(maxlen=max_history)
        self._route_count: int = 0

    def route(self, corruption_type: CorruptionType, severity: IntegritySeverity,
              context: Dict[str, Any],
              containment_engine: Optional[ContainmentEngine] = None,
              escalation_engine: Optional[EscalationEngine] = None) -> Dict[str, Any]:
        self._route_count += 1
        route_id = f"route_{self._route_count}"
        actions = []
        if severity in (IntegritySeverity.HIGH, IntegritySeverity.CRITICAL):
            wf_id = context.get('workflow_id', 'unknown')
            wf_type = context.get('workflow_type', 'unknown')
            tick = context.get('tick', 0)
            rule_contexts = {}
            if corruption_type == CorruptionType.FINANCIAL:
                rule_contexts['financial_imbalance'] = {
                    'journal_balance': context.get('journal_balance', 1),
                }
            elif corruption_type == CorruptionType.INVENTORY:
                rule_contexts['inventory_drift'] = {
                    'inventory_delta': context.get('inventory_delta', 1),
                    'movement_sum': context.get('movement_sum', 0),
                }
            elif corruption_type == CorruptionType.ORPHAN_STATE:
                rule_contexts['orphan_state'] = {
                    'orphan_found': True,
                }
            containment_active = False
            if containment_engine:
                containment_result = containment_engine.evaluate_and_contain(
                    wf_id, wf_type, tick, rule_contexts)
                actions.append({
                    'action': 'containment', 'result': containment_result,
                })
                containment_active = containment_result.get('contained', False)
            if escalation_engine and containment_active:
                esc_context = {
                    'risk_score': context.get('risk_score', 50),
                    'severity': severity.value,
                    'has_conflicts': context.get('has_conflicts', False),
                    'has_irreversible': context.get('has_irreversible', False),
                    'containment_active': True,
                    'source_module': context.get('source_module', 'unknown'),
                    'reason': context.get('reason', 'Corruption detected'),
                    'tick': tick,
                }
                escalation_result = escalation_engine.evaluate(
                    esc_context, affected_workflows=[wf_id])
                actions.append({
                    'action': 'escalation', 'result': escalation_result,
                })
        self._routing_history.append({
            'route_id': route_id, 'corruption_type': corruption_type.value,
            'severity': severity.value, 'actions_taken': len(actions),
        })
        return {
            'route_id': route_id, 'corruption_type': corruption_type.value,
            'severity': severity.value, 'actions': actions,
        }

    def clear(self):
        self._routing_history.clear()
        self._route_count = 0
