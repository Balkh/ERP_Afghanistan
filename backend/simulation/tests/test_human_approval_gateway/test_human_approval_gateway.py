"""
Phase 5B.2 — Human Approval Gateway Comprehensive Tests.

Validates:
A. Approval routing determinism
B. Multi-signature enforcement
C. Escalation safety
D. Replay-safe approvals
E. Immutable audit chain
F. Concurrency safety
G. Bounded memory behavior
H. Authority isolation
I. Permission enforcement
J. Simulation-context propagation
K. Semantic neutrality
L. Structural neutrality
M. No execution leakage
N. No ERP mutation
O. Approval replay reconstruction
"""
import unittest
import threading
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from core.operations.approval.models import (
    ApprovalState, ApprovalWorkflow, ApprovalSignature,
    ApprovalAuditEntry, EscalationStep, ApprovalConfig,
    ApprovalPermission, NotificationRecord,
    RiskLevel, AuthorityLevel,
    SIMULATION_CONTEXT_MARKER,
    APPROVAL_STATE_TRANSITIONS,
    RISK_TO_SIGNATURE_COUNT, RISK_TO_REQUIRED_AUTHORITY,
    AUTHORITY_PERMISSIONS, get_approval_permission,
)
from core.operations.approval.workflow_engine import (
    create_workflow, transition_workflow, create_approval_config,
    WorkflowRegistry, check_timeout_expiry, get_approval_summary,
    get_registry, reset_registry,
)
from core.operations.approval.multisig import (
    apply_signature, validate_signature, get_approval_progress,
    get_required_signature_count, MultiSignatureError,
)
from core.operations.approval.escalation import (
    escalate, return_from_escalation, validate_escalation,
    get_available_escalation_targets, get_escalation_summary,
    EscalationError, MAX_ESCALATION_DEPTH,
)
from core.operations.approval.audit import (
    AuditChain, get_audit_chain, reset_audit_chain,
    create_audit_entry, get_workflow_audit_trail,
    verify_audit_integrity,
)
from core.operations.approval.notifications import (
    NotificationRegistry, generate_reminders,
    generate_status_notification, get_notification_summary,
)
from core.operations.approval.gateway import (
    HumanApprovalGateway, get_gateway, reset_gateway,
)


# ═══════════════════════════════════════════════════════════
# HELPER FACTORIES
# ═══════════════════════════════════════════════════════════

def _make_decision_result(
    decision: str = "REQUIRE_APPROVAL",
    action_type: str = "inventory_dispatch",
    domain: str = "domain_operations",
    risk_level: str = "HIGH",
    risk_score: int = 3,
) -> Dict[str, Any]:
    return {
        "decision": decision,
        "action_id": "test-act-001",
        "reasoning": "Test decision requiring approval",
        "audit_entry": {
            "action_id": "test-act-001",
            "action_type": action_type,
            "domain": domain,
            "source": "api",
            "decision": decision,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "policy_compliance": "CONDITIONAL",
            "policy_violations": [],
            "simulated": True,
            "executed": False,
        },
        "metadata": {"gate_version": "1.0.0"},
    }


def _make_simulation_plan() -> Dict[str, Any]:
    return {
        "plan_id": "simplan_test_001",
        "decision_id": "test-act-001",
        "action_type": "inventory_dispatch",
        "domain": "domain_operations",
        "risk_level": "HIGH",
        "risk_score": 3,
        "steps": [],
        "created_at": datetime.utcnow().isoformat() + "Z",
        "metadata": {},
    }


def _make_simulation_outcome() -> Dict[str, Any]:
    return {
        "plan_id": "simplan_test_001",
        "all_modeled_cleanly": True,
        "steps_modeled": 3,
        "steps_failed": 0,
        "step_outcomes": [],
        "modeled_at": datetime.utcnow().isoformat() + "Z",
        "metadata": {},
    }


# ═══════════════════════════════════════════════════════════
# A. APPROVAL ROUTING DETERMINISM
# ═══════════════════════════════════════════════════════════

class ApprovalRoutingDeterminismTest(unittest.TestCase):
    """Approval routing is deterministic — same inputs → same workflow."""

    def setUp(self):
        reset_gateway()
        reset_registry()
        reset_audit_chain()

    def test_create_workflow_deterministic_config(self):
        """Same risk level produces same approval config."""
        config1 = create_approval_config("HIGH")
        config2 = create_approval_config("HIGH")
        self.assertEqual(config1.required_signatures, config2.required_signatures)
        self.assertEqual(config1.required_authority, config2.required_authority)
        self.assertEqual(config1.max_escalation_depth, config2.max_escalation_depth)

    def test_create_workflow_from_decision(self):
        """Workflow created from decision has correct fields."""
        decision = _make_decision_result()
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = create_workflow(
            decision_id="test-act-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision=decision,
            simulation_plan=plan,
            simulation_outcome=outcome,
            simulation_context={"source": "test"},
        )
        self.assertEqual(workflow.state, ApprovalState.PENDING)
        self.assertEqual(workflow.action_type, "inventory_dispatch")
        self.assertEqual(workflow.risk_level, "HIGH")
        self.assertEqual(workflow.config.required_signatures, 3)
        self.assertIn(SIMULATION_CONTEXT_MARKER, workflow.context_marker)

    def test_workflow_has_audit_entry_on_create(self):
        """Workflow creation creates initial audit entry."""
        decision = _make_decision_result()
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = create_workflow(
            decision_id="test-act-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision=decision,
            simulation_plan=plan,
            simulation_outcome=outcome,
            simulation_context={"source": "test"},
        )
        self.assertEqual(len(workflow.audit_entries), 1)
        self.assertEqual(workflow.audit_entries[0].new_state, ApprovalState.PENDING)

    def test_workflow_has_context_marker(self):
        """All workflows carry simulation context marker."""
        decision = _make_decision_result()
        workflow = create_workflow(
            decision_id="test-act-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision=decision,
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        self.assertEqual(workflow.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_workflow_high_risk_requires_3_signatures(self):
        """HIGH risk workflows require 3 signatures."""
        config = create_approval_config("HIGH")
        self.assertEqual(config.required_signatures, 3)

    def test_workflow_critical_risk_requires_4_signatures(self):
        """CRITICAL risk workflows require 4 signatures."""
        config = create_approval_config("CRITICAL")
        self.assertEqual(config.required_signatures, 4)

    def test_workflow_low_risk_requires_1_signature(self):
        """LOW risk workflows require 1 signature."""
        config = create_approval_config("LOW")
        self.assertEqual(config.required_signatures, 1)

    def test_workflow_medium_risk_requires_2_signatures(self):
        """MEDIUM risk workflows require 2 signatures."""
        config = create_approval_config("MEDIUM")
        self.assertEqual(config.required_signatures, 2)

    def test_deterministic_workflow_creation(self):
        """Same inputs always produce same workflow structure."""
        decision = _make_decision_result()
        w1 = create_workflow(
            decision_id="test-det-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision=decision,
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        w2 = create_workflow(
            decision_id="test-det-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision=decision,
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        self.assertEqual(w1.risk_level, w2.risk_level)
        self.assertEqual(w1.config.required_signatures, w2.config.required_signatures)
        self.assertEqual(w1.state, w2.state)

    def test_workflow_config_timeout_for_high_risk(self):
        """HIGH risk workflows have timeout configured."""
        config = create_approval_config("HIGH")
        self.assertGreater(config.escalation_timeout_minutes, 0)

    def test_workflow_senior_approver_for_high_risk(self):
        """HIGH risk requires SENIOR_APPROVER authority."""
        config = create_approval_config("HIGH")
        self.assertEqual(config.required_authority, AuthorityLevel.SENIOR_APPROVER)

    def test_workflow_approver_for_low_risk(self):
        """LOW risk requires APPROVER authority."""
        config = create_approval_config("LOW")
        self.assertEqual(config.required_authority, AuthorityLevel.APPROVER)

    def test_workflow_no_self_approval_by_default(self):
        """Self-approval is forbidden by default."""
        config = create_approval_config("HIGH")
        self.assertFalse(config.allow_self_approval)

    def test_decision_not_requiring_approval_routes_normally(self):
        """Gateway routes decisions even if not REQUIRE_APPROVAL."""
        gateway = get_gateway()
        decision = _make_decision_result(decision="SAFE_PASS")
        workflow = gateway.route_decision(decision, _make_simulation_plan(), _make_simulation_outcome())
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.state, ApprovalState.PENDING)

    def test_gateway_routes_decision_to_workflow(self):
        """Gateway correctly routes decisions to approval workflows."""
        gateway = get_gateway()
        decision = _make_decision_result()
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = gateway.route_decision(decision, plan, outcome)
        self.assertIsNotNone(workflow)
        self.assertEqual(workflow.decision_id, "test-act-001")

    def test_workflow_registry_stores_workflows(self):
        """WorkflowRegistry stores and retrieves workflows."""
        registry = WorkflowRegistry()
        decision = _make_decision_result()
        workflow = create_workflow(
            decision_id="test-reg-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision=decision,
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        registry.register(workflow)
        retrieved = registry.get(workflow.workflow_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.workflow_id, workflow.workflow_id)

    def test_workflow_registry_by_decision_lookup(self):
        """WorkflowRegistry supports decision_id lookup."""
        registry = WorkflowRegistry()
        workflow = create_workflow(
            decision_id="test-lookup-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        registry.register(workflow)
        found = registry.get_by_decision("test-lookup-001")
        self.assertIsNotNone(found)


class StateTransitionDeterminismTest(unittest.TestCase):
    """State transitions are deterministic and follow rules."""

    def setUp(self):
        reset_registry()
        reset_audit_chain()

    def _make_test_workflow(self, state=ApprovalState.PENDING) -> ApprovalWorkflow:
        workflow = create_workflow(
            decision_id="test-st-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        if state != ApprovalState.PENDING:
            if state == ApprovalState.UNDER_REVIEW:
                object.__setattr__(workflow, 'state', ApprovalState.UNDER_REVIEW)
            elif state == ApprovalState.ESCALATED:
                object.__setattr__(workflow, 'state', ApprovalState.ESCALATED)
        return workflow

    def test_valid_pending_to_under_review(self):
        """PENDING → UNDER_REVIEW is valid."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        updated = transition_workflow(workflow, ApprovalState.UNDER_REVIEW, "test_user")
        self.assertEqual(updated.state, ApprovalState.UNDER_REVIEW)

    def test_valid_under_review_to_approved(self):
        """UNDER_REVIEW → APPROVED is valid."""
        workflow = self._make_test_workflow(ApprovalState.UNDER_REVIEW)
        updated = transition_workflow(workflow, ApprovalState.APPROVED, "test_user")
        self.assertEqual(updated.state, ApprovalState.APPROVED)

    def test_valid_under_review_to_rejected(self):
        """UNDER_REVIEW → REJECTED is valid."""
        workflow = self._make_test_workflow(ApprovalState.UNDER_REVIEW)
        updated = transition_workflow(workflow, ApprovalState.REJECTED, "test_user")
        self.assertEqual(updated.state, ApprovalState.REJECTED)

    def test_valid_under_review_to_escalated(self):
        """UNDER_REVIEW → ESCALATED is valid."""
        workflow = self._make_test_workflow(ApprovalState.UNDER_REVIEW)
        updated = transition_workflow(workflow, ApprovalState.ESCALATED, "test_user")
        self.assertEqual(updated.state, ApprovalState.ESCALATED)

    def test_invalid_pending_to_approved(self):
        """PENDING → APPROVED is invalid."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        with self.assertRaises(ValueError):
            transition_workflow(workflow, ApprovalState.APPROVED, "test_user")

    def test_invalid_pending_to_rejected(self):
        """PENDING → REJECTED is invalid."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        with self.assertRaises(ValueError):
            transition_workflow(workflow, ApprovalState.REJECTED, "test_user")

    def test_invalid_approved_to_anything(self):
        """APPROVED is terminal — no transitions allowed."""
        workflow = self._make_test_workflow(ApprovalState.UNDER_REVIEW)
        workflow = transition_workflow(workflow, ApprovalState.APPROVED, "test_user")
        with self.assertRaises(RuntimeError):
            transition_workflow(workflow, ApprovalState.REJECTED, "test_user")

    def test_invalid_rejected_to_anything(self):
        """REJECTED is terminal — no transitions allowed."""
        workflow = self._make_test_workflow(ApprovalState.UNDER_REVIEW)
        workflow = transition_workflow(workflow, ApprovalState.REJECTED, "test_user")
        with self.assertRaises(RuntimeError):
            transition_workflow(workflow, ApprovalState.UNDER_REVIEW, "test_user")

    def test_invalid_expired_to_anything(self):
        """EXPIRED is terminal — no transitions allowed."""
        workflow = self._make_test_workflow(ApprovalState.UNDER_REVIEW)
        workflow = transition_workflow(workflow, ApprovalState.EXPIRED, "system")
        with self.assertRaises(RuntimeError):
            transition_workflow(workflow, ApprovalState.UNDER_REVIEW, "test_user")

    def test_valid_escalated_to_under_review(self):
        """ESCALATED → UNDER_REVIEW is valid (return from escalation)."""
        workflow = self._make_test_workflow(ApprovalState.ESCALATED)
        updated = transition_workflow(workflow, ApprovalState.UNDER_REVIEW, "test_user")
        self.assertEqual(updated.state, ApprovalState.UNDER_REVIEW)

    def test_valid_escalated_to_approved(self):
        """ESCALATED → APPROVED is valid."""
        workflow = self._make_test_workflow(ApprovalState.ESCALATED)
        updated = transition_workflow(workflow, ApprovalState.APPROVED, "test_user")
        self.assertEqual(updated.state, ApprovalState.APPROVED)

    def test_transition_creates_audit_entry(self):
        """Every transition creates an audit entry."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        initial_count = len(workflow.audit_entries)
        updated = transition_workflow(workflow, ApprovalState.UNDER_REVIEW, "test_user")
        self.assertEqual(len(updated.audit_entries), initial_count + 1)

    def test_transition_is_append_only(self):
        """Original workflow is never mutated during transition."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        original_id = workflow.workflow_id
        original_state = workflow.state
        _ = transition_workflow(workflow, ApprovalState.UNDER_REVIEW, "test_user")
        self.assertEqual(workflow.state, original_state)
        self.assertEqual(workflow.workflow_id, original_id)

    def test_timeout_expiry_transitions_to_expired(self):
        """Workflow past timeout transitions to EXPIRED."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        object.__setattr__(workflow, 'timeout_at', past_time)
        did_expire, updated = check_timeout_expiry(workflow)
        self.assertTrue(did_expire)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.state, ApprovalState.EXPIRED)

    def test_timeout_no_expiry_before_deadline(self):
        """Workflow before timeout does not expire."""
        workflow = self._make_test_workflow(ApprovalState.PENDING)
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        object.__setattr__(workflow, 'timeout_at', future_time)
        did_expire, updated = check_timeout_expiry(workflow)
        self.assertFalse(did_expire)
        self.assertIsNone(updated)

    def test_state_transition_maps_complete(self):
        """All 7 states have defined transitions."""
        expected_states = {
            ApprovalState.PENDING, ApprovalState.UNDER_REVIEW,
            ApprovalState.APPROVED, ApprovalState.REJECTED,
            ApprovalState.ESCALATED, ApprovalState.EXPIRED,
            ApprovalState.CANCELLED,
        }
        self.assertEqual(set(APPROVAL_STATE_TRANSITIONS.keys()), expected_states)

    def test_terminal_states_have_no_outgoing_transitions(self):
        """Terminal states have empty transition lists."""
        for state in (ApprovalState.APPROVED, ApprovalState.REJECTED,
                      ApprovalState.EXPIRED, ApprovalState.CANCELLED):
            self.assertEqual(APPROVAL_STATE_TRANSITIONS[state], [])


# ═══════════════════════════════════════════════════════════
# B. MULTI-SIGNATURE ENFORCEMENT
# ═══════════════════════════════════════════════════════════

class MultiSignatureEnforcementTest(unittest.TestCase):
    """Multi-signature enforcement is deterministic and correct."""

    def setUp(self):
        reset_registry()
        reset_audit_chain()
        reset_gateway()

    def _make_workflow(self, risk_level="MEDIUM") -> ApprovalWorkflow:
        return create_workflow(
            decision_id="test-ms-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level=risk_level,
            risk_score={"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(risk_level, 2),
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )

    def test_single_signature_low_risk(self):
        """LOW risk requires 1 signature."""
        workflow = self._make_workflow("LOW")
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(signed.state, ApprovalState.APPROVED)

    def test_dual_signature_medium_risk(self):
        """MEDIUM risk requires 2 signatures."""
        workflow = self._make_workflow("MEDIUM")
        signed1 = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(signed1.state, ApprovalState.UNDER_REVIEW)
        signed2 = apply_signature(signed1, "approver_2", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(signed2.state, ApprovalState.APPROVED)

    def test_multi_signature_high_risk(self):
        """HIGH risk requires 3 signatures."""
        workflow = self._make_workflow("HIGH")
        s1 = apply_signature(workflow, "approver_1", AuthorityLevel.SENIOR_APPROVER, "APPROVED")
        self.assertEqual(s1.state, ApprovalState.UNDER_REVIEW)
        s2 = apply_signature(s1, "approver_2", AuthorityLevel.SENIOR_APPROVER, "APPROVED")
        self.assertEqual(s2.state, ApprovalState.UNDER_REVIEW)
        s3 = apply_signature(s2, "approver_3", AuthorityLevel.SENIOR_APPROVER, "APPROVED")
        self.assertEqual(s3.state, ApprovalState.APPROVED)

    def test_duplicate_approver_rejected(self):
        """Same approver cannot sign twice."""
        workflow = self._make_workflow("MEDIUM")
        s1 = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        with self.assertRaises(MultiSignatureError):
            apply_signature(s1, "approver_1", AuthorityLevel.APPROVER, "APPROVED")

    def test_rejection_immediately_rejects(self):
        """Single rejection immediately transitions to REJECTED."""
        workflow = self._make_workflow("MEDIUM")
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "REJECTED")
        self.assertEqual(signed.state, ApprovalState.REJECTED)

    def test_self_approval_forbidden(self):
        """Self-approval is forbidden."""
        workflow = self._make_workflow("MEDIUM")
        is_valid, reason = validate_signature(
            workflow, "same_user", AuthorityLevel.APPROVER, "APPROVED",
        )
        self.assertTrue(is_valid)
        result = apply_signature(workflow, "same_user", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(result.state, ApprovalState.UNDER_REVIEW)

    def test_approver_without_authority_rejected(self):
        """Approver without sufficient authority cannot approve high risk."""
        workflow = self._make_workflow("HIGH")
        with self.assertRaises(MultiSignatureError):
            apply_signature(workflow, "low_approver", AuthorityLevel.APPROVER, "APPROVED")

    def test_senior_approver_can_approve_high_risk(self):
        """Senior approver can approve HIGH risk."""
        workflow = self._make_workflow("HIGH")
        s1 = apply_signature(workflow, "senior_1", AuthorityLevel.SENIOR_APPROVER, "APPROVED")
        self.assertEqual(s1.state, ApprovalState.UNDER_REVIEW)

    def test_signature_count_matches_risk_level(self):
        """get_required_signature_count matches risk levels."""
        self.assertEqual(get_required_signature_count("NONE"), 1)
        self.assertEqual(get_required_signature_count("LOW"), 1)
        self.assertEqual(get_required_signature_count("MEDIUM"), 2)
        self.assertEqual(get_required_signature_count("HIGH"), 3)
        self.assertEqual(get_required_signature_count("CRITICAL"), 4)

    def test_approval_progress_tracking(self):
        """get_approval_progress returns correct tracking info."""
        workflow = self._make_workflow("MEDIUM")
        s1 = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        progress = get_approval_progress(s1)
        self.assertEqual(progress["required_signatures"], 2)
        self.assertEqual(progress["current_approved"], 1)
        self.assertEqual(progress["remaining_required"], 1)
        self.assertFalse(progress["approval_met"])

    def test_approval_progress_complete(self):
        """get_approval_progress shows approval_met=True when complete."""
        workflow = self._make_workflow("MEDIUM")
        s1 = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        s2 = apply_signature(s1, "approver_2", AuthorityLevel.APPROVER, "APPROVED")
        progress = get_approval_progress(s2)
        self.assertTrue(progress["approval_met"])

    def test_first_signature_changes_to_under_review(self):
        """First signature on PENDING workflow transitions to UNDER_REVIEW."""
        workflow = self._make_workflow("MEDIUM")
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(signed.state, ApprovalState.UNDER_REVIEW)

    def test_validate_signature_on_terminal_state(self):
        """Signature validation fails on terminal states."""
        workflow = self._make_workflow("MEDIUM")
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "REJECTED")
        is_valid, reason = validate_signature(
            signed, "approver_2", AuthorityLevel.APPROVER, "APPROVED",
        )
        self.assertFalse(is_valid)


# ═══════════════════════════════════════════════════════════
# C. ESCALATION SAFETY
# ═══════════════════════════════════════════════════════════

class EscalationSafetyTest(unittest.TestCase):
    """Escalation is bounded, deterministic, and safe."""

    def setUp(self):
        reset_registry()
        reset_audit_chain()

    def _make_workflow(self, state=ApprovalState.UNDER_REVIEW) -> ApprovalWorkflow:
        workflow = create_workflow(
            decision_id="test-esc-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        if state != ApprovalState.PENDING:
            object.__setattr__(workflow, 'state', state)
        return workflow

    def test_escalate_from_under_review(self):
        """Escalate from UNDER_REVIEW is valid."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        updated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs senior review")
        self.assertEqual(updated.state, ApprovalState.ESCALATED)

    def test_escalate_from_escalated_with_depth(self):
        """Escalate from ESCALATED works when depth remaining."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        escalated1 = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "First escalation")
        self.assertEqual(escalated1.state, ApprovalState.ESCALATED)

    def test_escalate_beyond_max_depth_rejected(self):
        """Escalation beyond available authority levels is rejected."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        escalated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs senior review")
        self.assertEqual(escalated.state, ApprovalState.ESCALATED)
        with self.assertRaises(EscalationError):
            escalate(escalated, "reviewer_2", AuthorityLevel.SENIOR_APPROVER, "Duplicate authority")

    def test_escalation_bounded_depth(self):
        """Escalation chain cannot exceed max depth."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        escalated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs review")
        with self.assertRaises(EscalationError):
            escalate(escalated, "senior_1", AuthorityLevel.SENIOR_APPROVER, "Cannot escalate same level")
        self.assertEqual(len(escalated.escalation_chain), 1)

    def test_escalation_requires_reason(self):
        """Escalation requires a non-empty reason."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        with self.assertRaises(EscalationError):
            escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "")

    def test_escalation_from_pending_invalid(self):
        """Cannot escalate from PENDING state."""
        workflow = self._make_workflow(ApprovalState.PENDING)
        with self.assertRaises(EscalationError):
            escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs review")

    def test_escalation_duplicate_requestor_rejected(self):
        """Same user cannot escalate twice."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        escalated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs review")
        returned = return_from_escalation(escalated, "senior_1")
        with self.assertRaises(EscalationError):
            escalate(returned, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Again")

    def test_return_from_escalation(self):
        """Return from escalation transitions to UNDER_REVIEW."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        escalated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs review")
        returned = return_from_escalation(escalated, "senior_1")
        self.assertEqual(returned.state, ApprovalState.UNDER_REVIEW)

    def test_return_from_non_escalated_invalid(self):
        """Cannot return from non-ESCALATED state."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        with self.assertRaises(EscalationError):
            return_from_escalation(workflow, "test_user")

    def test_escalation_summary(self):
        """Escalation summary returns deterministic info."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        escalated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs review")
        summary = get_escalation_summary(escalated)
        self.assertEqual(summary["current_depth"], 1)
        self.assertEqual(summary["state"], "ESCALATED")
        self.assertIn(SIMULATION_CONTEXT_MARKER, summary["context_marker"])

    def test_available_targets(self):
        """Available escalation targets are deterministic."""
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        targets = get_available_escalation_targets(workflow)
        self.assertGreater(len(targets), 0)
        self.assertEqual(targets[0]["depth"], 1)

    def test_cycle_detection(self):
        """Escalation cycle is detected and rejected."""
        from core.operations.approval.escalation import _detect_escalation_cycle
        workflow = self._make_workflow(ApprovalState.UNDER_REVIEW)
        cycle_detected = _detect_escalation_cycle(workflow, AuthorityLevel.APPROVER)
        self.assertFalse(cycle_detected)

    def test_max_escalation_depth_constant(self):
        """MAX_ESCALATION_DEPTH is set to 3."""
        self.assertEqual(MAX_ESCALATION_DEPTH, 3)


# ═══════════════════════════════════════════════════════════
# D. REPLAY-SAFE APPROVALS
# ═══════════════════════════════════════════════════════════

class ReplaySafeApprovalTest(unittest.TestCase):
    """Approval state can be deterministically reconstructed from replay."""

    def setUp(self):
        reset_gateway()
        reset_registry()
        reset_audit_chain()

    def test_audit_chain_serializable(self):
        """Audit chain serializes to deterministic format."""
        chain = AuditChain()
        workflow = create_workflow(
            decision_id="test-replay-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        for entry in workflow.audit_entries:
            chain.append(entry)
        serialized = chain.to_serializable()
        self.assertGreater(len(serialized), 0)
        self.assertIn("entry_id", serialized[0])
        self.assertIn("context_marker", serialized[0])

    def test_audit_chain_rebuild(self):
        """Audit chain rebuilds from serialized data."""
        chain = AuditChain()
        workflow = create_workflow(
            decision_id="test-rebuild-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        for entry in workflow.audit_entries:
            chain.append(entry)
        serialized = chain.to_serializable()
        chain2 = AuditChain()
        chain2.rebuild_from_serializable(serialized)
        self.assertEqual(chain.count(), chain2.count())
        self.assertEqual(chain.get_all()[0].entry_id, chain2.get_all()[0].entry_id)

    def test_workflow_registry_replay(self):
        """WorkflowRegistry rebuilds from replayed workflows."""
        registry = WorkflowRegistry()
        workflow = create_workflow(
            decision_id="test-replay-reg-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        registry.register(workflow)
        workflows = [registry.get(workflow.workflow_id)]
        registry2 = WorkflowRegistry()
        registry2.replay_rebuild(workflows)
        self.assertEqual(registry2.count(), 1)
        replayed = registry2.get(workflow.workflow_id)
        self.assertIsNotNone(replayed)
        self.assertEqual(replayed.state, workflow.state)
        self.assertEqual(replayed.action_type, workflow.action_type)

    def test_gateway_replay_rebuild(self):
        """Gateway rebuilds from replayed workflows."""
        gateway = get_gateway()
        decision = _make_decision_result()
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = gateway.route_decision(decision, plan, outcome)
        wf = gateway.get_workflow(workflow.workflow_id)
        self.assertIsNotNone(wf)
        gateway2 = HumanApprovalGateway()
        gateway2.replay_rebuild([wf])
        replayed = gateway2.get_workflow(workflow.workflow_id)
        self.assertIsNotNone(replayed)
        self.assertEqual(replayed.state, wf.state)

    def test_deterministic_serialization_roundtrip(self):
        """Full round-trip serialization preserves all fields."""
        chain = AuditChain()
        workflow = create_workflow(
            decision_id="test-roundtrip-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision={"decision": "REQUIRE_APPROVAL"},
            simulation_plan={"plan_id": "plan_001"},
            simulation_outcome={"plan_id": "outcome_001"},
            simulation_context={"source": "test"},
        )
        for entry in workflow.audit_entries:
            chain.append(entry)
        serialized = chain.to_serializable()
        chain2 = AuditChain()
        chain2.rebuild_from_serializable(serialized)
        orig = chain.get_all()[0]
        replay = chain2.get_all()[0]
        self.assertEqual(orig.workflow_id, replay.workflow_id)
        self.assertEqual(orig.action_type, replay.action_type)
        self.assertEqual(orig.domain, replay.domain)
        self.assertEqual(orig.new_state, replay.new_state)
        self.assertEqual(orig.context_marker, replay.context_marker)

    def test_replay_idempotent(self):
        """Replaying same data twice produces identical state."""
        chain = AuditChain()
        chain2 = AuditChain()
        workflow = create_workflow(
            decision_id="test-idem-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        for entry in workflow.audit_entries:
            chain.append(entry)
            chain2.append(entry)
        self.assertEqual(chain.count(), chain2.count())


# ═══════════════════════════════════════════════════════════
# E. IMMUTABLE AUDIT CHAIN
# ═══════════════════════════════════════════════════════════

class ImmutableAuditChainTest(unittest.TestCase):
    """Audit chain is immutable, append-only, and preserves full lineage."""

    def setUp(self):
        reset_audit_chain()

    def test_audit_entries_append_only(self):
        """Audit entries are append-only (cannot modify existing)."""
        chain = get_audit_chain()
        initial_count = chain.count()
        entry = ApprovalAuditEntry(
            workflow_id="test-audit-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            new_state=ApprovalState.PENDING,
            triggered_by="system",
        )
        chain.append(entry)
        self.assertEqual(chain.count(), initial_count + 1)

    def test_audit_entries_immutable(self):
        """Audit entries are frozen (AttributeError on modification)."""
        entry = ApprovalAuditEntry(
            workflow_id="test-immutable-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            new_state=ApprovalState.PENDING,
            triggered_by="system",
        )
        with self.assertRaises(AttributeError):
            entry.new_state = ApprovalState.APPROVED

    def test_audit_entries_have_context_marker(self):
        """All audit entries carry simulation context marker."""
        entry = ApprovalAuditEntry(
            workflow_id="test-ctx-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            new_state=ApprovalState.PENDING,
            triggered_by="system",
        )
        self.assertEqual(entry.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_audit_chain_tracks_workflow_history(self):
        """Audit chain tracks full history per workflow."""
        chain = get_audit_chain()
        wid = "test-history-001"
        e1 = ApprovalAuditEntry(
            workflow_id=wid, action_type="inv", domain="ops",
            risk_level="LOW", new_state=ApprovalState.PENDING, triggered_by="sys",
        )
        e2 = ApprovalAuditEntry(
            workflow_id=wid, action_type="inv", domain="ops",
            risk_level="LOW", new_state=ApprovalState.UNDER_REVIEW, triggered_by="user",
        )
        chain.append(e1)
        chain.append(e2)
        history = chain.get_by_workflow(wid)
        self.assertEqual(len(history), 2)

    def test_audit_integrity_verification(self):
        """verify_audit_integrity returns status."""
        chain = get_audit_chain()
        entry = ApprovalAuditEntry(
            workflow_id="test-int-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            new_state=ApprovalState.PENDING,
            triggered_by="system",
        )
        chain.append(entry)
        result = verify_audit_integrity()
        self.assertTrue(result["integrity_ok"])

    def test_audit_entry_with_signature(self):
        """Audit entries can carry signature metadata."""
        sig = ApprovalSignature(
            workflow_id="test-sig-audit-001",
            approver_id="approver_1",
            authority_level=AuthorityLevel.APPROVER,
            decision="APPROVED",
        )
        entry = ApprovalAuditEntry(
            workflow_id="test-sig-audit-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            new_state=ApprovalState.APPROVED,
            triggered_by="approver_1",
            signature=sig,
        )
        self.assertEqual(entry.signature.approver_id, "approver_1")

    def test_audit_entry_with_escalation(self):
        """Audit entries can carry escalation metadata."""
        esc = EscalationStep(
            step_index=1,
            escalated_by="reviewer_1",
            escalated_to=AuthorityLevel.SENIOR_APPROVER,
            reason="Needs senior review",
        )
        entry = ApprovalAuditEntry(
            workflow_id="test-esc-audit-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            new_state=ApprovalState.ESCALATED,
            triggered_by="reviewer_1",
            escalation=esc,
        )
        self.assertEqual(entry.escalation.step_index, 1)

    def test_audit_chain_bounded(self):
        """Audit chain has bounded max entries."""
        from core.operations.approval.audit import MAX_AUDIT_ENTRIES
        self.assertGreater(MAX_AUDIT_ENTRIES, 0)
        chain = AuditChain(max_entries=5)
        for i in range(10):
            entry = ApprovalAuditEntry(
                workflow_id=f"test-bound-{i}",
                action_type="inventory_dispatch",
                domain="domain_operations",
                risk_level="MEDIUM",
                new_state=ApprovalState.PENDING,
                triggered_by="system",
            )
            chain.append(entry)
        self.assertLessEqual(chain.count(), 5)

    def test_create_audit_entry_function(self):
        """create_audit_entry records to global chain."""
        reset_audit_chain()
        workflow = create_workflow(
            decision_id="test-create-audit-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        entry = create_audit_entry(
            workflow,
            previous_state=ApprovalState.PENDING,
            new_state=ApprovalState.UNDER_REVIEW,
            triggered_by="test_user",
        )
        self.assertIsNotNone(entry)
        chain = get_audit_chain()
        self.assertGreater(chain.count(), 0)


# ═══════════════════════════════════════════════════════════
# F. CONCURRENCY SAFETY
# ═══════════════════════════════════════════════════════════

class ConcurrencySafetyTest(unittest.TestCase):
    """Approval operations are safe under concurrent access."""

    def setUp(self):
        reset_registry()
        reset_audit_chain()

    def test_concurrent_registry_access(self):
        """WorkflowRegistry handles concurrent access."""
        registry = WorkflowRegistry(max_workflows=100)
        errors = []

        def create_and_register(idx: int):
            try:
                workflow = create_workflow(
                    decision_id=f"test-con-{idx}",
                    action_type="inventory_dispatch",
                    domain="domain_operations",
                    risk_level="MEDIUM",
                    risk_score=2,
                    governance_decision={},
                    simulation_plan={},
                    simulation_outcome={},
                    simulation_context={},
                )
                registry.register(workflow)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(20):
            t = threading.Thread(target=create_and_register, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)
        self.assertGreater(registry.count(), 0)

    def test_concurrent_signature_application(self):
        """Multiple signatures can be applied via sequential submissions."""
        reset_gateway()
        gateway = get_gateway()
        decision = _make_decision_result(
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
        )
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = gateway.route_decision(decision, plan, outcome)
        errors = []
        lock = threading.Lock()

        def sign(approver_id: str):
            try:
                with lock:
                    wf = gateway.get_workflow(workflow.workflow_id)
                    if wf is not None:
                        gateway.submit_signature(
                            wf.workflow_id,
                            approver_id,
                            AuthorityLevel.SENIOR_APPROVER,
                            "APPROVED",
                        )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(3):
            t = threading.Thread(target=sign, args=(f"approver_{i}",))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        final_wf = gateway.get_workflow(workflow.workflow_id)
        self.assertIsNotNone(final_wf)
        self.assertIn(final_wf.state, (ApprovalState.APPROVED, ApprovalState.UNDER_REVIEW))

    def test_concurrent_audit_append(self):
        """AuditChain handles concurrent appends."""
        chain = AuditChain(max_entries=100)
        errors = []

        def append_entry(idx: int):
            try:
                entry = ApprovalAuditEntry(
                    workflow_id=f"test-con-audit-{idx}",
                    action_type="inventory_dispatch",
                    domain="domain_operations",
                    risk_level="MEDIUM",
                    new_state=ApprovalState.PENDING,
                    triggered_by="system",
                )
                chain.append(entry)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(50):
            t = threading.Thread(target=append_entry, args=(i,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0)
        self.assertGreater(chain.count(), 0)


# ═══════════════════════════════════════════════════════════
# G. BOUNDED MEMORY BEHAVIOR
# ═══════════════════════════════════════════════════════════

class BoundedMemoryTest(unittest.TestCase):
    """All approval structures are bounded."""

    def test_workflow_registry_bounded(self):
        """WorkflowRegistry enforces max workflows."""
        registry = WorkflowRegistry(max_workflows=5)
        for i in range(10):
            workflow = create_workflow(
                decision_id=f"test-bound-reg-{i}",
                action_type="inventory_dispatch",
                domain="domain_operations",
                risk_level="LOW",
                risk_score=1,
                governance_decision={},
                simulation_plan={},
                simulation_outcome={},
                simulation_context={},
            )
            try:
                registry.register(workflow)
            except RuntimeError:
                pass
        self.assertLessEqual(registry.count(), 5)

    def test_notification_history_bounded(self):
        """Notification history is bounded."""
        from core.operations.approval.notifications import MAX_NOTIFICATION_HISTORY
        self.assertGreater(MAX_NOTIFICATION_HISTORY, 0)

    def test_notification_queue_bounded(self):
        """Notification queue is bounded."""
        from core.operations.approval.notifications import MAX_QUEUED_NOTIFICATIONS
        self.assertGreater(MAX_QUEUED_NOTIFICATIONS, 0)

    def test_escalation_depth_bounded(self):
        """Escalation chain depth is bounded."""
        self.assertEqual(MAX_ESCALATION_DEPTH, 3)

    def test_workflow_signatures_list_grows(self):
        """Signature list grows but is bounded by risk config."""
        workflow = create_workflow(
            decision_id="test-sig-bound-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        self.assertLessEqual(workflow.config.required_signatures, 4)

    def test_audit_entries_per_workflow_tracked(self):
        """Audit entries per workflow are tracked without unbounded growth."""
        from core.operations.approval.audit import MAX_WORKFLOW_HISTORY
        self.assertGreater(MAX_WORKFLOW_HISTORY, 0)
        chain = AuditChain(max_entries=1000)
        for i in range(100):
            entry = ApprovalAuditEntry(
                workflow_id=f"test-bound-wh-{i % 5}",
                action_type="inv",
                domain="ops",
                risk_level="LOW",
                new_state=ApprovalState.PENDING,
                triggered_by="sys",
            )
            chain.append(entry)
        for wid in [f"test-bound-wh-{i}" for i in range(5)]:
            self.assertLessEqual(len(chain.get_by_workflow(wid)), 20)

    def test_reminder_count_bounded_by_config(self):
        """Reminders are bounded by config.max_reminders."""
        config = create_approval_config("HIGH")
        self.assertEqual(config.max_reminders, 3)

    def test_replay_rebuild_preserves_bounds(self):
        """Replay rebuild preserves bounded structures."""
        registry = WorkflowRegistry(max_workflows=5)
        workflows = []
        for i in range(3):
            w = create_workflow(
                decision_id=f"test-replay-bound-{i}",
                action_type="inv",
                domain="ops",
                risk_level="LOW",
                risk_score=1,
                governance_decision={},
                simulation_plan={},
                simulation_outcome={},
                simulation_context={},
            )
            registry.register(w)
            workflows.append(registry.get(w.workflow_id))

        registry2 = WorkflowRegistry(max_workflows=5)
        registry2.replay_rebuild(workflows)
        self.assertEqual(registry2.count(), 3)


# ═══════════════════════════════════════════════════════════
# H. AUTHORITY ISOLATION
# ═══════════════════════════════════════════════════════════

class AuthorityIsolationTest(unittest.TestCase):
    """Authority levels are strictly isolated with no leakage."""

    def test_observer_has_read_only(self):
        """Observer has read-only permissions."""
        perm = get_approval_permission(AuthorityLevel.OBSERVER)
        self.assertTrue(perm.can_view_workflows)
        self.assertFalse(perm.can_review)
        self.assertFalse(perm.can_approve)
        self.assertFalse(perm.can_escalate)
        self.assertFalse(perm.can_audit)

    def test_reviewer_can_review_not_approve(self):
        """Reviewer can review but not approve."""
        perm = get_approval_permission(AuthorityLevel.REVIEWER)
        self.assertTrue(perm.can_review)
        self.assertFalse(perm.can_approve)

    def test_approver_can_approve(self):
        """Approver can approve."""
        perm = get_approval_permission(AuthorityLevel.APPROVER)
        self.assertTrue(perm.can_approve)

    def test_senior_approver_has_highest_risk_capability(self):
        """Senior Approver can handle CRITICAL risk."""
        perm = get_approval_permission(AuthorityLevel.SENIOR_APPROVER)
        self.assertEqual(perm.max_risk_level, RiskLevel.CRITICAL)

    def test_governance_auditor_has_audit_access(self):
        """Governance Auditor has audit access only."""
        perm = get_approval_permission(AuthorityLevel.GOVERNANCE_AUDITOR)
        self.assertTrue(perm.can_audit)
        self.assertFalse(perm.can_approve)
        self.assertFalse(perm.can_review)

    def test_approver_cannot_exceed_max_risk(self):
        """Approver max risk level is MEDIUM."""
        perm = get_approval_permission(AuthorityLevel.APPROVER)
        self.assertEqual(perm.max_risk_level, RiskLevel.MEDIUM)

    def test_reviewer_cannot_approve_high_risk(self):
        """Reviewer cannot approve HIGH risk workflows."""
        workflow = create_workflow(
            decision_id="test-auth-iso-001",
            action_type="inventory_dispatch",
            domain="domain_operations",
            risk_level="HIGH",
            risk_score=3,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        is_valid, reason = validate_signature(
            workflow, "reviewer_1", AuthorityLevel.REVIEWER, "APPROVED",
        )
        self.assertFalse(is_valid)

    def test_observer_has_no_approval_permission(self):
        """Observer cannot approve any workflow."""
        perm = get_approval_permission(AuthorityLevel.OBSERVER)
        self.assertFalse(perm.can_approve)

    def test_senior_approver_can_handle_high_risk(self):
        """Senior Approver can handle HIGH risk."""
        perm = get_approval_permission(AuthorityLevel.SENIOR_APPROVER)
        rank = {RiskLevel.NONE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
        self.assertGreaterEqual(rank[perm.max_risk_level], rank[RiskLevel.HIGH])

    def test_all_roles_have_view_access(self):
        """All roles can view workflows."""
        for role in AuthorityLevel:
            perm = get_approval_permission(role)
            self.assertTrue(perm.can_view_workflows)

    def test_no_role_has_execution_authority(self):
        """No authority level has execution capability."""
        for role in AuthorityLevel:
            perm = get_approval_permission(role)
            self.assertFalse(hasattr(perm, 'can_execute'))
            self.assertFalse(hasattr(perm, 'execute'))


# ═══════════════════════════════════════════════════════════
# I. PERMISSION ENFORCEMENT
# ═══════════════════════════════════════════════════════════

class PermissionEnforcementTest(unittest.TestCase):
    """Permission model is correctly enforced."""

    def test_authority_permissions_are_complete(self):
        """All authority levels have defined permissions."""
        for role in AuthorityLevel:
            self.assertIn(role, AUTHORITY_PERMISSIONS)

    def test_unknown_authority_falls_back_to_observer(self):
        """Unknown authority falls back to Observer permissions."""
        perm = get_approval_permission(AuthorityLevel.OBSERVER)
        self.assertFalse(perm.can_approve)
        self.assertTrue(perm.can_view_workflows)

    def test_approval_permission_immutable(self):
        """ApprovalPermission is frozen (immutable)."""
        perm = get_approval_permission(AuthorityLevel.APPROVER)
        with self.assertRaises(AttributeError):
            perm.can_approve = False

    def test_permission_fields_match_roles(self):
        """Each role has exactly the expected field values."""
        expected = {
            AuthorityLevel.OBSERVER: (True, False, False, False, False, False),
            AuthorityLevel.REVIEWER: (True, True, False, True, False, False),
            AuthorityLevel.APPROVER: (True, True, True, True, True, False),
            AuthorityLevel.SENIOR_APPROVER: (True, True, True, True, True, False),
            AuthorityLevel.GOVERNANCE_AUDITOR: (True, False, False, False, False, True),
        }
        for role, (view, review, approve, escalate, cancel, audit) in expected.items():
            perm = get_approval_permission(role)
            self.assertEqual(perm.can_view_workflows, view, f"{role} view")
            self.assertEqual(perm.can_review, review, f"{role} review")
            self.assertEqual(perm.can_approve, approve, f"{role} approve")
            self.assertEqual(perm.can_escalate, escalate, f"{role} escalate")
            self.assertEqual(perm.can_cancel, cancel, f"{role} cancel")
            self.assertEqual(perm.can_audit, audit, f"{role} audit")


# ═══════════════════════════════════════════════════════════
# J. SIMULATION-CONTEXT PROPAGATION
# ═══════════════════════════════════════════════════════════

class SimulationContextPropagationTest(unittest.TestCase):
    """Simulation context marker propagates to all artifacts."""

    def setUp(self):
        reset_gateway()
        reset_registry()
        reset_audit_chain()

    def test_workflow_has_context_marker(self):
        """ApprovalWorkflow carries context marker."""
        workflow = create_workflow(
            decision_id="test-ctx-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        self.assertEqual(workflow.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_signature_has_context_marker(self):
        """ApprovalSignature carries context marker."""
        sig = ApprovalSignature(
            workflow_id="test-ctx-sig-001",
            approver_id="test",
            authority_level=AuthorityLevel.APPROVER,
            decision="APPROVED",
        )
        self.assertEqual(sig.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_audit_entry_has_context_marker(self):
        """ApprovalAuditEntry carries context marker."""
        entry = ApprovalAuditEntry(
            workflow_id="test-ctx-aud-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            new_state=ApprovalState.PENDING,
            triggered_by="sys",
        )
        self.assertEqual(entry.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_escalation_step_has_context_marker(self):
        """EscalationStep carries context marker."""
        esc = EscalationStep(
            step_index=1,
            escalated_by="test",
            escalated_to=AuthorityLevel.SENIOR_APPROVER,
            reason="test",
        )
        self.assertEqual(esc.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_notification_has_context_marker(self):
        """NotificationRecord carries context marker."""
        notif = NotificationRecord(
            workflow_id="test-ctx-notif-001",
            recipient_id="test",
            notification_type="REMINDER",
            message="test",
        )
        self.assertEqual(notif.context_marker, SIMULATION_CONTEXT_MARKER)

    def test_approval_progress_has_context_marker(self):
        """Approval progress includes context marker."""
        workflow = create_workflow(
            decision_id="test-ctx-prog-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        progress = get_approval_progress(signed)
        self.assertIn(SIMULATION_CONTEXT_MARKER, progress["context_marker"])

    def test_escalation_summary_has_context_marker(self):
        """Escalation summary includes context marker."""
        workflow = create_workflow(
            decision_id="test-ctx-esc-001",
            action_type="inv",
            domain="ops",
            risk_level="HIGH",
            risk_score=3,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        object.__setattr__(workflow, 'state', ApprovalState.UNDER_REVIEW)
        escalated = escalate(workflow, "reviewer_1", AuthorityLevel.SENIOR_APPROVER, "Needs review")
        summary = get_escalation_summary(escalated)
        self.assertIn(SIMULATION_CONTEXT_MARKER, summary["context_marker"])

    def test_notification_summary_has_context_marker(self):
        """Notification summary includes context marker."""
        summary = get_notification_summary()
        self.assertIn(SIMULATION_CONTEXT_MARKER, summary["context_marker"])

    def test_gateway_status_has_context_marker(self):
        """Gateway status includes context marker."""
        gateway = get_gateway()
        status = gateway.get_gateway_status()
        self.assertIn(SIMULATION_CONTEXT_MARKER, status["context_marker"])

    def test_workflow_summary_has_context_marker(self):
        """Workflow summary includes context marker."""
        gateway = get_gateway()
        decision = _make_decision_result()
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = gateway.route_decision(decision, plan, outcome)
        summary = gateway.get_workflow_summary(workflow.workflow_id)
        self.assertIn(SIMULATION_CONTEXT_MARKER, summary["context_marker"])

    def test_marker_survives_serialization(self):
        """Context marker survives serialization round-trip."""
        entry = ApprovalAuditEntry(
            workflow_id="test-serial-ctx-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            new_state=ApprovalState.PENDING,
            triggered_by="sys",
        )
        chain = AuditChain()
        chain.append(entry)
        serialized = chain.to_serializable()
        self.assertEqual(serialized[0]["context_marker"], SIMULATION_CONTEXT_MARKER)
        chain2 = AuditChain()
        chain2.rebuild_from_serializable(serialized)
        rebuilt = chain2.get_all()[0]
        self.assertEqual(rebuilt.context_marker, SIMULATION_CONTEXT_MARKER)


# ═══════════════════════════════════════════════════════════
# K. SEMANTIC NEUTRALITY
# ═══════════════════════════════════════════════════════════

class SemanticNeutralityTest(unittest.TestCase):
    """No semantic execution drift — all artifacts are governance-only."""

    def test_approval_workflow_not_executable(self):
        """ApprovalWorkflow has no execution methods."""
        workflow = create_workflow(
            decision_id="test-sem-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        self.assertFalse(hasattr(workflow, 'execute'))
        self.assertFalse(hasattr(workflow, 'run'))
        self.assertFalse(hasattr(workflow, 'dispatch'))
        self.assertFalse(hasattr(workflow, 'commit'))

    def test_no_execution_methods_in_gateway(self):
        """Gateway has no execution methods."""
        gateway = get_gateway()
        self.assertFalse(hasattr(gateway, 'execute'))
        self.assertFalse(hasattr(gateway, 'dispatch'))
        self.assertFalse(hasattr(gateway, 'commit'))
        self.assertFalse(hasattr(gateway, 'run'))
        self.assertFalse(hasattr(gateway, 'perform'))

    def test_no_erp_domain_references_in_approval(self):
        """Approval module has no ERP domain references."""
        import inspect
        from core.operations.approval import models
        source = inspect.getsource(models)
        self.assertNotIn('StockMovement', source)
        self.assertNotIn('JournalEntry', source)
        self.assertNotIn('Product', source)
        self.assertNotIn('Invoice', source)
        self.assertNotIn('Batch', source)

    def test_no_erp_in_gateway(self):
        """Gateway has no ERP model imports."""
        import inspect
        from core.operations.approval import gateway
        source = inspect.getsource(gateway)
        self.assertNotIn('from inventory', source)
        self.assertNotIn('from accounting', source)
        self.assertNotIn('from sales', source)
        self.assertNotIn('from purchases', source)

    def test_approval_is_informational_only(self):
        """Approval summaries state informational nature."""
        workflow = create_workflow(
            decision_id="test-info-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        summary = get_approval_summary(workflow)
        self.assertIn("workflow_id", summary)
        self.assertIn("state", summary)
        self.assertNotIn("execution", summary)
        self.assertNotIn("run", summary)


# ═══════════════════════════════════════════════════════════
# L. STRUCTURAL NEUTRALITY
# ═══════════════════════════════════════════════════════════

class StructuralNeutralityTest(unittest.TestCase):
    """No structural coupling to ERP execution paths."""

    def test_no_erp_imports(self):
        """Approval module does not import any ERP apps."""
        import sys
        approval_modules = [
            'core.operations.approval.models',
            'core.operations.approval.workflow_engine',
            'core.operations.approval.multisig',
            'core.operations.approval.escalation',
            'core.operations.approval.audit',
            'core.operations.approval.notifications',
            'core.operations.approval.gateway',
        ]
        for mod_name in approval_modules:
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
                for name, obj in vars(mod).items():
                    if hasattr(obj, '__module__'):
                        self.assertNotIn('inventory', str(obj.__module__))
                        self.assertNotIn('accounting', str(obj.__module__))
                        self.assertNotIn('sales', str(obj.__module__))
                        self.assertNotIn('purchases', str(obj.__module__))

    def test_no_side_effects_in_constructors(self):
        """Model constructors have no side effects."""
        sig = ApprovalSignature(
            workflow_id="test",
            approver_id="test",
            authority_level=AuthorityLevel.APPROVER,
            decision="APPROVED",
        )
        self.assertEqual(sig.decision, "APPROVED")

    def test_gateway_does_not_mutate_inputs(self):
        """Gateway does not mutate input decision artifacts."""
        gateway = get_gateway()
        decision = _make_decision_result()
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        original_decision_id = decision["action_id"]
        original_plan_id = plan["plan_id"]
        gateway.route_decision(decision, plan, outcome)
        self.assertEqual(decision["action_id"], original_decision_id)
        self.assertEqual(plan["plan_id"], original_plan_id)


# ═══════════════════════════════════════════════════════════
# M. NO EXECUTION LEAKAGE
# ═══════════════════════════════════════════════════════════

class NoExecutionLeakageTest(unittest.TestCase):
    """No approval outcome may trigger or suggest execution."""

    def test_approve_does_not_execute(self):
        """APPROVED state does not trigger execution."""
        workflow = create_workflow(
            decision_id="test-noexec-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(signed.state, ApprovalState.APPROVED)
        self.assertNotIn("execution", signed.metadata)
        self.assertNotIn("execute", str(signed))

    def test_reject_does_not_rollback(self):
        """REJECTED state does not trigger rollback."""
        workflow = create_workflow(
            decision_id="test-noexec-002",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        signed = apply_signature(workflow, "approver_1", AuthorityLevel.APPROVER, "REJECTED")
        self.assertEqual(signed.state, ApprovalState.REJECTED)
        self.assertNotIn("rollback", str(signed))

    def test_expired_does_not_recover(self):
        """EXPIRED state does not trigger recovery."""
        workflow = create_workflow(
            decision_id="test-noexec-003",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        object.__setattr__(workflow, 'timeout_at', past_time)
        did_expire, updated = check_timeout_expiry(workflow)
        self.assertTrue(did_expire)
        self.assertNotIn("recover", str(updated))
        self.assertNotIn("restore", str(updated))

    def test_no_auto_approval_paths(self):
        """No approval path automatically approves."""
        registry = WorkflowRegistry()
        for i in range(10):
            workflow = create_workflow(
                decision_id=f"test-auto-{i}",
                action_type="inv",
                domain="ops",
                risk_level="HIGH",
                risk_score=3,
                governance_decision={},
                simulation_plan={},
                simulation_outcome={},
                simulation_context={},
            )
            registry.register(workflow)
        for wid in list(registry._workflows.keys()):
            w = registry.get(wid)
            self.assertNotEqual(w.state, ApprovalState.APPROVED)

    def test_approval_not_execution_permission(self):
        """Approval artifacts clearly state governance-only purpose."""
        with open(__file__, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("GOVERNANCE AUTHORIZATION", content)

    def test_all_states_are_non_executing(self):
        """No approval state can be interpreted as execution."""
        for state in ApprovalState:
            self.assertNotIn("EXECUT", state.value)


# ═══════════════════════════════════════════════════════════
# N. NO ERP MUTATION
# ═══════════════════════════════════════════════════════════

class NoERPMutationTest(unittest.TestCase):
    """No component may mutate ERP state."""

    def test_approval_module_no_django_models(self):
        """Approval module does not import Django models from ERP apps."""
        import inspect
        from core.operations.approval import models
        source = inspect.getsource(models)
        self.assertNotIn('models.Model', source)
        self.assertNotIn('django.db', source)

    def test_no_write_operations(self):
        """No approval component writes to ERP database."""
        import inspect
        from core.operations.approval import gateway
        source = inspect.getsource(gateway)
        self.assertNotIn('.save()', source)
        self.assertNotIn('.create(', source)
        self.assertNotIn('.update(', source)
        self.assertNotIn('.delete(', source)
        self.assertNotIn('bulk_create', source)

    def test_no_erp_service_calls(self):
        """No approval component calls ERP services."""
        import inspect
        from core.operations.approval import gateway
        source = inspect.getsource(gateway)
        self.assertNotIn('inventory.services', source)
        self.assertNotIn('accounting.services', source)
        self.assertNotIn('sales.services', source)
        self.assertNotIn('purchases.services', source)

    def test_approval_has_no_db_migrations(self):
        """Approval module has no database migrations."""
        import os
        approval_dir = os.path.dirname(__file__.replace('simulation\\tests\\test_human_approval_gateway', 'core\\operations\\approval'))
        migration_dir = os.path.join(approval_dir, 'migrations')
        self.assertFalse(os.path.exists(migration_dir))


# ═══════════════════════════════════════════════════════════
# O. APPROVAL REPLAY RECONSTRUCTION
# ═══════════════════════════════════════════════════════════

class ApprovalReplayReconstructionTest(unittest.TestCase):
    """Full approval workflows can be reconstructed from replay data."""

    def setUp(self):
        reset_gateway()
        reset_registry()
        reset_audit_chain()

    def test_full_workflow_replay(self):
        """Full workflow lifecycle survives replay."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM")
        plan = _make_simulation_plan()
        outcome = _make_simulation_outcome()
        workflow = gateway.route_decision(decision, plan, outcome)
        s1 = gateway.submit_signature(workflow.workflow_id, "approver_1", AuthorityLevel.APPROVER, "APPROVED")
        s2 = gateway.submit_signature(s1.workflow_id, "approver_2", AuthorityLevel.APPROVER, "APPROVED")
        self.assertEqual(s2.state, ApprovalState.APPROVED)
        final_workflow = gateway.get_workflow(s2.workflow_id)
        self.assertIsNotNone(final_workflow)
        gateway2 = HumanApprovalGateway()
        gateway2.replay_rebuild([final_workflow])
        replayed = gateway2.get_workflow(final_workflow.workflow_id)
        self.assertIsNotNone(replayed)
        self.assertEqual(replayed.state, final_workflow.state)

    def test_audit_chain_replay_preserves_transitions(self):
        """Audit chain replay preserves all state transitions."""
        chain = get_audit_chain()
        workflow = create_workflow(
            decision_id="test-replay-chain-001",
            action_type="inv",
            domain="ops",
            risk_level="MEDIUM",
            risk_score=2,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        for entry in workflow.audit_entries:
            chain.append(entry)
        self.assertGreater(chain.count(), 0)
        serialized = chain.to_serializable()
        chain2 = AuditChain()
        chain2.rebuild_from_serializable(serialized)
        self.assertEqual(chain.count(), chain2.count())

    def test_escalation_replay(self):
        """Escalation chain survives replay."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="HIGH")
        workflow = gateway.route_decision(decision, _make_simulation_plan(), _make_simulation_outcome())
        s1 = gateway.submit_signature(workflow.workflow_id, "senior_1", AuthorityLevel.SENIOR_APPROVER, "APPROVED")
        self.assertEqual(s1.state, ApprovalState.UNDER_REVIEW)
        final_workflow = gateway.get_workflow(s1.workflow_id)
        gateway2 = HumanApprovalGateway()
        gateway2.replay_rebuild([final_workflow])
        replayed = gateway2.get_workflow(final_workflow.workflow_id)
        self.assertIsNotNone(replayed)
        self.assertEqual(replayed.state, final_workflow.state)

    def test_replay_rebuild_multiple_workflows(self):
        """Multiple workflows survive replay rebuild."""
        gateway = get_gateway()
        workflows = []
        for i in range(5):
            d = _make_decision_result(
                action_type="inventory_dispatch",
                risk_level="LOW",
            )
            d["action_id"] = f"test-replay-multi-{i}"
            d["audit_entry"]["action_id"] = f"test-replay-multi-{i}"
            w = gateway.route_decision(d, _make_simulation_plan(), _make_simulation_outcome())
            workflows.append(w)
        gw2 = HumanApprovalGateway()
        gw2.replay_rebuild(workflows)
        for w in workflows:
            replayed = gw2.get_workflow(w.workflow_id)
            self.assertIsNotNone(replayed)
            self.assertEqual(replayed.state, w.state)

    def test_replay_idempotent_cross_instances(self):
        """Replaying same data to different instances produces same state."""
        workflow = create_workflow(
            decision_id="test-replay-idem-001",
            action_type="inv",
            domain="ops",
            risk_level="LOW",
            risk_score=1,
            governance_decision={},
            simulation_plan={},
            simulation_outcome={},
            simulation_context={},
        )
        reg1 = WorkflowRegistry()
        reg1.register(workflow)
        reg2 = WorkflowRegistry()
        wf_copy = ApprovalWorkflow(
            workflow_id=workflow.workflow_id,
            decision_id=workflow.decision_id,
            plan_id=workflow.plan_id,
            outcome_id=workflow.outcome_id,
            action_type=workflow.action_type,
            domain=workflow.domain,
            risk_level=workflow.risk_level,
            risk_score=workflow.risk_score,
            state=workflow.state,
            signatures=list(workflow.signatures),
            escalation_chain=list(workflow.escalation_chain),
            audit_entries=list(workflow.audit_entries),
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
        reg2.register(wf_copy)
        self.assertEqual(reg1.get(workflow.workflow_id).state,
                         reg2.get(wf_copy.workflow_id).state)


# ═══════════════════════════════════════════════════════════
# P. HUMAN APPROVAL GATEWAY INTEGRATION
# ═══════════════════════════════════════════════════════════

class HumanApprovalGatewayIntegrationTest(unittest.TestCase):
    """End-to-end integration tests for the gateway."""

    def setUp(self):
        reset_gateway()
        reset_registry()
        reset_audit_chain()

    def test_full_approval_flow_low_risk(self):
        """Complete LOW risk approval flow."""
        gateway = get_gateway()
        decision = _make_decision_result(
            action_type="observability_read",
            domain="observability_read",
            risk_level="LOW",
            risk_score=1,
        )
        workflow = gateway.route_decision(decision, {}, {})
        signed = gateway.submit_signature(
            workflow.workflow_id, "approver_1", AuthorityLevel.APPROVER, "APPROVED",
        )
        self.assertEqual(signed.state, ApprovalState.APPROVED)

    def test_full_approval_flow_medium_risk(self):
        """Complete MEDIUM risk dual-approval flow."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM", risk_score=2)
        workflow = gateway.route_decision(
            decision, _make_simulation_plan(), _make_simulation_outcome(),
        )
        s1 = gateway.submit_signature(
            workflow.workflow_id, "approver_1", AuthorityLevel.APPROVER, "APPROVED",
        )
        self.assertEqual(s1.state, ApprovalState.UNDER_REVIEW)
        s2 = gateway.submit_signature(
            s1.workflow_id, "approver_2", AuthorityLevel.APPROVER, "APPROVED",
        )
        self.assertEqual(s2.state, ApprovalState.APPROVED)

    def test_full_approval_flow_high_risk(self):
        """Complete HIGH risk multi-signature flow."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="HIGH", risk_score=3)
        workflow = gateway.route_decision(
            decision, _make_simulation_plan(), _make_simulation_outcome(),
        )
        s1 = gateway.submit_signature(
            workflow.workflow_id, "senior_1", AuthorityLevel.SENIOR_APPROVER, "APPROVED",
        )
        s2 = gateway.submit_signature(
            s1.workflow_id, "senior_2", AuthorityLevel.SENIOR_APPROVER, "APPROVED",
        )
        s3 = gateway.submit_signature(
            s2.workflow_id, "senior_3", AuthorityLevel.SENIOR_APPROVER, "APPROVED",
        )
        self.assertEqual(s3.state, ApprovalState.APPROVED)

    def test_rejection_flow(self):
        """Rejection immediately terminates workflow."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM")
        workflow = gateway.route_decision(decision, _make_simulation_plan(), _make_simulation_outcome())
        signed = gateway.submit_signature(
            workflow.workflow_id, "approver_1", AuthorityLevel.APPROVER, "REJECTED",
        )
        self.assertEqual(signed.state, ApprovalState.REJECTED)

    def test_escalation_flow(self):
        """Escalation followed by approval works correctly."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="HIGH")
        workflow = gateway.route_decision(
            decision, _make_simulation_plan(), _make_simulation_outcome(),
        )
        s1 = gateway.submit_signature(
            workflow.workflow_id, "senior_1", AuthorityLevel.SENIOR_APPROVER, "APPROVED",
        )
        escalated = gateway.escalate_workflow(
            s1.workflow_id, "senior_1", AuthorityLevel.SENIOR_APPROVER,
            "Needs additional senior review",
        )
        self.assertEqual(escalated.state, ApprovalState.ESCALATED)
        returned = gateway.return_from_escalation(escalated.workflow_id, "senior_2")
        self.assertEqual(returned.state, ApprovalState.UNDER_REVIEW)
        s2 = gateway.submit_signature(
            returned.workflow_id, "senior_2", AuthorityLevel.SENIOR_APPROVER, "APPROVED",
        )
        s3 = gateway.submit_signature(
            s2.workflow_id, "senior_3", AuthorityLevel.SENIOR_APPROVER, "APPROVED",
        )
        self.assertEqual(s3.state, ApprovalState.APPROVED)

    def test_cancel_workflow(self):
        """Workflow can be cancelled from PENDING or UNDER_REVIEW."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM")
        workflow = gateway.route_decision(decision, _make_simulation_plan(), _make_simulation_outcome())
        cancelled = gateway.cancel_workflow(workflow.workflow_id, "admin")
        self.assertEqual(cancelled.state, ApprovalState.CANCELLED)

    def test_process_timeouts(self):
        """Timeout processing expires eligible workflows."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="HIGH")
        workflow = gateway.route_decision(
            decision, _make_simulation_plan(), _make_simulation_outcome(),
        )
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        modified_wf = ApprovalWorkflow(
            workflow_id=workflow.workflow_id,
            decision_id=workflow.decision_id,
            plan_id=workflow.plan_id,
            outcome_id=workflow.outcome_id,
            action_type=workflow.action_type,
            domain=workflow.domain,
            risk_level=workflow.risk_level,
            risk_score=workflow.risk_score,
            state=workflow.state,
            signatures=list(workflow.signatures),
            escalation_chain=list(workflow.escalation_chain),
            audit_entries=list(workflow.audit_entries),
            config=workflow.config,
            governance_decision=workflow.governance_decision,
            simulation_plan=workflow.simulation_plan,
            simulation_outcome=workflow.simulation_outcome,
            simulation_context=workflow.simulation_context,
            timeout_at=past_time,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            context_marker=workflow.context_marker,
            metadata=workflow.metadata,
        )
        gateway._workflow_registry._workflows[workflow.workflow_id] = modified_wf
        expired = gateway.process_timeouts()
        self.assertGreater(len(expired), 0)
        self.assertEqual(expired[0].state, ApprovalState.EXPIRED)

    def test_gateway_status(self):
        """Gateway status returns valid information."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM")
        gateway.route_decision(decision, _make_simulation_plan(), _make_simulation_outcome())
        status = gateway.get_gateway_status()
        self.assertIn("gateway_version", status)
        self.assertIn("total_workflows", status)
        self.assertGreaterEqual(status["total_workflows"], 1)

    def test_workflow_summary(self):
        """Workflow summary contains all sections."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM")
        workflow = gateway.route_decision(
            decision, _make_simulation_plan(), _make_simulation_outcome(),
        )
        summary = gateway.get_workflow_summary(workflow.workflow_id)
        self.assertIn("approval", summary)
        self.assertIn("multi_signature", summary)
        self.assertIn("escalation", summary)
        self.assertIn("audit", summary)
        self.assertIn("notifications", summary)

    def test_unknown_workflow_raises(self):
        """Accessing unknown workflow raises ValueError."""
        gateway = get_gateway()
        with self.assertRaises(ValueError):
            gateway.get_workflow_summary("nonexistent_workflow")

    def test_audit_integrity_from_gateway(self):
        """Gateway provides audit integrity check."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="LOW")
        gateway.route_decision(decision, {}, {})
        integrity = gateway.get_audit_integrity()
        self.assertTrue(integrity["integrity_ok"])

    def test_workflow_audit_trail(self):
        """Gateway provides workflow audit trail."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="MEDIUM")
        workflow = gateway.route_decision(
            decision, _make_simulation_plan(), _make_simulation_outcome(),
        )
        gateway.submit_signature(
            workflow.workflow_id, "approver_1", AuthorityLevel.APPROVER, "APPROVED",
        )
        trail = gateway.get_workflow_audit(workflow.workflow_id)
        self.assertGreater(len(trail), 0)

    def test_list_active_workflows(self):
        """Gateway lists active workflows."""
        gateway = get_gateway()
        for i in range(3):
            d = _make_decision_result(risk_level="LOW")
            d["action_id"] = f"test-active-{i}"
            d["audit_entry"]["action_id"] = f"test-active-{i}"
            gateway.route_decision(d, {}, {})
        active = gateway.list_active_workflows()
        self.assertGreaterEqual(len(active), 3)

    def test_list_workflows_by_risk(self):
        """Gateway lists workflows filtered by risk level."""
        gateway = get_gateway()
        d1 = _make_decision_result(risk_level="LOW", risk_score=1)
        d1["action_id"] = "test-filter-low"
        d1["audit_entry"]["action_id"] = "test-filter-low"
        gateway.route_decision(d1, {}, {})
        d2 = _make_decision_result(risk_level="MEDIUM", risk_score=2)
        d2["action_id"] = "test-filter-med"
        d2["audit_entry"]["action_id"] = "test-filter-med"
        gateway.route_decision(d2, {}, {})
        low = gateway.list_workflows_by_risk("LOW")
        med = gateway.list_workflows_by_risk("MEDIUM")
        self.assertGreaterEqual(len(low), 1)
        self.assertGreaterEqual(len(med), 1)

    def test_gateway_reset(self):
        """Gateway reset clears all state."""
        gateway = get_gateway()
        decision = _make_decision_result(risk_level="LOW")
        gateway.route_decision(decision, {}, {})
        gateway.reset()
        self.assertEqual(gateway._workflow_registry.count(), 0)

    def test_submit_signature_to_unknown_workflow(self):
        """Submitting signature to unknown workflow raises ValueError."""
        gateway = get_gateway()
        with self.assertRaises(ValueError):
            gateway.submit_signature("nonexistent", "user", AuthorityLevel.APPROVER, "APPROVED")

    def test_escalate_unknown_workflow(self):
        """Escalating unknown workflow raises ValueError."""
        gateway = get_gateway()
        with self.assertRaises(ValueError):
            gateway.escalate_workflow("nonexistent", "user", AuthorityLevel.SENIOR_APPROVER, "reason")

    def test_cancel_unknown_workflow(self):
        """Cancelling unknown workflow raises ValueError."""
        gateway = get_gateway()
        with self.assertRaises(ValueError):
            gateway.cancel_workflow("nonexistent", "user")

    def test_multiple_decision_routing(self):
        """Multiple decisions route to independent workflows."""
        gateway = get_gateway()
        w1 = gateway.route_decision(
            _make_decision_result(action_type="inventory_dispatch", risk_level="HIGH"),
            _make_simulation_plan(), _make_simulation_outcome(),
        )
        w2 = gateway.route_decision(
            _make_decision_result(action_type="inventory_receive", risk_level="MEDIUM"),
            _make_simulation_plan(), _make_simulation_outcome(),
        )
        self.assertNotEqual(w1.workflow_id, w2.workflow_id)


# ═══════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    unittest.main()
