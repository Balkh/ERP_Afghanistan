"""Recovery recommender — generates recovery recommendations based on detected issues."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import (RecoveryRecommendation, RecoveryPathType,
                                        CorruptionType, IntegritySeverity)
from simulation.recovery.recommendations.recovery_paths import RecoveryPathsRegistry
from simulation.recovery.recommendations.operational_playbooks import OperationalPlaybooks
from simulation.recovery.recommendations.remediation_priority import RemediationPriority


class RecoveryRecommender:
    def __init__(self, max_history: int = 200):
        self._paths = RecoveryPathsRegistry()
        self._playbooks = OperationalPlaybooks()
        self._priority = RemediationPriority()
        self._recommendation_history: deque = deque(maxlen=max_history)
        self._recommendation_count: int = 0

    @property
    def paths(self) -> RecoveryPathsRegistry:
        return self._paths

    @property
    def playbooks(self) -> OperationalPlaybooks:
        return self._playbooks

    @property
    def priority(self) -> RemediationPriority:
        return self._priority

    def generate_recommendations(self, corruption_type: CorruptionType,
                                  severity: IntegritySeverity,
                                  blast_radius_score: float = 0.0,
                                  has_irreversible: bool = False,
                                  workflows_blocked: int = 0,
                                  context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        context = context or {}
        recommendations = []
        priority_result = self._priority.calculate_priority(
            severity, blast_radius_score, has_irreversible, workflows_blocked)
        playbooks = self._playbooks.find_playbooks(corruption_type, severity)
        for pb in playbooks:
            self._recommendation_count += 1
            rec_id = f"rec_{self._recommendation_count}"
            path_type = (RecoveryPathType.MANUAL_INTERVENTION if severity in (
                IntegritySeverity.HIGH, IntegritySeverity.CRITICAL)
                         else RecoveryPathType.RECONCILE)
            path_info = self._paths.get_path(path_type)
            rec = RecoveryRecommendation(
                recommendation_id=rec_id, path_type=path_type,
                priority=int(priority_result['priority_score']),
                description=pb['name'] if pb else 'No matching playbook',
                estimated_effort=path_info['estimated_effort'],
                requires_manual_review=path_info['requires_manual_review'],
                automated_possible=path_info['automated_possible'],
                risks=path_info['risks'],
                steps=pb.get('steps', []) if pb else [],
            )
            recommendations.append({
                'recommendation_id': rec_id,
                'path_type': path_type.value,
                'priority': rec.priority,
                'description': rec.description,
                'estimated_effort': rec.estimated_effort,
                'requires_manual_review': rec.requires_manual_review,
                'automated_possible': rec.automated_possible,
                'risks': rec.risks,
                'steps': rec.steps,
            })
        self._recommendation_history.append({
            'count': len(recommendations),
            'corruption_type': corruption_type.value,
            'severity': severity.value,
        })
        return recommendations

    def get_recommendation_count(self) -> int:
        return self._recommendation_count

    def clear(self):
        self._paths.clear()
        self._playbooks.clear()
        self._priority.clear()
        self._recommendation_history.clear()
        self._recommendation_count = 0
