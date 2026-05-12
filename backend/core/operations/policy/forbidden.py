"""
Phase 5A.5.5 — Forbidden Action Registry.

Defines all operations that are forbidden in the operational runtime.
These are declarative policy definitions — NO execution enforcement.

The registry maps:
- action_id: unique identifier
- domain: which subsystem this belongs to
- risk_level: severity if bypassed
- description: what the action is
- reason: why it's forbidden
- authority_required: what authority would be needed (None = always forbidden)

NO execution capability. Declarative registry only.
"""
from typing import Any, Dict, List


FORBIDDEN_ACTIONS = [
    # ── ERP Mutation Actions ──
    {
        "action_id": "ERP-001",
        "domain": "erp_mutation",
        "action": "create_inventory_product",
        "risk_level": "CRITICAL",
        "description": "Create a new product in inventory",
        "reason": "ERP mutation — not allowed from operational runtime",
        "authority_required": None,
    },
    {
        "action_id": "ERP-002",
        "domain": "erp_mutation",
        "action": "update_inventory_batch",
        "risk_level": "CRITICAL",
        "description": "Update batch quantity or attributes",
        "reason": "ERP mutation — not allowed from operational runtime",
        "authority_required": None,
    },
    {
        "action_id": "ERP-003",
        "domain": "erp_mutation",
        "action": "create_sales_invoice",
        "risk_level": "CRITICAL",
        "description": "Create a new sales invoice",
        "reason": "ERP mutation — not allowed from operational runtime",
        "authority_required": None,
    },
    {
        "action_id": "ERP-004",
        "domain": "erp_mutation",
        "action": "create_purchase_invoice",
        "risk_level": "CRITICAL",
        "description": "Create a new purchase invoice",
        "reason": "ERP mutation — not allowed from operational runtime",
        "authority_required": None,
    },
    {
        "action_id": "ERP-005",
        "domain": "erp_mutation",
        "action": "create_journal_entry",
        "risk_level": "CRITICAL",
        "description": "Create a journal entry in accounting",
        "reason": "ERP mutation — not allowed from operational runtime",
        "authority_required": None,
    },
    # ── Domain Operation Actions ──
    {
        "action_id": "DOM-001",
        "domain": "domain_operations",
        "action": "dispatch_sales",
        "risk_level": "CRITICAL",
        "description": "Dispatch a sales invoice (update stock + create journal entry)",
        "reason": "Domain operation with ERP side effects",
        "authority_required": None,
    },
    {
        "action_id": "DOM-002",
        "domain": "domain_operations",
        "action": "receive_purchase",
        "risk_level": "CRITICAL",
        "description": "Receive a purchase invoice (update stock + create journal entry)",
        "reason": "Domain operation with ERP side effects",
        "authority_required": None,
    },
    {
        "action_id": "DOM-003",
        "domain": "domain_operations",
        "action": "transfer_warehouse",
        "risk_level": "HIGH",
        "description": "Transfer stock between warehouses",
        "reason": "Domain operation with inventory side effects",
        "authority_required": None,
    },
    {
        "action_id": "DOM-004",
        "domain": "domain_operations",
        "action": "adjust_stock",
        "risk_level": "HIGH",
        "description": "Adjust inventory stock levels",
        "reason": "Domain operation with inventory side effects",
        "authority_required": None,
    },
    # ── System Operation Actions ──
    {
        "action_id": "SYS-001",
        "domain": "system_operations",
        "action": "rollback_transaction",
        "risk_level": "CRITICAL",
        "description": "Roll back a financial transaction",
        "reason": "System operation with ERP side effects",
        "authority_required": None,
    },
    {
        "action_id": "SYS-002",
        "domain": "system_operations",
        "action": "recover_from_failure",
        "risk_level": "CRITICAL",
        "description": "Execute recovery from system failure",
        "reason": "System operation — not authorized from observability runtime",
        "authority_required": None,
    },
    {
        "action_id": "SYS-003",
        "domain": "system_operations",
        "action": "restore_from_backup",
        "risk_level": "CRITICAL",
        "description": "Restore ERP state from backup",
        "reason": "System operation — not authorized from observability runtime",
        "authority_required": None,
    },
    {
        "action_id": "SYS-004",
        "domain": "system_operations",
        "action": "close_fiscal_period",
        "risk_level": "CRITICAL",
        "description": "Close an accounting fiscal period",
        "reason": "System operation with ERP side effects",
        "authority_required": None,
    },
    # ── Security Operation Actions ──
    {
        "action_id": "SEC-001",
        "domain": "security_operations",
        "action": "create_user",
        "risk_level": "CRITICAL",
        "description": "Create a new system user",
        "reason": "Security operation — not allowed from operational runtime",
        "authority_required": None,
    },
    {
        "action_id": "SEC-002",
        "domain": "security_operations",
        "action": "update_permissions",
        "risk_level": "CRITICAL",
        "description": "Update user or role permissions",
        "reason": "Security operation — not allowed from operational runtime",
        "authority_required": None,
    },
    {
        "action_id": "SEC-003",
        "domain": "security_operations",
        "action": "delete_role",
        "risk_level": "CRITICAL",
        "description": "Delete a security role",
        "reason": "Security operation — not allowed from operational runtime",
        "authority_required": None,
    },
    # ── Governance Actions (future) ──
    {
        "action_id": "GOV-001",
        "domain": "governance_operations",
        "action": "approve_execution",
        "risk_level": "CRITICAL",
        "description": "Approve an operational execution request",
        "reason": "Governance operation — not implemented yet",
        "authority_required": "GovernanceAdmin",
    },
    {
        "action_id": "GOV-002",
        "domain": "governance_operations",
        "action": "reject_execution",
        "risk_level": "MEDIUM",
        "description": "Reject an operational execution request",
        "reason": "Governance operation — not implemented yet",
        "authority_required": "GovernanceAdmin",
    },
]


def get_forbidden_action(action_id: str) -> Any:
    """Get a forbidden action by ID."""
    for action in FORBIDDEN_ACTIONS:
        if action["action_id"] == action_id:
            return action
    return None


def get_all_forbidden_actions() -> List[Dict[str, Any]]:
    """Get all forbidden actions."""
    return list(FORBIDDEN_ACTIONS)


def get_forbidden_actions_by_domain(domain: str) -> List[Dict[str, Any]]:
    """Filter forbidden actions by domain."""
    return [a for a in FORBIDDEN_ACTIONS if a["domain"] == domain]


def get_forbidden_actions_by_risk(risk_level: str) -> List[Dict[str, Any]]:
    """Filter forbidden actions by risk level."""
    return [a for a in FORBIDDEN_ACTIONS if a["risk_level"] == risk_level]


def is_action_forbidden(action_name: str) -> bool:
    """Check if an action name matches any forbidden action."""
    return any(a["action"] == action_name for a in FORBIDDEN_ACTIONS)
