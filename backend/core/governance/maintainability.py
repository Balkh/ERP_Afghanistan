"""
Phase 6 — Operational Maintainability Governance.
Technical debt classification, change risk evaluation, architecture freeze,
and operational drift detection.
"""
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from core.governance.kernel import GovernanceKernel, PriorityTier

logger = logging.getLogger("erp.governance.maintainability")

MAINTAINABILITY_VERSION = "1.0.0"


@dataclass
class TechnicalDebtItem:
    debt_id: str
    category: str  # critical_runtime | governance | ui | advisory | isolated_legacy
    description: str
    severity: str  # critical | high | medium | low
    impact: str = ""
    recommendation: str = ""
    file_path: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class ChangeRiskAssessment:
    change_id: str = ""
    governance_impact: str = "none"  # none | low | medium | high | critical
    runtime_impact: str = "none"
    latency_impact: str = "none"
    memory_impact: str = "none"
    invariant_impact: str = "none"
    deployment_impact: str = "none"
    overall_risk: str = "low"  # low | medium | high | critical
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class OperationalDriftReport:
    drifting: bool
    config_drift: bool = False
    policy_drift: bool = False
    environment_drift: bool = False
    registry_drift: bool = False
    config_snapshot: Dict[str, str] = field(default_factory=dict)
    policy_snapshot: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class TechnicalDebtClassifier:
    """Classifies technical debt across critical, governance, UI, advisory, and legacy domains."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def classify_all(self) -> List[TechnicalDebtItem]:
        items = []

        # Critical runtime debt
        health = self._kernel.health()
        if health.get("audit_entries", 0) > 800:
            items.append(TechnicalDebtItem(
                debt_id="runtime.audit_near_capacity",
                category="critical_runtime",
                description="Audit log near capacity",
                severity="medium",
                impact="May lose audit trail data",
                recommendation="Increase audit_maxlen or archive entries",
            ))
        if health.get("failsafe_mode", False):
            items.append(TechnicalDebtItem(
                debt_id="runtime.failsafe_active",
                category="critical_runtime",
                description="Governance running in failsafe mode",
                severity="high",
                impact="Low-priority enforcement bypassed",
                recommendation="Investigate and resolve root cause, then disable failsafe",
            ))

        # Governance debt
        if health.get("policies", 0) < 4:
            items.append(TechnicalDebtItem(
                debt_id="governance.insufficient_policies",
                category="governance",
                description="Not all expected policies registered",
                severity="critical",
                impact="Incomplete governance coverage",
                recommendation="Register all 4+ enforcement policies",
            ))
        if health.get("degraded_tiers", []):
            items.append(TechnicalDebtItem(
                debt_id="governance.degraded_tiers",
                category="governance",
                description="Governance tiers are degraded",
                severity="high",
                impact="Some enforcement levels bypassed",
                recommendation="Restore degraded tiers",
            ))

        # UI debt
        items.append(TechnicalDebtItem(
            debt_id="ui.legacy_violations",
            category="ui",
            description="UI governance scanning may detect legacy violations",
            severity="medium",
            impact="Non-standard UI components may exist",
            recommendation="Run UI governance scanner and address violations",
        ))

        # Advisory debt
        items.append(TechnicalDebtItem(
            debt_id="advisory.documentation_gaps",
            category="advisory",
            description="Operational documentation may have gaps",
            severity="low",
            impact="Knowledge transfer risk",
            recommendation="Review and update operational documentation",
        ))

        # Isolated legacy
        try:
            from django.db.migrations.executor import MigrationExecutor
            from django.db import connections
            executor = MigrationExecutor(connections["default"])
            pending = len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
            if pending > 0:
                items.append(TechnicalDebtItem(
                    debt_id="legacy.pending_migrations",
                    category="isolated_legacy",
                    description=f"{pending} pending migration(s)",
                    severity="high",
                    impact="Schema drift between environments",
                    recommendation="Apply pending migrations",
                ))
        except Exception:
            pass

        return items


class ChangeRiskEngine:
    """Evaluates risk of changes before they are deployed."""

    ASSESSMENT_FIELDS = [
        "governance_impact", "runtime_impact", "latency_impact",
        "memory_impact", "invariant_impact", "deployment_impact",
    ]
    RISK_WEIGHTS = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def assess(self, change_id: str = "", **impacts: str) -> ChangeRiskAssessment:
        assessment = ChangeRiskAssessment(change_id=change_id or uuid.uuid4().hex[:8])
        for field in self.ASSESSMENT_FIELDS:
            value = impacts.get(field, "none")
            setattr(assessment, field, value)

        total_weight = sum(
            self.RISK_WEIGHTS.get(getattr(assessment, f, "none"), 0)
            for f in self.ASSESSMENT_FIELDS
        )
        max_weight = len(self.ASSESSMENT_FIELDS) * 4
        if max_weight == 0:
            return assessment

        risk_pct = total_weight / max_weight
        if risk_pct >= 0.7:
            assessment.overall_risk = "critical"
        elif risk_pct >= 0.5:
            assessment.overall_risk = "high"
        elif risk_pct >= 0.3:
            assessment.overall_risk = "medium"
        else:
            assessment.overall_risk = "low"

        if assessment.overall_risk in ("high", "critical"):
            assessment.recommendations.append("Requires governance review before deployment")
        if assessment.invariant_impact in ("high", "critical"):
            assessment.recommendations.append("Run full invariant scan before and after change")
        if assessment.deployment_impact in ("high", "critical"):
            assessment.recommendations.append("Schedule deployment during maintenance window")

        return assessment


class ArchitectureFreezeEnforcer:
    """Enforces architecture discipline — requires justification for new layers."""

    FORBIDDEN_PATTERNS = [
        "new_governance_layer",
        "new_event_system",
        "new_background_service",
        "new_observability_hook",
    ]

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def requires_justification(self, change_type: str) -> bool:
        return change_type in self.FORBIDDEN_PATTERNS

    def validate(self, change_type: str, justification: str = "") -> Tuple[bool, str]:
        if not self.requires_justification(change_type):
            return True, f"Change type '{change_type}' does not require justification"
        if not justification or len(justification.strip()) < 20:
            return False, (
                f"Architecture freeze: '{change_type}' requires detailed justification "
                f"(min 20 characters)"
            )
        return True, f"Change type '{change_type}' approved with justification"


class OperationalDriftDetector:
    """Detects configuration, policy, environment, and registry drift."""

    def __init__(self):
        self._config_snapshot: Dict[str, str] = {}
        self._policy_snapshot: Dict[str, str] = {}

    def take_config_snapshot(self) -> Dict[str, str]:
        snapshot = {}
        try:
            from django.conf import settings
            snapshot["debug"] = str(getattr(settings, "DEBUG", ""))
            snapshot["ssl"] = str(getattr(settings, "SECURE_SSL_REDIRECT", ""))
            snapshot["db_engine"] = str(getattr(settings, "DATABASES", {}).get("default", {}).get("ENGINE", ""))
            snapshot["timezone"] = str(getattr(settings, "TIME_ZONE", ""))
        except Exception:
            pass
        self._config_snapshot = snapshot
        return snapshot

    def take_policy_snapshot(self, kernel: GovernanceKernel) -> Dict[str, str]:
        snapshot = {}
        for pid, (rule, meta) in kernel.policies.list_all().items():
            snapshot[pid] = f"tier={rule.tier}|domain={meta.get('domain', '')}"
        self._policy_snapshot = snapshot
        return snapshot

    def detect_config_drift(self, kernel: GovernanceKernel) -> bool:
        current = {}
        try:
            from django.conf import settings
            current["debug"] = str(getattr(settings, "DEBUG", ""))
            current["ssl"] = str(getattr(settings, "SECURE_SSL_REDIRECT", ""))
        except Exception:
            return False
        if not self._config_snapshot:
            return False
        for key, val in current.items():
            if self._config_snapshot.get(key) != val:
                return True
        return False

    def detect_policy_drift(self, kernel: GovernanceKernel) -> bool:
        current = {}
        for pid, (rule, meta) in kernel.policies.list_all().items():
            current[pid] = f"tier={rule.tier}|domain={meta.get('domain', '')}"
        if not self._policy_snapshot:
            return False
        return current != self._policy_snapshot

    def detect_environment_drift(self, kernel: GovernanceKernel) -> bool:
        profile = kernel.environment.profile
        expected = os.environ.get("EXPECTED_ENV", profile)
        return profile != expected

    def detect_registry_drift(self, kernel: GovernanceKernel) -> bool:
        registries = [
            ("policies", kernel.policies.count()),
            ("invariants", kernel.invariants.count()),
            ("feature_gates", kernel.feature_gates.count()),
        ]
        # If any registry has 0 entries when it shouldn't
        for name, count in registries:
            if count == 0 and name not in ("feature_gates",):
                return True
        return False

    def run(self, kernel: GovernanceKernel) -> OperationalDriftReport:
        config_drift = self.detect_config_drift(kernel)
        policy_drift = self.detect_policy_drift(kernel)
        env_drift = self.detect_environment_drift(kernel)
        registry_drift = self.detect_registry_drift(kernel)

        warnings = []
        if config_drift:
            warnings.append("Configuration drift detected — settings may have changed")
        if policy_drift:
            warnings.append("Policy drift detected — governance rules may have changed")
        if env_drift:
            warnings.append("Environment drift detected — profile mismatch")
        if registry_drift:
            warnings.append("Registry drift detected — missing entries")

        return OperationalDriftReport(
            drifting=config_drift or policy_drift or env_drift or registry_drift,
            config_drift=config_drift,
            policy_drift=policy_drift,
            environment_drift=env_drift,
            registry_drift=registry_drift,
            config_snapshot=self._config_snapshot,
            policy_snapshot=self._policy_snapshot,
            warnings=warnings,
        )


import uuid
