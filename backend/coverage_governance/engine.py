"""
CoverageGovernanceEngine — Main orchestrator.
Runs all 11 phases and produces enterprise certification.
Integration point for CI/CD pipelines.
"""

import json
import os
from typing import Dict, List, Optional

from test_governance.weighted_coverage import WeightedCoverageEngine

from coverage_governance.weighted_coverage import RiskWeightedCoverageEngine
from coverage_governance.workflow_coverage import WorkflowCoverageAnalyzer
from coverage_governance.frontend_validator import FrontendOperationalValidator
from coverage_governance.reporting_validator import ReportingCoverageValidator
from coverage_governance.failure_scenario import FailureScenarioAnalyzer
from coverage_governance.replay_validator import ReplayDeterminismValidator
from coverage_governance.test_quality import TestQualityAnalyzer
from coverage_governance.certifier import CoverageCertifier


class CoverageGovernanceEngine:

    def __init__(self):
        self._risk_weighted = RiskWeightedCoverageEngine()
        self._workflow = WorkflowCoverageAnalyzer()
        self._frontend = FrontendOperationalValidator()
        self._reporting = ReportingCoverageValidator()
        self._failure = FailureScenarioAnalyzer()
        self._replay = ReplayDeterminismValidator()
        self._test_quality = TestQualityAnalyzer()
        self._certifier = CoverageCertifier()

    def run_full_certification(
        self,
        coverage_json_path: Optional[str] = None,
        export_report: bool = True,
    ) -> Dict:
        """Run all 11 phases and produce enterprise certification."""

        # Phase 1-2: Risk-weighted coverage from coverage.json
        risk_weighted = None
        base_coverage = None
        if coverage_json_path and os.path.exists(coverage_json_path):
            try:
                cov_data = self._risk_weighted.load_coverage_json(coverage_json_path)
                risk_weighted = self._risk_weighted.compute_risk_weighted(cov_data)
            except Exception:
                pass

        if risk_weighted is None:
            try:
                base_engine = WeightedCoverageEngine()
                base_result = base_engine.compute_from_htmlcov("htmlcov")
                if base_result:
                    risk_weighted = self._risk_weighted.compute_risk_weighted(
                        base_engine.load_coverage_json(
                            os.path.join("htmlcov", "coverage.json")
                        )
                    )
            except Exception:
                pass

        # Phase 3: Workflow coverage analysis
        workflow_result = self._workflow.analyze()
        workflow_scores = self._workflow.get_module_workflow_scores(workflow_result)

        # Phase 4: Frontend operational coverage
        frontend_result = self._frontend.validate()

        # Phase 5: Reporting coverage
        reporting_result = self._reporting.validate()

        # Phase 6: Failure scenario coverage
        failure_result = self._failure.analyze()
        failure_scores = self._failure.get_module_failure_scores(failure_result)

        # Phase 7: Replay + determinism
        replay_result = self._replay.validate()

        # Phase 8: Test quality
        test_quality_result = self._test_quality.analyze()
        tq_scores = self._test_quality.get_module_test_quality_scores(test_quality_result)

        # If we had coverage data, recompute with workflow/failure/quality scores
        if risk_weighted and (workflow_scores or failure_scores):
            try:
                cov_data_path = coverage_json_path or os.path.join("htmlcov", "coverage.json")
                if os.path.exists(cov_data_path):
                    cov_data = self._risk_weighted.load_coverage_json(cov_data_path)
                    risk_weighted = self._risk_weighted.compute_risk_weighted(
                        cov_data, workflow_scores, failure_scores, tq_scores
                    )
            except Exception:
                pass

        # Phase 9-11: Enterprise certification
        if risk_weighted is None:
            risk_weighted = self._risk_weighted.compute_risk_weighted(
                {"files": {}, "meta": {"format": 2}}
            )

        verdict = self._certifier.certify(
            risk_weighted=risk_weighted,
            workflow=workflow_result,
            frontend=frontend_result,
            reporting=reporting_result,
            failure=failure_result,
            replay=replay_result,
            test_quality=test_quality_result,
        )

        report_path = None
        if export_report:
            report_path = self._certifier.export_report(verdict)

        gate = self._certifier.get_gate_decision(verdict)

        return {
            "certification_verdict": {
                "verdict": verdict.verdict,
                "score": verdict.score,
                "weighted_score": verdict.weighted_score,
            },
            "dimension_scores": {
                "risk_weighted_coverage": verdict.score,
                "workflow_coverage": verdict.workflow_score,
                "frontend_operational": verdict.frontend_score,
                "reporting_reliability": verdict.reporting_score,
                "failure_scenario_coverage": verdict.failure_scenario_score,
                "replay_determinism": verdict.replay_score,
                "test_quality": verdict.test_quality_score,
            },
            "release_gate": gate,
            "blocking_issues": verdict.blocking_issues,
            "risk_report_summary": {
                key: getattr(verdict.risk_report, key)
                for key in [
                    "global_raw_coverage", "weighted_operational_coverage",
                    "critical_path_coverage", "workflow_coverage",
                    "frontend_operational_score", "reporting_reliability",
                    "replay_determinism_score", "auditability_score",
                    "top_uncovered_risks", "unsafe_modules",
                    "release_blockers", "final_certification",
                ]
            },
            "report_path": report_path if export_report else None,
        }

    def get_status(self) -> Dict:
        """Quick status without full re-run — returns last cached report."""
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docs", "audit",
            "ENTERPRISE_OPERATIONAL_RISK_REPORT.json"
        )
        if os.path.exists(report_path):
            with open(report_path, "r") as f:
                return json.load(f)
        return {"status": "no_report_available", "message": "Run run_full_certification() first"}
