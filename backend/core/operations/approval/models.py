"""
Phase 5B.2 — Human Approval Gateway Models.

All models are immutable frozen dataclasses — no mutation allowed.
These are governance authorization artifacts only.
NO execution authority. NO ERP mutation capability.

SIMULATION CONTEXT ONLY — NO REAL EXECUTION.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum


HUMAN_APPROVAL_GATEWAY_VERSION = "1.0.0"
SIMULATION_CONTEXT_MARKER = "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION"


class ApprovalState(str, Enum):
    """Deterministic approval states — immutable, append-only transitions."""
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class RiskLevel(str, Enum):
    """Risk levels mapped from governance pipeline."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuthorityLevel(str, Enum):
    """Human authority levels — NO execution capability."""
    OBSERVER = "OBSERVER"
    REVIEWER = "REVIEWER"
    APPROVER = "APPROVER"
    SENIOR_APPROVER = "SENIOR_APPROVER"
    GOVERNANCE_AUDITOR = "GOVERNANCE_AUDITOR"


APPROVAL_STATE_TRANSITIONS: Dict[ApprovalState, List[ApprovalState]] = {
    ApprovalState.PENDING: [ApprovalState.UNDER_REVIEW, ApprovalState.CANCELLED, ApprovalState.EXPIRED],
    ApprovalState.UNDER_REVIEW: [
        ApprovalState.APPROVED, ApprovalState.REJECTED,
        ApprovalState.ESCALATED, ApprovalState.CANCELLED, ApprovalState.EXPIRED,
    ],
    ApprovalState.APPROVED: [],
    ApprovalState.REJECTED: [],
    ApprovalState.ESCALATED: [
        ApprovalState.ESCALATED, ApprovalState.UNDER_REVIEW, ApprovalState.APPROVED,
        ApprovalState.REJECTED, ApprovalState.CANCELLED, ApprovalState.EXPIRED,
    ],
    ApprovalState.EXPIRED: [],
    ApprovalState.CANCELLED: [],
}


RISK_TO_SIGNATURE_COUNT: Dict[RiskLevel, int] = {
    RiskLevel.NONE: 1,
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


RISK_TO_REQUIRED_AUTHORITY: Dict[RiskLevel, AuthorityLevel] = {
    RiskLevel.NONE: AuthorityLevel.APPROVER,
    RiskLevel.LOW: AuthorityLevel.APPROVER,
    RiskLevel.MEDIUM: AuthorityLevel.APPROVER,
    RiskLevel.HIGH: AuthorityLevel.SENIOR_APPROVER,
    RiskLevel.CRITICAL: AuthorityLevel.SENIOR_APPROVER,
}


@dataclass(frozen=True)
class ApprovalSignature:
    """A single human approval signature.

    Immutable. Represents one governance authorization action.
    NO execution authority — governance record only.
    """
    signature_id: str = field(default_factory=lambda: f"sig_{uuid4().hex[:12]}")
    workflow_id: str = ""
    approver_id: str = ""
    authority_level: AuthorityLevel = AuthorityLevel.REVIEWER
    decision: str = ""  # APPROVED or REJECTED
    justification: str = ""
    signed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    context_marker: str = SIMULATION_CONTEXT_MARKER

    def __post_init__(self):
        if self.decision not in ("APPROVED", "REJECTED", ""):
            raise ValueError(f"Invalid signature decision: {self.decision}")


@dataclass(frozen=True)
class EscalationStep:
    """A single escalation step in the chain.

    Bounded. Immutable. Preserves full lineage.
    """
    step_index: int = 0
    escalated_by: str = ""
    escalated_to: AuthorityLevel = AuthorityLevel.SENIOR_APPROVER
    reason: str = ""
    escalated_from_state: ApprovalState = ApprovalState.UNDER_REVIEW
    escalated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    previous_workflow_id: str = ""
    context_marker: str = SIMULATION_CONTEXT_MARKER


@dataclass(frozen=True)
class ApprovalAuditEntry:
    """A single immutable entry in the governance audit chain.

    Append-only. Never modified. Full lineage preserved.
    """
    entry_id: str = field(default_factory=lambda: f"aud_{uuid4().hex[:12]}")
    workflow_id: str = ""
    action_type: str = ""
    domain: str = ""
    risk_level: str = ""
    previous_state: Optional[ApprovalState] = None
    new_state: ApprovalState = ApprovalState.PENDING
    triggered_by: str = ""  # approver_id, system, escalation, etc.
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    signature: Optional[ApprovalSignature] = None
    escalation: Optional[EscalationStep] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    context_marker: str = SIMULATION_CONTEXT_MARKER


@dataclass(frozen=True)
class ApprovalConfig:
    """Deterministic approval configuration for a risk level.

    Defines requirements without executing anything.
    """
    risk_level: RiskLevel = RiskLevel.NONE
    required_signatures: int = 1
    required_authority: AuthorityLevel = AuthorityLevel.APPROVER
    allow_self_approval: bool = False
    escalation_timeout_minutes: int = 0
    max_escalation_depth: int = 3
    reminder_interval_minutes: int = 0
    max_reminders: int = 3


@dataclass(frozen=True)
class ApprovalWorkflow:
    """Complete immutable approval workflow.

    Wraps governance DecisionResult + simulation outputs into
    a human-authorization-routing container.
    NO execution authority. Governance artifact only.
    """
    workflow_id: str = field(default_factory=lambda: f"awf_{uuid4().hex[:8]}")
    decision_id: str = ""
    plan_id: str = ""
    outcome_id: str = ""
    action_type: str = ""
    domain: str = ""
    risk_level: str = "NONE"
    risk_score: int = 0
    state: ApprovalState = ApprovalState.PENDING
    signatures: List[ApprovalSignature] = field(default_factory=list)
    escalation_chain: List[EscalationStep] = field(default_factory=list)
    audit_entries: List[ApprovalAuditEntry] = field(default_factory=list)
    config: ApprovalConfig = field(default_factory=lambda: ApprovalConfig())
    governance_decision: Dict[str, Any] = field(default_factory=dict)
    simulation_plan: Dict[str, Any] = field(default_factory=dict)
    simulation_outcome: Dict[str, Any] = field(default_factory=dict)
    simulation_context: Dict[str, Any] = field(default_factory=dict)
    timeout_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    context_marker: str = SIMULATION_CONTEXT_MARKER
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotificationRecord:
    """A single deterministic notification.

    Fixed, bounded, non-adaptive. NEVER behavioral influence.
    """
    notification_id: str = field(default_factory=lambda: f"notif_{uuid4().hex[:12]}")
    workflow_id: str = ""
    recipient_id: str = ""
    notification_type: str = "REMINDER"
    message: str = ""
    interval_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    context_marker: str = SIMULATION_CONTEXT_MARKER


@dataclass(frozen=True)
class ApprovalPermission:
    """Role-based authority for the approval gateway.

    NO execution authority. Governance visibility only.
    """
    role: AuthorityLevel = AuthorityLevel.OBSERVER
    can_view_workflows: bool = True
    can_review: bool = False
    can_approve: bool = False
    can_escalate: bool = False
    can_cancel: bool = False
    can_audit: bool = False
    max_risk_level: RiskLevel = RiskLevel.NONE


AUTHORITY_PERMISSIONS: Dict[AuthorityLevel, ApprovalPermission] = {
    AuthorityLevel.OBSERVER: ApprovalPermission(
        role=AuthorityLevel.OBSERVER,
        can_view_workflows=True,
        can_review=False,
        can_approve=False,
        can_escalate=False,
        can_cancel=False,
        can_audit=False,
        max_risk_level=RiskLevel.NONE,
    ),
    AuthorityLevel.REVIEWER: ApprovalPermission(
        role=AuthorityLevel.REVIEWER,
        can_view_workflows=True,
        can_review=True,
        can_approve=False,
        can_escalate=True,
        can_cancel=False,
        can_audit=False,
        max_risk_level=RiskLevel.MEDIUM,
    ),
    AuthorityLevel.APPROVER: ApprovalPermission(
        role=AuthorityLevel.APPROVER,
        can_view_workflows=True,
        can_review=True,
        can_approve=True,
        can_escalate=True,
        can_cancel=True,
        can_audit=False,
        max_risk_level=RiskLevel.MEDIUM,
    ),
    AuthorityLevel.SENIOR_APPROVER: ApprovalPermission(
        role=AuthorityLevel.SENIOR_APPROVER,
        can_view_workflows=True,
        can_review=True,
        can_approve=True,
        can_escalate=True,
        can_cancel=True,
        can_audit=False,
        max_risk_level=RiskLevel.CRITICAL,
    ),
    AuthorityLevel.GOVERNANCE_AUDITOR: ApprovalPermission(
        role=AuthorityLevel.GOVERNANCE_AUDITOR,
        can_view_workflows=True,
        can_review=False,
        can_approve=False,
        can_escalate=False,
        can_cancel=False,
        can_audit=True,
        max_risk_level=RiskLevel.CRITICAL,
    ),
}


def get_approval_permission(authority: AuthorityLevel) -> ApprovalPermission:
    """Get permission set for an authority level.

    Deterministic — same authority always returns same permissions.
    """
    return AUTHORITY_PERMISSIONS.get(authority, AUTHORITY_PERMISSIONS[AuthorityLevel.OBSERVER])
