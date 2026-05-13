"""
Phase 5B.2 — Deterministic Escalation Engine.

Bounded, deterministic escalation routing for approval workflows.
Escalation is a governance artifact only — NO execution.

Safety guarantees:
- Bounded escalation depth (max 3)
- Deterministic escalation paths
- No escalation loops (cycle detection)
- Preserves original decision metadata
- Immutable audit lineage
- Never auto-resolves decisions
- Never auto-approves
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set

from core.operations.approval.models import (
    ApprovalState, ApprovalWorkflow, ApprovalConfig,
    ApprovalAuditEntry, EscalationStep, ApprovalSignature,
    AuthorityLevel, RiskLevel,
    SIMULATION_CONTEXT_MARKER,
)
from core.operations.approval.workflow_engine import (
    transition_workflow,
)

logger = logging.getLogger('erp.approval.escalation')

ESCALATION_ENGINE_VERSION = "1.0.0"
MAX_ESCALATION_DEPTH = 3


class EscalationError(ValueError):
    """Raised when escalation validation fails."""
    pass


# Authority escalation order (deterministic, ordered)
ESCALATION_AUTHORITY_ORDER = [
    AuthorityLevel.APPROVER,
    AuthorityLevel.SENIOR_APPROVER,
]


def validate_escalation(
    workflow: ApprovalWorkflow,
    escalated_by: str,
    escalated_to: AuthorityLevel,
    reason: str,
) -> Tuple[bool, str]:
    """Validate that an escalation can proceed.

    Determines validity without any side effects.

    Args:
        workflow: The current workflow.
        escalated_by: Who is requesting escalation.
        escalated_to: Target authority level.
        reason: Escalation reason.

    Returns:
        (is_valid: bool, reason: str)
    """
    if workflow.state not in (ApprovalState.UNDER_REVIEW, ApprovalState.ESCALATED):
        return False, f"Cannot escalate from state: {workflow.state.value}"

    if workflow.state == ApprovalState.EXPIRED:
        return False, "Cannot escalate from EXPIRED state"

    if len(workflow.escalation_chain) >= MAX_ESCALATION_DEPTH:
        return False, f"Maximum escalation depth ({MAX_ESCALATION_DEPTH}) reached"

    if len(workflow.escalation_chain) >= workflow.config.max_escalation_depth:
        return False, f"Configuration max escalation depth ({workflow.config.max_escalation_depth}) reached"

    depth = len(workflow.escalation_chain)
    if escalated_to not in ESCALATION_AUTHORITY_ORDER:
        return False, f"Invalid escalation target: {escalated_to.value}"

    if depth > 0 and escalated_to == ESCALATION_AUTHORITY_ORDER[depth - 1]:
        return False, "Cannot escalate to same authority level as previous step"

    escalation_ids = [e.escalated_by for e in workflow.escalation_chain]
    if escalated_by in escalation_ids:
        return False, f"Duplicate escalation by {escalated_by}"

    if _detect_escalation_cycle(workflow, escalated_to):
        return False, f"Escalation would create a cycle at {escalated_to.value}"

    if not reason.strip():
        return False, "Escalation reason is required"

    return True, "Escalation valid"


def escalate(
    workflow: ApprovalWorkflow,
    escalated_by: str,
    escalated_to: AuthorityLevel,
    reason: str,
) -> ApprovalWorkflow:
    """Escalate a workflow to a higher authority level.

    Deterministic — same inputs produce same escalation result.

    Args:
        workflow: Current workflow.
        escalated_by: Who is escalating.
        escalated_to: Target authority level.
        reason: Escalation reason.

    Returns:
        Updated workflow in ESCALATED state.

    Raises:
        EscalationError: If escalation validation fails.
    """
    is_valid, msg = validate_escalation(workflow, escalated_by, escalated_to, reason)
    if not is_valid:
        raise EscalationError(msg)

    escalation_step = EscalationStep(
        step_index=len(workflow.escalation_chain) + 1,
        escalated_by=escalated_by,
        escalated_to=escalated_to,
        reason=reason,
        escalated_from_state=workflow.state,
    )

    return transition_workflow(
        workflow,
        ApprovalState.ESCALATED,
        triggered_by=escalated_by,
        escalation=escalation_step,
        metadata={
            "escalation_step": len(workflow.escalation_chain) + 1,
            "escalated_to": escalated_to.value,
            "reason": reason,
        },
    )


def return_from_escalation(
    workflow: ApprovalWorkflow,
    returned_by: str,
) -> ApprovalWorkflow:
    """Return workflow from escalation to UNDER_REVIEW.

    Args:
        workflow: Escalated workflow.
        returned_by: Who initiated the return.

    Returns:
        Workflow in UNDER_REVIEW state.
    """
    if workflow.state != ApprovalState.ESCALATED:
        raise EscalationError(f"Cannot return from state: {workflow.state.value}")

    return transition_workflow(
        workflow,
        ApprovalState.UNDER_REVIEW,
        triggered_by=returned_by,
        metadata={"reason": "returned_from_escalation"},
    )


def _detect_escalation_cycle(
    workflow: ApprovalWorkflow,
    target_authority: AuthorityLevel,
) -> bool:
    """Detect if escalation would create a cycle.

    Analyzes the existing escalation chain to detect
    if the target authority has already been visited.
    """
    visited: Set[str] = set()
    for step in workflow.escalation_chain:
        auth = step.escalated_to.value
        if auth in visited:
            return True
        visited.add(auth)
    if target_authority.value in visited:
        return True
    return False


def get_available_escalation_targets(
    workflow: ApprovalWorkflow,
) -> List[Dict[str, Any]]:
    """Get valid escalation targets for a workflow.

    Informational only. Deterministic.
    """
    if workflow.state not in (ApprovalState.UNDER_REVIEW, ApprovalState.ESCALATED):
        return []

    if len(workflow.escalation_chain) >= MAX_ESCALATION_DEPTH:
        return []

    targets = []
    for auth in ESCALATION_AUTHORITY_ORDER:
        if _detect_escalation_cycle(workflow, auth):
            continue
        targets.append({
            "authority": auth.value,
            "depth": len(workflow.escalation_chain) + 1,
            "max_depth": MAX_ESCALATION_DEPTH,
        })

    return targets


def get_escalation_summary(workflow: ApprovalWorkflow) -> Dict[str, Any]:
    """Get deterministic summary of escalation state.

    Informational only. NO execution influence.
    """
    return {
        "workflow_id": workflow.workflow_id,
        "state": workflow.state.value,
        "current_depth": len(workflow.escalation_chain),
        "max_depth": min(MAX_ESCALATION_DEPTH, workflow.config.max_escalation_depth),
        "escalation_chain": [
            {
                "step": e.step_index,
                "escalated_by": e.escalated_by,
                "escalated_to": e.escalated_to.value,
                "reason": e.reason,
                "escalated_at": e.escalated_at,
            }
            for e in workflow.escalation_chain
        ],
        "available_targets": get_available_escalation_targets(workflow),
        "context_marker": SIMULATION_CONTEXT_MARKER,
    }
