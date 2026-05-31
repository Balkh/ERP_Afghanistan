"""
Section 7 — Risk Engine & Release Assessment.
Evaluates risk levels for changes based on impact analysis.
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime


class RiskLevel:
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RiskFactor:
    category: str
    severity: str
    description: str
    weight: float = 1.0


@dataclass
class RiskAssessment:
    score: float
    level: str
    factors: List[RiskFactor]
    recommended_action: str
    timestamp: str

    @classmethod
    def from_factors(cls, factors: List[RiskFactor]) -> "RiskAssessment":
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 0.5}
        total = sum(weights.get(f.severity, 1) * f.weight for f in factors)
        score = min(total / max(len(factors), 1), 10)
        if score >= 8:
            level = RiskLevel.CRITICAL
            action = "BLOCK release until all critical/high risks mitigated"
        elif score >= 5:
            level = RiskLevel.HIGH
            action = "Requires manual review before release"
        elif score >= 2:
            level = RiskLevel.MEDIUM
            action = "Document risks; proceed with caution"
        else:
            level = RiskLevel.LOW
            action = "Safe to release"
        return cls(
            score=round(score, 2),
            level=level,
            factors=factors,
            recommended_action=action,
            timestamp=datetime.utcnow().isoformat(),
        )


def assess_change_risk(
    modified_modules: Set[str],
    has_migrations: bool,
    has_model_changes: bool,
    has_api_changes: bool,
    has_task_changes: bool,
) -> RiskAssessment:
    factors = []

    if has_migrations:
        factors.append(RiskFactor("migration", RiskLevel.HIGH, "Database migration present", 2.0))
    if has_model_changes:
        factors.append(RiskFactor("model", RiskLevel.HIGH, "Model changes", 1.5))
    if has_api_changes:
        factors.append(RiskFactor("api", RiskLevel.HIGH, "API contract changes", 1.5))
    if has_task_changes:
        factors.append(RiskFactor("task", RiskLevel.MEDIUM, "Background task changes", 1.0))

    if "accounting" in modified_modules:
        factors.append(RiskFactor("module", RiskLevel.HIGH, "Accounting module modified", 1.5))
    if "inventory" in modified_modules:
        factors.append(RiskFactor("module", RiskLevel.HIGH, "Inventory module modified", 1.5))
    if "sales" in modified_modules or "purchases" in modified_modules:
        factors.append(RiskFactor("module", RiskLevel.MEDIUM, "Transaction module modified"))
    if "core" in modified_modules:
        factors.append(RiskFactor("module", RiskLevel.CRITICAL, "Core infrastructure modified", 2.0))
    if "payments" in modified_modules:
        factors.append(RiskFactor("module", RiskLevel.HIGH, "Payment engine modified", 1.5))
    if "governance" in modified_modules:
        factors.append(RiskFactor("module", RiskLevel.MEDIUM, "Governance layer modified"))

    if not factors:
        factors.append(RiskFactor("default", RiskLevel.LOW, "No risk factors identified"))

    return RiskAssessment.from_factors(factors)
