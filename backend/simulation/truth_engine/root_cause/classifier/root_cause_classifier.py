"""
Task 2: RootCauseClassifier — Classifies primary root cause for each mismatch.
Exactly ONE primary root cause per mismatch. Confidence score required.
"""
import logging
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import (
    RootCause, RootCauseType,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.classifier')


class RootCauseClassifier:
    """
    Classifies the primary reason for each mismatch.
    Deterministic rules only. No ML. No inference without evidence.
    """

    RULE_MAP = {
        'financial_mismatch': {
            'primary': RootCauseType.LOGIC_ERROR,
            'secondary': [RootCauseType.DATA_INCONSISTENCY,
                          RootCauseType.MISSING_MAPPING],
            'base_confidence': 0.85,
        },
        'inventory_mismatch': {
            'primary': RootCauseType.CONCURRENCY_ISSUE,
            'secondary': [RootCauseType.TIMING_DESYNC,
                          RootCauseType.WORKFLOW_DESIGN_FLAW],
            'base_confidence': 0.80,
        },
        'transaction_missing': {
            'primary': RootCauseType.MISSING_MAPPING,
            'secondary': [RootCauseType.WORKFLOW_DESIGN_FLAW,
                          RootCauseType.LOGIC_ERROR],
            'base_confidence': 0.90,
        },
        'duplicate_entry': {
            'primary': RootCauseType.LOGIC_ERROR,
            'secondary': [RootCauseType.CONCURRENCY_ISSUE,
                          RootCauseType.TIMING_DESYNC],
            'base_confidence': 0.95,
        },
        'workflow_incomplete': {
            'primary': RootCauseType.WORKFLOW_DESIGN_FLAW,
            'secondary': [RootCauseType.TIMING_DESYNC,
                          RootCauseType.MISSING_MAPPING],
            'base_confidence': 0.85,
        },
        'state_drift': {
            'primary': RootCauseType.TIMING_DESYNC,
            'secondary': [RootCauseType.CONCURRENCY_ISSUE,
                          RootCauseType.DATA_INCONSISTENCY],
            'base_confidence': 0.75,
        },
    }

    def __init__(self):
        self._classifications: Dict[str, RootCause] = {}

    def classify(
        self,
        mismatch_id: str,
        mismatch_type: str,
        mismatch_description: str,
        affected_module: str,
        tick: int,
        event_count: int = 0,
    ) -> RootCause:
        rule = self.RULE_MAP.get(mismatch_type, {})
        primary = rule.get('primary', RootCauseType.UNKNOWN_CAUSE)
        secondary = rule.get('secondary', [])
        base_confidence = rule.get('base_confidence', 0.50)
        confidence = self._adjust_confidence(
            base_confidence, mismatch_type, event_count
        )
        desc = self._build_description(
            mismatch_type, affected_module, tick, primary
        )
        cause = RootCause(
            cause_id=f"cause_{mismatch_id}",
            primary_type=primary,
            confidence=confidence,
            mismatch_id=mismatch_id,
            description=desc,
            secondary_types=secondary,
            evidence_refs=[f"tick_{tick}", mismatch_type],
        )
        self._classifications[cause.cause_id] = cause
        return cause

    def _adjust_confidence(
        self, base: float, mismatch_type: str, event_count: int,
    ) -> float:
        if event_count > 5:
            return min(1.0, base + 0.10)
        if event_count == 0:
            return max(0.30, base - 0.20)
        return base

    def _build_description(
        self, mismatch_type: str, module: str, tick: int,
        primary: RootCauseType,
    ) -> str:
        descriptions = {
            RootCauseType.LOGIC_ERROR: (
                f"Business logic error in {module} at tick {tick}"
            ),
            RootCauseType.CONCURRENCY_ISSUE: (
                f"Concurrent access conflict in {module} at tick {tick}"
            ),
            RootCauseType.MISSING_MAPPING: (
                f"Missing mapping between workflow step and {module} "
                f"at tick {tick}"
            ),
            RootCauseType.WORKFLOW_DESIGN_FLAW: (
                f"Workflow design flaw in {module} workflow at tick {tick}"
            ),
            RootCauseType.DATA_INCONSISTENCY: (
                f"Data inconsistency detected in {module} at tick {tick}"
            ),
            RootCauseType.TIMING_DESYNC: (
                f"Timing desynchronization in {module} at tick {tick}"
            ),
            RootCauseType.UNKNOWN_CAUSE: (
                f"Insufficient evidence to classify mismatch in "
                f"{module} at tick {tick}"
            ),
        }
        return descriptions.get(
            primary,
            f"Unclassified cause in {module} at tick {tick}",
        )

    def get_classification(self, cause_id: str) -> Optional[RootCause]:
        return self._classifications.get(cause_id)

    @property
    def classification_count(self) -> int:
        return len(self._classifications)
