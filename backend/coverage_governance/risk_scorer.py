"""
Phase 9 — Risk Scoring Engine.
Combines all coverage dimensions into a unified enterprise risk report.
"""

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


TOTAL_WEIGHT = 100.0

DIMENSION_WEIGHTS = {
    "risk_weighted_coverage": 0.20,
    "workflow_coverage": 0.15,
    "frontend_operational": 0.10,
    "reporting_reliability": 0.10,
    "failure_scenario": 0.15,
    "replay_determinism": 0.10,
    "test_quality": 0.10,
    "auditability": 0.10,
}


class RiskScorer:

    def compute_enterprise_risk(
        self,
        risk_weighted: RiskWeightedCoverageResult,
        workflow: WorkflowCoverageResult,
        frontend: FrontendCoverageResult,
        reporting: ReportingCoverageResult,
        failure: FailureScenarioResult,
        replay: ReplayDeterminismResult,
        test_quality: TestQualityResult,
    ) -> EnterpriseRiskReport:

        top_uncovered = self._find_top_risks(
            risk_weighted, workflow, frontend, reporting, failure, test_quality
        )

        unsafe_modules = self._find_unsafe_modules(risk_weighted, workflow, failure)

        release_blockers = self._find_release_blockers(
            risk_weighted, workflow, failure, replay, frontend
        )

        workflow_score = workflow.workflow_coverage_pct
        frontend_score = frontend.overall_frontend_score
        reporting_score = reporting.overall_reporting_score
        failure_score = failure.scenario_coverage_pct
        replay_score = replay.replay_coverage_score
        auditability_score = replay.auditability_score

        # Composite weighted score
        weighted_score = (
            DIMENSION_WEIGHTS["risk_weighted_coverage"] * risk_weighted.risk_adjusted_score
            + DIMENSION_WEIGHTS["workflow_coverage"] * workflow_score
            + DIMENSION_WEIGHTS["frontend_operational"] * frontend_score
            + DIMENSION_WEIGHTS["reporting_reliability"] * reporting_score
            + DIMENSION_WEIGHTS["failure_scenario"] * failure_score
            + DIMENSION_WEIGHTS["replay_determinism"] * replay_score
            + DIMENSION_WEIGHTS["test_quality"] * test_quality.test_quality_score
            + DIMENSION_WEIGHTS["auditability"] * auditability_score
        )

        # Determine certification
        if len(release_blockers) > 0:
            final_cert = "RELEASE_BLOCKED"
        elif weighted_score >= 85 and failure_score >= 70 and replay_score >= 70:
            final_cert = "ENTERPRISE_SAFE"
        elif weighted_score >= 70 and failure_score >= 50:
            final_cert = "OPERATIONALLY_SAFE"
        elif weighted_score >= 55:
            final_cert = "CONDITIONALLY_SAFE"
        elif weighted_score >= 40:
            final_cert = "HIGH_RISK"
        else:
            final_cert = "RELEASE_BLOCKED"

        return EnterpriseRiskReport(
            global_raw_coverage=risk_weighted.global_raw_coverage,
            weighted_operational_coverage=risk_weighted.weighted_operational_coverage,
            critical_path_coverage=risk_weighted.critical_path_coverage,
            workflow_coverage=round(workflow_score, 2),
            frontend_operational_score=round(frontend_score, 2),
            reporting_reliability=round(reporting_score, 2),
            replay_determinism_score=round(replay_score, 2),
            auditability_score=round(auditability_score, 2),
            top_uncovered_risks=top_uncovered,
            unsafe_modules=unsafe_modules,
            release_blockers=release_blockers,
            final_certification=final_cert,
        )

    def _find_top_risks(
        self,
        risk_weighted: RiskWeightedCoverageResult,
        workflow: WorkflowCoverageResult,
        frontend: FrontendCoverageResult,
        reporting: ReportingCoverageResult,
        failure: FailureScenarioResult,
        test_quality: TestQualityResult,
    ) -> List[str]:
        risks = []

        for m in risk_weighted.modules:
            if not m.meets_minimum:
                risks.append(f"Module '{m.name}' ({m.tier}) at {m.raw_coverage}% < {self._get_min(m.tier)}% minimum")

        for wf in workflow.workflows:
            if wf.coverage_pct < 50 and len(wf.missing_steps) >= 2:
                risks.append(f"Workflow '{wf.workflow_name}' only {wf.coverage_pct}% covered; missing: {', '.join(wf.missing_steps[:3])}")

        if frontend.overall_frontend_score < 60:
            risks.append(f"Frontend operational score {frontend.overall_frontend_score}% — {frontend.unmigrated_widgets} screens not on BaseScreen")

        if reporting.overall_reporting_score < 60:
            risks.append(f"Reporting reliability {reporting.overall_reporting_score}%")

        for scenario in failure.scenarios:
            if not scenario.test_found and scenario.severity == "critical":
                risks.append(f"Critical failure scenario '{scenario.scenario_name}' has NO test")

        if test_quality.assertionless_tests > 0:
            risks.append(f"{test_quality.assertionless_tests} assertionless tests detected")
        if test_quality.dead_tests > 0:
            risks.append(f"{test_quality.dead_tests} dead/placeholder tests detected")

        return risks[:15]

    def _find_unsafe_modules(
        self,
        risk_weighted: RiskWeightedCoverageResult,
        workflow: WorkflowCoverageResult,
        failure: FailureScenarioResult,
    ) -> List[str]:
        unsafe = []
        for m in risk_weighted.modules:
            if m.tier in ("CRITICAL", "HIGH") and not m.meets_minimum:
                unsafe.append(m.name)
        return unsafe

    def _find_release_blockers(
        self,
        risk_weighted: RiskWeightedCoverageResult,
        workflow: WorkflowCoverageResult,
        failure: FailureScenarioResult,
        replay: ReplayDeterminismResult,
        frontend: FrontendCoverageResult,
    ) -> List[str]:
        blockers = []

        if risk_weighted.critical_path_coverage < 85:
            for m in risk_weighted.modules:
                if m.tier == "CRITICAL" and not m.meets_minimum:
                    blockers.append(f"CRITICAL module '{m.name}' at {m.raw_coverage}% < 85% minimum")

        critical_failure_uncovered = [
            s.scenario_name for s in failure.scenarios
            if not s.test_found and s.severity == "critical"
        ]
        if critical_failure_uncovered:
            blockers.append(f"Critical failure scenarios uncovered: {', '.join(critical_failure_uncovered[:5])}")

        if not replay.replay_checksum_tests_found:
            blockers.append("No replay checksum verification tests found")

        if workflow.workflow_coverage_pct < 40:
            blockers.append(f"Workflow coverage {workflow.workflow_coverage_pct}% < 40%")

        return blockers

    def _get_min(self, tier: str) -> float:
        from coverage_governance.module_classifier import TIER_MINIMUMS
        return TIER_MINIMUMS.get(tier, 0.0)
