"""
Phase 5B.2 — Human Approval Gateway.

DETERMINISTIC GOVERNANCE AUTHORIZATION LAYER.
ZERO EXECUTION AUTHORITY. HUMAN GOVERNANCE ONLY.

This module provides:
- ApprovalWorkflow: immutable approval workflow state machine
- MultiSignatureEnforcer: deterministic multi-signature enforcement
- EscalationEngine: bounded, deterministic escalation routing
- AuditChain: immutable governance audit trail
- ApprovalNotifier: deterministic, non-coercive notification system
- ApprovalPermission: role-based authority model (no execution)
- HumanApprovalGateway: orchestrator connecting all components

SIMULATION CONTEXT ONLY — NO ERP EXECUTION.
"""

HUMAN_APPROVAL_GATEWAY_VERSION = "1.0.0"
SIMULATION_CONTEXT_MARKER = "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION"
