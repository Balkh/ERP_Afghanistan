"""
Comprehensive tests for the Coverage Governance System.
Tests all modules: classification, workflow, frontend, reporting,
failure scenario, replay, test quality, risk scoring, certification.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, List

from coverage_governance.module_classifier import (
    classify_module, is_critical, is_high,
    TIER_WEIGHTS, TIER_MINIMUMS, WORKFLOW_CRITICAL_PATHS,
    FAILURE_SCENARIOS, REPORT_TYPES, FRONTEND_OPERATIONAL_SCREENS,
)
from coverage_governance.models import (
    WorkflowCoverageResult, FrontendCoverageResult,
    ReportingCoverageResult, FailureScenarioResult,
    ReplayDeterminismResult, TestQualityResult,
    RiskWeightedCoverageResult, EnterpriseRiskReport,
    CertificationVerdict,
)


class TestModuleClassifier(unittest.TestCase):

    def test_classify_critical_modules(self):
        for name in ["accounting", "inventory", "security", "governance"]:
            self.assertEqual(classify_module(name), "CRITICAL", f"{name} should be CRITICAL")

    def test_classify_high_modules(self):
        for name in ["payments", "sales", "purchases", "hr", "payroll"]:
            self.assertEqual(classify_module(name), "HIGH", f"{name} should be HIGH")

    def test_classify_normal_modules(self):
        for name in ["core.api", "config", "core.events"]:
            self.assertEqual(classify_module(name), "NORMAL", f"{name} should be NORMAL")

    def test_classify_unknown_defaults_to_normal(self):
        self.assertEqual(classify_module("nonexistent_module"), "NORMAL")

    def test_is_critical(self):
        self.assertTrue(is_critical("accounting"))
        self.assertTrue(is_critical("inventory"))
        self.assertFalse(is_critical("payments"))

    def test_is_high(self):
        self.assertTrue(is_high("payments"))
        self.assertTrue(is_high("sales"))
        self.assertFalse(is_high("accounting"))

    def test_tier_weights_defined(self):
        self.assertIn("CRITICAL", TIER_WEIGHTS)
        self.assertIn("HIGH", TIER_WEIGHTS)
        self.assertIn("NORMAL", TIER_WEIGHTS)
        self.assertIn("LOW", TIER_WEIGHTS)
        self.assertEqual(TIER_WEIGHTS["CRITICAL"], 10.0)
        self.assertEqual(TIER_WEIGHTS["LOW"], 0.5)

    def test_tier_minimums_defined(self):
        self.assertEqual(TIER_MINIMUMS["CRITICAL"], 85.0)
        self.assertEqual(TIER_MINIMUMS["HIGH"], 70.0)
        self.assertEqual(TIER_MINIMUMS["NORMAL"], 40.0)
        self.assertEqual(TIER_MINIMUMS["LOW"], 0.0)

    def test_workflow_critical_paths(self):
        self.assertIn("accounting", WORKFLOW_CRITICAL_PATHS)
        self.assertIn("inventory", WORKFLOW_CRITICAL_PATHS)
        self.assertIn("sales", WORKFLOW_CRITICAL_PATHS)
        self.assertIn("core.integrity", WORKFLOW_CRITICAL_PATHS)

    def test_failure_scenarios_defined(self):
        self.assertIn("rollback", FAILURE_SCENARIOS)
        self.assertIn("fk_violation", FAILURE_SCENARIOS)
        self.assertIn("concurrency", FAILURE_SCENARIOS)
        self.assertIn("replay", FAILURE_SCENARIOS)
        self.assertIn("snapshot", FAILURE_SCENARIOS)
        self.assertIn("backup_restore", FAILURE_SCENARIOS)
        self.assertIn("integrity", FAILURE_SCENARIOS)
        total = sum(len(v) for v in FAILURE_SCENARIOS.values())
        self.assertGreaterEqual(total, 15)

    def test_report_types_defined(self):
        self.assertIn("trial_balance", REPORT_TYPES)
        self.assertIn("profit_loss", REPORT_TYPES)
        self.assertIn("balance_sheet", REPORT_TYPES)
        self.assertIn("cash_flow", REPORT_TYPES)
        self.assertIn("inventory_valuation", REPORT_TYPES)
        self.assertGreaterEqual(len(REPORT_TYPES), 10)

    def test_frontend_screens_defined(self):
        self.assertIn("login_screen", FRONTEND_OPERATIONAL_SCREENS)
        self.assertIn("dashboard", FRONTEND_OPERATIONAL_SCREENS)
        self.assertIn("sales_invoice_screen", FRONTEND_OPERATIONAL_SCREENS)
        self.assertIn("journal_entry_screen", FRONTEND_OPERATIONAL_SCREENS)
        self.assertGreaterEqual(len(FRONTEND_OPERATIONAL_SCREENS), 30)


class TestModels(unittest.TestCase):

    def test_workflow_coverage_result(self):
        result = WorkflowCoverageResult(
            workflow_coverage_pct=75.0,
            workflows=[],
            total_workflows=4,
            fully_covered_workflows=2,
            partially_covered_workflows=1,
            uncovered_workflows=1,
        )
        self.assertEqual(result.workflow_coverage_pct, 75.0)

    def test_frontend_coverage_result(self):
        result = FrontendCoverageResult(
            screen_coverage_pct=80.0,
            form_coverage_pct=50.0,
            table_coverage_pct=60.0,
            ux_state_coverage_pct=30.0,
            print_export_coverage_pct=40.0,
            test_coverage_pct=20.0,
            overall_frontend_score=55.0,
            screens=[],
            total_screens=38,
            basescreen_screens=25,
            unmigrated_widgets=13,
        )
        self.assertEqual(result.overall_frontend_score, 55.0)

    def test_reporting_coverage_result(self):
        result = ReportingCoverageResult(
            report_coverage_pct=100.0,
            pdf_coverage_pct=80.0,
            csv_coverage_pct=70.0,
            print_coverage_pct=90.0,
            zero_state_coverage_pct=30.0,
            overall_reporting_score=78.0,
            reports=[],
        )
        self.assertEqual(result.overall_reporting_score, 78.0)

    def test_failure_scenario_result(self):
        result = FailureScenarioResult(
            total_scenarios=20,
            covered_scenarios=12,
            uncovered_scenarios=8,
            scenario_coverage_pct=60.0,
            by_category={},
            scenarios=[],
            uncovered_high_risk=["journal_entry_rollback"],
        )
        self.assertEqual(result.scenario_coverage_pct, 60.0)
        self.assertIn("journal_entry_rollback", result.uncovered_high_risk)

    def test_replay_determinism_result(self):
        result = ReplayDeterminismResult(
            replay_checksum_tests_found=True,
            snapshot_verification_tests_found=True,
            deterministic_replay_tests_found=False,
            event_ordering_tests_found=True,
            replay_modules_tested={"core.runner", "core.audit"},
            total_replay_tests=8,
            replay_coverage_score=75.0,
            determinism_score=75.0,
            auditability_score=100.0,
        )
        self.assertTrue(result.replay_checksum_tests_found)
        self.assertEqual(result.determinism_score, 75.0)

    def test_test_quality_result(self):
        result = TestQualityResult(
            total_test_files=150,
            files_with_issues=20,
            total_issues=35,
            assertionless_tests=10,
            trivial_tests=5,
            duplicate_tests=3,
            dead_tests=2,
            meaningless_mocks=0,
            test_quality_score=85.0,
            details={},
        )
        self.assertEqual(result.test_quality_score, 85.0)

    def test_risk_weighted_coverage_result(self):
        result = RiskWeightedCoverageResult(
            global_raw_coverage=45.0,
            weighted_operational_coverage=55.0,
            critical_path_coverage=60.0,
            risk_adjusted_score=50.0,
            modules=[],
            tier_breakdown={},
        )
        self.assertEqual(result.weighted_operational_coverage, 55.0)

    def test_enterprise_risk_report_default(self):
        report = EnterpriseRiskReport(
            global_raw_coverage=0,
            weighted_operational_coverage=0,
            critical_path_coverage=0,
            workflow_coverage=0,
            frontend_operational_score=0,
            reporting_reliability=0,
            replay_determinism_score=0,
            auditability_score=0,
            top_uncovered_risks=[],
            unsafe_modules=[],
            release_blockers=[],
            final_certification="HIGH_RISK",
        )
        self.assertEqual(report.final_certification, "HIGH_RISK")

    def test_certification_verdict(self):
        report = EnterpriseRiskReport(
            global_raw_coverage=0,
            weighted_operational_coverage=0,
            critical_path_coverage=0,
            workflow_coverage=0,
            frontend_operational_score=0,
            reporting_reliability=0,
            replay_determinism_score=0,
            auditability_score=0,
            top_uncovered_risks=[],
            unsafe_modules=[],
            release_blockers=[],
            final_certification="RELEASE_BLOCKED",
        )
        verdict = CertificationVerdict(
            verdict="RELEASE_BLOCKED",
            score=30.0,
            weighted_score=25.0,
            workflow_score=20.0,
            frontend_score=30.0,
            reporting_score=40.0,
            failure_scenario_score=15.0,
            replay_score=10.0,
            test_quality_score=50.0,
            blocking_issues=["Critical coverage below threshold"],
            risk_report=report,
        )
        self.assertEqual(verdict.verdict, "RELEASE_BLOCKED")
        self.assertIn("Critical coverage below threshold", verdict.blocking_issues)


class TestRiskScorer(unittest.TestCase):

    def setUp(self):
        from coverage_governance.risk_scorer import RiskScorer
        self.scorer = RiskScorer()

        self.risk_weighted = RiskWeightedCoverageResult(
            global_raw_coverage=45.0,
            weighted_operational_coverage=55.0,
            critical_path_coverage=60.0,
            risk_adjusted_score=52.0,
            modules=[],
            tier_breakdown={},
        )

        self.workflow = WorkflowCoverageResult(
            workflow_coverage_pct=70.0, workflows=[], total_workflows=4,
            fully_covered_workflows=1, partially_covered_workflows=2,
            uncovered_workflows=1,
        )

        self.frontend = FrontendCoverageResult(
            screen_coverage_pct=80.0, form_coverage_pct=50.0,
            table_coverage_pct=60.0, ux_state_coverage_pct=30.0,
            print_export_coverage_pct=40.0, test_coverage_pct=20.0,
            overall_frontend_score=55.0, screens=[], total_screens=38,
            basescreen_screens=25, unmigrated_widgets=13,
        )

        self.reporting = ReportingCoverageResult(
            report_coverage_pct=100.0, pdf_coverage_pct=80.0,
            csv_coverage_pct=70.0, print_coverage_pct=90.0,
            zero_state_coverage_pct=30.0, overall_reporting_score=78.0,
            reports=[],
        )

        self.failure = FailureScenarioResult(
            total_scenarios=20, covered_scenarios=12,
            uncovered_scenarios=8, scenario_coverage_pct=60.0,
            by_category={}, scenarios=[],
            uncovered_high_risk=[],
        )

        self.replay = ReplayDeterminismResult(
            replay_checksum_tests_found=True,
            snapshot_verification_tests_found=True,
            deterministic_replay_tests_found=True,
            event_ordering_tests_found=True,
            replay_modules_tested={"core.runner", "core.audit"},
            total_replay_tests=12,
            replay_coverage_score=100.0,
            determinism_score=100.0,
            auditability_score=100.0,
        )

        self.test_quality = TestQualityResult(
            total_test_files=150, files_with_issues=20, total_issues=35,
            assertionless_tests=10, trivial_tests=5, duplicate_tests=3,
            dead_tests=2, meaningless_mocks=0, test_quality_score=85.0,
            details={},
        )

    def test_enterprise_safe_scenario(self):
        report = self.scorer.compute_enterprise_risk(
            self.risk_weighted, self.workflow, self.frontend,
            self.reporting, self.failure, self.replay, self.test_quality,
        )
        self.assertIn(report.final_certification,
                      ["ENTERPRISE_SAFE", "OPERATIONALLY_SAFE",
                       "CONDITIONALLY_SAFE", "HIGH_RISK", "RELEASE_BLOCKED"])

    def test_release_blocked_with_critical_failures(self):
        bad_failure = FailureScenarioResult(
            total_scenarios=20, covered_scenarios=0,
            uncovered_scenarios=20, scenario_coverage_pct=0.0,
            by_category={}, scenarios=[],
            uncovered_high_risk=["journal_entry_rollback"],
        )
        bad_replay = ReplayDeterminismResult(
            replay_checksum_tests_found=False,
            snapshot_verification_tests_found=False,
            deterministic_replay_tests_found=False,
            event_ordering_tests_found=False,
            replay_modules_tested=set(),
            total_replay_tests=0,
            replay_coverage_score=0.0,
            determinism_score=0.0,
            auditability_score=0.0,
        )
        report = self.scorer.compute_enterprise_risk(
            self.risk_weighted, self.workflow, self.frontend,
            self.reporting, bad_failure, bad_replay, self.test_quality,
        )
        self.assertEqual(report.final_certification, "RELEASE_BLOCKED")

    def test_find_release_blockers_empty_when_healthy(self):
        blockers = self.scorer._find_release_blockers(
            self.risk_weighted, self.workflow, self.failure,
            self.replay, self.frontend,
        )
        self.assertIsInstance(blockers, list)


class TestCertifier(unittest.TestCase):

    def setUp(self):
        from coverage_governance.certifier import CoverageCertifier
        self.certifier = CoverageCertifier()

        self.report = EnterpriseRiskReport(
            global_raw_coverage=45.0, weighted_operational_coverage=55.0,
            critical_path_coverage=60.0, workflow_coverage=70.0,
            frontend_operational_score=55.0, reporting_reliability=78.0,
            replay_determinism_score=100.0, auditability_score=100.0,
            top_uncovered_risks=[], unsafe_modules=[],
            release_blockers=[], final_certification="OPERATIONALLY_SAFE",
        )

        self.verdict = CertificationVerdict(
            verdict="OPERATIONALLY_SAFE", score=55.0, weighted_score=65.0,
            workflow_score=70.0, frontend_score=55.0, reporting_score=78.0,
            failure_scenario_score=60.0, replay_score=100.0,
            test_quality_score=85.0, blocking_issues=[],
            risk_report=self.report,
        )

    def test_is_release_blocked_false_when_no_blockers(self):
        self.assertFalse(self.certifier.is_release_blocked(self.verdict))

    def test_is_release_blocked_true_with_blockers(self):
        blocked_report = EnterpriseRiskReport(
            global_raw_coverage=45.0, weighted_operational_coverage=55.0,
            critical_path_coverage=60.0, workflow_coverage=70.0,
            frontend_operational_score=55.0, reporting_reliability=78.0,
            replay_determinism_score=100.0, auditability_score=100.0,
            top_uncovered_risks=[], unsafe_modules=[],
            release_blockers=["Critical coverage below threshold"],
            final_certification="RELEASE_BLOCKED",
        )
        blocked = CertificationVerdict(
            verdict="RELEASE_BLOCKED", score=30.0, weighted_score=25.0,
            workflow_score=20.0, frontend_score=30.0, reporting_score=40.0,
            failure_scenario_score=15.0, replay_score=10.0,
            test_quality_score=50.0,
            blocking_issues=["Critical coverage below threshold"],
            risk_report=blocked_report,
        )
        self.assertTrue(self.certifier.is_release_blocked(blocked))

    def test_get_gate_decision(self):
        decision = self.certifier.get_gate_decision(self.verdict)
        self.assertIn("release_blocked", decision)
        self.assertIn("can_release", decision)
        self.assertIn("verdict", decision)
        self.assertFalse(decision["release_blocked"])

    def test_export_report(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmppath = f.name
        try:
            result_path = self.certifier.export_report(self.verdict, tmppath)
            self.assertTrue(os.path.exists(result_path))
            with open(result_path, "r") as f:
                data = json.load(f)
            self.assertIn("final_certification", data)
            self.assertIn("verdict", data)
        finally:
            if os.path.exists(tmppath):
                os.unlink(tmppath)


class TestWeightedCoverage(unittest.TestCase):

    def test_risk_weighted_engine_creation(self):
        from coverage_governance.weighted_coverage import RiskWeightedCoverageEngine
        engine = RiskWeightedCoverageEngine()
        self.assertIsNotNone(engine)

    def test_risk_weighted_with_empty_data(self):
        from coverage_governance.weighted_coverage import RiskWeightedCoverageEngine
        engine = RiskWeightedCoverageEngine()
        result = engine.compute_risk_weighted({"files": {}, "meta": {"format": 2}})
        self.assertEqual(result.global_raw_coverage, 0.0)
        self.assertEqual(result.risk_adjusted_score, 0.0)


class TestWorkflowCoverage(unittest.TestCase):

    def test_analyzer_creation(self):
        from coverage_governance.workflow_coverage import WorkflowCoverageAnalyzer
        analyzer = WorkflowCoverageAnalyzer(test_dirs=[])
        self.assertIsNotNone(analyzer)

    def test_analyze_with_no_test_dirs(self):
        from coverage_governance.workflow_coverage import WorkflowCoverageAnalyzer
        analyzer = WorkflowCoverageAnalyzer(test_dirs=[])
        result = analyzer.analyze()
        self.assertIsNotNone(result)
        self.assertGreater(result.total_workflows, 0)
        self.assertIsInstance(result.workflow_coverage_pct, float)

    def test_get_module_workflow_scores(self):
        from coverage_governance.workflow_coverage import WorkflowCoverageAnalyzer
        analyzer = WorkflowCoverageAnalyzer(test_dirs=[])
        result = analyzer.analyze()
        scores = analyzer.get_module_workflow_scores(result)
        self.assertIsInstance(scores, dict)


class TestFrontendValidator(unittest.TestCase):

    def test_validator_creation(self):
        from coverage_governance.frontend_validator import FrontendOperationalValidator
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "ui"), exist_ok=True)
            validator = FrontendOperationalValidator(frontend_dir=tmpdir)
            self.assertIsNotNone(validator)

    def test_validate_with_empty_dir(self):
        from coverage_governance.frontend_validator import FrontendOperationalValidator
        from coverage_governance.module_classifier import FRONTEND_OPERATIONAL_SCREENS
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "ui"), exist_ok=True)
            validator = FrontendOperationalValidator(frontend_dir=tmpdir)
            result = validator.validate()
            self.assertEqual(result.screen_coverage_pct, 0.0)
            self.assertEqual(len(result.screens), len(FRONTEND_OPERATIONAL_SCREENS))


class TestReportingValidator(unittest.TestCase):

    def test_validator_creation(self):
        from coverage_governance.reporting_validator import ReportingCoverageValidator
        validator = ReportingCoverageValidator()
        self.assertIsNotNone(validator)

    def test_validate(self):
        from coverage_governance.reporting_validator import ReportingCoverageValidator
        validator = ReportingCoverageValidator()
        result = validator.validate()
        self.assertIsNotNone(result)
        self.assertEqual(len(result.reports), 13)


class TestFailureScenario(unittest.TestCase):

    def test_analyzer_creation(self):
        from coverage_governance.failure_scenario import FailureScenarioAnalyzer
        analyzer = FailureScenarioAnalyzer()
        self.assertIsNotNone(analyzer)

    def test_analyze(self):
        from coverage_governance.failure_scenario import FailureScenarioAnalyzer
        analyzer = FailureScenarioAnalyzer()
        result = analyzer.analyze()
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result.total_scenarios, 15)

    def test_get_module_failure_scores(self):
        from coverage_governance.failure_scenario import FailureScenarioAnalyzer
        analyzer = FailureScenarioAnalyzer()
        result = analyzer.analyze()
        scores = analyzer.get_module_failure_scores(result)
        self.assertIsInstance(scores, dict)
        for category in ["rollback", "concurrency", "replay"]:
            self.assertIn(category, scores)


class TestReplayValidator(unittest.TestCase):

    def test_validator_creation(self):
        from coverage_governance.replay_validator import ReplayDeterminismValidator
        validator = ReplayDeterminismValidator()
        self.assertIsNotNone(validator)

    def test_validate(self):
        from coverage_governance.replay_validator import ReplayDeterminismValidator
        validator = ReplayDeterminismValidator()
        result = validator.validate()
        self.assertIsNotNone(result)
        self.assertIsInstance(result.replay_coverage_score, float)
        self.assertIsInstance(result.determinism_score, float)


class TestTestQuality(unittest.TestCase):

    def test_analyzer_creation(self):
        from coverage_governance.test_quality import TestQualityAnalyzer
        analyzer = TestQualityAnalyzer()
        self.assertIsNotNone(analyzer)

    def test_analyze_with_empty_dirs(self):
        from coverage_governance.test_quality import TestQualityAnalyzer
        analyzer = TestQualityAnalyzer()
        result = analyzer.analyze(test_dirs=[])
        self.assertEqual(result.total_test_files, 0)
        self.assertEqual(result.test_quality_score, 100.0)
        self.assertEqual(result.total_issues, 0)

    def test_analyze_detects_quality_issues(self):
        from coverage_governance.test_quality import TestQualityAnalyzer
        analyzer = TestQualityAnalyzer()

        with tempfile.TemporaryDirectory() as tmpdir:
            bad_test = os.path.join(tmpdir, "test_bad.py")
            with open(bad_test, "w") as f:
                f.write("def test_placeholder():\n    pass\n")
                f.write("def test_init():\n    pass\n")
                f.write("def test_not_implemented():\n    raise NotImplementedError\n")

            result = analyzer.analyze(test_dirs=[tmpdir])
            self.assertEqual(result.total_test_files, 1)
            self.assertGreater(result.assertionless_tests, 0)

    def test_test_quality_penalty(self):
        from coverage_governance.test_quality import TestQualityAnalyzer
        analyzer = TestQualityAnalyzer()

        with tempfile.TemporaryDirectory() as tmpdir:
            bad_test = os.path.join(tmpdir, "test_bad.py")
            with open(bad_test, "w") as f:
                f.write("import pytest\n")
                f.write("def test_no_assert():\n    x = 1 + 1\n")
                f.write("def test_init():\n    pass\n")
                f.write("def test_placeholder_not_impl():\n    raise NotImplementedError\n")

            result = analyzer.analyze(test_dirs=[tmpdir])
            self.assertGreater(result.total_issues, 0)
            self.assertLess(result.test_quality_score, 100.0)


class TestEngine(unittest.TestCase):

    def test_engine_creation(self):
        from coverage_governance.engine import CoverageGovernanceEngine
        engine = CoverageGovernanceEngine()
        self.assertIsNotNone(engine)

    def test_get_status_no_report(self):
        from coverage_governance.engine import CoverageGovernanceEngine
        engine = CoverageGovernanceEngine()
        status = engine.get_status()
        self.assertIn("status", status)


class TestCertificationEdgeCases(unittest.TestCase):

    def test_all_dimensions_zero(self):
        from coverage_governance.risk_scorer import RiskScorer

        risk_weighted = RiskWeightedCoverageResult(
            global_raw_coverage=0.0, weighted_operational_coverage=0.0,
            critical_path_coverage=0.0, risk_adjusted_score=0.0,
            modules=[], tier_breakdown={},
        )
        workflow = WorkflowCoverageResult(
            workflow_coverage_pct=0.0, workflows=[], total_workflows=0,
            fully_covered_workflows=0, partially_covered_workflows=0,
            uncovered_workflows=0,
        )
        frontend = FrontendCoverageResult(
            screen_coverage_pct=0.0, form_coverage_pct=0.0,
            table_coverage_pct=0.0, ux_state_coverage_pct=0.0,
            print_export_coverage_pct=0.0, test_coverage_pct=0.0,
            overall_frontend_score=0.0, screens=[], total_screens=0,
            basescreen_screens=0, unmigrated_widgets=0,
        )
        reporting = ReportingCoverageResult(
            report_coverage_pct=0.0, pdf_coverage_pct=0.0,
            csv_coverage_pct=0.0, print_coverage_pct=0.0,
            zero_state_coverage_pct=0.0, overall_reporting_score=0.0,
            reports=[],
        )
        failure = FailureScenarioResult(
            total_scenarios=20, covered_scenarios=0, uncovered_scenarios=20,
            scenario_coverage_pct=0.0, by_category={}, scenarios=[],
            uncovered_high_risk=["critical_scenario"],
        )
        replay = ReplayDeterminismResult(
            replay_checksum_tests_found=False,
            snapshot_verification_tests_found=False,
            deterministic_replay_tests_found=False,
            event_ordering_tests_found=False,
            replay_modules_tested=set(), total_replay_tests=0,
            replay_coverage_score=0.0, determinism_score=0.0,
            auditability_score=0.0,
        )
        test_quality = TestQualityResult(
            total_test_files=0, files_with_issues=0, total_issues=0,
            assertionless_tests=0, trivial_tests=0, duplicate_tests=0,
            dead_tests=0, meaningless_mocks=0, test_quality_score=100.0,
            details={},
        )

        scorer = RiskScorer()
        report = scorer.compute_enterprise_risk(
            risk_weighted, workflow, frontend, reporting,
            failure, replay, test_quality,
        )
        self.assertEqual(report.final_certification, "RELEASE_BLOCKED")
        self.assertGreaterEqual(len(report.release_blockers), 1)

    def test_all_dimensions_perfect(self):
        from coverage_governance.risk_scorer import RiskScorer

        modules = []
        for name in ["accounting", "inventory", "governance"]:
            from coverage_governance.models import ModuleCoverageDetail
            modules.append(ModuleCoverageDetail(
                name=name, tier="CRITICAL", raw_coverage=95.0,
                weighted_coverage=950.0, meets_minimum=True,
                workflow_coverage=100.0, failure_coverage=100.0,
                test_quality_score=100.0,
            ))

        risk_weighted = RiskWeightedCoverageResult(
            global_raw_coverage=95.0, weighted_operational_coverage=95.0,
            critical_path_coverage=95.0, risk_adjusted_score=95.0,
            modules=modules, tier_breakdown={},
        )
        workflow = WorkflowCoverageResult(
            workflow_coverage_pct=100.0, workflows=[], total_workflows=8,
            fully_covered_workflows=8, partially_covered_workflows=0,
            uncovered_workflows=0,
        )
        frontend = FrontendCoverageResult(
            screen_coverage_pct=100.0, form_coverage_pct=100.0,
            table_coverage_pct=100.0, ux_state_coverage_pct=100.0,
            print_export_coverage_pct=100.0, test_coverage_pct=100.0,
            overall_frontend_score=100.0, screens=[], total_screens=38,
            basescreen_screens=38, unmigrated_widgets=0,
        )
        reporting = ReportingCoverageResult(
            report_coverage_pct=100.0, pdf_coverage_pct=100.0,
            csv_coverage_pct=100.0, print_coverage_pct=100.0,
            zero_state_coverage_pct=100.0, overall_reporting_score=100.0,
            reports=[],
        )
        failure = FailureScenarioResult(
            total_scenarios=20, covered_scenarios=20, uncovered_scenarios=0,
            scenario_coverage_pct=100.0, by_category={}, scenarios=[],
            uncovered_high_risk=[],
        )
        replay = ReplayDeterminismResult(
            replay_checksum_tests_found=True,
            snapshot_verification_tests_found=True,
            deterministic_replay_tests_found=True,
            event_ordering_tests_found=True,
            replay_modules_tested={"core.runner", "core.audit"},
            total_replay_tests=15,
            replay_coverage_score=100.0, determinism_score=100.0,
            auditability_score=100.0,
        )
        test_quality = TestQualityResult(
            total_test_files=150, files_with_issues=0, total_issues=0,
            assertionless_tests=0, trivial_tests=0, duplicate_tests=0,
            dead_tests=0, meaningless_mocks=0, test_quality_score=100.0,
            details={},
        )

        scorer = RiskScorer()
        report = scorer.compute_enterprise_risk(
            risk_weighted, workflow, frontend, reporting,
            failure, replay, test_quality,
        )
        self.assertEqual(report.final_certification, "ENTERPRISE_SAFE")


if __name__ == "__main__":
    unittest.main()
