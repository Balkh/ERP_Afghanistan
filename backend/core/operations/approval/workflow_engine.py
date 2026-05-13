"""
Phase 5B.2 — Deterministic Approval Workflow Engine.

Routes governance DecisionResult + SimulationPlan + SimulationOutcome
through structured human approval workflows.

ZERO EXECUTION AUTHORITY. Approval routing only.
NO ERP mutation. NO side effects.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from core.operations.approval.models import (
    ApprovalState, ApprovalState, ApprovalWorkflow, ApprovalConfig,
    ApprovalAuditEntry, ApprovalSignature, EscalationStep,
    RiskLevel, AuthorityLevel,
    APPROVAL_STATE_TRANSITIONS, RISK_TO_SIGNATURE_COUNT,
    RISK_TO_REQUIRED_AUTHORITY, SIMULATION_CONTEXT_MARKER,
    HUMAN_APPROVAL_GATEWAY_VERSION,
)

logger = logging.getLogger('erp.approval.workflow_engine')

WORKFLOW_ENGINE_VERSION = "1.0.0"
MAX_WORKFLOWS_IN_MEMORY = 1000


class WorkflowRegistry:
    """Deterministic, bounded registry for active approval workflows.

    Bounded memory — maxlen enforcement.
    Append-only. No mutation of existing workflows.
    """

    def __init__(self, max_workflows: int = MAX_WORKFLOWS_IN_MEMORY):
        self._workflows: Dict[str, ApprovalWorkflow] = {}
        self._max_workflows = max_workflows
        self._decision_to_workflow: Dict[str, str] = {}
        self._plan_to_workflow: Dict[str, str] = {}

    def register(self, workflow: ApprovalWorkflow) -> None:
        if workflow.workflow_id in self._workflows:
            raise ValueError(f"Workflow {workflow.workflow_id} already registered")
        if len(self._workflows) >= self._max_workflows:
            raise RuntimeError(f"Workflow registry full (max={self._max_workflows})")
        self._workflows[workflow.workflow_id] = workflow
        if workflow.decision_id:
            self._decision_to_workflow[workflow.decision_id] = workflow.workflow_id
        if workflow.plan_id:
            self._plan_to_workflow[workflow.plan_id] = workflow.workflow_id

    def get(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        return self._workflows.get(workflow_id)

    def get_by_decision(self, decision_id: str) -> Optional[ApprovalWorkflow]:
        wid = self._decision_to_workflow.get(decision_id)
        return self._workflows.get(wid) if wid else None

    def get_by_plan(self, plan_id: str) -> Optional[ApprovalWorkflow]:
        wid = self._plan_to_workflow.get(plan_id)
        return self._workflows.get(wid) if wid else None

    def list_active(self) -> List[ApprovalWorkflow]:
        active_states = {ApprovalState.PENDING, ApprovalState.UNDER_REVIEW, ApprovalState.ESCALATED}
        return [w for w in self._workflows.values() if w.state in active_states]

    def list_by_risk(self, risk_level: str) -> List[ApprovalWorkflow]:
        return [w for w in self._workflows.values() if w.risk_level == risk_level]

    def count(self) -> int:
        return len(self._workflows)

    def clear(self) -> None:
        self._workflows.clear()
        self._decision_to_workflow.clear()
        self._plan_to_workflow.clear()

    def replay_rebuild(self, workflows: List[ApprovalWorkflow]) -> None:
        self.clear()
        for w in workflows:
            self._workflows[w.workflow_id] = w
            if w.decision_id:
                self._decision_to_workflow[w.decision_id] = w.workflow_id
            if w.plan_id:
                self._plan_to_workflow[w.plan_id] = w.workflow_id


# Global registry instance
_registry: Optional[WorkflowRegistry] = None


def get_registry() -> WorkflowRegistry:
    global _registry
    if _registry is None:
        _registry = WorkflowRegistry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None


def create_approval_config(risk_level: str) -> ApprovalConfig:
    """Create deterministic approval config from risk level.

    Args:
        risk_level: NONE, LOW, MEDIUM, HIGH, CRITICAL

    Returns:
        Immutable ApprovalConfig with deterministic requirements.
    """
    try:
        rl = RiskLevel(risk_level)
    except ValueError:
        rl = RiskLevel.NONE

    required_sigs = RISK_TO_SIGNATURE_COUNT.get(rl, 1)
    required_auth = RISK_TO_REQUIRED_AUTHORITY.get(rl, AuthorityLevel.APPROVER)

    timeout_map = {
        RiskLevel.NONE: 0,
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1440,
        RiskLevel.HIGH: 720,
        RiskLevel.CRITICAL: 360,
    }

    reminder_map = {
        RiskLevel.NONE: 0,
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1440,
        RiskLevel.HIGH: 720,
        RiskLevel.CRITICAL: 360,
    }

    return ApprovalConfig(
        risk_level=rl,
        required_signatures=required_sigs,
        required_authority=required_auth,
        allow_self_approval=False,
        escalation_timeout_minutes=timeout_map.get(rl, 0),
        max_escalation_depth=3,
        reminder_interval_minutes=reminder_map.get(rl, 0),
        max_reminders=3,
    )


def create_workflow(
    decision_id: str,
    action_type: str,
    domain: str,
    risk_level: str,
    risk_score: int,
    governance_decision: Dict[str, Any],
    simulation_plan: Dict[str, Any],
    simulation_outcome: Dict[str, Any],
    simulation_context: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> ApprovalWorkflow:
    """Create a new immutable approval workflow.

    Deterministic — same inputs produce same routing configuration.

    Args:
        decision_id: The governance DecisionResult decision_id.
        action_type: Type of action requiring approval.
        domain: Operational domain.
        risk_level: Risk level (NONE|LOW|MEDIUM|HIGH|CRITICAL).
        risk_score: Numeric risk score.
        governance_decision: DecisionResult artifact (dict).
        simulation_plan: SimulationPlan artifact (dict).
        simulation_outcome: SimulationOutcome artifact (dict).
        simulation_context: Simulation context metadata.
        metadata: Optional additional metadata.

    Returns:
        An immutable ApprovalWorkflow in PENDING state.

    Raises:
        ValueError: If required fields are missing.
    """
    if not decision_id:
        raise ValueError("decision_id is required")
    if not action_type:
        raise ValueError("action_type is required")

    config = create_approval_config(risk_level)

    timeout_at = None
    if config.escalation_timeout_minutes > 0:
        timeout_dt = datetime.utcnow() + timedelta(minutes=config.escalation_timeout_minutes)
        timeout_at = timeout_dt.isoformat() + "Z"

    workflow = ApprovalWorkflow(
        decision_id=decision_id,
        plan_id=simulation_plan.get("plan_id", "") if simulation_plan else "",
        outcome_id=simulation_outcome.get("plan_id", "") if simulation_outcome else "",
        action_type=action_type,
        domain=domain,
        risk_level=risk_level,
        risk_score=risk_score,
        state=ApprovalState.PENDING,
        config=config,
        governance_decision=governance_decision,
        simulation_plan=simulation_plan,
        simulation_outcome=simulation_outcome,
        simulation_context=simulation_context,
        timeout_at=timeout_at,
        metadata={
            "workflow_engine_version": WORKFLOW_ENGINE_VERSION,
            **(metadata or {}),
        },
    )

    audit_entry = ApprovalAuditEntry(
        workflow_id=workflow.workflow_id,
        action_type=action_type,
        domain=domain,
        risk_level=risk_level,
        previous_state=None,
        new_state=ApprovalState.PENDING,
        triggered_by="system",
        metadata={"reason": "workflow_created", "decision_id": decision_id},
    )

    object.__setattr__(workflow, 'audit_entries', [audit_entry])

    return workflow


def transition_workflow(
    workflow: ApprovalWorkflow,
    new_state: ApprovalState,
    triggered_by: str,
    signature: Optional[ApprovalSignature] = None,
    escalation: Optional[EscalationStep] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ApprovalWorkflow:
    """Deterministically transition a workflow to a new state.

    Creates a new workflow instance with updated state (append-only).
    Original workflow is never mutated.

    Args:
        workflow: Current immutable workflow.
        new_state: Target state.
        triggered_by: Who/what triggered the transition.
        signature: Optional signature artifact.
        escalation: Optional escalation step.
        metadata: Optional transition metadata.

    Returns:
        A new immutable workflow in the new state.

    Raises:
        ValueError: If the transition is invalid.
        RuntimeError: If the workflow is in a terminal state.
    """
    if workflow.state in (ApprovalState.APPROVED, ApprovalState.REJECTED,
                          ApprovalState.EXPIRED, ApprovalState.CANCELLED):
        raise RuntimeError(
            f"Cannot transition from terminal state: {workflow.state.value}"
        )

    allowed = APPROVAL_STATE_TRANSITIONS.get(workflow.state, [])
    if new_state not in allowed:
        raise ValueError(
            f"Invalid state transition: {workflow.state.value} → {new_state.value}. "
            f"Allowed from {workflow.state.value}: {[s.value for s in allowed]}"
        )

    new_signatures = list(workflow.signatures)
    if signature is not None:
        new_signatures.append(signature)

    new_escalation_chain = list(workflow.escalation_chain)
    if escalation is not None:
        new_escalation_chain.append(escalation)

    new_audit = ApprovalAuditEntry(
        workflow_id=workflow.workflow_id,
        action_type=workflow.action_type,
        domain=workflow.domain,
        risk_level=workflow.risk_level,
        previous_state=workflow.state,
        new_state=new_state,
        triggered_by=triggered_by,
        signature=signature,
        escalation=escalation,
        metadata={"workflow_engine_version": WORKFLOW_ENGINE_VERSION, **(metadata or {})},
    )

    updated_audit_entries = list(workflow.audit_entries) + [new_audit]

    try:
        from core.operations.approval.audit import get_audit_chain as _get_ac
        _ac = _get_ac()
        if _ac is not None:
            _ac.append(new_audit)
    except Exception:
        pass

    new_workflow = ApprovalWorkflow(
        workflow_id=workflow.workflow_id,
        decision_id=workflow.decision_id,
        plan_id=workflow.plan_id,
        outcome_id=workflow.outcome_id,
        action_type=workflow.action_type,
        domain=workflow.domain,
        risk_level=workflow.risk_level,
        risk_score=workflow.risk_score,
        state=new_state,
        signatures=new_signatures,
        escalation_chain=new_escalation_chain,
        audit_entries=updated_audit_entries,
        config=workflow.config,
        governance_decision=workflow.governance_decision,
        simulation_plan=workflow.simulation_plan,
        simulation_outcome=workflow.simulation_outcome,
        simulation_context=workflow.simulation_context,
        timeout_at=workflow.timeout_at,
        created_at=workflow.created_at,
        updated_at=datetime.utcnow().isoformat() + "Z",
        context_marker=workflow.context_marker,
        metadata=workflow.metadata,
    )

    if _registry:
        _registry._workflows[new_workflow.workflow_id] = new_workflow

    return new_workflow


def check_timeout_expiry(workflow: ApprovalWorkflow) -> Tuple[bool, Optional[ApprovalWorkflow]]:
    """Check if a workflow has timed out and transition to EXPIRED.

    Deterministic — same workflow + same clock = same result.

    Args:
        workflow: The workflow to check.

    Returns:
        (True, new_workflow) if timed out, (False, None) otherwise.
    """
    if workflow.state in (ApprovalState.APPROVED, ApprovalState.REJECTED,
                          ApprovalState.EXPIRED, ApprovalState.CANCELLED):
        return False, None

    if workflow.timeout_at is None:
        return False, None

    try:
        timeout_dt = datetime.fromisoformat(workflow.timeout_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return False, None

    timeout_dt = timeout_dt.replace(tzinfo=None)
    if datetime.utcnow() >= timeout_dt:
        new_workflow = transition_workflow(
            workflow,
            ApprovalState.EXPIRED,
            triggered_by="system_timeout",
            metadata={"reason": "approval_timeout_expired", "timeout_at": workflow.timeout_at},
        )
        return True, new_workflow

    return False, None


def get_approval_summary(workflow: ApprovalWorkflow) -> Dict[str, Any]:
    """Generate a deterministic summary of workflow state.

    Informational only. NO execution data.
    """
    return {
        "workflow_id": workflow.workflow_id,
        "decision_id": workflow.decision_id,
        "action_type": workflow.action_type,
        "domain": workflow.domain,
        "risk_level": workflow.risk_level,
        "risk_score": workflow.risk_score,
        "state": workflow.state.value,
        "signature_count": len(workflow.signatures),
        "required_signatures": workflow.config.required_signatures,
        "escalation_depth": len(workflow.escalation_chain),
        "max_escalation_depth": workflow.config.max_escalation_depth,
        "audit_entry_count": len(workflow.audit_entries),
        "timeout_at": workflow.timeout_at,
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
        "context_marker": workflow.context_marker,
    }
