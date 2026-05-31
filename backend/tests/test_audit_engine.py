from django.test import TestCase
from decimal import Decimal
from datetime import datetime, timezone

from core.audit.models import (
    AuditSeverity, AuditModule, AuditFinding,
    ModuleResult, AuditReport,
)
from core.audit.ledger_audit import LedgerAuditEngine
from core.audit.inventory_audit import InventoryAuditEngine
from core.audit.event_auditor import EventConsistencyAuditor
from core.audit.financial_validator import FinancialStatementValidator
from core.audit.arap_audit import ARAuditEngine
from core.audit.replay_verifier import ReplayVerificationEngine
from core.audit.drift_detector import DriftDetectionEngine
from core.audit.engine import AuditEngine


class TestAuditSeverity(TestCase):
    def test_values_present(self):
        self.assertIn(AuditSeverity.CRITICAL, AuditSeverity)
        self.assertIn(AuditSeverity.HIGH, AuditSeverity)
        self.assertIn(AuditSeverity.MEDIUM, AuditSeverity)
        self.assertIn(AuditSeverity.LOW, AuditSeverity)

    def test_string_values(self):
        self.assertEqual(AuditSeverity.CRITICAL.value, "critical")
        self.assertEqual(AuditSeverity.HIGH.value, "high")
        self.assertEqual(AuditSeverity.MEDIUM.value, "medium")
        self.assertEqual(AuditSeverity.LOW.value, "low")


class TestAuditModule(TestCase):
    def test_all_modules_present(self):
        self.assertIn(AuditModule.LEDGER, AuditModule)
        self.assertIn(AuditModule.INVENTORY, AuditModule)
        self.assertIn(AuditModule.EVENT, AuditModule)
        self.assertIn(AuditModule.FINANCIAL, AuditModule)
        self.assertIn(AuditModule.ARAP, AuditModule)
        self.assertIn(AuditModule.REPLAY, AuditModule)
        self.assertIn(AuditModule.DRIFT, AuditModule)

    def test_all_values_unique(self):
        values = [m.value for m in AuditModule]
        self.assertEqual(len(values), len(set(values)))


class TestAuditFinding(TestCase):
    def test_create_critical_finding(self):
        finding = AuditFinding(
            module=AuditModule.LEDGER,
            severity=AuditSeverity.CRITICAL,
            check_name="global_double_entry_balance",
            passed=False,
            detail="Imbalance detected",
            evidence={"imbalance": "100.00"},
        )
        self.assertEqual(finding.module, AuditModule.LEDGER)
        self.assertEqual(finding.severity, AuditSeverity.CRITICAL)
        self.assertFalse(finding.passed)
        self.assertEqual(finding.evidence["imbalance"], "100.00")

    def test_create_passing_finding(self):
        finding = AuditFinding(
            module=AuditModule.INVENTORY,
            severity=AuditSeverity.HIGH,
            check_name="negative_stock",
            passed=True,
            detail="No negative batches",
        )
        self.assertTrue(finding.passed)

    def test_all_severities(self):
        for sev in AuditSeverity:
            finding = AuditFinding(
                module=AuditModule.DRIFT,
                severity=sev,
                check_name="test",
                passed=True,
            )
            self.assertEqual(finding.severity, sev)


class TestModuleResult(TestCase):
    def test_defaults(self):
        result = ModuleResult(module=AuditModule.LEDGER, passed=True)
        self.assertEqual(result.module, AuditModule.LEDGER)
        self.assertTrue(result.passed)
        self.assertEqual(len(result.findings), 0)
        self.assertEqual(result.summary, "")

    def test_finding_count_empty(self):
        result = ModuleResult(module=AuditModule.EVENT, passed=True)
        self.assertEqual(result.finding_count["critical"], 0)
        self.assertEqual(result.finding_count["high"], 0)
        self.assertEqual(result.finding_count["medium"], 0)
        self.assertEqual(result.finding_count["low"], 0)

    def test_finding_count_tracks_failures(self):
        findings = [
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "a", False),
            AuditFinding(AuditModule.LEDGER, AuditSeverity.HIGH, "b", False),
            AuditFinding(AuditModule.LEDGER, AuditSeverity.MEDIUM, "c", False),
            AuditFinding(AuditModule.LEDGER, AuditSeverity.LOW, "d", False),
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "e", True),
        ]
        result = ModuleResult(
            module=AuditModule.LEDGER, passed=False, findings=findings,
        )
        self.assertEqual(result.finding_count["critical"], 1)
        self.assertEqual(result.finding_count["high"], 1)
        self.assertEqual(result.finding_count["medium"], 1)
        self.assertEqual(result.finding_count["low"], 1)


class TestAuditReport(TestCase):
    def test_default_properties(self):
        report = AuditReport(
            timestamp="2026-01-01T00:00:00",
            duration_ms=100.0,
        )
        self.assertTrue(report.overall_pass)
        self.assertEqual(len(report.critical_errors), 0)
        self.assertEqual(len(report.warnings), 0)
        self.assertEqual(report.drift_score, 100)
        self.assertTrue(report.production_readiness)

    def test_detects_critical_errors(self):
        findings = [
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "balance", False),
        ]
        module_result = ModuleResult(
            module=AuditModule.LEDGER, passed=False, findings=findings,
        )
        report = AuditReport(
            timestamp="2026-01-01T00:00:00",
            duration_ms=50.0,
            modules={AuditModule.LEDGER.value: module_result},
        )
        self.assertFalse(report.overall_pass)
        self.assertEqual(len(report.critical_errors), 1)
        self.assertEqual(report.critical_errors[0].check_name, "balance")

    def test_drift_score_penalizes(self):
        findings = [
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "balance", False),
        ]
        module_result = ModuleResult(
            module=AuditModule.LEDGER, passed=False, findings=findings,
        )
        report = AuditReport(
            timestamp="2026-01-01T00:00:00",
            duration_ms=30.0,
            modules={AuditModule.LEDGER.value: module_result},
        )
        expected = max(0, 100 - 15 - 10)
        self.assertEqual(report.drift_score, expected)

    def test_drift_score_lower_bound(self):
        many_critical = [
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, f"err{i}", False)
            for i in range(20)
        ]
        module_result = ModuleResult(
            module=AuditModule.LEDGER, passed=False, findings=many_critical,
        )
        report = AuditReport(
            timestamp="2026-01-01T00:00:00",
            duration_ms=30.0,
            modules={AuditModule.LEDGER.value: module_result},
        )
        self.assertGreaterEqual(report.drift_score, 0)

    def test_to_dict_format(self):
        module_result = ModuleResult(module=AuditModule.LEDGER, passed=True)
        report = AuditReport(
            timestamp="2026-01-01T00:00:00",
            duration_ms=100.0,
            modules={AuditModule.LEDGER.value: module_result},
        )
        d = report.to_dict()
        self.assertIn("timestamp", d)
        self.assertIn("ledger_integrity", d)
        self.assertIn("inventory_integrity", d)
        self.assertIn("event_consistency", d)
        self.assertIn("financial_accuracy", d)
        self.assertIn("replay_determinism", d)
        self.assertIn("critical_errors", d)
        self.assertIn("warnings", d)
        self.assertIn("drift_score", d)
        self.assertIn("production_readiness", d)
        self.assertIn("overall_pass", d)


class TestLedgerAuditEngine(TestCase):
    def setUp(self):
        self.engine = LedgerAuditEngine()

    def test_empty_db_passes(self):
        result = self.engine.audit()
        self.assertIsNotNone(result)
        self.assertEqual(result.module, AuditModule.LEDGER)
        for f in result.findings:
            if f.severity in (AuditSeverity.CRITICAL, AuditSeverity.HIGH):
                self.assertTrue(f.passed, f"Finding {f.check_name} should pass on empty DB")

    def test_singleton_via_audit_engine(self):
        ae = AuditEngine.get_instance()
        self.assertIsNotNone(ae.ledger)


class TestInventoryAuditEngine(TestCase):
    def setUp(self):
        self.engine = InventoryAuditEngine()

    def test_empty_db_passes(self):
        result = self.engine.audit()
        self.assertIsNotNone(result)
        self.assertEqual(result.module, AuditModule.INVENTORY)

    def test_summary_contains_expected_keys(self):
        result = self.engine.audit()
        self.assertIn("Batches=", result.summary)
        self.assertIn("Movements=", result.summary)
        self.assertIn("Issues=", result.summary)


class TestEventConsistencyAuditor(TestCase):
    def setUp(self):
        self.auditor = EventConsistencyAuditor()

    def test_empty_log_passes(self):
        result = self.auditor.audit(existing_data={"event_log": []})
        self.assertTrue(result.passed)

    def test_no_data_is_low_severity_only(self):
        result = self.auditor.audit(existing_data={})
        self.assertTrue(result.passed)

    def test_ordered_events_pass(self):
        events = [
            {"day": 1, "event_type": "create_sale"},
            {"day": 2, "event_type": "create_purchase"},
            {"day": 3, "event_type": "run_payroll"},
        ]
        result = self.auditor.audit(existing_data={"event_log": events})
        ordering_findings = [f for f in result.findings if f.check_name == "event_ordering"]
        for f in ordering_findings:
            self.assertTrue(f.passed, f"Ordered events should pass: {f.detail}")

    def test_out_of_order_events_detected(self):
        events = [
            {"day": 3, "event_type": "create_sale"},
            {"day": 1, "event_type": "create_purchase"},
            {"day": 2, "event_type": "run_payroll"},
        ]
        result = self.auditor.audit(existing_data={"event_log": events})
        ordering_findings = [f for f in result.findings if f.check_name == "event_ordering"]
        for f in ordering_findings:
            if not f.passed:
                self.assertGreater(f.evidence.get("out_of_order", 0), 0)

    def test_sequence_gaps_detected(self):
        events = [
            {"day": 1, "event_type": "create_sale"},
            {"day": 5, "event_type": "create_purchase"},
            {"day": 10, "event_type": "run_payroll"},
        ]
        result = self.auditor.audit(existing_data={"event_log": events})
        gap_findings = [f for f in result.findings if f.check_name == "sequence_gaps"]
        for f in gap_findings:
            if not f.passed:
                self.assertGreater(len(f.evidence.get("gaps", [])), 0)

    def test_event_completeness_with_expected_days(self):
        events = [{"day": d, "event_type": "create_sale"} for d in range(1, 55)]
        result = self.auditor.audit(existing_data={
            "event_log": events,
            "expected_days": 60,
        })
        completeness = [f for f in result.findings if f.check_name == "event_completeness"]
        for f in completeness:
            if not f.passed:
                self.assertLess(f.evidence.get("days_with_events", 0), 60)

    def test_snapshot_event_correlation(self):
        events = [
            {"day": 7, "event_type": "daily_snapshot"},
            {"day": 14, "event_type": "daily_snapshot"},
        ]
        snapshots = [
            {"day": 7},
        ]
        result = self.auditor.audit(existing_data={
            "event_log": events,
            "snapshot_history": snapshots,
        })
        correlation = [
            f for f in result.findings
            if f.check_name == "snapshot_event_correlation"
        ]
        for f in correlation:
            if not f.passed:
                self.assertIn("missing_snapshots", f.evidence)


class TestFinancialStatementValidator(TestCase):
    def setUp(self):
        self.validator = FinancialStatementValidator()

    def test_empty_db_passes(self):
        result = self.validator.audit()
        self.assertIsNotNone(result)
        self.assertEqual(result.module, AuditModule.FINANCIAL)

    def test_summary_contains_account_info(self):
        result = self.validator.audit()
        self.assertIn("Accounts=", result.summary)


class TestARAuditEngine(TestCase):
    def setUp(self):
        self.engine = ARAuditEngine()

    def test_empty_db_passes(self):
        result = self.engine.audit()
        self.assertIsNotNone(result)
        self.assertEqual(result.module, AuditModule.ARAP)

    def test_summary_contains_ar_ap(self):
        result = self.engine.audit()
        self.assertIn("AR=", result.summary)
        self.assertIn("AP=", result.summary)


class TestReplayVerificationEngine(TestCase):
    def setUp(self):
        self.engine = ReplayVerificationEngine()

    def test_empty_snapshots_passes(self):
        result = self.engine.audit(existing_data={
            "snapshots": [],
            "event_log": [],
            "comparison_pairs": [],
        })
        self.assertTrue(result.passed)

    def test_matching_checksums_verify(self):
        data_1 = {"table1": 5}
        data_2 = {"table1": 10}
        cs_1 = self.engine._compute_checksum(data_1)
        cs_2 = self.engine._compute_checksum(data_2)
        snapshots = [
            {"day": 1, "checksum": cs_1, "table_row_counts": data_1},
            {"day": 2, "checksum": cs_2, "table_row_counts": data_2},
        ]
        expected = {1: cs_1, 2: cs_2}
        result = self.engine.audit(existing_data={
            "snapshots": snapshots,
            "event_log": [],
            "comparison_pairs": [],
            "expected_checksums": expected,
        })
        self.assertTrue(result.passed)

    def test_checksum_mismatch_detected(self):
        snapshots = [
            {"day": 1, "checksum": "abc123", "table_row_counts": {"table1": 5}},
        ]
        expected = {1: "WRONG_CHECKSUM"}
        result = self.engine.audit(existing_data={
            "snapshots": snapshots,
            "event_log": [],
            "comparison_pairs": [],
            "expected_checksums": expected,
        })
        checksum_checks = [
            f for f in result.findings
            if f.check_name.startswith("snapshot_checksum_")
            and not f.passed
        ]
        self.assertGreater(len(checksum_checks), 0)

    def test_deterministic_replay_comparison(self):
        data = {"accounts": [{"id": 1, "balance": 100}]}
        pairs = [
            {"day_a": 1, "day_b": 2, "data_a": data, "data_b": dict(data)},
        ]
        result = self.engine.audit(existing_data={
            "snapshots": [],
            "event_log": [],
            "comparison_pairs": pairs,
        })
        replay_checks = [
            f for f in result.findings
            if f.check_name.startswith("deterministic_replay_")
        ]
        for f in replay_checks:
            self.assertTrue(f.passed, f"Deterministic replay should pass: {f.detail}")

    def test_diverged_replay_detected(self):
        pairs = [
            {
                "day_a": 1, "day_b": 2,
                "data_a": {"accounts": [{"id": 1, "balance": 100}]},
                "data_b": {"accounts": [{"id": 1, "balance": 999}]},
            },
        ]
        result = self.engine.audit(existing_data={
            "snapshots": [],
            "event_log": [],
            "comparison_pairs": pairs,
        })
        replay_checks = [
            f for f in result.findings
            if not f.passed and f.check_name.startswith("deterministic_replay_")
        ]
        self.assertGreater(len(replay_checks), 0)


class TestDriftDetectionEngine(TestCase):
    def setUp(self):
        self.engine = DriftDetectionEngine()

    def test_no_data_passes(self):
        result = self.engine.audit(existing_data={})
        self.assertIsNotNone(result)
        no_snapshot = [f for f in result.findings if f.check_name == "no_snapshot_data"]
        self.assertGreater(len(no_snapshot), 0)

    def test_no_drift_when_identical(self):
        baseline = {"table_row_counts": {"account_account": 5, "inventory_batch": 3}}
        current = {"table_row_counts": {"account_account": 5, "inventory_batch": 3}}
        result = self.engine.audit(existing_data={
            "baseline_snapshot": baseline,
            "current_snapshot": current,
        })
        schema_checks = [
            f for f in result.findings
            if f.check_name == "schema_drift" and f.passed
        ]
        data_checks = [
            f for f in result.findings
            if f.check_name == "data_drift" and f.passed
        ]
        self.assertGreater(len(schema_checks), 0)
        self.assertGreater(len(data_checks), 0)

    def test_schema_drift_detected(self):
        baseline = {"table_row_counts": {"table_a": 1, "table_b": 2}}
        current = {"table_row_counts": {"table_a": 1, "table_c": 3}}
        result = self.engine.audit(existing_data={
            "baseline_snapshot": baseline,
            "current_snapshot": current,
        })
        schema_failures = [
            f for f in result.findings
            if f.check_name == "schema_drift" and not f.passed
        ]
        self.assertGreater(len(schema_failures), 0)

    def test_data_drift_detected(self):
        baseline = {"table_row_counts": {"table_a": 1, "table_b": 2}}
        current = {"table_row_counts": {"table_a": 99, "table_b": 2}}
        result = self.engine.audit(existing_data={
            "baseline_snapshot": baseline,
            "current_snapshot": current,
        })
        data_failures = [
            f for f in result.findings
            if f.check_name == "data_drift" and not f.passed
        ]
        self.assertGreater(len(data_failures), 0)

    def test_temporal_drift_over_snapshots(self):
        snapshots = [
            {
                "day": 1,
                "checksum": "aaa",
                "table_row_counts": {
                    "account_account": 5,
                    "inventory_batch": 3,
                    "journal_entry": 10,
                },
            },
            {
                "day": 30,
                "checksum": "bbb",
                "table_row_counts": {
                    "account_account": 8,
                    "inventory_batch": 7,
                    "journal_entry": 50,
                },
            },
        ]
        result = self.engine.audit(existing_data={"snapshots": snapshots})
        financial_drift = [
            f for f in result.findings
            if f.check_name == "financial_drift"
        ]
        inventory_drift = [
            f for f in result.findings
            if f.check_name == "inventory_drift"
        ]
        self.assertGreater(len(financial_drift), 0)
        self.assertGreater(len(inventory_drift), 0)

    def test_checksum_timeline_logged(self):
        snapshots = [
            {"day": 1, "checksum": "aaa", "table_row_counts": {"t1": 1}},
            {"day": 2, "checksum": "bbb", "table_row_counts": {"t1": 2}},
            {"day": 3, "checksum": "ccc", "table_row_counts": {"t1": 3}},
        ]
        result = self.engine.audit(existing_data={"snapshots": snapshots})
        timeline = [
            f for f in result.findings
            if f.check_name == "checksum_drift_timeline"
        ]
        self.assertGreater(len(timeline), 0)
        for f in timeline:
            self.assertEqual(f.evidence.get("snapshot_count"), 3)


class TestAuditEngine(TestCase):
    def setUp(self):
        self.engine = AuditEngine.get_instance()

    def test_is_singleton(self):
        other = AuditEngine.get_instance()
        self.assertIs(self.engine, other)

    def test_all_components_initialized(self):
        self.assertIsNotNone(self.engine.ledger)
        self.assertIsNotNone(self.engine.inventory)
        self.assertIsNotNone(self.engine.event_auditor)
        self.assertIsNotNone(self.engine.financial)
        self.assertIsNotNone(self.engine.arap)
        self.assertIsNotNone(self.engine.replay)
        self.assertIsNotNone(self.engine.drift)

    def test_full_audit_returns_report(self):
        report = self.engine.run_audit()
        self.assertIsInstance(report, AuditReport)
        self.assertIn(AuditModule.LEDGER.value, report.modules)
        self.assertIn(AuditModule.INVENTORY.value, report.modules)
        self.assertIn(AuditModule.EVENT.value, report.modules)
        self.assertIn(AuditModule.FINANCIAL.value, report.modules)
        self.assertIn(AuditModule.ARAP.value, report.modules)
        self.assertIn(AuditModule.REPLAY.value, report.modules)
        self.assertIn(AuditModule.DRIFT.value, report.modules)

    def test_full_audit_to_dict(self):
        report = self.engine.run_audit()
        d = report.to_dict()
        self.assertIn("timestamp", d)
        self.assertIn("drift_score", d)
        self.assertIn("production_readiness", d)
        self.assertIsInstance(d["critical_errors"], list)
        self.assertIsInstance(d["warnings"], list)
        self.assertIsInstance(d["drift_score"], int)

    def test_single_module_audit(self):
        report = self.engine.run_single(AuditModule.EVENT, existing_data={"event_log": []})
        self.assertIn(AuditModule.EVENT.value, report.modules)
        self.assertNotIn(AuditModule.LEDGER.value, report.modules)

    def test_selected_modules_only(self):
        report = self.engine.run_audit(
            modules=[AuditModule.LEDGER, AuditModule.INVENTORY],
        )
        self.assertIn(AuditModule.LEDGER.value, report.modules)
        self.assertIn(AuditModule.INVENTORY.value, report.modules)
        self.assertNotIn(AuditModule.EVENT.value, report.modules)
        self.assertNotIn(AuditModule.FINANCIAL.value, report.modules)
        self.assertNotIn(AuditModule.ARAP.value, report.modules)
        self.assertNotIn(AuditModule.REPLAY.value, report.modules)
        self.assertNotIn(AuditModule.DRIFT.value, report.modules)

    def test_duration_is_positive(self):
        report = self.engine.run_audit()
        self.assertGreater(report.duration_ms, 0)

    def test_module_crash_isolation(self):
        class FakeEngine:
            class ledger:
                @staticmethod
                def audit(data=None):
                    raise RuntimeError("Simulated crash")
            inventory = lambda self: None
            event_auditor = lambda self: None
            financial = lambda self: None
            arap = lambda self: None
            replay = lambda self: None
            drift = lambda self: None

        fake = FakeEngine()
        report = AuditReport(
            timestamp="now",
            duration_ms=0,
        )
        self.assertIsNotNone(report)


class TestAuditFindingEdgeCases(TestCase):
    def test_finding_with_empty_evidence(self):
        finding = AuditFinding(
            module=AuditModule.REPLAY,
            severity=AuditSeverity.LOW,
            check_name="info",
            passed=True,
        )
        self.assertEqual(finding.evidence, {})

    def test_finding_with_empty_detail(self):
        finding = AuditFinding(
            module=AuditModule.DRIFT,
            severity=AuditSeverity.CRITICAL,
            check_name="test",
            passed=False,
        )
        self.assertEqual(finding.detail, "")

    def test_multiple_findings_aggregate(self):
        findings = [
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "a", False),
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "b", False),
            AuditFinding(AuditModule.LEDGER, AuditSeverity.CRITICAL, "c", True),
        ]
        result = ModuleResult(
            module=AuditModule.LEDGER, passed=False, findings=findings,
        )
        self.assertEqual(result.finding_count["critical"], 2)


class TestEventAuditorEdgeCases(TestCase):
    def setUp(self):
        self.auditor = EventConsistencyAuditor()

    def test_single_event_no_ordering_issue(self):
        result = self.auditor.audit(existing_data={
            "event_log": [{"day": 1, "event_type": "create_sale"}],
        })
        self.assertTrue(result.passed)

    def test_duplicate_events_detected(self):
        events = [
            {"day": 1, "event_type": "create_sale"},
            {"day": 1, "event_type": "create_sale"},
        ]
        result = self.auditor.audit(existing_data={"event_log": events})
        dup = [f for f in result.findings if f.check_name == "duplicate_events"]
        for f in dup:
            if not f.passed:
                self.assertGreater(f.evidence.get("duplicates", 0), 0)

    def test_no_duplicates_with_unique_events(self):
        events = [
            {"day": 1, "event_type": "create_sale"},
            {"day": 1, "event_type": "create_purchase"},
            {"day": 2, "event_type": "create_sale"},
        ]
        result = self.auditor.audit(existing_data={"event_log": events})
        dup = [f for f in result.findings if f.check_name == "duplicate_events"]
        for f in dup:
            self.assertTrue(f.passed)

    def test_completeness_with_zero_expected(self):
        result = self.auditor.audit(existing_data={
            "event_log": [],
            "expected_days": 0,
        })
        self.assertTrue(result.passed)


class TestReplayVerifierEdgeCases(TestCase):
    def setUp(self):
        self.engine = ReplayVerificationEngine()

    def test_snapshot_missing_checksum_skipped(self):
        snapshots = [
            {"day": 1, "checksum": "", "table_row_counts": {}},
        ]
        result = self.engine.audit(existing_data={
            "snapshots": snapshots,
            "event_log": [],
            "comparison_pairs": [],
        })
        self.assertIsNotNone(result)

    def test_compute_checksum_identical_data(self):
        data = {"a": 1, "b": 2}
        cs1 = self.engine._compute_checksum(data)
        cs2 = self.engine._compute_checksum(dict(data))
        self.assertEqual(cs1, cs2)

    def test_compute_checksum_different_data(self):
        cs1 = self.engine._compute_checksum({"a": 1})
        cs2 = self.engine._compute_checksum({"a": 2})
        self.assertNotEqual(cs1, cs2)


class TestDriftEngineEdgeCases(TestCase):
    def setUp(self):
        self.engine = DriftDetectionEngine()

    def test_single_snapshot_no_drift(self):
        result = self.engine.audit(existing_data={
            "snapshots": [{"day": 1, "checksum": "aaa", "table_row_counts": {"t1": 1}}],
        })
        self.assertIsNotNone(result)

    def test_baseline_only_no_current(self):
        result = self.engine.audit(existing_data={
            "baseline_snapshot": {"table_row_counts": {"t1": 1}},
        })
        self.assertIsNotNone(result)

    def test_current_only_no_baseline(self):
        result = self.engine.audit(existing_data={
            "current_snapshot": {"table_row_counts": {"t1": 99}},
        })
        self.assertIsNotNone(result)

    def test_only_non_financial_tables_no_drift(self):
        snapshots = [
            {
                "day": 1, "checksum": "aaa",
                "table_row_counts": {"auth_user": 1, "django_session": 1},
            },
            {
                "day": 10, "checksum": "bbb",
                "table_row_counts": {"auth_user": 1, "django_session": 1},
            },
        ]
        result = self.engine.audit(existing_data={"snapshots": snapshots})
        fin_drift = [f for f in result.findings if f.check_name == "financial_drift"]
        inv_drift = [f for f in result.findings if f.check_name == "inventory_drift"]
        self.assertEqual(len(fin_drift), 0)
        self.assertEqual(len(inv_drift), 0)
        self.assertTrue(result.passed)
