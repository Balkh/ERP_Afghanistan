"""
Phase 5 — DriftPreventionLayer.
Prevents operational drift before it becomes system instability.
Threshold enforcement, auto-safe response (log + alert only, never auto-rewrite),
and escalation policy. Fail-safe.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.control_plane.drift_prevention")

DRIFT_THRESHOLDS = {
    "config_drift": 1,
    "policy_drift": 1,
    "environment_drift": 1,
    "registry_drift": 1,
}


class DriftEscalationLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftAlert:
    drift_type: str
    level: DriftEscalationLevel
    message: str
    detail: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class DriftPreventionReport:
    alerts: List[DriftAlert] = field(default_factory=list)
    drift_detected: bool = False
    blocked_deployment: bool = False
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


_ESCALATION_MAP: Dict[str, DriftEscalationLevel] = {
    "config_drift": DriftEscalationLevel.HIGH,
    "policy_drift": DriftEscalationLevel.CRITICAL,
    "environment_drift": DriftEscalationLevel.HIGH,
    "registry_drift": DriftEscalationLevel.MEDIUM,
}

_ESCALATION_BLOCK: Dict[DriftEscalationLevel, bool] = {
    DriftEscalationLevel.LOW: False,
    DriftEscalationLevel.MEDIUM: False,
    DriftEscalationLevel.HIGH: True,
    DriftEscalationLevel.CRITICAL: True,
}

_SUGGESTION_MAP: Dict[str, str] = {
    "config_drift": "Review django settings against baseline snapshot. No auto-rewrite.",
    "policy_drift": "Review governance policies. Re-register expected policies if needed.",
    "environment_drift": "Check EXPECTED_ENV environment variable. May indicate deployment mismatch.",
    "registry_drift": "Check governance registries. Some may have been cleared unexpectedly.",
}


class DriftPreventionLayer:
    """
    Detects and prevents operational drift.
    - Threshold enforcement: config, policy, environment, registry
    - Auto-safe response: log + alert only, never auto-rewrite
    - Escalation policy: LOW→MEDIUM→HIGH→CRITICAL
    - HIGH/CRITICAL blocks deployment
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()
        self._previous_report: Optional[DriftPreventionReport] = None

    def check(self) -> DriftPreventionReport:
        alerts = []
        warnings = []
        suggestions = []
        drift_detected = False

        try:
            from core.governance.maintainability import OperationalDriftDetector
            odd = OperationalDriftDetector()
            odd.take_config_snapshot()
            odd.take_policy_snapshot(self._kernel)
            drift = odd.run(self._kernel)
        except Exception as e:
            return DriftPreventionReport(
                warnings=[f"Drift detection error: {e}"],
            )

        drift_types = {
            "config_drift": drift.config_drift,
            "policy_drift": drift.policy_drift,
            "environment_drift": drift.environment_drift,
            "registry_drift": drift.registry_drift,
        }

        for drift_type, detected in drift_types.items():
            if not detected:
                continue
            drift_detected = True
            level = _ESCALATION_MAP.get(drift_type, DriftEscalationLevel.MEDIUM)
            suggestion = _SUGGESTION_MAP.get(drift_type, "Investigate and resolve drift source.")
            suggestions.append(suggestion)

            alert = DriftAlert(
                drift_type=drift_type,
                level=level,
                message=f"Drift detected: {drift_type}",
                detail=f"Escalation: {level.value}",
            )
            alerts.append(alert)
            warnings.append(f"{drift_type} — {level.value} severity")

        blocked = any(
            alert.level in (DriftEscalationLevel.HIGH, DriftEscalationLevel.CRITICAL)
            for alert in alerts
        )

        report = DriftPreventionReport(
            alerts=alerts,
            drift_detected=drift_detected,
            blocked_deployment=blocked,
            warnings=warnings,
            suggestions=suggestions,
        )
        self._previous_report = report
        return report

    def should_block_deployment(self) -> Tuple[bool, List[str]]:
        report = self.check()
        if report.blocked_deployment:
            reasons = [
                f"{a.drift_type} ({a.level.value})" for a in report.alerts
                if a.level in (DriftEscalationLevel.HIGH, DriftEscalationLevel.CRITICAL)
            ]
            return True, reasons
        return False, []

    def get_last_report(self) -> Optional[DriftPreventionReport]:
        return self._previous_report
