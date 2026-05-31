"""
Coverage Governance — Risk-Weighted Enterprise Coverage Certification System.
Additive layer that extends backend/test_governance/ with workflow, frontend,
failure-scenario, and replay/determinism coverage analysis.
"""

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
