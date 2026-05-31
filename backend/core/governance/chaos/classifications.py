"""
Failure Classification System.

Classifies resilience test outcomes by severity and subsystem impact.
Deterministic — same failure always produces same classification.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class FailureSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ADVISORY = "advisory"


class FailureDomain(str, Enum):
    GOVERNANCE = "governance"
    FINANCIAL = "financial"
    UI = "ui"
    PERFORMANCE = "performance"
    RECOVERY = "recovery"
    SECURITY = "security"
    PERSISTENCE = "persistence"


@dataclass
class FailureClassification:
    """Complete failure classification with root cause and impact analysis."""

    failure_id: str
    severity: FailureSeverity
    domain: FailureDomain
    subsystem: str
    root_cause: str
    symptom: str
    governance_response: str
    invariant_response: str
    recovery_possible: bool
    recovery_strategy: str
    regression_risk: str  # low | medium | high
    affected_components: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    def to_dict(self) -> dict:
        return {
            "failure_id": self.failure_id,
            "severity": self.severity.value,
            "domain": self.domain.value,
            "subsystem": self.subsystem,
            "root_cause": self.root_cause,
            "symptom": self.symptom,
            "governance_response": self.governance_response,
            "invariant_response": self.invariant_response,
            "recovery_possible": self.recovery_possible,
            "recovery_strategy": self.recovery_strategy,
            "regression_risk": self.regression_risk,
            "affected_components": self.affected_components,
            "timestamp": self.timestamp,
        }


def classify_failure(
    failure_mode: str,
    subsystem: str = "",
    details: Optional[dict] = None,
) -> FailureClassification:
    """Classify a failure based on its mode and context.

    Deterministic classification — same inputs always produce same result.
    """
    details = details or {}

    # Failure mode → classification mapping
    classification_map = {
        "governance_collapse": FailureClassification(
            failure_id="FC-GOV-001",
            severity=FailureSeverity.CRITICAL,
            domain=FailureDomain.GOVERNANCE,
            subsystem=subsystem or "governance_kernel",
            root_cause="Governance kernel entered recursive enforcement loop",
            symptom="Enforcement latency exceeded threshold, multiple denials",
            governance_response="Failsafe mode triggered, critical policies preserved",
            invariant_response="Invariants continued functioning",
            recovery_possible=True,
            recovery_strategy="Automatic failsafe recovery via self_health monitor",
            regression_risk="high",
            affected_components=["governance_kernel", "policy_enforcer"],
        ),
        "event_storm": FailureClassification(
            failure_id="FC-GOV-002",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.GOVERNANCE,
            subsystem=subsystem or "event_bus",
            root_cause="Excessive governance events triggered amplification loop",
            symptom="Event rate exceeded threshold, queue backlog growing",
            governance_response="Deduplication reduced duplicate events, failsafe degraded low-tier",
            invariant_response="Not affected",
            recovery_possible=True,
            recovery_strategy="Event dedup + self-health auto-throttling",
            regression_risk="medium",
            affected_components=["event_bus", "metrics"],
        ),
        "recursion_attack": FailureClassification(
            failure_id="FC-GOV-003",
            severity=FailureSeverity.CRITICAL,
            domain=FailureDomain.GOVERNANCE,
            subsystem=subsystem or "policy_enforcer",
            root_cause="Circular policy dependency created infinite enforcement chain",
            symptom="Recursion depth exceeded safety limit",
            governance_response="Recursion detector triggered failsafe, blocked further enforcement",
            invariant_response="Not affected",
            recovery_possible=True,
            recovery_strategy="Recursion detection + fail-closed enforcement",
            regression_risk="high",
            affected_components=["policy_enforcer", "self_health"],
        ),
        "audit_saturation": FailureClassification(
            failure_id="FC-GOV-004",
            severity=FailureSeverity.MEDIUM,
            domain=FailureDomain.GOVERNANCE,
            subsystem=subsystem or "audit_log",
            root_cause="Audit log reached capacity, oldest entries evicted",
            symptom="Audit log entries being dropped",
            governance_response="Bounded audit log preserved most recent entries",
            invariant_response="Not affected",
            recovery_possible=True,
            recovery_strategy="Bounded deque ensures memory safety",
            regression_risk="low",
            affected_components=["audit_log"],
        ),
        "partial_transaction_failure": FailureClassification(
            failure_id="FC-FIN-001",
            severity=FailureSeverity.CRITICAL,
            domain=FailureDomain.FINANCIAL,
            subsystem=subsystem or "accounting",
            root_cause="Transaction rolled back mid-posting due to invariant violation",
            symptom="Journal entry partially created then rolled back",
            governance_response="Atomic rollback preserved accounting integrity",
            invariant_response="Invariant check triggered rollback, no orphan records",
            recovery_possible=True,
            recovery_strategy="Atomic transaction rollback restores consistent state",
            regression_risk="high",
            affected_components=["accounting", "journal_engine"],
        ),
        "duplicate_action": FailureClassification(
            failure_id="FC-FIN-002",
            severity=FailureSeverity.MEDIUM,
            domain=FailureDomain.FINANCIAL,
            subsystem=subsystem or "workflow",
            root_cause="Duplicate state transition attempted",
            symptom="Same transition requested twice",
            governance_response="State machine blocked duplicate, audit recorded",
            invariant_response="Not affected — transition never executed",
            recovery_possible=True,
            recovery_strategy="Idempotency via state machine validation",
            regression_risk="low",
            affected_components=["state_machine", "enforcer"],
        ),
        "illegal_state_mutation": FailureClassification(
            failure_id="FC-FIN-003",
            severity=FailureSeverity.CRITICAL,
            domain=FailureDomain.FINANCIAL,
            subsystem=subsystem or "accounting",
            root_cause="Direct state mutation bypassed governance",
            symptom="Status changed without journal entry or stock movement",
            governance_response="Invariant check detected inconsistency, audit recorded",
            invariant_response="Failed — missing journal entry for approved return",
            recovery_possible=True,
            recovery_strategy="Invariant scanner detects and reports on next scan",
            regression_risk="high",
            affected_components=["returns", "sales", "purchases", "enforcer"],
        ),
        "listener_saturation": FailureClassification(
            failure_id="FC-GOV-005",
            severity=FailureSeverity.MEDIUM,
            domain=FailureDomain.GOVERNANCE,
            subsystem=subsystem or "event_bus",
            root_cause="Event listeners exceeded capacity limit",
            symptom="Listener registration blocked",
            governance_response="Listener limit enforced, existing listeners preserved",
            invariant_response="Not affected",
            recovery_possible=True,
            recovery_strategy="Bounded listener registry with capacity enforcement",
            regression_risk="low",
            affected_components=["event_bus", "self_health"],
        ),
        "startup_blocked": FailureClassification(
            failure_id="FC-REC-001",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.RECOVERY,
            subsystem=subsystem or "system",
            root_cause="Missing dependency prevented system startup",
            symptom="System check failed with actionable diagnostic",
            governance_response="Fail-closed startup — system will not start in broken state",
            invariant_response="Not applicable",
            recovery_possible=True,
            recovery_strategy="Install missing dependency, re-run system check",
            regression_risk="low",
            affected_components=["readiness", "system_checks"],
        ),
        "memory_growth": FailureClassification(
            failure_id="FC-PERF-001",
            severity=FailureSeverity.HIGH,
            domain=FailureDomain.PERFORMANCE,
            subsystem=subsystem or "governance_kernel",
            root_cause="Unbounded queue growth under sustained load",
            symptom="Memory usage increased linearly with scenario duration",
            governance_response="Bounded structures prevented unbounded growth",
            invariant_response="Not affected",
            recovery_possible=True,
            recovery_strategy="Bounded deques with maxlen enforcement",
            regression_risk="medium",
            affected_components=["events", "metrics", "audit_log"],
        ),
    }

    return classification_map.get(
        failure_mode,
        FailureClassification(
            failure_id=f"FC-UNK-{hash(failure_mode) % 10000:04d}",
            severity=FailureSeverity.ADVISORY,
            domain=FailureDomain.GOVERNANCE,
            subsystem=subsystem or "unknown",
            root_cause=f"Unclassified failure: {failure_mode}",
            symptom="Unknown failure pattern",
            governance_response="Not classified",
            invariant_response="Not classified",
            recovery_possible=True,
            recovery_strategy="Investigate and classify manually",
            regression_risk="unknown",
        ),
    )
