"""
Enterprise Operational Certification — Master Orchestrator.
Coordinates all 7 certification phases into a single certifiable result.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel
from core.governance.deployment import (
    DeploymentValidator, AtomicDeploymentValidator, DeploymentReport,
)
from core.governance.backup_recovery import (
    BackupValidator, RestoreCertification, RecoveryReadinessAssessor,
    SafeRecoveryManager, RecoveryCertificationResult, RecoveryReadinessScore,
)
from core.governance.upgrade import (
    MigrationGovernor, SafeUpgradeSimulator, BackwardCompatibilityValidator,
    MigrationGovernanceResult, UpgradeSimulationResult,
)
from core.governance.soak import (
    SoakTestFramework, SoakTestResult, MemoryStabilityReport, LatencyDriftReport,
)
from core.governance.offline import (
    OfflineResilienceTester, MultiBranchGovernanceValidator,
    SyncConflictCertifier, NetworkDegradationSimulator,
    OfflineResilienceTestResult, MultiBranchGovernanceResult,
    SyncConflictResult, NetworkDegradationTestResult,
)
from core.governance.maintainability import (
    TechnicalDebtClassifier, ChangeRiskEngine, ArchitectureFreezeEnforcer,
    OperationalDriftDetector, TechnicalDebtItem, ChangeRiskAssessment,
    OperationalDriftReport,
)
from core.governance.observability import (
    OperationalHealthDashboard, IncidentReconstructor,
    NoiseSafeTelemetryManager, OperationalHealth,
)

logger = logging.getLogger("erp.governance.operational_certification")

CERTIFICATION_VERSION = "2.0.0"


@dataclass
class PhaseCertificationResult:
    phase: int
    name: str
    passed: bool
    score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class MasterCertificationReport:
    overall_passed: bool
    overall_score: float
    phases: List[PhaseCertificationResult] = field(default_factory=list)
    governance_status: Dict[str, Any] = field(default_factory=dict)
    deployment: DeploymentReport = field(default_factory=DeploymentReport)
    recovery_score: RecoveryReadinessScore = field(
        default_factory=lambda: RecoveryReadinessScore(overall_score=0)
    )
    migration_governance: MigrationGovernanceResult = field(
        default_factory=MigrationGovernanceResult
    )
    soak_battery: Dict[str, Any] = field(default_factory=dict)
    operational_health: OperationalHealth = field(
        default_factory=lambda: OperationalHealth(overall="unknown")
    )
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class OperationalCertificationOrchestrator:
    """Master orchestrator for all 7 certification phases.

    Coordinates deployment, backup/recovery, upgrade, soak, offline,
    maintainability, and observability certifications.
    Read-only: all validations are passive observations. Never mutates DB.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def certify_all(self, soak_iterations: int = 100) -> MasterCertificationReport:
        results = []

        # Phase 1: Deployment
        p1 = self._certify_deployment()
        results.append(p1)

        # Phase 2: Backup + Recovery
        p2 = self._certify_backup_recovery()
        results.append(p2)

        # Phase 3: Upgrade + Migration
        p3 = self._certify_upgrade()
        results.append(p3)

        # Phase 4: Long-Duration Runtime
        p4 = self._certify_soak(iterations=soak_iterations)
        results.append(p4)

        # Phase 5: Offline-First + Multi-Branch
        p5 = self._certify_offline()
        results.append(p5)

        # Phase 6: Maintainability
        p6 = self._certify_maintainability()
        results.append(p6)

        # Phase 7: Observability
        p7 = self._certify_observability()
        results.append(p7)

        passed_count = sum(1 for r in results if r.passed)
        total_score = sum(r.score for r in results) / max(len(results), 1)
        overall_passed = passed_count == len(results)

        all_warnings = []
        all_errors = []
        for r in results:
            all_warnings.extend(r.warnings)
            all_errors.extend(r.errors)

        governance_status = self._kernel.health()

        return MasterCertificationReport(
            overall_passed=overall_passed,
            overall_score=round(total_score, 1),
            phases=results,
            governance_status=governance_status,
            warnings=all_warnings,
            errors=all_errors,
        )

    def _certify_deployment(self) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            dv = DeploymentValidator(self._kernel)
            dep_report = dv.run_all()
            if dep_report.blockers:
                errors.extend(dep_report.blockers)
            if dep_report.warnings:
                warnings.extend(dep_report.warnings)

            adv = AtomicDeploymentValidator(self._kernel)
            atomic_ok, atomic_msg = adv.validate_atomic()
            if not atomic_ok:
                warnings.append(atomic_msg)

            passed = len(errors) == 0
            score = 100 if passed else max(0, 100 - len(errors) * 25)
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=1, name="Deployment Certification",
            passed=passed, score=score,
            details={
                "deployment_valid": dep_report.overall if 'dep_report' in dir() else "unknown",
                "atomic_valid": atomic_ok if 'atomic_ok' in dir() else False,
                "operational_risk": dep_report.operational_risk if 'dep_report' in dir() else "unknown",
                "check_count": len(dep_report.checks) if 'dep_report' in dir() else 0,
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )

    def _certify_backup_recovery(self) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            rc = RestoreCertification(self._kernel)
            restore_results = rc.run_all()

            ra = RecoveryReadinessAssessor(self._kernel)
            rec_score = ra.assess()

            sm = SafeRecoveryManager(self._kernel)
            safe_ok, safe_msg = sm.validate_recovery_safe()

            passed = all(r.passed for r in restore_results) and rec_score.overall_score >= 50
            score = rec_score.overall_score

            if not safe_ok:
                warnings.append(safe_msg)
            for r in restore_results:
                if not r.passed:
                    errors.extend(r.errors)
                    warnings.extend(r.warnings)
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=2, name="Backup + Recovery Certification",
            passed=passed, score=score,
            details={
                "recovery_score": rec_score.overall_score if 'rec_score' in dir() else 0,
                "restore_scenarios": len(restore_results) if 'restore_results' in dir() else 0,
                "restore_passed": sum(1 for r in restore_results if r.passed) if 'restore_results' in dir() else 0,
                "safe_recovery": safe_ok if 'safe_ok' in dir() else False,
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )

    def _certify_upgrade(self) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            mg = MigrationGovernor(self._kernel)
            gov_result = mg.run()

            sus = SafeUpgradeSimulator(self._kernel)
            upgrade_results = sus.run_all()

            bcv = BackwardCompatibilityValidator(self._kernel)
            legacy_ok, legacy_msg = bcv.validate_legacy_workflows()
            contracts_ok, contracts_msg = bcv.validate_contracts_valid()

            passed = gov_result.passed and all(r.passed for r in upgrade_results)
            score = 100 if passed else 50

            if not gov_result.passed:
                errors.extend(gov_result.errors)
                warnings.extend(gov_result.warnings)
            if not legacy_ok:
                warnings.append(legacy_msg)
            if not contracts_ok:
                warnings.append(contracts_msg)
            for r in upgrade_results:
                if not r.passed:
                    warnings.extend(r.warnings)
                    errors.extend(r.errors)
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=3, name="Upgrade + Migration Certification",
            passed=passed, score=score,
            details={
                "migration_ordered": gov_result.ordered_correctly if 'gov_result' in dir() else False,
                "rollback_compatible": gov_result.rollback_compatible if 'gov_result' in dir() else False,
                "schema_consistent": gov_result.schema_consistent if 'gov_result' in dir() else False,
                "upgrade_scenarios": len(upgrade_results) if 'upgrade_results' in dir() else 0,
                "upgrade_passed": sum(1 for r in upgrade_results if r.passed) if 'upgrade_results' in dir() else 0,
                "legacy_workflows_ok": legacy_ok if 'legacy_ok' in dir() else False,
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )

    def _certify_soak(self, iterations: int = 100) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            sf = SoakTestFramework(self._kernel)
            battery = sf.run_full_soak_battery(iterations=iterations)

            gov_soak = battery.get("governance_soak", {})
            inv_soak = battery.get("invariant_soak", {})
            mem_stable = battery.get("memory_stability", {})
            evt_stable = battery.get("event_stability", {})
            drift = battery.get("latency_drift", {})

            passed = (
                gov_soak.get("passed", False) and
                inv_soak.get("passed", False) and
                mem_stable.get("stable", False) and
                evt_stable.get("passed", False) and
                drift.get("stable", False)
            )
            score = 100 if passed else 50

            for section_name, section in battery.items():
                for w in section.get("warnings", []):
                    warnings.append(f"[{section_name}] {w}")
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=4, name="Long-Duration Runtime Certification",
            passed=passed, score=score,
            details={
                "soak_battery": battery if 'battery' in dir() else {},
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )

    def _certify_offline(self) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            ort = OfflineResilienceTester(self._kernel)
            offline_results = ort.run_all()

            mbv = MultiBranchGovernanceValidator(self._kernel)
            branch_result = mbv.run()

            scc = SyncConflictCertifier(self._kernel)
            sync_results = scc.run_all()

            nds = NetworkDegradationSimulator(self._kernel)
            net_results = nds.run_all()

            passed = (
                all(r.passed for r in offline_results) and
                branch_result.isolation_valid and
                all(r.passed for r in sync_results) and
                all(r.passed for r in net_results)
            )
            score = 100 if passed else 50

            for r in offline_results:
                if not r.passed:
                    errors.extend(r.errors)
            if not branch_result.isolation_valid:
                errors.extend(branch_result.errors)
            for r in sync_results:
                if not r.passed:
                    errors.extend(r.errors)
            for r in net_results:
                if not r.passed:
                    errors.extend(r.errors)
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=5, name="Offline-First + Multi-Branch Certification",
            passed=passed, score=score,
            details={
                "offline_scenarios": len(offline_results) if 'offline_results' in dir() else 0,
                "offline_passed": sum(1 for r in offline_results if r.passed) if 'offline_results' in dir() else 0,
                "branch_isolation_valid": branch_result.isolation_valid if 'branch_result' in dir() else False,
                "sync_scenarios": len(sync_results) if 'sync_results' in dir() else 0,
                "sync_passed": sum(1 for r in sync_results if r.passed) if 'sync_results' in dir() else 0,
                "network_scenarios": len(net_results) if 'net_results' in dir() else 0,
                "network_passed": sum(1 for r in net_results if r.passed) if 'net_results' in dir() else 0,
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )

    def _certify_maintainability(self) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            tdc = TechnicalDebtClassifier(self._kernel)
            debt_items = tdc.classify_all()

            cre = ChangeRiskEngine(self._kernel)
            risk = cre.assess(change_id="certification-run")

            afe = ArchitectureFreezeEnforcer(self._kernel)
            freeze_valid, freeze_msg = afe.validate("new_governance_layer",
                                                     "Certification requires governance validation")

            odd = OperationalDriftDetector()
            _ = odd.take_config_snapshot()
            _ = odd.take_policy_snapshot(self._kernel)
            drift = odd.run(self._kernel)

            critical_debt = [d for d in debt_items if d.severity == "critical"]
            passed = len(critical_debt) == 0 and not drift.drifting
            score = 100 if passed else max(0, 100 - len(critical_debt) * 25 - len(drift.warnings) * 15)

            for d in critical_debt:
                warnings.append(f"Critical debt: {d.description}")
            if drift.drifting:
                warnings.extend(drift.warnings)
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=6, name="Operational Maintainability Governance",
            passed=passed, score=score,
            details={
                "debt_items": len(debt_items) if 'debt_items' in dir() else 0,
                "critical_debt": len(critical_debt) if 'critical_debt' in dir() else 0,
                "overall_risk": risk.overall_risk if 'risk' in dir() else "unknown",
                "architecture_freeze_valid": freeze_valid if 'freeze_valid' in dir() else False,
                "drift_detected": drift.drifting if 'drift' in dir() else False,
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )

    def _certify_observability(self) -> PhaseCertificationResult:
        start = time.time()
        warnings = []
        errors = []

        try:
            ohd = OperationalHealthDashboard(self._kernel)
            health = ohd.get_health()

            ir = IncidentReconstructor(self._kernel)
            reconstruction = ir.reconstruct()

            nst = NoiseSafeTelemetryManager(self._kernel)
            telemetry = nst.get_summary()

            passed = health.overall != "critical"
            score = health.score

            if health.warnings:
                warnings.extend(health.warnings)
            if not reconstruction.reconstruction_complete:
                warnings.append("Incident reconstruction incomplete")
        except Exception as e:
            passed = False
            score = 0
            errors.append(str(e))

        duration = (time.time() - start) * 1000
        return PhaseCertificationResult(
            phase=7, name="Enterprise Operational Observability",
            passed=passed, score=score,
            details={
                "health_overall": health.overall if 'health' in dir() else "unknown",
                "health_score": health.score if 'health' in dir() else 0,
                "gov_policies": self._kernel.policies.count(),
                "gov_invariants": self._kernel.invariants.count(),
                "incident_reconstruction": reconstruction.reconstruction_complete if 'reconstruction' in dir() else False,
                "telemetry": telemetry.__dict__ if 'telemetry' in dir() else {},
            },
            warnings=warnings, errors=errors,
            duration_ms=round(duration, 1),
        )
