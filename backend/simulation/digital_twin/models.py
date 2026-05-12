from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class TimeConstraint(str, Enum):
    SLA_BOUND = 'sla_bound'
    DEADLINE = 'deadline'
    BUDGET = 'budget'


class SLAStatus(str, Enum):
    WITHIN = 'within'
    WARNING = 'warning'
    BREACHED = 'breached'


class ExternalSystemType(str, Enum):
    BANKING = 'banking'
    GATEWAY = 'gateway'
    SUPPLIER = 'supplier'
    CREDIT = 'credit'
    TAX = 'tax'


class FailureMode(str, Enum):
    TIMEOUT = 'timeout'
    REJECTION = 'rejection'
    DOWNTIME = 'downtime'
    DELAY = 'delay'
    PARTIAL = 'partial'
    REVERSAL = 'reversal'


class PipelineStage(str, Enum):
    EVENT_INJECTION = 'event_injection'
    WORKFLOW_EXECUTION = 'workflow_execution'
    SYSTEM_MUTATION = 'system_mutation'
    TRUTH_EVALUATION = 'truth_evaluation'
    ROOT_CAUSE = 'root_cause'
    PREDICTIVE_FORECAST = 'predictive_forecast'
    CONTAINMENT_DECISION = 'containment_decision'
    RECOVERY_EXECUTION = 'recovery_execution'
    REPLAY_VERIFICATION = 'replay_verification'
    CONTROL_CENTER_REPORTING = 'control_center_reporting'


class IntegrityCheckType(str, Enum):
    ACCOUNTING = 'accounting'
    INVENTORY = 'inventory'
    TRANSACTION = 'transaction'
    REPLAY = 'replay'
    AUDIT = 'audit'


class RecoveryStage(str, Enum):
    APPROVAL = 'approval'
    EXECUTION = 'execution'
    ROLLBACK = 'rollback'
    RECONCILIATION = 'reconciliation'


class ScenarioType(str, Enum):
    CORE_BUSINESS = 'core_business'
    FAILURE_MODE = 'failure_mode'
    TIME_PRESSURE = 'time_pressure'
    EXTERNAL_INTEGRATION = 'external_integration'


@dataclass
class SLAViolation:
    operation: str
    elapsed_ticks: int
    sla_target: int
    tick: int


@dataclass
class ExternalRequest:
    system: str
    operation: str
    params: Dict[str, Any]
    timestamp: float


@dataclass
class ExternalResponse:
    success: bool
    data: Dict[str, Any]
    error: Optional[str]
    latency_ticks: int
    failure_mode: Optional[str] = None


@dataclass
class ScenarioConfig:
    name: str
    scenario_type: str
    ticks: int
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    name: str
    scenario_type: str
    passed: bool
    stages: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    integrity: Dict[str, Any]


@dataclass
class IntegrityReport:
    all_pass: bool
    checks: List[Dict[str, Any]]
    violations: List[str]
    timestamp: str


@dataclass
class PipelineStageResult:
    stage: str
    success: bool
    input_summary: str
    output_summary: str
    duration_ticks: int
    error: Optional[str] = None


@dataclass
class PipelineResult:
    scenario_name: str
    stages: List[PipelineStageResult]
    all_pass: bool
    integrity_report: Optional[IntegrityReport]
    duration_ticks: int


@dataclass
class DigitalTwinSummary:
    total_scenarios: int
    passed: int
    failed: int
    pass_rate: float
    integrity_all_pass: bool
