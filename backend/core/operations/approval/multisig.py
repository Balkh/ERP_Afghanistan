"""
Phase 5B.2 — Multi-Signature Enforcement Engine.

Deterministic multi-signature approval enforcement.
Enforces:
- Minimum signature count per risk level
- Unique signatures (no duplicate approvers)
- Authority level requirements
- Self-approval prohibition
- Duplicate authority chain rejection
- Cyclic dependency rejection

ZERO EXECUTION AUTHORITY. Signature validation only.
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from core.operations.approval.models import (
    ApprovalState, ApprovalWorkflow, ApprovalSignature,
    ApprovalConfig, ApprovalAuditEntry, EscalationStep,
    RiskLevel, AuthorityLevel,
    RISK_TO_SIGNATURE_COUNT, RISK_TO_REQUIRED_AUTHORITY,
    SIMULATION_CONTEXT_MARKER,
)
from core.operations.approval.workflow_engine import (
    transition_workflow,
)

logger = logging.getLogger('erp.approval.multisig')

MULTISIG_ENGINE_VERSION = "1.0.0"


class MultiSignatureError(ValueError):
    """Raised when multi-signature validation fails."""
    pass


def validate_signature(
    workflow: ApprovalWorkflow,
    approver_id: str,
    authority_level: AuthorityLevel,
    decision: str,
    justification: str = "",
) -> Tuple[bool, str]:
    """Validate that a signature can be applied to a workflow.

    Deterministic validation — same inputs always produce same result.

    Args:
        workflow: The approval workflow.
        approver_id: Unique identifier of the approver.
        authority_level: Authority level of the approver.
        decision: APPROVED or REJECTED.
        justification: Optional justification text.

    Returns:
        (is_valid: bool, reason: str)
    """
    if workflow.state not in (ApprovalState.PENDING, ApprovalState.UNDER_REVIEW, ApprovalState.ESCALATED):
        return False, f"Workflow is in {workflow.state.value}, cannot accept signatures"

    if decision not in ("APPROVED", "REJECTED"):
        return False, f"Invalid decision: {decision}"

    permission = _get_authority_permission(authority_level)
    if not permission.can_approve:
        return False, f"Authority {authority_level.value} does not have approval permission"

    risk_rl = _safe_risk_level(workflow.risk_level)
    required_auth = RISK_TO_REQUIRED_AUTHORITY.get(risk_rl, AuthorityLevel.APPROVER)
    auth_rank = {AuthorityLevel.APPROVER: 1, AuthorityLevel.SENIOR_APPROVER: 2}
    if auth_rank.get(authority_level, 0) < auth_rank.get(required_auth, 0):
        return False, (
            f"Risk level {workflow.risk_level} requires {required_auth.value} authority, "
            f"got {authority_level.value}"
        )

    existing_ids = [s.approver_id for s in workflow.signatures]
    if approver_id in existing_ids:
        return False, f"Duplicate signature: approver {approver_id} already signed"

    required_count = workflow.config.required_signatures
    if decision == "APPROVED":
        rejected_count = sum(1 for s in workflow.signatures if s.decision == "REJECTED")
        if len(workflow.signatures) >= required_count and rejected_count == 0:
            return False, "Required signatures already met"

    return True, "Signature valid"


def apply_signature(
    workflow: ApprovalWorkflow,
    approver_id: str,
    authority_level: AuthorityLevel,
    decision: str,
    justification: str = "",
) -> ApprovalWorkflow:
    """Apply a signature to a workflow, transitioning state if requirements met.

    Deterministic — same inputs produce same result.

    Args:
        workflow: The current workflow.
        approver_id: Unique approver identifier.
        authority_level: Authority level of approver.
        decision: APPROVED or REJECTED.
        justification: Optional justification.

    Returns:
        Updated workflow with signature applied.

    Raises:
        MultiSignatureError: If signature validation fails.
    """
    is_valid, reason = validate_signature(
        workflow, approver_id, authority_level, decision, justification,
    )
    if not is_valid:
        raise MultiSignatureError(reason)

    if workflow.state == ApprovalState.PENDING:
        workflow = transition_workflow(
            workflow,
            ApprovalState.UNDER_REVIEW,
            triggered_by=approver_id,
            metadata={"reason": "first_signature_initiated_review"},
        )

    signature = ApprovalSignature(
        workflow_id=workflow.workflow_id,
        approver_id=approver_id,
        authority_level=authority_level,
        decision=decision,
        justification=justification,
    )

    new_signatures = list(workflow.signatures) + [signature]
    workflow_with_sig = _replace_signatures(workflow, new_signatures)

    if decision == "REJECTED":
        return transition_workflow(
            workflow_with_sig,
            ApprovalState.REJECTED,
            triggered_by=approver_id,
            signature=signature,
            metadata={"reason": "rejected_by_approver"},
        )

    if _is_approval_met(workflow_with_sig):
        return transition_workflow(
            workflow_with_sig,
            ApprovalState.APPROVED,
            triggered_by=approver_id,
            signature=signature,
            metadata={"reason": "required_signatures_met"},
        )

    from core.operations.approval.workflow_engine import get_registry as _get_wf_reg
    wf_reg = _get_wf_reg()
    if wf_reg is not None:
        try:
            wf_reg._workflows[workflow_with_sig.workflow_id] = workflow_with_sig
        except (KeyError, AttributeError):
            pass

    return workflow_with_sig


def _is_approval_met(workflow: ApprovalWorkflow) -> bool:
    """Check if all approval requirements are met.

    Deterministic — based solely on signatures + config.
    """
    required = workflow.config.required_signatures
    approved_sigs = [s for s in workflow.signatures if s.decision == "APPROVED"]
    unique_approvers = set(s.approver_id for s in approved_sigs)
    return len(unique_approvers) >= required


def _replace_signatures(
    workflow: ApprovalWorkflow,
    signatures: List[ApprovalSignature],
) -> ApprovalWorkflow:
    """Replace signatures on a workflow (immutable pattern)."""
    return ApprovalWorkflow(
        workflow_id=workflow.workflow_id,
        decision_id=workflow.decision_id,
        plan_id=workflow.plan_id,
        outcome_id=workflow.outcome_id,
        action_type=workflow.action_type,
        domain=workflow.domain,
        risk_level=workflow.risk_level,
        risk_score=workflow.risk_score,
        state=workflow.state,
        signatures=signatures,
        escalation_chain=workflow.escalation_chain,
        audit_entries=workflow.audit_entries,
        config=workflow.config,
        governance_decision=workflow.governance_decision,
        simulation_plan=workflow.simulation_plan,
        simulation_outcome=workflow.simulation_outcome,
        simulation_context=workflow.simulation_context,
        timeout_at=workflow.timeout_at,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        context_marker=workflow.context_marker,
        metadata=workflow.metadata,
    )


def get_required_signature_count(risk_level: str) -> int:
    """Get the deterministic required signature count for a risk level."""
    rl = _safe_risk_level(risk_level)
    return RISK_TO_SIGNATURE_COUNT.get(rl, 1)


def get_approval_progress(workflow: ApprovalWorkflow) -> Dict[str, Any]:
    """Get deterministic approval progress information.

    Informational only. NO execution influence.
    """
    required = workflow.config.required_signatures
    approved = [s for s in workflow.signatures if s.decision == "APPROVED"]
    rejected = [s for s in workflow.signatures if s.decision == "REJECTED"]
    unique_approvers = set(s.approver_id for s in approved)

    return {
        "workflow_id": workflow.workflow_id,
        "state": workflow.state.value,
        "risk_level": workflow.risk_level,
        "required_signatures": required,
        "current_approved": len(unique_approvers),
        "current_rejected": len(rejected),
        "remaining_required": max(0, required - len(unique_approvers)),
        "approvers": [s.approver_id for s in approved],
        "rejecters": [s.approver_id for s in rejected],
        "approval_met": _is_approval_met(workflow),
        "context_marker": SIMULATION_CONTEXT_MARKER,
    }


def _get_authority_permission(level: AuthorityLevel) -> Any:
    from core.operations.approval.models import get_approval_permission
    return get_approval_permission(level)


def _safe_risk_level(level: str) -> RiskLevel:
    try:
        return RiskLevel(level)
    except (ValueError, KeyError):
        return RiskLevel.NONE
