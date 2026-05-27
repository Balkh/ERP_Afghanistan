"""
Governance Kernel — Enterprise Runtime Governance Layer.

Single authoritative source for ALL runtime governance operations.
Lazily initialized. Zero startup overhead. Forward-compatible.

Modules:
  kernel               — Central GovernanceKernel orchestrator
  registries           — Policy, Invariant, Environment, FeatureGate, Readiness, UIRule registries
  contracts            — Deterministic governance contracts (all domains)
  enforcer             — Central policy enforcer + state transition validation
  events               — Structured governance events with noise control
  metrics              — Lightweight governance metrics (latency, denials, failures)
  self_health          — Governance kernel self-monitoring and failsafe
  api                  — Discovery API and auto-documentation
  readiness            — System readiness validator (11 checks)
  bootstrap            — Idempotent bootstrap orchestrator
  state_transitions    — Domain state machines (ReturnOrder, SalesInvoice, PurchaseInvoice)
  invariant_validator  — Domain invariant validator (6 domains)
  observability_config — Environment-aware observability sampling
  ui_governance        — UI governance scanner
  graceful_degradation — Graceful degradation computation
  runtime_governor     — Runtime state aggregation (deprecated — use kernel.health())
  query_governance     — Query governance enforcement (soft mode)
  chaos/engine         — SAFE chaos execution engine (production-locked, rollback-safe)
  chaos/classifications — Failure classification system
  chaos/simulations    — Pre-built chaos simulation scenarios

  deployment           — Phase 1: Deployment Certification (prechecks, atomic validation, fingerprint)
  backup_recovery      — Phase 2: Backup + Recovery Certification (validation, restore, readiness)
  upgrade              — Phase 3: Upgrade + Migration Certification (governance, simulation, compat)
  soak                 — Phase 4: Long-Duration Runtime Certification (soak, memory, drift)
  offline              — Phase 5: Offline-First + Multi-Branch Certification (resilience, sync, degredation)
  maintainability      — Phase 6: Operational Maintainability Governance (debt, risk, drift)
  observability        — Phase 7: Enterprise Operational Observability (health, reconstruction, telemetry)
  operational_certification — Master orchestrator for all 7 certification phases

KERNEL_VERSION = "2.0.0"
"""

from core.governance.kernel import GovernanceKernel, PriorityTier, EnforcementResult
from core.governance.registries import (
    PolicyRegistry, InvariantRegistry, EnvironmentRegistry,
    FeatureGateRegistry, ReadinessRegistry, UIRuleRegistry, PolicyRule,
)
from core.governance.events import get_event_bus, GovernanceEvent, EventSeverity
from core.governance.metrics import get_metrics

# Certification modules
from core.governance.deployment import (
    DeploymentValidator, AtomicDeploymentValidator, DeploymentReport,
    DeploymentFingerprint, DeploymentCheck,
)
from core.governance.backup_recovery import (
    BackupValidator, RestoreCertification, RecoveryReadinessAssessor,
    SafeRecoveryManager, BackupValidationResult, RecoveryCertificationResult,
    RecoveryReadinessScore, SafeRecoveryMode,
)
from core.governance.upgrade import (
    MigrationGovernor, SafeUpgradeSimulator, BackwardCompatibilityValidator,
    UpgradeAuditLog, UpgradeAuditEntry,
)
from core.governance.soak import (
    SoakTestFramework, SoakTestResult, MemoryStabilityReport, LatencyDriftReport,
)
from core.governance.offline import (
    OfflineResilienceTester, MultiBranchGovernanceValidator,
    SyncConflictCertifier, NetworkDegradationSimulator,
)
from core.governance.maintainability import (
    TechnicalDebtClassifier, ChangeRiskEngine, ArchitectureFreezeEnforcer,
    OperationalDriftDetector,
)
from core.governance.observability import (
    OperationalHealthDashboard, IncidentReconstructor,
    NoiseSafeTelemetryManager, OperationalHealth,
)
from core.governance.industrial_test_suite import (
    IndustrialTestSuiteRunner, IndustrialTestReport,
    PhaseA, PhaseB, PhaseC, PhaseD, PhaseE, PhaseF, PhaseG,
    PhaseAResult, PhaseBResult, PhaseCResult, PhaseDResult,
    PhaseEResult, PhaseFResult, PhaseGResult,
)
from core.governance.operational_certification import (
    OperationalCertificationOrchestrator, MasterCertificationReport,
    PhaseCertificationResult,
)

# Control Plane modules
from core.governance.control_plane import (
    ControlPlaneOrchestrator,
    OperationalScheduleRegistry, ScheduleEntry, ScheduleFrequency,
    ExecutionPolicyEngine, ExecutionStatus,
    CertificationScheduler,
    OperationalIntelligenceEngine, TrendWindow, RiskFactors, OperationalRiskScore,
    DeploymentControlGate, GateResult, GateVerdict,
    DriftPreventionLayer, DriftEscalationLevel, DriftAlert,
    RecoveryOrchestrationLayer, RecoveryPlan, RecoveryStep,
    OperationalHealthLoop, HealthSnapshot, StabilityScore,
    CONTROL_PLANE_VERSION,
)

__all__ = [
    "GovernanceKernel", "PriorityTier", "EnforcementResult",
    "PolicyRegistry", "InvariantRegistry", "EnvironmentRegistry",
    "FeatureGateRegistry", "ReadinessRegistry", "UIRuleRegistry", "PolicyRule",
    "get_event_bus", "GovernanceEvent", "EventSeverity",
    "get_metrics",
    # Phase 1
    "DeploymentValidator", "AtomicDeploymentValidator", "DeploymentReport",
    "DeploymentFingerprint", "DeploymentCheck",
    # Phase 2
    "BackupValidator", "RestoreCertification", "RecoveryReadinessAssessor",
    "SafeRecoveryManager", "BackupValidationResult", "RecoveryCertificationResult",
    "RecoveryReadinessScore", "SafeRecoveryMode",
    # Phase 3
    "MigrationGovernor", "SafeUpgradeSimulator", "BackwardCompatibilityValidator",
    "UpgradeAuditLog", "UpgradeAuditEntry",
    # Phase 4
    "SoakTestFramework", "SoakTestResult", "MemoryStabilityReport", "LatencyDriftReport",
    # Phase 5
    "OfflineResilienceTester", "MultiBranchGovernanceValidator",
    "SyncConflictCertifier", "NetworkDegradationSimulator",
    # Phase 6
    "TechnicalDebtClassifier", "ChangeRiskEngine", "ArchitectureFreezeEnforcer",
    "OperationalDriftDetector",
    # Phase 7
    "OperationalHealthDashboard", "IncidentReconstructor",
    "NoiseSafeTelemetryManager", "OperationalHealth",
    # Orchestrator
    "OperationalCertificationOrchestrator", "MasterCertificationReport",
    "PhaseCertificationResult",
    # Control Plane
    "ControlPlaneOrchestrator",
    "OperationalScheduleRegistry", "ScheduleEntry", "ScheduleFrequency",
    "ExecutionPolicyEngine", "ExecutionStatus",
    "CertificationScheduler",
    "OperationalIntelligenceEngine", "TrendWindow", "RiskFactors", "OperationalRiskScore",
    "DeploymentControlGate", "GateResult", "GateVerdict",
    "DriftPreventionLayer", "DriftEscalationLevel", "DriftAlert",
    "RecoveryOrchestrationLayer", "RecoveryPlan", "RecoveryStep",
    "OperationalHealthLoop", "HealthSnapshot", "StabilityScore",
    "CONTROL_PLANE_VERSION",
]
