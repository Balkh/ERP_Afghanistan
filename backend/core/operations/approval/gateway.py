"""
Phase 5B.2 — Human Approval Gateway Orchestrator.

Main entry point for human governance authorization.
Routes DecisionResult + SimulationPlan + SimulationOutcome
through structured approval workflows with multi-signature enforcement,
bounded escalation, and immutable audit trails.

ZERO EXECUTION AUTHORITY.
SIMULATION CONTEXT ONLY — NO REAL EXECUTION.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from core.operations.approval.models import (
    ApprovalState, ApprovalWorkflow, ApprovalSignature,
    ApprovalAuditEntry, EscalationStep,
    RiskLevel, AuthorityLevel,
    SIMULATION_CONTEXT_MARKER,
)
from core.operations.approval.workflow_engine import (
    WorkflowRegistry, create_workflow, transition_workflow,
    get_registry, check_timeout_expiry, get_approval_summary,
)
from core.operations.approval.multisig import (
    apply_signature, validate_signature, get_approval_progress,
    MultiSignatureError,
)
from core.operations.approval.escalation import (
    escalate, return_from_escalation, get_escalation_summary,
    EscalationError,
)
from core.operations.approval.audit import (
    get_audit_chain, get_workflow_audit_trail, verify_audit_integrity,
    create_audit_entry,
)
from core.operations.approval.notifications import (
    generate_reminders, generate_status_notification, get_notification_summary,
)

logger = logging.getLogger('erp.approval.gateway')

GATEWAY_VERSION = "1.0.0"


class HumanApprovalGateway:
    """Primary orchestrator for human approval workflows.

    Connects governance decisions → simulation outputs → human authorization.
    All operations are deterministic, audit-grade, and execution-free.

    This is the ONLY public interface for approval operations.
    """

    def __init__(self):
        self._workflow_registry: WorkflowRegistry = get_registry()
        self._version = GATEWAY_VERSION

    def route_decision(
        self,
        decision_result: Dict[str, Any],
        simulation_plan: Optional[Dict[str, Any]] = None,
        simulation_outcome: Optional[Dict[str, Any]] = None,
        simulation_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalWorkflow:
        """Route a governance DecisionResult through the approval gateway.

        Creates an immutable approval workflow for human authorization.
        Does NOT execute anything — governance artifact only.

        Args:
            decision_result: DecisionResult dict from governance pipeline.
            simulation_plan: Optional SimulationPlan dict from sandbox.
            simulation_outcome: Optional SimulationOutcome dict from sandbox.
            simulation_context: Optional simulation context metadata.
            metadata: Optional additional metadata.

        Returns:
            An immutable ApprovalWorkflow in PENDING state.

        Raises:
            ValueError: If the decision result is missing required fields.
        """
        decision = decision_result.get("decision", "BLOCKED")
        if decision != "REQUIRE_APPROVAL":
            logger.info(f"Decision {decision} does not require approval routing")

        action_id = decision_result.get("action_id", "")
        audit = decision_result.get("audit_entry", {})
        action_type = audit.get("action_type", "unknown")
        domain = audit.get("domain", "unknown")
        risk_level = audit.get("risk_level", "NONE")
        risk_score = audit.get("risk_score", 0)

        sim_plan = simulation_plan or {}
        sim_outcome = simulation_outcome or {}
        sim_ctx = simulation_context or {
            "source": "governance_pipeline",
            "marker": SIMULATION_CONTEXT_MARKER,
        }

        workflow = create_workflow(
            decision_id=action_id or decision_result.get("decision_id", ""),
            action_type=action_type,
            domain=domain,
            risk_level=risk_level,
            risk_score=risk_score,
            governance_decision=decision_result,
            simulation_plan=sim_plan,
            simulation_outcome=sim_outcome,
            simulation_context=sim_ctx,
            metadata={
                "gateway_version": self._version,
                **(metadata or {}),
            },
        )

        self._workflow_registry.register(workflow)

        generate_status_notification(workflow, "CREATED")

        logger.info(
            f"Created approval workflow {workflow.workflow_id} "
            f"for decision {action_id} ({action_type}, risk={risk_level})"
        )
        return workflow

    def submit_signature(
        self,
        workflow_id: str,
        approver_id: str,
        authority_level: AuthorityLevel,
        decision: str,
        justification: str = "",
    ) -> ApprovalWorkflow:
        """Submit an approval or rejection signature.

        Validates and applies the signature, transitioning state as needed.

        Args:
            workflow_id: Target workflow ID.
            approver_id: Unique approver identifier.
            authority_level: Approver's authority level.
            decision: APPROVED or REJECTED.
            justification: Optional justification.

        Returns:
            Updated workflow with signature applied.

        Raises:
            ValueError: If workflow not found.
            MultiSignatureError: If signature validation fails.
        """
        workflow = self._workflow_registry.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        updated = apply_signature(
            workflow, approver_id, authority_level, decision, justification,
        )

        if updated.state != workflow.state:
            notify_type = "APPROVED" if updated.state == ApprovalState.APPROVED else "REJECTED"
            generate_status_notification(updated, notify_type)

        return updated

    def escalate_workflow(
        self,
        workflow_id: str,
        escalated_by: str,
        escalated_to: AuthorityLevel,
        reason: str,
    ) -> ApprovalWorkflow:
        """Escalate a workflow to a higher authority.

        Args:
            workflow_id: Target workflow ID.
            escalated_by: Who is escalating.
            escalated_to: Target authority level.
            reason: Escalation reason.

        Returns:
            Updated workflow in ESCALATED state.

        Raises:
            ValueError: If workflow not found.
            EscalationError: If escalation validation fails.
        """
        workflow = self._workflow_registry.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        updated = escalate(workflow, escalated_by, escalated_to, reason)
        generate_status_notification(updated, "ESCALATED")
        return updated

    def return_from_escalation(
        self,
        workflow_id: str,
        returned_by: str,
    ) -> ApprovalWorkflow:
        """Return a workflow from escalation to UNDER_REVIEW.

        Args:
            workflow_id: Target workflow ID.
            returned_by: Who initiated the return.

        Returns:
            Updated workflow in UNDER_REVIEW state.
        """
        workflow = self._workflow_registry.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        updated = return_from_escalation(workflow, returned_by)
        generate_status_notification(updated, "STATUS_CHANGE")
        return updated

    def cancel_workflow(self, workflow_id: str, cancelled_by: str) -> ApprovalWorkflow:
        """Cancel a pending workflow.

        Args:
            workflow_id: Target workflow ID.
            cancelled_by: Who cancelled the workflow.

        Returns:
            Updated workflow in CANCELLED state.
        """
        workflow = self._workflow_registry.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        permitted = workflow.state in (ApprovalState.PENDING, ApprovalState.UNDER_REVIEW)
        if not permitted:
            raise ValueError(
                f"Cannot cancel workflow in state: {workflow.state.value}"
            )

        updated = transition_workflow(
            workflow,
            ApprovalState.CANCELLED,
            triggered_by=cancelled_by,
            metadata={"reason": "cancelled_by_user"},
        )
        generate_status_notification(updated, "CANCELLED")
        return updated

    def process_timeouts(self) -> List[ApprovalWorkflow]:
        """Process all workflows that have timed out.

        Transitions expired workflows to EXPIRED state.
        Deterministic — same state always produces same result.

        Returns:
            List of workflows that transitioned to EXPIRED.
        """
        expired: List[ApprovalWorkflow] = []
        for workflow in self._workflow_registry.list_active():
            did_expire, updated = check_timeout_expiry(workflow)
            if did_expire and updated is not None:
                expired.append(updated)
                generate_status_notification(updated, "EXPIRED")
                logger.info(f"Workflow {workflow.workflow_id} expired due to timeout")
        return expired

    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        """Get a workflow by ID.

        Returns None if not found.
        """
        return self._workflow_registry.get(workflow_id)

    def get_workflow_by_decision(self, decision_id: str) -> Optional[ApprovalWorkflow]:
        """Get workflow associated with a governance decision."""
        return self._workflow_registry.get_by_decision(decision_id)

    def list_active_workflows(self) -> List[ApprovalWorkflow]:
        """List all active (non-terminal) workflows."""
        return self._workflow_registry.list_active()

    def list_workflows_by_risk(self, risk_level: str) -> List[ApprovalWorkflow]:
        """List workflows filtered by risk level."""
        return self._workflow_registry.list_by_risk(risk_level)

    def get_workflow_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Get a comprehensive summary of a workflow.

        Informational only. NO execution influence.
        """
        workflow = self._workflow_registry.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        return {
            "approval": get_approval_summary(workflow),
            "multi_signature": get_approval_progress(workflow),
            "escalation": get_escalation_summary(workflow),
            "audit": get_workflow_audit_trail(workflow_id),
            "notifications": get_notification_summary(workflow_id),
            "context_marker": SIMULATION_CONTEXT_MARKER,
        }

    def get_gateway_status(self) -> Dict[str, Any]:
        """Get overall gateway status.

        Informational only. NO execution influence.
        """
        active = self._workflow_registry.list_active()
        by_state: Dict[str, int] = {}
        for w in active:
            s = w.state.value
            by_state[s] = by_state.get(s, 0) + 1

        return {
            "gateway_version": self._version,
            "total_workflows": self._workflow_registry.count(),
            "active_workflows": len(active),
            "active_by_state": by_state,
            "audit_integrity": verify_audit_integrity(),
            "context_marker": SIMULATION_CONTEXT_MARKER,
        }

    def get_workflow_audit(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get the full audit trail for a workflow."""
        return get_workflow_audit_trail(workflow_id)

    def get_audit_integrity(self) -> Dict[str, Any]:
        """Verify and return audit chain integrity status."""
        return verify_audit_integrity()

    def replay_rebuild(self, workflows: List[ApprovalWorkflow]) -> None:
        """Rebuild gateway state from replayed workflows.

        Used for deterministic replay reconstruction.
        """
        self._workflow_registry.replay_rebuild(workflows)
        logger.info(f"Gateway rebuilt from replay: {len(workflows)} workflows")

    def reset(self) -> None:
        """Reset gateway state. For testing only."""
        from core.operations.approval.workflow_engine import reset_registry as reset_wf
        from core.operations.approval.audit import reset_audit_chain
        from core.operations.approval.notifications import reset_registry as reset_notif
        reset_wf()
        reset_audit_chain()
        reset_notif()
        self._workflow_registry = get_registry()
        logger.info("Gateway state reset")


# Global gateway instance
_gateway: Optional[HumanApprovalGateway] = None


def get_gateway() -> HumanApprovalGateway:
    global _gateway
    if _gateway is None:
        _gateway = HumanApprovalGateway()
    return _gateway


def reset_gateway() -> None:
    global _gateway
    if _gateway is not None:
        _gateway.reset()
    _gateway = None
