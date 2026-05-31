"""
Data models for the coverage governance system.
All dataclasses — no ORM, no runtime mutation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class WorkflowCoverageEntry:
    workflow_name: str
    steps: List[str]
    covered_steps: List[str]
    missing_steps: List[str]
    coverage_pct: float


@dataclass
class WorkflowCoverageResult:
    workflow_coverage_pct: float
    workflows: List[WorkflowCoverageEntry]
    total_workflows: int
    fully_covered_workflows: int
    partially_covered_workflows: int
    uncovered_workflows: int


@dataclass
class FrontendScreenEntry:
    screen_name: str
    exists: bool
    has_form: bool
    has_table: bool
    has_pagination: bool
    has_search: bool
    has_loading_state: bool
    has_empty_state: bool
    has_error_state: bool
    has_printable_output: bool
    has_exportable_output: bool
    on_basescreen: bool
    test_file_found: bool
    test_coverage_score: float


@dataclass
class FrontendCoverageResult:
    screen_coverage_pct: float
    form_coverage_pct: float
    table_coverage_pct: float
    ux_state_coverage_pct: float
    print_export_coverage_pct: float
    test_coverage_pct: float
    overall_frontend_score: float
    screens: List[FrontendScreenEntry]
    total_screens: int
    basescreen_screens: int
    unmigrated_widgets: int


@dataclass
class ReportingCoverageEntry:
    report_name: str
    exists: bool
    has_pdf: bool
    has_csv: bool
    has_print_preview: bool
    has_zero_state: bool
    has_large_dataset_handling: bool
    test_coverage_score: float


@dataclass
class ReportingCoverageResult:
    report_coverage_pct: float
    pdf_coverage_pct: float
    csv_coverage_pct: float
    print_coverage_pct: float
    zero_state_coverage_pct: float
    overall_reporting_score: float
    reports: List[ReportingCoverageEntry]


@dataclass
class FailureScenarioEntry:
    scenario_name: str
    category: str
    severity: str
    test_found: bool
    test_file: Optional[str]
    test_function: Optional[str]


@dataclass
class FailureScenarioResult:
    total_scenarios: int
    covered_scenarios: int
    uncovered_scenarios: int
    scenario_coverage_pct: float
    by_category: Dict[str, Dict]
    scenarios: List[FailureScenarioEntry]
    uncovered_high_risk: List[str]


@dataclass
class ReplayDeterminismResult:
    replay_checksum_tests_found: bool
    snapshot_verification_tests_found: bool
    deterministic_replay_tests_found: bool
    event_ordering_tests_found: bool
    replay_modules_tested: Set[str]
    total_replay_tests: int
    replay_coverage_score: float
    determinism_score: float
    auditability_score: float


@dataclass
class TestQualityIssue:
    file: str
    line: int
    issue_type: str
    severity: str


@dataclass
class TestQualityResult:
    total_test_files: int
    files_with_issues: int
    total_issues: int
    assertionless_tests: int
    trivial_tests: int
    duplicate_tests: int
    dead_tests: int
    meaningless_mocks: int
    test_quality_score: float
    details: Dict[str, List[Dict]]


@dataclass
class ModuleCoverageDetail:
    name: str
    tier: str
    raw_coverage: float
    weighted_coverage: float
    meets_minimum: bool
    workflow_coverage: Optional[float]
    failure_coverage: Optional[float]
    test_quality_score: Optional[float]


@dataclass
class RiskWeightedCoverageResult:
    global_raw_coverage: float
    weighted_operational_coverage: float
    critical_path_coverage: float
    risk_adjusted_score: float
    modules: List[ModuleCoverageDetail]
    tier_breakdown: Dict[str, Dict]


@dataclass
class EnterpriseRiskReport:
    global_raw_coverage: float
    weighted_operational_coverage: float
    critical_path_coverage: float
    workflow_coverage: float
    frontend_operational_score: float
    reporting_reliability: float
    replay_determinism_score: float
    auditability_score: float
    top_uncovered_risks: List[str]
    unsafe_modules: List[str]
    release_blockers: List[str]
    final_certification: str


@dataclass
class CertificationVerdict:
    verdict: str  # ENTERPRISE_SAFE | OPERATIONALLY_SAFE | CONDITIONALLY_SAFE | HIGH_RISK | RELEASE_BLOCKED
    score: float
    weighted_score: float
    workflow_score: float
    frontend_score: float
    reporting_score: float
    failure_scenario_score: float
    replay_score: float
    test_quality_score: float
    blocking_issues: List[str]
    risk_report: EnterpriseRiskReport
