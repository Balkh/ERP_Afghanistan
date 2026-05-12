from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContainmentStatus(str, Enum):
    ISOLATED = 'isolated'
    QUARANTINED = 'quarantined'
    MONITORING = 'monitoring'
    RELEASED = 'released'
    FAILED = 'failed'


class IntegritySeverity(str, Enum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class CorruptionType(str, Enum):
    FINANCIAL = 'financial'
    INVENTORY = 'inventory'
    ORPHAN_STATE = 'orphan_state'
    RECONCILIATION = 'reconciliation'
    JOURNAL_BALANCE = 'journal_balance'
    CONSISTENCY = 'consistency'


class EscalationPriority(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    IMMEDIATE = 'immediate'


class RecoveryPathType(str, Enum):
    ROLLBACK = 'rollback'
    RECONCILE = 'reconcile'
    REPROCESS = 'reprocess'
    MANUAL_INTERVENTION = 'manual_intervention'
    IGNORE = 'ignore'


class DegradationLevel(str, Enum):
    FULL = 'full'
    REDUCED = 'reduced'
    MINIMUM = 'minimum'
    EMERGENCY = 'emergency'


class OperationalStatus(str, Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    CONTAINED = 'contained'
    CRITICAL = 'critical'


class RecoverySeverity(str, Enum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


@dataclass
class ContainmentRecord:
    workflow_id: str
    workflow_type: str
    status: ContainmentStatus
    isolation_tick: int
    reason: str
    affected_components: List[str] = field(default_factory=list)
    quarantine_expiry_tick: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuarantineRecord:
    workflow_id: str
    workflow_type: str
    quarantined_at_tick: int
    reason: str
    severity: IntegritySeverity
    evidence: List[str] = field(default_factory=list)
    related_workflows: List[str] = field(default_factory=list)
    expiry_tick: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContainmentResult:
    contained: bool
    containment_id: str
    status: ContainmentStatus
    blocking: bool
    isolated_workflows: List[str] = field(default_factory=list)
    quarantined_workflows: List[str] = field(default_factory=list)
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityViolation:
    violation_id: str
    violation_type: CorruptionType
    severity: IntegritySeverity
    source_module: str
    description: str
    detected_at_tick: int
    affected_entities: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorruptionRecord:
    corruption_id: str
    corruption_type: CorruptionType
    severity: IntegritySeverity
    source_module: str
    description: str
    detected_at_tick: int
    affected_entities: List[str] = field(default_factory=list)
    estimated_blast_radius: float = 0.0
    requires_manual_intervention: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlastRadiusResult:
    estimated_impact_score: float
    affected_workflows: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    financial_exposure: float = 0.0
    inventory_items_affected: int = 0
    total_dependencies: int = 0
    critical_path_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyImpact:
    module_name: str
    impact_score: float
    dependency_depth: int
    affected_downstream: List[str] = field(default_factory=list)
    is_critical_path: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FinancialRiskEstimate:
    estimated_exposure: float
    risk_level: IntegritySeverity
    currency: str = "AFN"
    affected_accounts: List[str] = field(default_factory=list)
    potential_je_corrections: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InventoryRiskEstimate:
    estimated_items_affected: int
    risk_level: IntegritySeverity
    affected_warehouses: List[str] = field(default_factory=list)
    potential_batch_corrections: int = 0
    estimated_value_at_risk: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryRecommendation:
    recommendation_id: str
    path_type: RecoveryPathType
    priority: int
    description: str
    estimated_effort: str = "medium"
    requires_manual_review: bool = False
    automated_possible: bool = False
    risks: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPlaybook:
    playbook_id: str
    name: str
    applicable_corruption_types: List[CorruptionType] = field(default_factory=list)
    severity_threshold: IntegritySeverity = IntegritySeverity.MEDIUM
    steps: List[str] = field(default_factory=list)
    estimated_duration_ticks: int = 10
    requires_escalation: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackSimulation:
    simulation_id: str
    target_tick: int
    workflows_affected: int = 0
    journal_entries_affected: int = 0
    inventory_movements_affected: int = 0
    estimated_risk_score: float = 0.0
    has_conflicts: bool = False
    conflicts: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackRisk:
    risk_score: float
    severity: IntegritySeverity
    conflicting_transactions: List[str] = field(default_factory=list)
    dependency_chain_length: int = 0
    has_irreversible_operations: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EscalationRecord:
    escalation_id: str
    priority: EscalationPriority
    source_module: str
    reason: str
    severity: IntegritySeverity
    generated_at_tick: int
    affected_workflows: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    requires_immediate_action: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DegradationAction:
    action_id: str
    degradation_level: DegradationLevel
    description: str
    services_to_reduce: List[str] = field(default_factory=list)
    services_to_preserve: List[str] = field(default_factory=list)
    estimated_impact: str = "low"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DegradationPolicy:
    policy_id: str
    degradation_level: DegradationLevel
    active: bool = False
    allowed_operations: List[str] = field(default_factory=list)
    restricted_operations: List[str] = field(default_factory=list)
    fallback_strategy: str = "reject"
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryPipeline:
    pipeline_id: str
    steps: List[str] = field(default_factory=list)
    current_step: int = 0
    is_running: bool = False
    is_complete: bool = False
    has_failed: bool = False
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrityIncident:
    incident_id: str
    severity: IntegritySeverity
    detected_at_tick: int
    violations: List[IntegrityViolation] = field(default_factory=list)
    corruption_records: List[CorruptionRecord] = field(default_factory=list)
    blast_radius: Optional[BlastRadiusResult] = None
    recommendations: List[RecoveryRecommendation] = field(default_factory=list)
    escalation: Optional[EscalationRecord] = None
    containment: Optional[ContainmentResult] = None
    requires_manual_intervention: bool = False
    is_resolved: bool = False
    resolved_at_tick: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FullRecoveryReport:
    report_id: str
    generated_at_tick: int
    operational_status: OperationalStatus
    degradation_level: DegradationLevel
    active_incidents: List[IntegrityIncident] = field(default_factory=list)
    contained_workflows: List[ContainmentRecord] = field(default_factory=list)
    quarantined_workflows: List[QuarantineRecord] = field(default_factory=list)
    active_escalations: List[EscalationRecord] = field(default_factory=list)
    active_pipelines: List[RecoveryPipeline] = field(default_factory=list)
    overall_risk_score: float = 0.0
    recommendations_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
