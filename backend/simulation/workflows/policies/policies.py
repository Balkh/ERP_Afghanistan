import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger('erp.simulation.policy_engine')


class SimulationPolicyEngine:
    """
    Validates workflow execution and enforces simulation rules.
    NO correction logic. ONLY validation + blocking.
    """

    def __init__(self):
        self._rules: Dict[str, dict] = {}
        self._violations: List[Dict[str, Any]] = []
        self._register_default_rules()

    def _register_default_rules(self):
        self.add_rule('inventory_non_negative', {
            'name': 'Inventory Non-Negative',
            'description': 'Inventory quantities must not go negative',
            'category': 'inventory',
            'severity': 'error',
        })
        self.add_rule('balanced_financial', {
            'name': 'Balanced Financial Operations',
            'description': 'Financial operations must remain balanced',
            'category': 'financial',
            'severity': 'error',
        })
        self.add_rule('valid_workflow_transition', {
            'name': 'Valid Workflow Transition',
            'description': 'Workflow transitions must follow defined steps',
            'category': 'workflow',
            'severity': 'error',
        })
        self.add_rule('agent_not_mutating_db', {
            'name': 'Agent No DB Mutation',
            'description': 'Agents must not directly mutate database',
            'category': 'agent',
            'severity': 'error',
        })
        self.add_rule('no_concurrent_workflows', {
            'name': 'No Concurrent Workflows',
            'description': 'Prevent duplicate active workflow instances',
            'category': 'workflow',
            'severity': 'warning',
        })

    def add_rule(self, rule_id: str, rule_def: dict):
        if rule_id in self._rules:
            raise ValueError(f"Rule '{rule_id}' already exists")
        self._rules[rule_id] = rule_def

    def get_rule(self, rule_id: str) -> Optional[dict]:
        return self._rules.get(rule_id)

    @property
    def rules(self) -> Dict[str, dict]:
        return dict(self._rules)

    @property
    def violations(self) -> List[Dict[str, Any]]:
        return list(self._violations)

    def validate_workflow_execution(
        self, workflow_id: str, step_id: str,
        available_steps: List[str],
    ) -> bool:
        if step_id not in available_steps:
            self._record_violation(
                'valid_workflow_transition',
                f"Step '{step_id}' not in workflow '{workflow_id}'",
                {'workflow_id': workflow_id, 'step_id': step_id},
            )
            return False
        return True

    def validate_inventory_operation(
        self, operation: str, quantity: float,
    ) -> bool:
        if operation in ('out', 'transfer_out') and quantity < 0:
            self._record_violation(
                'inventory_non_negative',
                f"Negative inventory operation: {operation}",
                {'operation': operation, 'quantity': quantity},
            )
            return False
        return True

    def validate_financial_balance(
        self, debits: float, credits: float,
    ) -> bool:
        if abs(debits - credits) > 0.001:
            self._record_violation(
                'balanced_financial',
                f"Unbalanced financial: debits={debits}, credits={credits}",
                {'debits': debits, 'credits': credits},
            )
            return False
        return True

    def block_workflow(self, workflow_id: str,
                       reason: str) -> Dict[str, Any]:
        violation = {
            'rule_id': 'workflow_blocked',
            'workflow_id': workflow_id,
            'reason': reason,
        }
        self._violations.append(violation)
        logger.warning("Workflow '%s' blocked: %s", workflow_id, reason)
        return {'status': 'blocked', 'workflow_id': workflow_id,
                'reason': reason}

    def _record_violation(self, rule_id: str, message: str,
                          details: Optional[dict] = None):
        violation = {
            'rule_id': rule_id,
            'message': message,
            'details': dict(details) if details else {},
        }
        self._violations.append(violation)
        logger.warning("Policy violation: %s — %s", rule_id, message)

    def clear_violations(self):
        self._violations.clear()

    @property
    def violation_count(self) -> int:
        return len(self._violations)
