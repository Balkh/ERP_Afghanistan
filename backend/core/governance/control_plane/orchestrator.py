"""
Phase 1 — ControlPlaneOrchestrator.
Coordinates existing deployment, recovery, drift, health, and governance systems.
Lightweight orchestration only — no duplicate logic.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.control_plane.orchestrator")


@dataclass
class OrchestrationResult:
    operation: str
    success: bool
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class ControlPlaneOrchestrator:
    """
    Single entry point for all control plane operations.
    Orchestrates existing systems — never duplicates logic.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def run_deployment_readiness(self) -> OrchestrationResult:
        start = time.time()
        try:
            from core.governance.deployment import DeploymentValidator
            dv = DeploymentValidator(self._kernel)
            report = dv.run_all()
            return OrchestrationResult(
                operation="deployment_readiness",
                success=report.overall != "blocked",
                summary={
                    "overall": report.overall,
                    "blockers": report.blockers,
                    "warnings": report.warnings,
                    "operational_risk": report.operational_risk,
                    "check_count": len(report.checks),
                },
                warnings=report.warnings,
                errors=report.blockers,
                duration_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return OrchestrationResult(
                operation="deployment_readiness", success=False,
                errors=[str(e)],
                duration_ms=round((time.time() - start) * 1000, 1),
            )

    def run_drift_detection(self) -> OrchestrationResult:
        start = time.time()
        try:
            from core.governance.maintainability import OperationalDriftDetector
            odd = OperationalDriftDetector()
            odd.take_config_snapshot()
            odd.take_policy_snapshot(self._kernel)
            drift = odd.run(self._kernel)
            return OrchestrationResult(
                operation="drift_detection",
                success=not drift.drifting,
                summary={
                    "drifting": drift.drifting,
                    "config_drift": drift.config_drift,
                    "policy_drift": drift.policy_drift,
                    "environment_drift": drift.environment_drift,
                    "registry_drift": drift.registry_drift,
                },
                warnings=drift.warnings,
                duration_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return OrchestrationResult(
                operation="drift_detection", success=False,
                errors=[str(e)],
                duration_ms=round((time.time() - start) * 1000, 1),
            )

    def run_health_check(self) -> OrchestrationResult:
        start = time.time()
        try:
            from core.governance.observability import OperationalHealthDashboard
            ohd = OperationalHealthDashboard(self._kernel)
            health = ohd.get_health()
            return OrchestrationResult(
                operation="health_check",
                success=health.overall != "critical",
                summary={
                    "overall": health.overall,
                    "score": health.score,
                    "governance": health.governance,
                    "invariants": health.invariants,
                    "deployment": health.deployment,
                    "memory": health.memory,
                    "latency": health.latency,
                    "recovery": health.recovery,
                },
                warnings=health.warnings,
                duration_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return OrchestrationResult(
                operation="health_check", success=False,
                errors=[str(e)],
                duration_ms=round((time.time() - start) * 1000, 1),
            )

    def run_recovery_readiness(self) -> OrchestrationResult:
        start = time.time()
        try:
            from core.governance.backup_recovery import RecoveryReadinessAssessor
            ra = RecoveryReadinessAssessor(self._kernel)
            score = ra.assess()
            return OrchestrationResult(
                operation="recovery_readiness",
                success=score.overall_score >= 50,
                summary={
                    "overall_score": score.overall_score,
                    "backup_exists": score.backup_exists,
                    "backup_validated": score.backup_validated,
                    "restore_tested": score.restore_tested,
                    "governance_recoverable": score.governance_recoverable,
                    "accounting_recoverable": score.accounting_recoverable,
                },
                warnings=score.warnings,
                duration_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return OrchestrationResult(
                operation="recovery_readiness", success=False,
                errors=[str(e)],
                duration_ms=round((time.time() - start) * 1000, 1),
            )

    def run_governance_check(self) -> OrchestrationResult:
        start = time.time()
        try:
            health = self._kernel.health()
            failsafe = health.get("failsafe_mode", False)
            degraded = health.get("degraded_tiers", [])
            policies = health.get("policies", 0)
            invariants = health.get("invariants", 0)
            warnings = []
            if failsafe:
                warnings.append("Governance in failsafe mode")
            if degraded:
                warnings.append(f"Degraded tiers: {degraded}")
            if policies < 4:
                warnings.append(f"Only {policies} policies registered (expected 4+)")
            return OrchestrationResult(
                operation="governance_check",
                success=not failsafe and not degraded and policies >= 4,
                summary={
                    "initialized": health.get("initialized", False),
                    "policies": policies,
                    "invariants": invariants,
                    "failsafe": failsafe,
                    "degraded_tiers": degraded,
                    "audit_entries": health.get("audit_entries", 0),
                },
                warnings=warnings,
                duration_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return OrchestrationResult(
                operation="governance_check", success=False,
                errors=[str(e)],
                duration_ms=round((time.time() - start) * 1000, 1),
            )

    def run_full_certification(self, soak_iterations: int = 50) -> OrchestrationResult:
        start = time.time()
        try:
            from core.governance.operational_certification import (
                OperationalCertificationOrchestrator,
            )
            orch = OperationalCertificationOrchestrator(self._kernel)
            report = orch.certify_all(soak_iterations=soak_iterations)
            return OrchestrationResult(
                operation="full_certification",
                success=report.overall_passed,
                summary={
                    "overall_passed": report.overall_passed,
                    "overall_score": report.overall_score,
                    "phases_passed": sum(1 for p in report.phases if p.passed),
                    "phases_total": len(report.phases),
                    "phases": [
                        {
                            "phase": p.phase,
                            "name": p.name,
                            "passed": p.passed,
                            "score": p.score,
                        }
                        for p in report.phases
                    ],
                },
                warnings=report.warnings,
                errors=report.errors,
                duration_ms=round((time.time() - start) * 1000, 1),
            )
        except Exception as e:
            return OrchestrationResult(
                operation="full_certification", success=False,
                errors=[str(e)],
                duration_ms=round((time.time() - start) * 1000, 1),
            )

    def run_all_checks(self) -> Dict[str, OrchestrationResult]:
        return {
            "deployment": self.run_deployment_readiness(),
            "drift": self.run_drift_detection(),
            "health": self.run_health_check(),
            "recovery": self.run_recovery_readiness(),
            "governance": self.run_governance_check(),
        }
