"""
Phase 5A.5.5 — Authority Classification Matrix.

Defines deterministic authority classifications, risk levels,
and approval requirements for all operational domains.

NO execution capability. Declarative matrix only.
"""
from typing import Any, Dict, List


AUTHORITY_MATRIX_VERSION = "1.0.0"


# ── Authority Classifications ──

AUTHORITY_CLASSIFICATIONS = [
    {
        "authority_id": "AUTH-OBSERVER",
        "name": "Observer",
        "risk_level": "NONE",
        "allowed_domains": ["observability_read"],
        "description": "Read-only access to observability data",
        "requires_approval": False,
        "simulation_required": False,
    },
    {
        "authority_id": "AUTH-ANALYST",
        "name": "Analyst",
        "risk_level": "LOW",
        "allowed_domains": ["observability_read", "replay_view", "forensic_analysis"],
        "description": "Observability + replay viewing + forensic analysis",
        "requires_approval": False,
        "simulation_required": False,
    },
    {
        "authority_id": "AUTH-AUDITOR",
        "name": "Auditor",
        "risk_level": "LOW",
        "allowed_domains": ["observability_read", "replay_view", "audit_log_view"],
        "description": "Observability + replay + audit log access",
        "requires_approval": False,
        "simulation_required": False,
    },
    {
        "authority_id": "AUTH-OBSERVABILITY-ADMIN",
        "name": "ObservabilityAdmin",
        "risk_level": "MEDIUM",
        "allowed_domains": [
            "observability_read", "replay_view", "forensic_analysis",
            "observability_config", "replay_config",
        ],
        "description": "Full observability configuration access",
        "requires_approval": False,
        "simulation_required": False,
    },
]

# ── Operational Risk Levels ──

RISK_LEVELS = {
    "NONE": {
        "score": 0,
        "description": "No operational risk — read-only operations",
        "requires_approval": False,
        "requires_simulation": False,
    },
    "LOW": {
        "score": 1,
        "description": "Low risk — config changes with no ERP impact",
        "requires_approval": False,
        "requires_simulation": False,
    },
    "MEDIUM": {
        "score": 2,
        "description": "Medium risk — operational config changes",
        "requires_approval": True,
        "requires_simulation": True,
    },
    "HIGH": {
        "score": 3,
        "description": "High risk — operational state changes",
        "requires_approval": True,
        "requires_simulation": True,
    },
    "CRITICAL": {
        "score": 4,
        "description": "Critical risk — ERP mutation or execution",
        "requires_approval": True,
        "requires_simulation": True,
    },
}

# ── Approval Requirement Map ──

APPROVAL_REQUIREMENTS = {
    "single_signature": {
        "risk_levels": ["NONE", "LOW"],
        "description": "One authorized user approval required",
    },
    "dual_signature": {
        "risk_levels": ["MEDIUM"],
        "description": "Two authorized users approval required",
    },
    "multi_signature": {
        "risk_levels": ["HIGH", "CRITICAL"],
        "description": "Three or more authorized users approval required",
    },
}

# ── Domain-to-Authority Mapping ──

DOMAIN_AUTHORITY_MAP = {
    "observability_read": ["AUTH-OBSERVER", "AUTH-ANALYST", "AUTH-AUDITOR", "AUTH-OBSERVABILITY-ADMIN"],
    "replay_view": ["AUTH-ANALYST", "AUTH-AUDITOR", "AUTH-OBSERVABILITY-ADMIN"],
    "forensic_analysis": ["AUTH-ANALYST", "AUTH-OBSERVABILITY-ADMIN"],
    "audit_log_view": ["AUTH-AUDITOR", "AUTH-OBSERVABILITY-ADMIN"],
    "observability_config": ["AUTH-OBSERVABILITY-ADMIN"],
    "replay_config": ["AUTH-OBSERVABILITY-ADMIN"],
}


def get_authority(authority_id: str) -> Any:
    """Get authority classification by ID."""
    for auth in AUTHORITY_CLASSIFICATIONS:
        if auth["authority_id"] == authority_id:
            return auth
    return None


def get_authorities_for_domain(domain: str) -> List[Dict[str, Any]]:
    """Get all authorities that can access a domain."""
    auth_ids = DOMAIN_AUTHORITY_MAP.get(domain, [])
    return [a for a in AUTHORITY_CLASSIFICATIONS if a["authority_id"] in auth_ids]


def get_risk_level(level: str) -> Dict[str, Any]:
    """Get risk level details."""
    return RISK_LEVELS.get(level, {"score": -1, "description": "Unknown risk level"})


def check_authority_for_action(authority_id: str, domain: str) -> Dict[str, Any]:
    """Check if an authority can access a domain.

    Returns a deterministic evaluation result.
    """
    authority = get_authority(authority_id)
    if authority is None:
        return {"allowed": False, "reason": f"Unknown authority: {authority_id}"}
    allowed_domains = authority.get("allowed_domains", [])
    if domain not in allowed_domains:
        return {
            "allowed": False,
            "reason": f"Authority {authority_id} not allowed for domain {domain}",
            "required_authorities": get_authorities_for_domain(domain),
        }
    return {
        "allowed": True,
        "reason": f"Authority {authority_id} allowed for domain {domain}",
        "risk_level": authority["risk_level"],
    }
