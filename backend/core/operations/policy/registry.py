"""
Phase 5A.5.5 — Operational Policy Registry.

Declarative, immutable operational policies for governance boundary definition.
Policies are READ-ONLY — they define what governance SHOULD enforce,
but do NOT execute any enforcement.

All policies are:
- Deterministic (same input → same policy evaluation)
- Immutable (policy definitions cannot change after freeze)
- Versioned (each policy has a schema version)
- Audit-traceable (each policy has an id and description)

NO execution capability allowed.
"""
from typing import Any, Dict, List


POLICY_REGISTRY_VERSION = "1.0.0"

# ── Replay Operation Policies ──

REPLAY_POLICIES = [
    {
        "policy_id": "REPLAY-001",
        "name": "replay_write_block",
        "description": "All write operations are blocked during replay execution",
        "authority_required": None,
        "risk_level": "CRITICAL",
        "enforcement": "ALWAYS_BLOCKED",
        "forbidden_actions": [
            "dispatch", "receive", "transfer", "adjust",
            "create_record", "update_record", "delete_record",
        ],
    },
    {
        "policy_id": "REPLAY-002",
        "name": "replay_business_logic_block",
        "description": "All business logic operations are blocked during replay",
        "authority_required": None,
        "risk_level": "CRITICAL",
        "enforcement": "ALWAYS_BLOCKED",
    },
]

# ── Observability Policies ──

OBSERVABILITY_POLICIES = [
    {
        "policy_id": "OBS-001",
        "name": "observability_read_only",
        "description": "All observability endpoints are read-only (GET only)",
        "authority_required": None,
        "risk_level": "CRITICAL",
        "enforcement": "METHOD_RESTRICTION",
    },
    {
        "policy_id": "OBS-002",
        "name": "observability_auth_required",
        "description": "All observability endpoints require authentication",
        "authority_required": "IsAuthenticated",
        "risk_level": "HIGH",
        "enforcement": "PERMISSION_CHECK",
    },
    {
        "policy_id": "OBS-003",
        "name": "observability_read_only_flag",
        "description": "All responses include read_only: true in meta",
        "authority_required": None,
        "risk_level": "MEDIUM",
        "enforcement": "RESPONSE_ATTRIBUTE",
    },
]

# ── Safety Policies ──

SAFETY_POLICIES = [
    {
        "policy_id": "SAFE-001",
        "name": "bounded_memory_enforcement",
        "description": "All containers must use bounded deques (maxlen)",
        "authority_required": None,
        "risk_level": "CRITICAL",
        "enforcement": "ARCHITECTURAL",
    },
    {
        "policy_id": "SAFE-002",
        "name": "exception_safe_processing",
        "description": "All signal processing must be wrapped in try/except",
        "authority_required": None,
        "risk_level": "HIGH",
        "enforcement": "ARCHITECTURAL",
    },
    {
        "policy_id": "SAFE-003",
        "name": "max_orchestration_depth",
        "description": "Engine enforces maximum orchestration depth (100000)",
        "authority_required": None,
        "risk_level": "MEDIUM",
        "enforcement": "HARD_CAP",
    },
]

# ── Governance Boundary Policies ──

GOVERNANCE_POLICIES = [
    {
        "policy_id": "GOV-001",
        "name": "no_erp_mutation",
        "description": "Operational runtime must not mutate ERP state",
        "authority_required": None,
        "risk_level": "CRITICAL",
        "enforcement": "ARCHITECTURAL",
    },
    {
        "policy_id": "GOV-002",
        "name": "no_execution_authority",
        "description": "Operational runtime must not execute write operations",
        "authority_required": None,
        "risk_level": "CRITICAL",
        "enforcement": "ARCHITECTURAL",
    },
    {
        "policy_id": "GOV-003",
        "name": "simulation_before_execution",
        "description": "Governance operations must simulate before executing (policy only, no enforcement yet)",
        "authority_required": "GovernanceAdmin",
        "risk_level": "HIGH",
        "enforcement": "DECLARATIVE_ONLY",
    },
    {
        "policy_id": "GOV-004",
        "name": "multi_signature_required",
        "description": "Critical operations may require multi-signature approval (policy only, no enforcement yet)",
        "authority_required": "MultiSignature",
        "risk_level": "CRITICAL",
        "enforcement": "DECLARATIVE_ONLY",
    },
]

# ── All Policies ──

ALL_POLICIES = (
    REPLAY_POLICIES +
    OBSERVABILITY_POLICIES +
    SAFETY_POLICIES +
    GOVERNANCE_POLICIES
)


def get_policy(policy_id: str) -> Any:
    """Get a specific policy by ID."""
    for policy in ALL_POLICIES:
        if policy["policy_id"] == policy_id:
            return policy
    return None


def get_all_policies() -> List[Dict[str, Any]]:
    """Get all registered policies."""
    return list(ALL_POLICIES)


def get_policies_by_risk(risk_level: str) -> List[Dict[str, Any]]:
    """Filter policies by risk level."""
    return [p for p in ALL_POLICIES if p["risk_level"] == risk_level]


def get_policies_by_enforcement(enforcement: str) -> List[Dict[str, Any]]:
    """Filter policies by enforcement type."""
    return [p for p in ALL_POLICIES if p["enforcement"] == enforcement]


def evaluate_policy(policy: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically evaluate a policy against a context.

    This is a DECLARATIVE evaluation — it does NOT enforce anything.
    It returns the policy's decision based on the context.

    Returns:
        {
            "policy_id": str,
            "allowed": bool,
            "reason": str,
            "authority_required": str or None,
        }
    """
    policy_id = policy["policy_id"]
    enforcement = policy["enforcement"]

    # Always-blocked policies
    if enforcement == "ALWAYS_BLOCKED":
        return {
            "policy_id": policy_id,
            "allowed": False,
            "reason": f"Policy {policy_id}: {policy['description']}",
            "authority_required": policy.get("authority_required"),
        }

    # Method restriction policies
    if enforcement == "METHOD_RESTRICTION":
        method = context.get("method", "GET").upper()
        if method != "GET":
            return {
                "policy_id": policy_id,
                "allowed": False,
                "reason": f"Policy {policy_id}: only GET allowed",
                "authority_required": policy.get("authority_required"),
            }
        return {
            "policy_id": policy_id,
            "allowed": True,
            "reason": f"Policy {policy_id}: GET allowed",
            "authority_required": None,
        }

    # Permission check policies
    if enforcement == "PERMISSION_CHECK":
        user_authorities = context.get("authorities", [])
        required = policy.get("authority_required")
        if required and required not in user_authorities:
            return {
                "policy_id": policy_id,
                "allowed": False,
                "reason": f"Policy {policy_id}: requires {required}",
                "authority_required": required,
            }
        return {
            "policy_id": policy_id,
            "allowed": True,
            "reason": f"Policy {policy_id}: authority satisfied",
            "authority_required": required,
        }

    # Response attribute policies
    if enforcement == "RESPONSE_ATTRIBUTE":
        return {
            "policy_id": policy_id,
            "allowed": True,
            "reason": f"Policy {policy_id}: response attribute enforced",
            "authority_required": None,
        }

    # Architectural policies (always allowed — enforced by architecture)
    if enforcement == "ARCHITECTURAL":
        return {
            "policy_id": policy_id,
            "allowed": True,
            "reason": f"Policy {policy_id}: enforced by architecture",
            "authority_required": None,
        }

    # Declarative-only policies (no enforcement yet)
    if enforcement == "DECLARATIVE_ONLY":
        return {
            "policy_id": policy_id,
            "allowed": True,
            "reason": f"Policy {policy_id}: declarative (not enforced yet)",
            "authority_required": policy.get("authority_required"),
        }

    # Hard cap policies
    if enforcement == "HARD_CAP":
        return {
            "policy_id": policy_id,
            "allowed": True,
            "reason": f"Policy {policy_id}: hard cap enforced",
            "authority_required": None,
        }

    return {
        "policy_id": policy_id,
        "allowed": False,
        "reason": f"Unknown enforcement type: {enforcement}",
        "authority_required": None,
    }
