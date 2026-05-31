"""
Phase 2 — Risk-Weighted Coverage Engine.
Extends test_governance/weighted_coverage.py with workflow/failure/test-quality weighting.
"""

import json
import os
from typing import Dict, List, Optional, Set

from test_governance.weighted_coverage import WeightedCoverageEngine as BaseWeightedEngine
from test_governance.weighted_coverage import CoverageResult, ModuleCoverage

from coverage_governance.module_classifier import (
    TIER_WEIGHTS, TIER_MINIMUMS, classify_module,
)
from coverage_governance.models import RiskWeightedCoverageResult, ModuleCoverageDetail


class RiskWeightedCoverageEngine(BaseWeightedEngine):
    """Extends base weighted engine with workflow/failure/test-quality multipliers."""

    def compute_risk_weighted(
        self,
        coverage_data: Dict,
        workflow_scores: Optional[Dict[str, float]] = None,
        failure_scores: Optional[Dict[str, float]] = None,
        test_quality_scores: Optional[Dict[str, float]] = None,
    ) -> RiskWeightedCoverageResult:
        workflow_scores = workflow_scores or {}
        failure_scores = failure_scores or {}
        test_quality_scores = test_quality_scores or {}

        base_result = self.compute(coverage_data)

        module_details = []
        total_weighted = 0.0
        total_weights = 0.0
        critical_pct_sum = 0.0
        critical_count = 0

        for mc in base_result.module_results:
            module_name = mc.name
            tier = classify_module(module_name)
            weight = TIER_WEIGHTS.get(tier, 1.0)
            minimum = TIER_MINIMUMS.get(tier, 0.0)

            wf = workflow_scores.get(module_name)
            ff = failure_scores.get(module_name)
            tq = test_quality_scores.get(module_name)

            meets = mc.coverage_pct >= minimum

            module_details.append(ModuleCoverageDetail(
                name=module_name,
                tier=tier,
                raw_coverage=mc.coverage_pct,
                weighted_coverage=mc.weighted_pct,
                meets_minimum=meets,
                workflow_coverage=wf,
                failure_coverage=ff,
                test_quality_score=tq,
            ))

            total_weighted += mc.weighted_pct
            total_weights += mc.weight

            if tier == "CRITICAL":
                critical_pct_sum += mc.coverage_pct
                critical_count += 1

        weighted_op = (total_weighted / total_weights) if total_weights > 0 else 0.0
        critical_path = (critical_pct_sum / critical_count) if critical_count > 0 else 0.0

        risk_adjusted = (
            weighted_op * 0.5
            + critical_path * 0.3
        )

        if workflow_scores:
            avg_wf = sum(workflow_scores.values()) / len(workflow_scores)
            risk_adjusted = risk_adjusted * 0.7 + avg_wf * 0.15

        if failure_scores:
            avg_ff = sum(failure_scores.values()) / len(failure_scores)
            risk_adjusted = risk_adjusted * 0.85 + avg_ff * 0.075

        if test_quality_scores:
            avg_tq = sum(test_quality_scores.values()) / len(test_quality_scores)
            risk_adjusted = risk_adjusted * 0.925 + avg_tq * 0.0375

        tier_breakdown = base_result.tier_breakdown

        return RiskWeightedCoverageResult(
            global_raw_coverage=base_result.raw_coverage,
            weighted_operational_coverage=round(weighted_op, 2),
            critical_path_coverage=round(critical_path, 2),
            risk_adjusted_score=round(risk_adjusted, 2),
            modules=module_details,
            tier_breakdown=tier_breakdown,
        )
