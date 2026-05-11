import logging
from typing import Any, Dict, List

from simulation.truth_engine.models.models import (
    Mismatch, MismatchType, MismatchSeverity,
    ExpectedState, ActualState,
)


logger = logging.getLogger('erp.simulation.truth.scoring')


class IntegrityScorer:
    """
    Computes integrity scores (0-100).
    Observational only. NO correction logic.
    """

    SEVERITY_WEIGHTS = {
        MismatchSeverity.CRITICAL: 25.0,
        MismatchSeverity.HIGH: 15.0,
        MismatchSeverity.MEDIUM: 8.0,
        MismatchSeverity.LOW: 3.0,
        MismatchSeverity.INFO: 1.0,
    }

    def __init__(self):
        self._scores: Dict[str, float] = {}

    def compute_scores(
        self, expected: ExpectedState, actual: ActualState,
        mismatches: List[Mismatch],
    ) -> Dict[str, float]:
        scores = {}
        scores['financial_integrity_score'] = self._score_financial(
            expected, actual, mismatches
        )
        scores['inventory_integrity_score'] = self._score_inventory(
            expected, actual, mismatches
        )
        scores['workflow_completion_score'] = self._score_workflow(
            expected, mismatches
        )
        scores['overall_system_score'] = self._compute_overall(scores)
        scores['drift_percentage'] = self._compute_drift(
            expected, actual, mismatches
        )
        scores['consistency_ratio'] = self._compute_consistency(
            expected, actual, mismatches
        )
        self._scores = scores
        return scores

    def _score_financial(
        self, expected: ExpectedState, actual: ActualState,
        mismatches: List[Mismatch],
    ) -> float:
        financial_mismatches = [
            m for m in mismatches
            if m.mismatch_type == MismatchType.FINANCIAL_MISMATCH
            or m.mismatch_type == MismatchType.DUPLICATE_ENTRY
        ]
        penalty = sum(
            self.SEVERITY_WEIGHTS.get(m.severity, 5.0)
            for m in financial_mismatches
        )
        score = max(0.0, 100.0 - penalty)
        return round(score, 2)

    def _score_inventory(
        self, expected: ExpectedState, actual: ActualState,
        mismatches: List[Mismatch],
    ) -> float:
        inv_mismatches = [
            m for m in mismatches
            if m.mismatch_type == MismatchType.INVENTORY_MISMATCH
        ]
        penalty = sum(
            self.SEVERITY_WEIGHTS.get(m.severity, 5.0)
            for m in inv_mismatches
        )
        score = max(0.0, 100.0 - penalty)
        return round(score, 2)

    def _score_workflow(
        self, expected: ExpectedState,
        mismatches: List[Mismatch],
    ) -> float:
        workflow_mismatches = [
            m for m in mismatches
            if m.mismatch_type == MismatchType.WORKFLOW_INCOMPLETE
            or m.mismatch_type == MismatchType.TRANSACTION_MISSING
        ]
        penalty = sum(
            self.SEVERITY_WEIGHTS.get(m.severity, 5.0)
            for m in workflow_mismatches
        )
        score = max(0.0, 100.0 - penalty)
        return round(score, 2)

    def _compute_overall(self, scores: Dict[str, float]) -> float:
        financial = scores.get('financial_integrity_score', 100.0)
        inventory = scores.get('inventory_integrity_score', 100.0)
        workflow = scores.get('workflow_completion_score', 100.0)
        overall = (financial + inventory + workflow) / 3.0
        return round(overall, 2)

    def _compute_drift(
        self, expected: ExpectedState, actual: ActualState,
        mismatches: List[Mismatch],
    ) -> float:
        if not expected._inventory_delta:
            return 0.0
        drift_count = len(mismatches)
        total_expected = (
            expected._sales_count +
            expected._purchase_count +
            len(expected._inventory_delta)
        )
        if total_expected == 0:
            return 0.0
        drift = (drift_count / total_expected) * 100.0
        return round(min(100.0, drift), 2)

    def _compute_consistency(
        self, expected: ExpectedState, actual: ActualState,
        mismatches: List[Mismatch],
    ) -> float:
        total_entities = (
            expected._sales_count +
            expected._purchase_count +
            expected._returns_count +
            len(expected._inventory_delta)
        )
        if total_entities == 0:
            return 100.0
        consistent = total_entities - len(mismatches)
        ratio = (consistent / total_entities) * 100.0
        return round(max(0.0, ratio), 2)

    @property
    def scores(self) -> Dict[str, float]:
        return dict(self._scores)
