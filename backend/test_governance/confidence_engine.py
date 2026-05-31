"""
Section 7 — Release Confidence Engine.
Computes release confidence based on multiple weighted signals.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from test_governance.weighted_coverage import CoverageResult, TIER_MINIMUMS, PathTier
from test_governance.coverage_policy import PolicyResult, evaluate_policy
from test_governance.regression_priority import REGRESSION_ENGINE


class ConfidenceLevel:
    LOW = "LOW_CONFIDENCE"
    MEDIUM = "MEDIUM_CONFIDENCE"
    HIGH = "HIGH_CONFIDENCE"
    ENTERPRISE_SAFE = "ENTERPRISE_SAFE"


CONFIDENCE_THRESHOLDS = {
    ConfidenceLevel.ENTERPRISE_SAFE: 90.0,
    ConfidenceLevel.HIGH: 75.0,
    ConfidenceLevel.MEDIUM: 55.0,
}


@dataclass
class ConfidenceResult:
    level: str
    score: float
    signals: Dict[str, float]
    blocking_issues: List[str]
    summary: str


class ReleaseConfidenceEngine:

    def compute(self,
                coverage_result: CoverageResult,
                policy_results: List[PolicyResult],
                executed_tests: Optional[set] = None,
                invariant_stable: bool = True,
                replay_safe: bool = True,
                migration_safe: bool = True,
                ) -> ConfidenceResult:
        signals = {}
        blocking_issues = []

        # Signal 1: Weighted coverage score
        weighted = coverage_result.weighted_coverage
        signals["weighted_coverage"] = weighted

        # Signal 2: Critical path coverage
        critical = coverage_result.critical_path_coverage
        signals["critical_path_coverage"] = critical

        # Signal 3: Risk-adjusted score
        risk = coverage_result.risk_adjusted_score
        signals["risk_adjusted_score"] = risk

        # Signal 4: Policy compliance
        blocking = [r for r in policy_results if not r.passed and r.severity == "critical"]
        policy_score = 100.0 if not blocking else max(0, 100 - len(blocking) * 20)
        signals["policy_compliance"] = policy_score
        if blocking:
            blocking_issues.extend(r.detail for r in blocking)

        # Signal 5: Invariant stability
        signals["invariant_stability"] = 100.0 if invariant_stable else 30.0
        if not invariant_stable:
            blocking_issues.append("Invariant stability check failed")

        # Signal 6: Replay safety
        signals["replay_safety"] = 100.0 if replay_safe else 20.0
        if not replay_safe:
            blocking_issues.append("Replay determinism check failed")

        # Signal 7: Migration safety
        signals["migration_safety"] = 100.0 if migration_safe else 20.0
        if not migration_safe:
            blocking_issues.append("Migration safety check failed")

        # Signal 8: Regression protection
        if executed_tests is not None:
            blocked, missing = REGRESSION_ENGINE.is_regression_blocked(executed_tests)
            reg_score = 100.0 if blocked else max(0, 100 - len(missing) * 15)
            signals["regression_protection"] = reg_score
            if not blocked:
                for d in missing:
                    blocking_issues.append(f"Regression domain '{d.name}' not covered")
        else:
            signals["regression_protection"] = 50.0

        # Composite score
        weights = {
            "weighted_coverage": 0.15,
            "critical_path_coverage": 0.20,
            "risk_adjusted_score": 0.10,
            "policy_compliance": 0.15,
            "invariant_stability": 0.15,
            "replay_safety": 0.10,
            "migration_safety": 0.10,
            "regression_protection": 0.05,
        }

        score = sum(signals[k] * weights[k] for k in weights if k in signals)

        # Apply penalties for blocking issues
        penalty = len(blocking_issues) * 5.0
        score = max(0, score - penalty)

        # Determine level
        if score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.ENTERPRISE_SAFE] and not blocking_issues:
            level = ConfidenceLevel.ENTERPRISE_SAFE
            summary = "Enterprise-safe release — all critical protections active"
        elif score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.HIGH]:
            level = ConfidenceLevel.HIGH
            summary = "High confidence — minor non-blocking issues"
        elif score >= CONFIDENCE_THRESHOLDS[ConfidenceLevel.MEDIUM]:
            level = ConfidenceLevel.MEDIUM
            summary = "Medium confidence — review blocking issues before release"
        else:
            level = ConfidenceLevel.LOW
            summary = "Low confidence — DO NOT release without remediation"

        return ConfidenceResult(
            level=level,
            score=round(score, 2),
            signals=signals,
            blocking_issues=blocking_issues,
            summary=summary,
        )
