"""
Task 5: RootCauseExplainer — Deterministic explanation generation.
Output must reference real events. No generic or fabricated explanations.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from simulation.truth_engine.root_cause.models import (
    RootCause, RootCauseType, CausalChain, Explanation,
)


logger = logging.getLogger('erp.simulation.truth.root_cause.explainer')


class RootCauseExplainer:
    """
    Generates structured explanations for mismatches.
    Deterministic output only. Must reference real logged events.
    """

    def __init__(self):
        self._explanations: Dict[str, Explanation] = {}

    def explain(
        self,
        mismatch_id: str,
        mismatch_type: str,
        mismatch_description: str,
        affected_module: str,
        tick: int,
        root_cause: RootCause,
        causal_chain: CausalChain,
    ) -> Explanation:
        explanation_id = f"expl_{mismatch_id}"
        problem = self._build_problem_summary(
            mismatch_type, affected_module, mismatch_description
        )
        chains = self._build_root_cause_chain(
            mismatch_type, root_cause, causal_chain
        )
        evidence = self._build_evidence_list(
            mismatch_type, root_cause, causal_chain
        )
        recommendation = self._build_recommendation(
            root_cause.primary_type, affected_module
        )
        explanation = Explanation(
            explanation_id=explanation_id,
            mismatch_id=mismatch_id,
            problem_summary=problem,
            root_cause_chain=chains,
            confidence=root_cause.confidence,
            evidence=evidence,
            recommendation=recommendation,
            generated_at=datetime.now(),
        )
        self._explanations[explanation_id] = explanation
        return explanation

    def _build_problem_summary(
        self, mtype: str, module: str, desc: str,
    ) -> str:
        label = mtype.replace('_', ' ').title()
        return f"{label} in {module}: {desc}"

    def _build_root_cause_chain(
        self, mtype: str, cause: RootCause, chain: CausalChain,
    ) -> List[str]:
        steps = []
        for link in chain.links:
            steps.append(
                f"{link.source_type.value} '{link.source_id}' "
                f"{link.edge_type.value} "
                f"{link.target_type.value} '{link.target_id}'"
            )
        steps.append(
            f"Primary cause: {cause.primary_type.value} "
            f"(confidence: {cause.confidence}%)"
        )
        for sec in cause.secondary_types:
            steps.append(f"Secondary factor: {sec.value}")
        return steps

    def _build_evidence_list(
        self, mtype: str, cause: RootCause, chain: CausalChain,
    ) -> List[str]:
        evidence = []
        for link in chain.links:
            meta = link.metadata
            if 'event_type' in meta:
                evidence.append(
                    f"Event '{meta['event_type']}' at "
                    f"{meta.get('event_timestamp', 'unknown')}"
                )
        evidence.extend([
            f"Root cause classification: {cause.primary_type.value}",
            f"Confidence score: {cause.confidence}%",
        ])
        return evidence

    def _build_recommendation(
        self, cause_type: RootCauseType, module: str,
    ) -> str:
        recs = {
            RootCauseType.LOGIC_ERROR: (
                f"Review business logic in {module} for correctness"
            ),
            RootCauseType.CONCURRENCY_ISSUE: (
                f"Add locking or serialization for {module} operations"
            ),
            RootCauseType.MISSING_MAPPING: (
                f"Verify workflow-to-{module} mapping configuration"
            ),
            RootCauseType.WORKFLOW_DESIGN_FLAW: (
                f"Redesign {module} workflow to handle edge cases"
            ),
            RootCauseType.DATA_INCONSISTENCY: (
                f"Validate data integrity constraints in {module}"
            ),
            RootCauseType.TIMING_DESYNC: (
                f"Adjust timing parameters for {module} synchronization"
            ),
            RootCauseType.UNKNOWN_CAUSE: (
                f"Gather more data to classify {module} mismatch"
            ),
        }
        return recs.get(cause_type, f"Investigate {module} further")

    def get_explanation(
        self, explanation_id: str,
    ) -> Optional[Explanation]:
        return self._explanations.get(explanation_id)

    @property
    def explanation_count(self) -> int:
        return len(self._explanations)
