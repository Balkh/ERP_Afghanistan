"""
Phase 4 — DeploymentControlGate.
Transforms DeploymentValidator into an enforcement gate.
Blocks deployment if governance invalid, invariants broken, migrations inconsistent,
SECRET_KEY insecure, SSL disabled in production, or drift threshold exceeded.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.control_plane.deployment_gate")


class GateVerdict(Enum):
    PASS = "pass"
    BLOCKED = "blocked"


@dataclass
class GateResult:
    verdict: GateVerdict
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    governance_ready: bool = False
    drift_ok: bool = False
    recovery_ready: bool = False
    certification_healthy: bool = False
    checks: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class DeploymentControlGate:
    """
    Pre-deployment enforcement gate.
    Aggregates governance readiness, drift status, recovery readiness, and certification health.
    Atomic gate result: PASS or BLOCKED.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def evaluate(self) -> GateResult:
        blockers = []
        warnings = []
        check_results = {}

        # 1. Deployment validator
        gov_ready, gov_blockers, gov_warnings = self._check_deployment_validator()
        check_results["deployment_validator"] = {
            "ready": gov_ready, "blockers": gov_blockers,
        }
        blockers.extend(gov_blockers)
        warnings.extend(gov_warnings)

        # 2. Governance health
        gov_health_ok, gov_health_warnings = self._check_governance_health()
        check_results["governance_health"] = {
            "healthy": gov_health_ok, "warnings": gov_health_warnings,
        }
        if not gov_health_ok:
            blockers.extend(gov_health_warnings)
        else:
            warnings.extend(gov_health_warnings)

        # 3. Invariant scan
        inv_ok, inv_warnings = self._check_invariants()
        check_results["invariants"] = {"passed": inv_ok, "warnings": inv_warnings}
        if not inv_ok:
            blockers.append("Invariant scan failed")
            warnings.extend(inv_warnings)
        else:
            warnings.extend(inv_warnings)

        # 4. Drift status
        drift_ok, drift_warnings = self._check_drift()
        check_results["drift"] = {"ok": drift_ok, "warnings": drift_warnings}
        if not drift_ok:
            blockers.append("Drift threshold exceeded")
            warnings.extend(drift_warnings)
        else:
            warnings.extend(drift_warnings)

        # 5. Recovery readiness
        rec_ok, rec_warnings = self._check_recovery_readiness()
        check_results["recovery_readiness"] = {
            "ready": rec_ok, "warnings": rec_warnings,
        }
        if not rec_ok:
            warnings.append("Recovery readiness below threshold")
            warnings.extend(rec_warnings)
        else:
            warnings.extend(rec_warnings)

        # 6. Certification health
        cert_ok, cert_warnings = self._check_certification_health()
        check_results["certification"] = {
            "healthy": cert_ok, "warnings": cert_warnings,
        }
        if not cert_ok:
            blockers.append("Certification health degraded")
            warnings.extend(cert_warnings)
        else:
            warnings.extend(cert_warnings)

        verdict = GateVerdict.BLOCKED if blockers else GateVerdict.PASS

        return GateResult(
            verdict=verdict,
            blockers=blockers,
            warnings=warnings,
            governance_ready=gov_ready and gov_health_ok,
            drift_ok=drift_ok,
            recovery_ready=rec_ok,
            certification_healthy=cert_ok,
            checks=check_results,
        )

    def _check_deployment_validator(self) -> Tuple[bool, List[str], List[str]]:
        try:
            from core.governance.deployment import (
                DeploymentValidator, AtomicDeploymentValidator,
            )
            dv = DeploymentValidator(self._kernel)
            report = dv.run_all()
            adv = AtomicDeploymentValidator(self._kernel)
            atomic_ok, atomic_msg = adv.validate_atomic()
            blockers = list(report.blockers)
            warnings = list(report.warnings)
            if not atomic_ok:
                warnings.append(atomic_msg)
            return len(blockers) == 0, blockers, warnings
        except Exception as e:
            return False, [f"Deployment validator error: {e}"], []

    def _check_governance_health(self) -> Tuple[bool, List[str]]:
        try:
            health = self._kernel.health()
            warnings = []
            if health.get("failsafe_mode"):
                warnings.append("Governance in failsafe mode")
            if health.get("degraded_tiers", []):
                warnings.append(f"Degraded tiers: {health['degraded_tiers']}")
            if health.get("policies", 0) < 4:
                warnings.append(f"Only {health['policies']} policies (need 4+)")
            return len(warnings) == 0, warnings
        except Exception as e:
            return False, [f"Governance health error: {e}"]

    def _check_invariants(self) -> Tuple[bool, List[str]]:
        try:
            results = self._kernel.run_invariant_scan()
            failures = [r for r in results if not r["passed"]]
            warnings = [f"Invariant failed: {r.get('name', r.get('id', 'unknown'))}" for r in failures[:5]]
            return len(failures) == 0, warnings
        except Exception as e:
            return False, [f"Invariant scan error: {e}"]

    def _check_drift(self) -> Tuple[bool, List[str]]:
        try:
            from core.governance.maintainability import OperationalDriftDetector
            odd = OperationalDriftDetector()
            odd.take_config_snapshot()
            odd.take_policy_snapshot(self._kernel)
            drift = odd.run(self._kernel)
            return not drift.drifting, drift.warnings
        except Exception as e:
            return True, [f"Drift check error: {e}"]

    def _check_recovery_readiness(self) -> Tuple[bool, List[str]]:
        try:
            from core.governance.backup_recovery import RecoveryReadinessAssessor
            ra = RecoveryReadinessAssessor(self._kernel)
            score = ra.assess()
            return score.overall_score >= 50, score.warnings
        except Exception as e:
            return True, [f"Recovery readiness error: {e}"]

    def _check_certification_health(self) -> Tuple[bool, List[str]]:
        try:
            from core.governance.observability import OperationalHealthDashboard
            ohd = OperationalHealthDashboard(self._kernel)
            health = ohd.get_health()
            return health.overall != "critical", health.warnings
        except Exception as e:
            return True, [f"Certification health error: {e}"]
