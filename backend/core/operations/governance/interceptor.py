"""
Phase 5B.0 — Governance Interceptor.

Captures ALL potential system actions before execution.
Creates ActionIntent objects for every intercepted action.

Read-only interception — no execution, no side effects, no mutation.

Interceptor pipeline:
1. Receive action request (source, type, domain, context)
2. Validate action request structure
3. Create ActionIntent with metadata
4. Return ActionIntent for policy evaluation

No action bypasses this interceptor.
"""
from typing import Any, Dict, Optional
from core.operations.governance.models import ActionIntent
from core.operations.policy.forbidden import is_action_forbidden, get_forbidden_actions_by_domain


INTERCEPTOR_VERSION = "1.0.0"

# All recognized action types and their domains
ACTION_TYPE_REGISTRY = {
    "replay_execute": {"domain": "replay_operations", "risk_pre": "HIGH"},
    "replay_start": {"domain": "replay_operations", "risk_pre": "MEDIUM"},
    "replay_pause": {"domain": "replay_operations", "risk_pre": "LOW"},
    "replay_resume": {"domain": "replay_operations", "risk_pre": "LOW"},
    "replay_step": {"domain": "replay_operations", "risk_pre": "LOW"},
    "inventory_dispatch": {"domain": "domain_operations", "risk_pre": "CRITICAL"},
    "inventory_receive": {"domain": "domain_operations", "risk_pre": "CRITICAL"},
    "inventory_transfer": {"domain": "domain_operations", "risk_pre": "HIGH"},
    "inventory_adjust": {"domain": "domain_operations", "risk_pre": "HIGH"},
    "accounting_journal_entry": {"domain": "erp_mutation", "risk_pre": "CRITICAL"},
    "accounting_close_period": {"domain": "system_operations", "risk_pre": "CRITICAL"},
    "erp_create_product": {"domain": "erp_mutation", "risk_pre": "CRITICAL"},
    "erp_update_batch": {"domain": "erp_mutation", "risk_pre": "CRITICAL"},
    "erp_create_invoice": {"domain": "erp_mutation", "risk_pre": "CRITICAL"},
    "security_create_user": {"domain": "security_operations", "risk_pre": "CRITICAL"},
    "security_update_permissions": {"domain": "security_operations", "risk_pre": "CRITICAL"},
    "system_rollback": {"domain": "system_operations", "risk_pre": "CRITICAL"},
    "system_recover": {"domain": "system_operations", "risk_pre": "CRITICAL"},
    "system_restore": {"domain": "system_operations", "risk_pre": "CRITICAL"},
    "observability_read": {"domain": "observability_read", "risk_pre": "NONE"},
    "observability_query": {"domain": "observability_read", "risk_pre": "NONE"},
}

# Sources that can trigger actions
VALID_SOURCES = ["api", "ui", "workflow", "system", "replay", "external"]


def intercept(action_type: str, source: str, context: Optional[Dict[str, Any]] = None,
              metadata: Optional[Dict[str, Any]] = None) -> ActionIntent:
    """Intercept a potential action before execution.

    Creates an ActionIntent that must pass through the full governance pipeline
    before any execution consideration.

    Args:
        action_type: Type of action (from ACTION_TYPE_REGISTRY).
        source: Source of the action (api, ui, workflow, system, replay, external).
        context: Action-specific context.
        metadata: Additional metadata.

    Returns:
        An immutable ActionIntent.

    Raises:
        ValueError: If action_type is unknown or source is invalid.
    """
    if action_type not in ACTION_TYPE_REGISTRY:
        raise ValueError(f"Unknown action type: {action_type}")

    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source: {source}. Valid: {VALID_SOURCES}")

    action_info = ACTION_TYPE_REGISTRY[action_type]
    return ActionIntent(
        action_type=action_type,
        domain=action_info["domain"],
        source=source,
        context=context or {},
        metadata={
            "interceptor_version": INTERCEPTOR_VERSION,
            "risk_pre_classification": action_info["risk_pre"],
            "is_forbidden": action_info["domain"] in ("erp_mutation", "system_operations", "security_operations", "domain_operations"),
            **(metadata or {}),
        },
    )


def get_supported_action_types() -> Dict[str, Dict[str, str]]:
    """Return the registry of all recognized action types."""
    return dict(ACTION_TYPE_REGISTRY)


def is_action_type_registered(action_type: str) -> bool:
    """Check if an action type is registered in the interceptor."""
    return action_type in ACTION_TYPE_REGISTRY
