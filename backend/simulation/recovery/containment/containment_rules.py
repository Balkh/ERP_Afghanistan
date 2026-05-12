"""Containment policies and rule evaluation."""
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from simulation.recovery.models import ContainmentStatus, IntegritySeverity, CorruptionType


@dataclass
class ContainmentRule:
    rule_id: str
    name: str
    description: str
    condition: str
    severity_threshold: IntegritySeverity
    auto_isolate: bool = False
    auto_quarantine: bool = False
    quarantine_duration_ticks: int = 50


class ContainmentRules:
    KNOWN_RULES = {
        'financial_imbalance': ContainmentRule(
            rule_id='fin_001', name='Financial Imbalance',
            description='Journal entry imbalance detected - isolate workflow',
            condition='journal_balance != 0', severity_threshold=IntegritySeverity.HIGH,
            auto_isolate=True, auto_quarantine=True,
        ),
        'inventory_drift': ContainmentRule(
            rule_id='inv_001', name='Inventory Drift',
            description='Inventory quantity inconsistency detected',
            condition='inventory_delta != movement_sum', severity_threshold=IntegritySeverity.HIGH,
            auto_isolate=True, auto_quarantine=True,
        ),
        'orphan_state': ContainmentRule(
            rule_id='orp_001', name='Orphan State',
            description='Orphan workflow state detected',
            condition='orphan_found == True', severity_threshold=IntegritySeverity.MEDIUM,
            auto_isolate=True, auto_quarantine=False,
        ),
        'reconciliation_failure': ContainmentRule(
            rule_id='rec_001', name='Reconciliation Failure',
            description='Reconciliation mismatch exceeds threshold',
            condition='reconciliation_gap > threshold', severity_threshold=IntegritySeverity.MEDIUM,
            auto_isolate=False, auto_quarantine=False,
        ),
        'cascade_risk': ContainmentRule(
            rule_id='cas_001', name='Cascade Risk',
            description='High risk of cascading workflow failure',
            condition='cascade_probability > 0.7', severity_threshold=IntegritySeverity.CRITICAL,
            auto_isolate=True, auto_quarantine=True,
        ),
    }

    def __init__(self):
        self._evaluation_history: deque = deque(maxlen=200)

    def get_rule(self, rule_key: str) -> Optional[ContainmentRule]:
        return self.KNOWN_RULES.get(rule_key)

    def evaluate_rule(self, rule_key: str, context: Dict[str, Any]) -> Dict[str, Any]:
        rule = self.get_rule(rule_key)
        if rule is None:
            return {'triggered': False, 'reason': 'Unknown rule'}
        triggered = self._check_condition(rule.condition, context)
        self._evaluation_history.append({
            'rule_key': rule_key, 'triggered': triggered,
            'context': context, 'rule_id': rule.rule_id,
        })
        if triggered:
            return {
                'triggered': True, 'rule': rule_key,
                'severity': rule.severity_threshold.value,
                'auto_isolate': rule.auto_isolate,
                'auto_quarantine': rule.auto_quarantine,
                'quarantine_duration': rule.quarantine_duration_ticks,
                'message': rule.description,
            }
        return {'triggered': False, 'reason': 'Condition not met'}

    def evaluate_multi(self, contexts: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for rule_key in self.KNOWN_RULES:
            ctx = contexts.get(rule_key, {})
            results.append(self.evaluate_rule(rule_key, ctx))
        return results

    def _check_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        if condition == 'journal_balance != 0':
            return context.get('journal_balance', 0) != 0
        elif condition == 'inventory_delta != movement_sum':
            return context.get('inventory_delta', 0) != context.get('movement_sum', 0)
        elif condition == 'orphan_found == True':
            return context.get('orphan_found', False) is True
        elif condition == 'reconciliation_gap > threshold':
            gap = context.get('reconciliation_gap', 0)
            threshold = context.get('threshold', 0)
            return gap > threshold
        elif condition == 'cascade_probability > 0.7':
            return context.get('cascade_probability', 0) > 0.7
        return False

    def evaluation_count(self) -> int:
        return len(self._evaluation_history)

    def clear(self):
        self._evaluation_history.clear()
