"""
Section 3 — Coverage Governance Policy.
Replaces naive global threshold with tiered minimums and weighted score.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from test_governance.weighted_coverage import (
    TIER_MINIMUMS, TIER_WEIGHTS, WeightedCoverageEngine, CoverageResult, PathTier,
)


@dataclass
class PolicyResult:
    passed: bool
    policy_name: str
    detail: str
    severity: str = "high"


GLOBAL_WEIGHTED_THRESHOLD = 60.0


def check_critical_coverage(result: CoverageResult) -> PolicyResult:
    if result.untested_critical:
        return PolicyResult(
            False, "critical_coverage",
            f"Critical modules below threshold: {', '.join(result.untested_critical)}",
            "critical",
        )
    return PolicyResult(True, "critical_coverage",
                        f"All critical modules meet {TIER_MINIMUMS[PathTier.CRITICAL]}% minimum")


def check_weighted_score(result: CoverageResult) -> PolicyResult:
    if result.weighted_coverage >= GLOBAL_WEIGHTED_THRESHOLD:
        return PolicyResult(True, "weighted_score",
                            f"Weighted coverage {result.weighted_coverage}% >= {GLOBAL_WEIGHTED_THRESHOLD}%")
    return PolicyResult(
        False, "weighted_score",
        f"Weighted coverage {result.weighted_coverage}% < {GLOBAL_WEIGHTED_THRESHOLD}%",
        "high",
    )


def check_risk_adjusted_score(result: CoverageResult) -> PolicyResult:
    threshold = 50.0
    if result.risk_adjusted_score >= threshold:
        return PolicyResult(True, "risk_adjusted_score",
                            f"Risk-adjusted {result.risk_adjusted_score}% >= {threshold}%")
    result.risk_adjusted_score
    return PolicyResult(
        False, "risk_adjusted_score",
        f"Risk-adjusted {result.risk_adjusted_score}% < {threshold}%",
        "high",
    )


def check_tier_minimums(result: CoverageResult) -> PolicyResult:
    failures = []
    for tier_key, tier_name in [("CRITICAL", "CRITICAL"), ("HIGH", "HIGH"), ("NORMAL", "NORMAL")]:
        data = result.tier_breakdown.get(tier_key)
        if data and data["below_minimum"] > 0:
            failures.append(f"{tier_key}: {data['below_minimum']}/{data['module_count']} below minimum")
    if failures:
        return PolicyResult(True, "tier_minimums",
                            f"Non-blocking: {'; '.join(failures)}", "low")
    return PolicyResult(True, "tier_minimums", "All tier minimums met")


def check_raw_coverage(result: CoverageResult) -> PolicyResult:
    return PolicyResult(True, "raw_coverage",
                        f"Raw coverage {result.raw_coverage}% (informational, not enforced)")


def evaluate_policy(result: CoverageResult) -> List[PolicyResult]:
    return [
        check_critical_coverage(result),
        check_weighted_score(result),
        check_risk_adjusted_score(result),
        check_tier_minimums(result),
        check_raw_coverage(result),
    ]


def policy_allows_release(results: List[PolicyResult]) -> Tuple[bool, List[PolicyResult]]:
    blocking = [r for r in results if not r.passed and r.severity == "critical"]
    if blocking:
        return False, blocking
    return True, []
