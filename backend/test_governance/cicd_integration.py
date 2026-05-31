"""
Section 9 — CI/CD Governance Integration.
Pipelines rules for blocking or allowing releases based on test governance.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from test_governance.confidence_engine import (
    ReleaseConfidenceEngine, ConfidenceResult, ConfidenceLevel,
)
from test_governance.weighted_coverage import CoverageResult, TIER_MINIMUMS, PathTier
from test_governance.coverage_policy import PolicyResult, evaluate_policy
from test_governance.regression_priority import REGRESSION_ENGINE


@dataclass
class PipelineDecision:
    action: str
    reason: str
    blocking: bool


class CICDGovernanceIntegration:

    def __init__(self):
        self._confidence = ReleaseConfidenceEngine()

    def evaluate_release(self,
                         coverage_result: CoverageResult,
                         executed_tests: set,
                         invariant_stable: bool = True,
                         replay_safe: bool = True,
                         migration_safe: bool = True,
                         ) -> Dict:
        policy_results = evaluate_policy(coverage_result)
        confidence = self._confidence.compute(
            coverage_result=coverage_result,
            policy_results=policy_results,
            executed_tests=executed_tests,
            invariant_stable=invariant_stable,
            replay_safe=replay_safe,
            migration_safe=migration_safe,
        )

        decisions = self._build_decisions(
            coverage_result, policy_results, confidence, executed_tests,
            replay_safe=replay_safe,
            migration_safe=migration_safe,
            invariant_stable=invariant_stable,
        )

        blocked = any(d.blocking for d in decisions)
        return {
            "confidence": {
                "level": confidence.level,
                "score": confidence.score,
                "summary": confidence.summary,
            },
            "blocked": blocked,
            "decisions": [
                {"action": d.action, "reason": d.reason, "blocking": d.blocking}
                for d in decisions
            ],
            "can_release": not blocked,
        }

    def _build_decisions(self,
                         coverage_result: CoverageResult,
                         policy_results: List[PolicyResult],
                         confidence: ConfidenceResult,
                         executed_tests: set,
                         replay_safe: bool = True,
                         migration_safe: bool = True,
                         invariant_stable: bool = True,
                         ) -> List[PipelineDecision]:
        decisions = []

        # Critical coverage gate
        if coverage_result.critical_path_coverage < TIER_MINIMUMS[PathTier.CRITICAL]:
            decisions.append(PipelineDecision(
                "BLOCK", f"Critical coverage {coverage_result.critical_path_coverage}% < {TIER_MINIMUMS[PathTier.CRITICAL]}%",
                True,
            ))
        else:
            decisions.append(PipelineDecision(
                "PASS", f"Critical coverage {coverage_result.critical_path_coverage}% meets minimum", False,
            ))

        # Critical policy gate
        critical_failures = [r for r in policy_results if not r.passed and r.severity == "critical"]
        if critical_failures:
            for cf in critical_failures:
                decisions.append(PipelineDecision("BLOCK", cf.detail, True))

        # Regression protection gate
        reg_blocked, missing = REGRESSION_ENGINE.is_regression_blocked(executed_tests)
        if not reg_blocked:
            for d in missing:
                decisions.append(PipelineDecision(
                    "BLOCK", f"Critical regression domain '{d.name}' not tested", True,
                ))

        # Replay safety gate
        if not replay_safe:
            decisions.append(PipelineDecision("BLOCK", "Replay determinism check failed", True))

        # Migration safety gate
        if not migration_safe:
            decisions.append(PipelineDecision("BLOCK", "Migration safety check failed", True))

        # Invariant stability
        if not invariant_stable:
            decisions.append(PipelineDecision("BLOCK", "Invariant stability check failed", True))

        # Non-blocking warnings
        if confidence.level == ConfidenceLevel.LOW:
            decisions.append(PipelineDecision(
                "WARN", "Release confidence is LOW — review before deploy", False,
            ))

        # Policy warnings
        warnings = [r for r in policy_results if not r.passed and r.severity != "critical"]
        for w in warnings:
            decisions.append(PipelineDecision("WARN", w.detail, False))

        return decisions


def build_test_set_from_plan(plan) -> List[str]:
    """Build test file list from CI build plan."""
    return plan.validation_suites
