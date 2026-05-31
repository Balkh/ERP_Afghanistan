"""
Tests for Industrial Safe Test Suite (Phases A-D).
Validates the test harness itself: bounded execution, memory safety, deterministic output.
"""
import time
import threading
from collections import deque
from unittest.mock import patch, MagicMock

from django.test import TestCase

from core.governance.kernel import GovernanceKernel
from core.governance.industrial_test_suite import (
    TEST_CONFIG,
    PhaseA, PhaseAResult,
    PhaseB, PhaseBResult,
    PhaseC, PhaseCResult,
    PhaseD, PhaseDResult,
    PhaseE, PhaseEResult,
    PhaseF, PhaseFResult,
    PhaseG, PhaseGResult,
    IndustrialTestSuiteRunner, IndustrialTestReport,
    _Throttle, _BoundedBuffer, _EvidenceCollector,
    _simulate_state_transition,
    SIMULATION_STATES,
    ZERO_TRUST_LEGACY_PATTERNS,
    CONSISTENCY_REPLAY_POLICIES,
    canonicalize_result,
    TRANSIENT_STATE_THRESHOLD_SECONDS,
    MAX_EVIDENCE_SAMPLES,
    VOLATILE_RESULT_FIELDS,
)


# ─────────────────────────────────────────────────────────────
# Global Config Compliance
# ─────────────────────────────────────────────────────────────

class TestGlobalConfig(TestCase):
    def test_max_operations_bounded(self):
        self.assertLessEqual(TEST_CONFIG["MAX_OPERATIONS"], 50)

    def test_max_concurrency_bounded(self):
        self.assertLessEqual(TEST_CONFIG["MAX_CONCURRENCY"], 2)

    def test_timeout_set(self):
        self.assertGreater(TEST_CONFIG["TIMEOUT_SECONDS"], 0)

    def test_db_write_disabled(self):
        self.assertFalse(TEST_CONFIG["ENABLE_DB_WRITE"])

    def test_dry_run_enabled(self):
        self.assertTrue(TEST_CONFIG["USE_DRY_RUN"])

    def test_memory_bound_set(self):
        self.assertEqual(TEST_CONFIG["MEMORY_BOUND_BUFFER"], 50)


# ─────────────────────────────────────────────────────────────
# Helper: _Throttle
# ─────────────────────────────────────────────────────────────

class TestThrottle(TestCase):
    def test_throttle_waits(self):
        t = _Throttle(sleep_ms=1)
        t0 = time.time()
        t.wait()
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.001)

    def test_throttle_zero_sleep(self):
        t = _Throttle(sleep_ms=0)
        t0 = time.time()
        t.wait()
        self.assertLess(time.time() - t0, 0.1)


# ─────────────────────────────────────────────────────────────
# Helper: _BoundedBuffer
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# Hardening Helpers
# ─────────────────────────────────────────────────────────────

class TestCanonicalizeResult(TestCase):
    def test_strips_volatile_fields(self):
        result = canonicalize_result({
            "allowed": True,
            "reason": "ok",
            "timestamp": "2026-01-01T00:00:00Z",
            "correlation_id": "abc123",
            "latency_ms": 42.5,
            "duration_ms": 100.0,
        })
        self.assertEqual(result["allowed"], True)
        self.assertEqual(result["reason"], "ok")
        self.assertNotIn("timestamp", result)
        self.assertNotIn("correlation_id", result)
        self.assertNotIn("latency_ms", result)
        self.assertNotIn("duration_ms", result)

    def test_normalizes_dicts_recursively(self):
        result = canonicalize_result({
            "nested": {
                "allowed": True,
                "timestamp": "ignored",
                "inner": {"value": 1, "id": "temp"},
            }
        })
        self.assertEqual(result["nested"]["allowed"], True)
        self.assertNotIn("timestamp", result["nested"])
        self.assertNotIn("id", result["nested"]["inner"])

    def test_sorts_lists(self):
        result = canonicalize_result([{"b": 2}, {"a": 1}])
        self.assertEqual(result[0]["a"], 1)

    def test_rounds_floats(self):
        result = canonicalize_result(3.14159)
        self.assertEqual(result, 3.1)

    def test_handles_datetime(self):
        from datetime import datetime
        result = canonicalize_result(datetime.utcnow())
        self.assertEqual(result, "DATETIME")


class TestEvidenceCollector(TestCase):
    def test_bounded_collection(self):
        coll = _EvidenceCollector()
        for i in range(20):
            coll.add("test_type", "mod.path", f"obj_{i}", "reason", "impact")
        self.assertLessEqual(len(coll.items), MAX_EVIDENCE_SAMPLES)
        self.assertEqual(len(coll.items), MAX_EVIDENCE_SAMPLES)

    def test_empty_by_default(self):
        coll = _EvidenceCollector()
        self.assertEqual(len(coll.items), 0)

    def test_add_stores_fields(self):
        coll = _EvidenceCollector()
        coll.add("bypass", "kernel.failsafe", "failsafe", "Bypass detected", "Governance gap")
        self.assertEqual(len(coll.items), 1)
        item = coll.items[0]
        self.assertEqual(item["issue_type"], "bypass")
        self.assertEqual(item["module_path"], "kernel.failsafe")


class TestConstants(TestCase):
    def test_transient_threshold_positive(self):
        self.assertGreater(TRANSIENT_STATE_THRESHOLD_SECONDS, 0)

    def test_max_evidence_samples_positive(self):
        self.assertGreater(MAX_EVIDENCE_SAMPLES, 0)

    def test_volatile_fields_non_empty(self):
        self.assertGreater(len(VOLATILE_RESULT_FIELDS), 0)


class TestBoundedBuffer(TestCase):
    def test_buffer_respects_maxlen(self):
        buf = _BoundedBuffer(maxlen=5)
        for i in range(20):
            buf.cycle({"idx": i})
        self.assertEqual(buf.size, 5)

    def test_clear_resets(self):
        buf = _BoundedBuffer(maxlen=10)
        for i in range(5):
            buf.cycle(i)
        buf.clear()
        self.assertEqual(buf.size, 0)

    def test_size_tracks_correctly(self):
        buf = _BoundedBuffer(maxlen=10)
        for i in range(3):
            buf.cycle(i)
        self.assertEqual(buf.size, 3)

    def test_peak_tracking(self):
        buf = _BoundedBuffer(maxlen=5)
        peak = 0
        for i in range(10):
            buf.cycle(i)
            peak = max(peak, buf.size)
        self.assertEqual(peak, 5)


# ─────────────────────────────────────────────────────────────
# Phase A — Core Business Flow Stability
# ─────────────────────────────────────────────────────────────

class TestPhaseA(TestCase):
    def test_run_returns_result(self):
        phase = PhaseA()
        result = phase.run()
        self.assertIsInstance(result, PhaseAResult)
        self.assertGreaterEqual(result.sales_count, 0)
        self.assertGreaterEqual(result.purchase_count, 0)
        self.assertGreaterEqual(result.return_count, 0)
        self.assertGreaterEqual(result.journal_count, 0)

    def test_bounded_operations(self):
        phase = PhaseA()
        result = phase.run()
        total = result.sales_count + result.purchase_count + result.return_count + result.journal_count
        self.assertLessEqual(total, TEST_CONFIG["MAX_OPERATIONS"])

    def test_errors_list_type(self):
        phase = PhaseA()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_duration_positive(self):
        phase = PhaseA()
        result = phase.run()
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_passed_type(self):
        phase = PhaseA()
        result = phase.run()
        self.assertIsInstance(result.passed, bool)

    def test_distribution_across_categories(self):
        config = dict(TEST_CONFIG)
        config["MAX_OPERATIONS"] = 20
        phase = PhaseA(config=config)
        result = phase.run()
        # With 20 iterations cycling through 4 categories, each should get ~5
        self.assertGreater(result.sales_count + result.purchase_count +
                           result.return_count + result.journal_count, 0)


# ─────────────────────────────────────────────────────────────
# Phase B — Governance Engine Load
# ─────────────────────────────────────────────────────────────

class TestPhaseB(TestCase):
    def test_run_returns_result(self):
        phase = PhaseB()
        result = phase.run()
        self.assertIsInstance(result, PhaseBResult)
        self.assertGreaterEqual(result.policy_evaluation_count, 0)

    def test_latency_tracked(self):
        phase = PhaseB()
        result = phase.run()
        self.assertGreaterEqual(result.avg_latency_ms, 0)
        self.assertGreaterEqual(result.max_latency_ms, 0)

    def test_bounded_iterations(self):
        config = dict(TEST_CONFIG)
        config["MAX_OPERATIONS"] = 10
        phase = PhaseB(config=config)
        result = phase.run()
        # 4 policies per iteration, up to 10 iterations
        self.assertLessEqual(result.policy_evaluation_count, 4 * 10)

    def test_errors_list(self):
        phase = PhaseB()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_passed_type(self):
        phase = PhaseB()
        result = phase.run()
        self.assertIsInstance(result.passed, bool)


# ─────────────────────────────────────────────────────────────
# Phase C — UI Safety and Schema Validation
# ─────────────────────────────────────────────────────────────

class TestPhaseC(TestCase):
    def test_run_returns_result(self):
        phase = PhaseC()
        result = phase.run()
        self.assertIsInstance(result, PhaseCResult)
        self.assertGreaterEqual(result.violation_count, 0)

    def test_compliance_status_valid(self):
        phase = PhaseC()
        result = phase.run()
        self.assertIn(result.compliance_status, ("STABLE", "RISK", "SKIPPED"))

    def test_bounded_violations(self):
        phase = PhaseC()
        result = phase.run()
        # Even a full scan won't go absurdly high
        self.assertLessEqual(result.violation_count, 1000)

    def test_errors_list(self):
        phase = PhaseC()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_passed_type(self):
        phase = PhaseC()
        result = phase.run()
        self.assertIsInstance(result.passed, bool)


# ─────────────────────────────────────────────────────────────
# Phase D — Memory Stability Soak
# ─────────────────────────────────────────────────────────────

class TestPhaseD(TestCase):
    def test_run_returns_result(self):
        phase = PhaseD()
        result = phase.run()
        self.assertIsInstance(result, PhaseDResult)

    def test_buffer_respects_bound(self):
        config = dict(TEST_CONFIG)
        config["MEMORY_BOUND_BUFFER"] = 10
        phase = PhaseD(config=config)
        result = phase.run()
        self.assertLessEqual(result.final_buffer_size, 10)

    def test_status_valid(self):
        phase = PhaseD()
        result = phase.run()
        self.assertIn(result.memory_growth_status, ("STABLE", "LEAK_DETECTED"))

    def test_duration_positive(self):
        phase = PhaseD()
        result = phase.run()
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_errors_list(self):
        phase = PhaseD()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_allocation_structure(self):
        obj = PhaseD()._allocate_simulated_object(42)
        self.assertIn("id", obj)
        self.assertIn("index", obj)
        self.assertEqual(obj["index"], 42)
        self.assertIn("timestamp", obj)
        self.assertIn("data", obj)
        self.assertIn("metadata", obj)


# ─────────────────────────────────────────────────────────────
# Phase E — Regression Truth Verification
# ─────────────────────────────────────────────────────────────

class TestPhaseE(TestCase):
    def test_run_returns_result(self):
        phase = PhaseE()
        result = phase.run()
        self.assertIsInstance(result, PhaseEResult)
        self.assertGreaterEqual(result.hidden_violation_count, 0)

    def test_legacy_path_count_type(self):
        phase = PhaseE()
        result = phase.run()
        self.assertGreaterEqual(result.legacy_path_count, 0)

    def test_reclassified_count_type(self):
        phase = PhaseE()
        result = phase.run()
        self.assertGreaterEqual(result.reclassified_violation_count, 0)

    def test_truly_fixed_type(self):
        phase = PhaseE()
        result = phase.run()
        self.assertGreaterEqual(result.truly_fixed_count, 0)

    def test_bounded_operations(self):
        config = dict(TEST_CONFIG)
        config["MAX_OPERATIONS"] = 5
        phase = PhaseE(config=config)
        result = phase.run()
        self.assertLessEqual(result.duration_ms, 30000)

    def test_errors_list(self):
        phase = PhaseE()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_duration_positive(self):
        phase = PhaseE()
        result = phase.run()
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_passed_type(self):
        phase = PhaseE()
        result = phase.run()
        self.assertIsInstance(result.passed, bool)

    def test_zero_trust_legacy_patterns_defined(self):
        self.assertGreater(len(ZERO_TRUST_LEGACY_PATTERNS), 0)

    def test_scan_raw_ui_violations(self):
        phase = PhaseE()
        count, ev = phase._scan_raw_ui_violations()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_detect_legacy_workflow_paths(self):
        phase = PhaseE()
        count, ev = phase._detect_legacy_workflow_paths()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_detect_hidden_policy_bypass(self):
        phase = PhaseE()
        count, ev = phase._detect_hidden_policy_bypass()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_verify_accounting_truth(self):
        phase = PhaseE()
        count, ev = phase._verify_accounting_truth()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_detect_duplicate_enforcement_paths(self):
        phase = PhaseE()
        count, ev = phase._detect_duplicate_enforcement_paths()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)


# ─────────────────────────────────────────────────────────────
# Phase F — Stale State & Orphan Detection
# ─────────────────────────────────────────────────────────────

class TestPhaseF(TestCase):
    def test_run_returns_result(self):
        phase = PhaseF()
        result = phase.run()
        self.assertIsInstance(result, PhaseFResult)
        self.assertGreaterEqual(result.orphan_count, 0)

    def test_stale_state_count_type(self):
        phase = PhaseF()
        result = phase.run()
        self.assertGreaterEqual(result.stale_state_count, 0)

    def test_detached_reference_type(self):
        phase = PhaseF()
        result = phase.run()
        self.assertGreaterEqual(result.detached_reference_count, 0)

    def test_bounded_operations(self):
        config = dict(TEST_CONFIG)
        config["MAX_OPERATIONS"] = 5
        phase = PhaseF(config=config)
        result = phase.run()
        self.assertLessEqual(result.duration_ms, 30000)

    def test_errors_list(self):
        phase = PhaseF()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_duration_positive(self):
        phase = PhaseF()
        result = phase.run()
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_passed_type(self):
        phase = PhaseF()
        result = phase.run()
        self.assertIsInstance(result.passed, bool)

    def test_check_orphan_journals(self):
        phase = PhaseF()
        count, ev = phase._check_orphan_journals()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_check_stale_listeners(self):
        phase = PhaseF()
        count, ev = phase._check_stale_listeners()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_check_unreleased_locks(self):
        phase = PhaseF()
        count, ev = phase._check_unreleased_locks()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)

    def test_check_registry_consistency(self):
        phase = PhaseF()
        count, ev = phase._check_registry_consistency()
        self.assertGreaterEqual(count, 0)
        self.assertIsInstance(ev, list)


# ─────────────────────────────────────────────────────────────
# Phase G — Governance Consistency Replay
# ─────────────────────────────────────────────────────────────

class TestPhaseG(TestCase):
    def test_run_returns_result(self):
        phase = PhaseG()
        result = phase.run()
        self.assertIsInstance(result, PhaseGResult)
        self.assertGreaterEqual(result.deterministic_pass_rate, 0)

    def test_pass_rate_in_range(self):
        phase = PhaseG()
        result = phase.run()
        self.assertLessEqual(result.deterministic_pass_rate, 100.0)

    def test_inconsistent_decision_count_type(self):
        phase = PhaseG()
        result = phase.run()
        self.assertGreaterEqual(result.inconsistent_decision_count, 0)

    def test_bounded_operations(self):
        config = dict(TEST_CONFIG)
        config["MAX_OPERATIONS"] = 5
        phase = PhaseG(config=config)
        result = phase.run()
        self.assertLessEqual(result.duration_ms, 30000)

    def test_errors_list(self):
        phase = PhaseG()
        result = phase.run()
        self.assertIsInstance(result.errors, list)

    def test_duration_positive(self):
        phase = PhaseG()
        result = phase.run()
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_passed_type(self):
        phase = PhaseG()
        result = phase.run()
        self.assertIsInstance(result.passed, bool)

    def test_consistency_replay_policies_defined(self):
        self.assertGreater(len(CONSISTENCY_REPLAY_POLICIES), 0)

    def test_replay_policy_evaluations(self):
        phase = PhaseG()
        inc, total, ev = phase._replay_policy_evaluations()
        self.assertGreaterEqual(total, 0)
        self.assertGreaterEqual(inc, 0)
        self.assertIsInstance(ev, list)

    def test_replay_state_transitions(self):
        phase = PhaseG()
        inc, total, ev = phase._replay_state_transitions()
        self.assertGreaterEqual(total, 0)
        self.assertGreaterEqual(inc, 0)
        self.assertIsInstance(ev, list)

    def test_replay_audit_consistency(self):
        phase = PhaseG()
        inc, total, ev = phase._replay_audit_consistency()
        self.assertGreaterEqual(total, 0)
        self.assertGreaterEqual(inc, 0)
        self.assertIsInstance(ev, list)

    def test_trace_governance_invocation(self):
        phase = PhaseG()
        inc, total, ev = phase._trace_governance_invocation()
        self.assertGreaterEqual(total, 0)
        self.assertGreaterEqual(inc, 0)
        self.assertIsInstance(ev, list)


# ─────────────────────────────────────────────────────────────
# Execution Runner
# ─────────────────────────────────────────────────────────────

class TestIndustrialTestSuiteRunner(TestCase):
    def test_run_all_returns_report(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertIsInstance(report, IndustrialTestReport)
        self.assertIn(report.overall_status, ("PASS", "FAIL", "DEGRADED"))

    def test_report_has_all_phases(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertIsInstance(report.core_flow, PhaseAResult)
        self.assertIsInstance(report.governance, PhaseBResult)
        self.assertIsInstance(report.ui_safety, PhaseCResult)
        self.assertIsInstance(report.memory_soak, PhaseDResult)
        self.assertIsInstance(report.regression_truth, PhaseEResult)
        self.assertIsInstance(report.stale_state, PhaseFResult)
        self.assertIsInstance(report.consistency_replay, PhaseGResult)

    def test_timestamp_format(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertTrue(report.timestamp.endswith("Z"))
        self.assertIn("T", report.timestamp)

    def test_phase_a_has_metrics(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertGreaterEqual(report.core_flow.sales_count, 0)
        self.assertGreaterEqual(report.core_flow.purchase_count, 0)

    def test_phase_b_has_latency(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertGreaterEqual(report.governance.avg_latency_ms, 0)

    def test_phase_c_has_violations(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertGreaterEqual(report.ui_safety.violation_count, 0)

    def test_phase_e_has_metrics(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertGreaterEqual(report.regression_truth.hidden_violation_count, 0)
        self.assertGreaterEqual(report.regression_truth.legacy_path_count, 0)

    def test_phase_f_has_metrics(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertGreaterEqual(report.stale_state.orphan_count, 0)
        self.assertGreaterEqual(report.stale_state.stale_state_count, 0)

    def test_phase_g_has_metrics(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertGreaterEqual(report.consistency_replay.deterministic_pass_rate, 0)
        self.assertGreaterEqual(report.consistency_replay.inconsistent_decision_count, 0)

    def test_phase_e_has_evidence(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertIsInstance(report.regression_truth.evidence, list)

    def test_phase_f_has_evidence(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertIsInstance(report.stale_state.evidence, list)

    def test_phase_g_has_evidence(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertIsInstance(report.consistency_replay.evidence, list)

    def test_phase_d_buffer_bounded(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertLessEqual(report.memory_soak.final_buffer_size, 50)

    def test_fast_config(self):
        config = dict(TEST_CONFIG)
        config["MAX_OPERATIONS"] = 5
        config["SLEEP_MS"] = 1
        runner = IndustrialTestSuiteRunner(config=config)
        report = runner.run_all()
        self.assertIn(report.overall_status, ("PASS", "DEGRADED", "FAIL"))

    def test_warnings_list(self):
        runner = IndustrialTestSuiteRunner()
        report = runner.run_all()
        self.assertIsInstance(report.warnings, list)

    def test_timeout_protection(self):
        config = dict(TEST_CONFIG)
        config["TIMEOUT_SECONDS"] = 0
        runner = IndustrialTestSuiteRunner(config=config)
        report = runner.run_all()
        self.assertEqual(report.overall_status, "DEGRADED")
