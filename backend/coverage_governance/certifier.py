"""
Phase 10-11 — Certification Engine + CI/CD Integration + Release Governance.
Combines all dimensions into final certification verdict.
Generates ENTERPRISE_OPERATIONAL_RISK_REPORT.json and blocks unsafe releases.
"""

import json
import os
from typing import Dict, List, Optional

from coverage_governance.models import (
    RiskWeightedCoverageResult,
    WorkflowCoverageResult,
    FrontendCoverageResult,
    ReportingCoverageResult,
    FailureScenarioResult,
    ReplayDeterminismResult,
    TestQualityResult,
    EnterpriseRiskReport,
    CertificationVerdict,
)
from coverage_governance.risk_scorer import RiskScorer, DIMENSION_WEIGHTS


REPORTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "docs", "audit")
)

REPORT_FILE = os.path.join(REPORTS_DIR, "ENTERPRISE_OPERATIONAL_RISK_REPORT.json")


class CoverageCertifier:

    def __init__(self):
        self._scorer = RiskScorer()
        os.makedirs(REPORTS_DIR, exist_ok=True)

    def certify(
        self,
        risk_weighted: RiskWeightedCoverageResult,
        workflow: WorkflowCoverageResult,
        frontend: FrontendCoverageResult,
        reporting: ReportingCoverageResult,
        failure: FailureScenarioResult,
        replay: ReplayDeterminismResult,
        test_quality: TestQualityResult,
    ) -> CertificationVerdict:

        risk_report = self._scorer.compute_enterprise_risk(
            risk_weighted=risk_weighted,
            workflow=workflow,
            frontend=frontend,
            reporting=reporting,
            failure=failure,
            replay=replay,
            test_quality=test_quality,
        )

        # Compute weighted composite score
        score = risk_report.weighted_operational_coverage
        weighted_score = (
            DIMENSION_WEIGHTS["risk_weighted_coverage"] * risk_weighted.risk_adjusted_score
            + DIMENSION_WEIGHTS["workflow_coverage"] * workflow.workflow_coverage_pct
            + DIMENSION_WEIGHTS["frontend_operational"] * frontend.overall_frontend_score
            + DIMENSION_WEIGHTS["reporting_reliability"] * reporting.overall_reporting_score
            + DIMENSION_WEIGHTS["failure_scenario"] * failure.scenario_coverage_pct
            + DIMENSION_WEIGHTS["replay_determinism"] * replay.replay_coverage_score
            + DIMENSION_WEIGHTS["test_quality"] * test_quality.test_quality_score
            + DIMENSION_WEIGHTS["auditability"] * replay.auditability_score
        )

        verdict_str = risk_report.final_certification
        blocking = list(risk_report.release_blockers)

        return CertificationVerdict(
            verdict=verdict_str,
            score=round(score, 2),
            weighted_score=round(weighted_score, 2),
            workflow_score=round(workflow.workflow_coverage_pct, 2),
            frontend_score=round(frontend.overall_frontend_score, 2),
            reporting_score=round(reporting.overall_reporting_score, 2),
            failure_scenario_score=round(failure.scenario_coverage_pct, 2),
            replay_score=round(replay.replay_coverage_score, 2),
            test_quality_score=round(test_quality.test_quality_score, 2),
            blocking_issues=blocking,
            risk_report=risk_report,
        )

    def export_report(self, verdict: CertificationVerdict, output_path: Optional[str] = None):
        path = output_path or REPORT_FILE

        report = {
            "global_raw_coverage": verdict.risk_report.global_raw_coverage,
            "weighted_operational_coverage": verdict.risk_report.weighted_operational_coverage,
            "critical_path_coverage": verdict.risk_report.critical_path_coverage,
            "workflow_coverage": verdict.risk_report.workflow_coverage,
            "frontend_operational_score": verdict.risk_report.frontend_operational_score,
            "reporting_reliability": verdict.risk_report.reporting_reliability,
            "replay_determinism_score": verdict.risk_report.replay_determinism_score,
            "auditability_score": verdict.risk_report.auditability_score,
            "top_uncovered_risks": verdict.risk_report.top_uncovered_risks,
            "unsafe_modules": verdict.risk_report.unsafe_modules,
            "release_blockers": verdict.risk_report.release_blockers,
            "final_certification": verdict.risk_report.final_certification,
            "verdict": {
                "verdict": verdict.verdict,
                "score": verdict.score,
                "weighted_score": verdict.weighted_score,
                "workflow_score": verdict.workflow_score,
                "frontend_score": verdict.frontend_score,
                "reporting_score": verdict.reporting_score,
                "failure_scenario_score": verdict.failure_scenario_score,
                "replay_score": verdict.replay_score,
                "test_quality_score": verdict.test_quality_score,
                "blocking_issues": verdict.blocking_issues,
            },
            "metadata": {
                "generated_by": "CoverageGovernanceEngine",
                "dimension_weights": DIMENSION_WEIGHTS,
            },
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return path

    def is_release_blocked(self, verdict: CertificationVerdict) -> bool:
        if verdict.verdict == "RELEASE_BLOCKED":
            return True
        if len(verdict.blocking_issues) > 0:
            return True
        if verdict.verdict == "HIGH_RISK":
            return True
        return False

    def get_gate_decision(self, verdict: CertificationVerdict) -> Dict:
        blocked = self.is_release_blocked(verdict)
        return {
            "release_blocked": blocked,
            "verdict": verdict.verdict,
            "blocking_issues": verdict.blocking_issues,
            "can_release": not blocked,
            "score": verdict.weighted_score,
            "enterprise_risk_report": {
                "workflow_coverage": verdict.workflow_score,
                "frontend_score": verdict.frontend_score,
                "reporting_score": verdict.reporting_score,
                "failure_coverage": verdict.failure_scenario_score,
                "replay_determinism": verdict.replay_score,
                "test_quality": verdict.test_quality_score,
            },
        }
