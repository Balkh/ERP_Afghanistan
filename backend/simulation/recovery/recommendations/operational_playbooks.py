"""Operational playbooks — predefined response playbooks for common incident types."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import RecoveryPlaybook, CorruptionType, IntegritySeverity


class OperationalPlaybooks:
    PLAYBOOKS = {
        'financial_imbalance': RecoveryPlaybook(
            playbook_id='pb_fin_001', name='Financial Imbalance Response',
            applicable_corruption_types=[CorruptionType.FINANCIAL, CorruptionType.JOURNAL_BALANCE],
            severity_threshold=IntegritySeverity.MEDIUM,
            steps=[
                'Isolate affected accounting workflows',
                'Verify journal entry balances',
                'Identify unbalanced entries',
                'Generate correction recommendations',
                'Escalate if imbalance exceeds threshold',
            ],
            estimated_duration_ticks=20, requires_escalation=True,
        ),
        'inventory_drift': RecoveryPlaybook(
            playbook_id='pb_inv_001', name='Inventory Drift Response',
            applicable_corruption_types=[CorruptionType.INVENTORY],
            severity_threshold=IntegritySeverity.MEDIUM,
            steps=[
                'Isolate inventory workflows',
                'Verify stock movement records',
                'Compare expected vs actual quantities',
                'Generate reconciliation recommendations',
            ],
            estimated_duration_ticks=15, requires_escalation=False,
        ),
        'orphan_cleanup': RecoveryPlaybook(
            playbook_id='pb_orp_001', name='Orphan State Cleanup',
            applicable_corruption_types=[CorruptionType.ORPHAN_STATE],
            severity_threshold=IntegritySeverity.LOW,
            steps=[
                'Identify orphan workflow instances',
                'Verify no dependent workflows',
                'Generate cleanup recommendations',
                'Recommend manual review for complex cases',
            ],
            estimated_duration_ticks=10, requires_escalation=False,
        ),
        'reconciliation_recovery': RecoveryPlaybook(
            playbook_id='pb_rec_001', name='Reconciliation Recovery',
            applicable_corruption_types=[CorruptionType.RECONCILIATION, CorruptionType.CONSISTENCY],
            severity_threshold=IntegritySeverity.MEDIUM,
            steps=[
                'Identify reconciliation gaps',
                'Trace gap to source transactions',
                'Generate reconciliation adjustments',
                'Verify post-reconciliation balance',
            ],
            estimated_duration_ticks=25, requires_escalation=True,
        ),
    }

    def __init__(self):
        self._access_history: deque = deque(maxlen=200)

    def get_playbook(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        pb = self.PLAYBOOKS.get(playbook_id)
        if pb is None:
            return None
        self._access_history.append(playbook_id)
        return {
            'playbook_id': pb.playbook_id, 'name': pb.name,
            'applicable_types': [t.value for t in pb.applicable_corruption_types],
            'severity_threshold': pb.severity_threshold.value,
            'steps': pb.steps,
            'estimated_duration_ticks': pb.estimated_duration_ticks,
            'requires_escalation': pb.requires_escalation,
        }

    def find_playbooks(self, corruption_type: CorruptionType,
                       severity: IntegritySeverity) -> List[Dict[str, Any]]:
        results = []
        for pb in self.PLAYBOOKS.values():
            if corruption_type in pb.applicable_corruption_types:
                severity_values = [s.value for s in [IntegritySeverity.INFO, IntegritySeverity.LOW,
                                                      IntegritySeverity.MEDIUM, IntegritySeverity.HIGH,
                                                      IntegritySeverity.CRITICAL]]
                pb_idx = severity_values.index(pb.severity_threshold.value) if pb.severity_threshold.value in severity_values else 0
                cur_idx = severity_values.index(severity.value) if severity.value in severity_values else 0
                if cur_idx >= pb_idx:
                    results.append(self.get_playbook(pb.playbook_id))
        return results

    def clear(self):
        self._access_history.clear()
