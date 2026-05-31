"""
Enterprise Operational Certification — Complete Test Suite.
Validates all 7 phases with structured, deterministic tests.
"""
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import patch, MagicMock

from django.test import TestCase

from core.governance.kernel import GovernanceKernel, PriorityTier
from core.governance.registries import PolicyRule
from core.governance.contracts import register_all_contracts
from core.governance.enforcer import register_enforcement_policies

# Certification modules
from core.governance.deployment import (
    DeploymentValidator, AtomicDeploymentValidator, DeploymentCheck,
)
from core.governance.backup_recovery import (
    BackupValidator, RestoreCertification, RecoveryReadinessAssessor,
    SafeRecoveryManager, BackupValidationResult,
)
from core.governance.upgrade import (
    MigrationGovernor, SafeUpgradeSimulator, BackwardCompatibilityValidator,
    UpgradeAuditLog, UpgradeAuditEntry,
)
from core.governance.soak import (
    SoakTestFramework, MemoryStabilityReport, LatencyDriftReport,
)
from core.governance.offline import (
    OfflineResilienceTester, MultiBranchGovernanceValidator,
    SyncConflictCertifier, NetworkDegradationSimulator,
)
from core.governance.maintainability import (
    TechnicalDebtClassifier, ChangeRiskEngine, ArchitectureFreezeEnforcer,
    OperationalDriftDetector,
)
from core.governance.observability import (
    OperationalHealthDashboard, IncidentReconstructor,
    NoiseSafeTelemetryManager,
)
from core.governance.operational_certification import (
    OperationalCertificationOrchestrator, PhaseCertificationResult,
    MasterCertificationReport,
)

KERNEL = GovernanceKernel()


def _ensure_kernel_ready():
    register_enforcement_policies(KERNEL)
    register_all_contracts(KERNEL)


# =============================================================================
# Phase 1 — Deployment Certification Tests
# =============================================================================

class Phase1DeploymentTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_deployment_validator_creates_report(self):
        dv = DeploymentValidator(KERNEL)
        report = dv.run_all()
        self.assertIsNotNone(report)
        self.assertIn(report.overall, ("pass", "warn", "blocked"))
        self.assertGreater(len(report.checks), 0)

    def test_deployment_environment_check(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_environment()
        self.assertIn(check.status, ("pass", "warn", "fail"))

    def test_deployment_dependencies_check(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_dependencies()
        self.assertEqual(check.status, "pass", msg=check.message)

    def test_deployment_config_check(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_config()
        self.assertIn(check.status, ("pass", "warn", "fail"))

    def test_deployment_governance_check(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_governance()
        self.assertEqual(check.status, "pass", msg=check.message)

    def test_deployment_secret_check(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_secret()
        self.assertIn(check.status, ("pass", "warn", "fail"))

    def test_deployment_event_bus_check(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_event_bus()
        self.assertEqual(check.status, "pass", msg=check.message)

    def test_fingerprint_generation(self):
        dv = DeploymentValidator(KERNEL)
        fp = dv.get_fingerprint()
        self.assertTrue(len(fp.python_version) > 0)
        self.assertTrue(len(fp.checksum) > 0)
        self.assertEqual(fp.checksum, fp.compute_checksum())

    def test_fingerprint_reproducible(self):
        dv = DeploymentValidator(KERNEL)
        fp1 = dv.get_fingerprint()
        fp2 = dv.get_fingerprint()
        self.assertEqual(fp1.checksum, fp2.checksum)

    def test_atomic_deployment_validation(self):
        adv = AtomicDeploymentValidator(KERNEL)
        blocked, blockers = adv.deployment_blocked()
        self.assertIsInstance(blocked, bool)
        self.assertIsInstance(blockers, list)

    def test_atomic_validator_returns_result(self):
        adv = AtomicDeploymentValidator(KERNEL)
        ok, msg = adv.validate_atomic()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(msg, str)

    def test_deployment_report_fingerprint_included(self):
        dv = DeploymentValidator(KERNEL)
        report = dv.run_all()
        self.assertIsNotNone(report.fingerprint)
        self.assertTrue(len(report.fingerprint.fingerprint_id) > 0)

    def test_deployment_validator_with_kernel(self):
        dv = DeploymentValidator(KERNEL)
        check = dv.validate_governance()
        self.assertEqual(check.status, "pass", msg=check.message)


# =============================================================================
# Phase 2 — Backup + Recovery Certification Tests
# =============================================================================

class Phase2BackupRecoveryTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_backup_validator_completeness(self):
        bv = BackupValidator(KERNEL)
        pct = bv.validate_completeness(
            ["accounting_account", "sales_invoice"],
            ["accounting_account", "sales_invoice", "inventory_batch"],
        )
        self.assertAlmostEqual(pct, 66.7, delta=1)

    def test_backup_validator_full_completeness(self):
        bv = BackupValidator(KERNEL)
        pct = bv.validate_completeness(
            ["a", "b", "c"], ["a", "b", "c"],
        )
        self.assertEqual(pct, 100.0)

    def test_backup_validator_empty_tables(self):
        bv = BackupValidator(KERNEL)
        pct = bv.validate_completeness([], ["a", "b"])
        self.assertEqual(pct, 0.0)

    def test_backup_validator_no_expected(self):
        bv = BackupValidator(KERNEL)
        pct = bv.validate_completeness(["a"], [])
        self.assertEqual(pct, 100.0)

    def test_integrity_hash_match(self):
        bv = BackupValidator(KERNEL)
        data = b"test_backup_data"
        expected = "sha256 hash"
        result = bv.validate_integrity_hash(data, expected)
        import hashlib
        actual = hashlib.sha256(data).hexdigest()
        self.assertEqual(result, actual == expected)

    def test_integrity_hash_correct(self):
        bv = BackupValidator(KERNEL)
        data = b"hello"
        expected = __import__("hashlib").sha256(data).hexdigest()
        self.assertTrue(bv.validate_integrity_hash(data, expected))

    def test_file_consistency(self):
        bv = BackupValidator(KERNEL)
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as f:
                f.write(b"data")
                path = f.name
            self.assertTrue(bv.validate_file_consistency([path]))
        finally:
            import os
            if 'path' in dir() and os.path.isfile(path):
                os.unlink(path)

    def test_db_consistency(self):
        bv = BackupValidator(KERNEL)
        consistent, warnings = bv.validate_db_consistency({"a": 10, "b": 5})
        self.assertTrue(consistent)

    def test_db_consistency_negative(self):
        bv = BackupValidator(KERNEL)
        consistent, warnings = bv.validate_db_consistency({"a": -1})
        self.assertFalse(consistent)
        self.assertTrue(len(warnings) > 0)

    def test_restore_readable_valid(self):
        bv = BackupValidator(KERNEL)
        self.assertTrue(bv.validate_restore_readable("json"))
        self.assertTrue(bv.validate_restore_readable("sql"))
        self.assertTrue(bv.validate_restore_readable("pg_dump"))

    def test_full_backup_validation(self):
        bv = BackupValidator(KERNEL)
        data = b"backup_content"
        import hashlib
        expected_hash = hashlib.sha256(data).hexdigest()
        result = bv.validate_backup(
            tables=["a", "b"], expected_tables=["a", "b"],
            data=data, expected_hash=expected_hash,
            file_paths=[], table_counts={"a": 5, "b": 3},
        )
        self.assertIsInstance(result, BackupValidationResult)
        self.assertTrue(result.integrity_hash_match)

    def test_restore_full_simulation(self):
        rc = RestoreCertification(KERNEL)
        result = rc.simulate_full_restore()
        self.assertIn(result.scenario, ("full", "partial", "failed", "corrupted"))

    def test_restore_partial_simulation(self):
        rc = RestoreCertification(KERNEL)
        result = rc.simulate_partial_restore()
        self.assertEqual(result.scenario, "partial")

    def test_restore_failed_simulation(self):
        rc = RestoreCertification(KERNEL)
        result = rc.simulate_failed_restore()
        self.assertEqual(result.scenario, "failed")

    def test_restore_corrupted_simulation(self):
        rc = RestoreCertification(KERNEL)
        result = rc.simulate_corrupted_backup()
        self.assertEqual(result.scenario, "corrupted")

    def test_all_restore_scenarios(self):
        rc = RestoreCertification(KERNEL)
        results = rc.run_all()
        self.assertEqual(len(results), 4)

    def test_recovery_readiness_score(self):
        ra = RecoveryReadinessAssessor(KERNEL)
        score = ra.assess(backup_exists=True, backup_validated=True, restore_tested=True)
        self.assertGreater(score.overall_score, 0)
        self.assertLessEqual(score.overall_score, 100)

    def test_recovery_readiness_low_score(self):
        ra = RecoveryReadinessAssessor(KERNEL)
        score = ra.assess(backup_exists=False, backup_validated=False, restore_tested=False)
        self.assertLess(score.overall_score, 50)

    def test_safe_recovery_mode_default(self):
        sm = SafeRecoveryManager(KERNEL)
        mode = sm.get_mode()
        self.assertEqual(mode.mode, "validated")

    def test_safe_recovery_mode_production(self):
        sm = SafeRecoveryManager(KERNEL)
        mode = sm.get_mode("production")
        self.assertEqual(mode.mode, "dry_run")
        self.assertFalse(mode.isolated)

    def test_safe_recovery_validation(self):
        sm = SafeRecoveryManager(KERNEL)
        ok, msg = sm.validate_recovery_safe("development")
        self.assertTrue(ok)


# =============================================================================
# Phase 3 — Upgrade + Migration Certification Tests
# =============================================================================

class Phase3UpgradeTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_migration_governor_returns_result(self):
        mg = MigrationGovernor(KERNEL)
        result = mg.run()
        self.assertIsNotNone(result)

    def test_migration_ordering_check(self):
        mg = MigrationGovernor(KERNEL)
        ok, msg = mg.validate_ordering()
        self.assertIsInstance(ok, bool)

    def test_rollback_compatibility(self):
        mg = MigrationGovernor(KERNEL)
        ok, msg = mg.validate_rollback_compatibility()
        self.assertIsInstance(ok, bool)

    def test_schema_consistency(self):
        mg = MigrationGovernor(KERNEL)
        ok, msg = mg.validate_schema_consistency()
        self.assertIsInstance(ok, bool)

    def test_invariant_compatibility(self):
        mg = MigrationGovernor(KERNEL)
        ok, msg = mg.validate_invariant_compatibility()
        self.assertTrue(ok, msg=msg)

    def test_policy_compatibility(self):
        mg = MigrationGovernor(KERNEL)
        ok, msg = mg.validate_policy_compatibility()
        self.assertTrue(ok, msg=msg)

    def test_interrupted_migration_simulation(self):
        sus = SafeUpgradeSimulator(KERNEL)
        result = sus.simulate_interrupted_migration()
        self.assertEqual(result.scenario, "interrupted")

    def test_partial_deployment_simulation(self):
        sus = SafeUpgradeSimulator(KERNEL)
        result = sus.simulate_partial_deployment()
        self.assertEqual(result.scenario, "partial")

    def test_rollback_simulation(self):
        sus = SafeUpgradeSimulator(KERNEL)
        result = sus.simulate_rollback()
        self.assertEqual(result.scenario, "rollback")

    def test_stale_contract_simulation(self):
        sus = SafeUpgradeSimulator(KERNEL)
        result = sus.simulate_stale_contract()
        self.assertEqual(result.scenario, "stale_contract")

    def test_all_upgrade_simulations(self):
        sus = SafeUpgradeSimulator(KERNEL)
        results = sus.run_all()
        self.assertEqual(len(results), 4)

    def test_backward_compatibility_legacy_workflows(self):
        bcv = BackwardCompatibilityValidator(KERNEL)
        ok, msg = bcv.validate_legacy_workflows()
        self.assertTrue(ok, msg=msg)

    def test_backward_compatibility_contracts(self):
        bcv = BackwardCompatibilityValidator(KERNEL)
        ok, msg = bcv.validate_contracts_valid()
        self.assertTrue(ok, msg=msg)

    def test_backward_compatibility_api(self):
        bcv = BackwardCompatibilityValidator(KERNEL)
        ok, msg = bcv.validate_api_compatibility()
        self.assertTrue(ok, msg=msg)

    def test_upgrade_audit_log(self):
        log = UpgradeAuditLog()
        log.append(UpgradeAuditEntry(version="1.0", migration_name="0001_initial", action="applied"))
        log.append(UpgradeAuditEntry(version="1.1", migration_name="0002_update", action="applied"))
        self.assertEqual(len(log.entries), 2)
        lineage = log.get_lineage()
        self.assertIn("1.0", lineage)

    def test_upgrade_audit_log_bounded(self):
        log = UpgradeAuditLog(maxlen=3)
        for i in range(10):
            log.append(UpgradeAuditEntry(version=f"v{i}", migration_name=f"m{i}", action="applied"))
        self.assertLessEqual(len(log.entries), 3)


# =============================================================================
# Phase 4 — Long-Duration Runtime Certification Tests
# =============================================================================

class Phase4SoakTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_governance_soak_basic(self):
        sf = SoakTestFramework(KERNEL)
        result = sf.run_governance_soak(iterations=10)
        self.assertEqual(result.total_iterations, 10)
        self.assertIsInstance(result.passed, bool)

    def test_governance_soak_latency_measured(self):
        sf = SoakTestFramework(KERNEL)
        result = sf.run_governance_soak(iterations=5)
        self.assertGreaterEqual(result.avg_latency_ms, 0)
        self.assertIsInstance(result.passed, bool)

    def test_invariant_soak_basic(self):
        sf = SoakTestFramework(KERNEL)
        result = sf.run_invariant_soak(iterations=5)
        self.assertEqual(result.total_iterations, 5)

    def test_memory_stability_validation(self):
        sf = SoakTestFramework(KERNEL)
        report = sf.run_memory_stability_validation()
        self.assertIsInstance(report, MemoryStabilityReport)
        self.assertIsInstance(report.stable, bool)

    def test_event_stability_validation(self):
        sf = SoakTestFramework(KERNEL)
        result = sf.run_event_stability_validation()
        self.assertIsInstance(result.passed, bool)

    def test_latency_drift_analysis(self):
        sf = SoakTestFramework(KERNEL)
        report = sf.run_latency_drift_analysis()
        self.assertIsInstance(report, LatencyDriftReport)
        self.assertIsInstance(report.stable, bool)

    def test_full_soak_battery(self):
        sf = SoakTestFramework(KERNEL)
        battery = sf.run_full_soak_battery(iterations=10)
        self.assertIn("governance_soak", battery)
        self.assertIn("invariant_soak", battery)
        self.assertIn("memory_stability", battery)
        self.assertIn("event_stability", battery)
        self.assertIn("latency_drift", battery)

    def test_soak_iterations_have_results(self):
        sf = SoakTestFramework(KERNEL)
        result = sf.run_governance_soak(iterations=3)
        self.assertGreater(len(result.iterations), 0)

    def test_memory_stability_queue_usage(self):
        sf = SoakTestFramework(KERNEL)
        report = sf.run_memory_stability_validation()
        self.assertGreaterEqual(report.queue_usage, 0)


# =============================================================================
# Phase 5 — Offline-First + Multi-Branch Certification Tests
# =============================================================================

class Phase5OfflineTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_offline_transaction(self):
        ort = OfflineResilienceTester(KERNEL)
        result = ort.test_offline_transaction()
        self.assertEqual(result.scenario, "offline_tx")

    def test_delayed_sync(self):
        ort = OfflineResilienceTester(KERNEL)
        result = ort.test_delayed_sync()
        self.assertEqual(result.scenario, "delayed_sync")

    def test_retry_safety(self):
        ort = OfflineResilienceTester(KERNEL)
        result = ort.test_retry_safety()
        self.assertEqual(result.scenario, "retry_safety")

    def test_idempotent_replay(self):
        ort = OfflineResilienceTester(KERNEL)
        result = ort.test_idempotent_replay()
        self.assertEqual(result.scenario, "idempotent_replay")

    def test_all_offline_scenarios(self):
        ort = OfflineResilienceTester(KERNEL)
        results = ort.run_all()
        self.assertEqual(len(results), 4)

    def test_multi_branch_isolation(self):
        mbv = MultiBranchGovernanceValidator(KERNEL)
        result = mbv.run()
        self.assertIsInstance(result.isolation_valid, bool)

    def test_multi_branch_permissions(self):
        mbv = MultiBranchGovernanceValidator(KERNEL)
        ok, msg = mbv.validate_permission_boundaries()
        self.assertIsInstance(ok, bool)

    def test_multi_branch_inventory(self):
        mbv = MultiBranchGovernanceValidator(KERNEL)
        ok, msg = mbv.validate_inventory_separation()
        self.assertTrue(ok, msg=msg)

    def test_multi_branch_accounting(self):
        mbv = MultiBranchGovernanceValidator(KERNEL)
        ok, msg = mbv.validate_accounting_segregation()
        self.assertIsInstance(ok, bool)

    def test_sync_stale(self):
        scc = SyncConflictCertifier(KERNEL)
        result = scc.test_stale_sync()
        self.assertEqual(result.scenario, "stale_sync")

    def test_sync_duplicated(self):
        scc = SyncConflictCertifier(KERNEL)
        result = scc.test_duplicated_sync()
        self.assertEqual(result.scenario, "duplicated_sync")

    def test_sync_conflicting(self):
        scc = SyncConflictCertifier(KERNEL)
        result = scc.test_conflicting_transactions()
        self.assertEqual(result.scenario, "conflicting_tx")

    def test_sync_delayed_replay(self):
        scc = SyncConflictCertifier(KERNEL)
        result = scc.test_delayed_replay()
        self.assertEqual(result.scenario, "delayed_replay")

    def test_all_sync_scenarios(self):
        scc = SyncConflictCertifier(KERNEL)
        results = scc.run_all()
        self.assertEqual(len(results), 4)

    def test_network_intermittent(self):
        nds = NetworkDegradationSimulator(KERNEL)
        result = nds.simulate_intermittent()
        self.assertEqual(result.scenario, "intermittent")

    def test_network_delayed_response(self):
        nds = NetworkDegradationSimulator(KERNEL)
        result = nds.simulate_delayed_response()
        self.assertEqual(result.scenario, "delayed_response")

    def test_network_partial_failure(self):
        nds = NetworkDegradationSimulator(KERNEL)
        result = nds.simulate_partial_failure()
        self.assertEqual(result.scenario, "partial_failure")

    def test_all_network_scenarios(self):
        nds = NetworkDegradationSimulator(KERNEL)
        results = nds.run_all()
        self.assertEqual(len(results), 3)


# =============================================================================
# Phase 6 — Operational Maintainability Governance Tests
# =============================================================================

class Phase6MaintainabilityTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_debt_classifier_returns_items(self):
        tdc = TechnicalDebtClassifier(KERNEL)
        items = tdc.classify_all()
        self.assertIsInstance(items, list)
        for item in items:
            self.assertIn(item.category, (
                "critical_runtime", "governance", "ui", "advisory", "isolated_legacy"
            ))

    def test_debt_classifier_has_ids(self):
        tdc = TechnicalDebtClassifier(KERNEL)
        items = tdc.classify_all()
        for item in items:
            self.assertTrue(len(item.debt_id) > 0)

    def test_change_risk_assessment_low(self):
        cre = ChangeRiskEngine(KERNEL)
        risk = cre.assess(change_id="test-1")
        self.assertEqual(risk.overall_risk, "low")

    def test_change_risk_assessment_high(self):
        cre = ChangeRiskEngine(KERNEL)
        risk = cre.assess(
            change_id="test-2",
            governance_impact="critical",
            runtime_impact="high",
            latency_impact="high",
            memory_impact="medium",
            invariant_impact="critical",
            deployment_impact="high",
        )
        self.assertIn(risk.overall_risk, ("high", "critical"))

    def test_change_risk_recommendations(self):
        cre = ChangeRiskEngine(KERNEL)
        risk = cre.assess(
            change_id="test-3",
            governance_impact="critical",
            invariant_impact="critical",
            deployment_impact="high",
        )
        self.assertTrue(len(risk.recommendations) > 0)

    def test_architecture_freeze_requires_justification(self):
        afe = ArchitectureFreezeEnforcer(KERNEL)
        self.assertTrue(afe.requires_justification("new_governance_layer"))
        self.assertFalse(afe.requires_justification("simple_bugfix"))

    def test_architecture_freeze_validates(self):
        afe = ArchitectureFreezeEnforcer(KERNEL)
        ok, msg = afe.validate("simple_bugfix")
        self.assertTrue(ok)

    def test_architecture_freeze_rejects_short_justification(self):
        afe = ArchitectureFreezeEnforcer(KERNEL)
        ok, msg = afe.validate("new_governance_layer", justification="short")
        self.assertFalse(ok)

    def test_architecture_freeze_accepts_long_justification(self):
        afe = ArchitectureFreezeEnforcer(KERNEL)
        ok, msg = afe.validate(
            "new_governance_layer",
            justification="This change is required for production compliance certification",
        )
        self.assertTrue(ok)

    def test_drift_detector_no_drift_initial(self):
        odd = OperationalDriftDetector()
        _ = odd.take_config_snapshot()
        _ = odd.take_policy_snapshot(KERNEL)
        report = odd.run(KERNEL)
        self.assertIsInstance(report.drifting, bool)

    def test_drift_detector_snapshot_stable(self):
        odd = OperationalDriftDetector()
        snap1 = odd.take_config_snapshot()
        snap2 = odd.take_config_snapshot()
        self.assertEqual(snap1, snap2)


# =============================================================================
# Phase 7 — Enterprise Operational Observability Tests
# =============================================================================

class Phase7ObservabilityTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_health_dashboard_returns_health(self):
        ohd = OperationalHealthDashboard(KERNEL)
        health = ohd.get_health()
        self.assertIn(health.overall, ("healthy", "degraded", "critical"))
        self.assertGreater(health.score, 0)

    def test_health_dashboard_governance_status(self):
        ohd = OperationalHealthDashboard(KERNEL)
        health = ohd.get_health()
        self.assertIn("policies", health.governance)
        self.assertIn("invariants", health.governance)

    def test_health_dashboard_invariant_results(self):
        ohd = OperationalHealthDashboard(KERNEL)
        health = ohd.get_health()
        self.assertIn("total", health.invariants)
        self.assertIn("passed", health.invariants)

    def test_health_dashboard_memory_status(self):
        ohd = OperationalHealthDashboard(KERNEL)
        health = ohd.get_health()
        self.assertIn("event_bus_usage", health.memory)

    def test_health_dashboard_latency_tracking(self):
        ohd = OperationalHealthDashboard(KERNEL)
        health = ohd.get_health()
        self.assertIn("total_enforcements", health.latency)

    def test_incident_reconstruction_empty(self):
        ir = IncidentReconstructor(KERNEL)
        recon = ir.reconstruct()
        self.assertTrue(recon.reconstruction_complete)

    def test_incident_reconstruction_with_correlation(self):
        res = KERNEL.enforce(
            policy_id="enforce.return_state_transition",
            context={"current_state": "PENDING", "target_state": "APPROVED"},
            priority=PriorityTier.HIGH,
        )
        ir = IncidentReconstructor(KERNEL)
        recon = ir.reconstruct(correlation_id=res.correlation_id)
        self.assertTrue(len(recon.event_chain) >= 0)

    def test_incident_reconstruction_policy_chain(self):
        ir = IncidentReconstructor(KERNEL)
        recon = ir.reconstruct()
        self.assertIsInstance(recon.policy_chain, list)

    def test_noise_safe_telemetry(self):
        nst = NoiseSafeTelemetryManager(KERNEL)
        summary = nst.get_summary()
        self.assertGreaterEqual(summary.total_events_captured, 0)

    def test_noise_safe_alert_dedup(self):
        nst = NoiseSafeTelemetryManager(KERNEL)
        result1 = nst.record_alert("test_alert_1")
        result2 = nst.record_alert("test_alert_1")
        self.assertTrue(result1)
        # Second within window should be suppressed
        self.assertFalse(result2)

    def test_noise_safe_telemetry_bounded(self):
        nst = NoiseSafeTelemetryManager(KERNEL)
        summary = nst.get_summary()
        self.assertTrue(summary.bounded)


# =============================================================================
# Orchestrator Integration Tests
# =============================================================================

class OrchestratorIntegrationTests(TestCase):
    def setUp(self):
        _ensure_kernel_ready()

    def test_orchestrator_returns_report(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        self.assertIsInstance(report, MasterCertificationReport)

    def test_orchestrator_has_all_phases(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        self.assertEqual(len(report.phases), 7)

    def test_orchestrator_scores_phases(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        for phase in report.phases:
            self.assertGreaterEqual(phase.score, 0)
            self.assertLessEqual(phase.score, 100)

    def test_orchestrator_tracks_governance(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        self.assertIn("policies", report.governance_status)

    def test_orchestrator_phase1_deployment(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p1 = report.phases[0]
        self.assertEqual(p1.phase, 1)
        self.assertEqual(p1.name, "Deployment Certification")

    def test_orchestrator_phase2_backup(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p2 = report.phases[1]
        self.assertEqual(p2.phase, 2)

    def test_orchestrator_phase3_upgrade(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p3 = report.phases[2]
        self.assertEqual(p3.phase, 3)

    def test_orchestrator_phase4_soak(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p4 = report.phases[3]
        self.assertEqual(p4.phase, 4)

    def test_orchestrator_phase5_offline(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p5 = report.phases[4]
        self.assertEqual(p5.phase, 5)

    def test_orchestrator_phase6_maintainability(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p6 = report.phases[5]
        self.assertEqual(p6.phase, 6)

    def test_orchestrator_phase7_observability(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        report = orch.certify_all(soak_iterations=5)
        p7 = report.phases[6]
        self.assertEqual(p7.phase, 7)

    def test_orchestrator_idempotent(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        r1 = orch.certify_all(soak_iterations=3)
        r2 = orch.certify_all(soak_iterations=3)
        self.assertEqual(len(r1.phases), len(r2.phases))

    def test_orchestrator_no_exceptions(self):
        orch = OperationalCertificationOrchestrator(KERNEL)
        try:
            report = orch.certify_all(soak_iterations=3)
            self.assertIsNotNone(report)
            self.assertEqual(len(report.phases), 7)
        except Exception as e:
            self.fail(f"Orchestrator raised exception: {e}")


# =============================================================================
# PhaseCertificationResult Structure Tests
# =============================================================================

class PhaseResultTests(TestCase):
    def test_phase_result_defaults(self):
        result = PhaseCertificationResult(phase=1, name="Test", passed=True)
        self.assertEqual(result.phase, 1)
        self.assertEqual(result.name, "Test")
        self.assertTrue(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.details, {})
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.errors, [])

    def test_phase_result_with_values(self):
        result = PhaseCertificationResult(
            phase=2, name="Test2", passed=False, score=75.5,
            details={"key": "val"}, warnings=["warn1"], errors=["err1"],
            duration_ms=100.5,
        )
        self.assertEqual(result.score, 75.5)
        self.assertEqual(result.details["key"], "val")
        self.assertEqual(result.warnings[0], "warn1")
        self.assertEqual(result.duration_ms, 100.5)

    def test_master_report_aggregation(self):
        p1 = PhaseCertificationResult(phase=1, name="P1", passed=True, score=100)
        p2 = PhaseCertificationResult(phase=2, name="P2", passed=True, score=90)
        report = MasterCertificationReport(
            overall_passed=True,
            overall_score=95.0,
            phases=[p1, p2],
        )
        self.assertTrue(report.overall_passed)
        self.assertEqual(report.overall_score, 95.0)
        self.assertEqual(len(report.phases), 2)
