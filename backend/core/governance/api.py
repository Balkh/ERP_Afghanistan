"""
Governance Discovery API — Phase 6.

Exposes governance introspection without adding runtime overhead.
Provides auto-generated documentation and policy maps.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.api")

API_VERSION = "1.0.0"


@dataclass
class GovernanceDocEntry:
    """Single entry in auto-generated governance documentation."""
    type: str  # policy | invariant | feature_gate | readiness_check | ui_rule
    id: str
    description: str
    domain: str = ""
    severity: str = ""
    tier: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class GovernanceDocumentation:
    generated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    policies: List[GovernanceDocEntry] = field(default_factory=list)
    invariants: List[GovernanceDocEntry] = field(default_factory=list)
    feature_gates: List[GovernanceDocEntry] = field(default_factory=list)
    readiness_checks: List[GovernanceDocEntry] = field(default_factory=list)
    ui_rules: List[GovernanceDocEntry] = field(default_factory=list)


def generate_documentation(kernel: GovernanceKernel) -> GovernanceDocumentation:
    """Auto-generate full governance documentation from registered items."""
    doc = GovernanceDocumentation()

    for pid, (rule, meta) in kernel.policies.list_all().items():
        doc.policies.append(GovernanceDocEntry(
            type="policy",
            id=pid,
            description=rule.description,
            domain=meta.get("domain", ""),
            tier=rule.tier,
            details={"check_fn": rule.check_fn.__name__},
        ))

    for iid, (checker, meta) in kernel.invariants.list_all().items():
        doc.invariants.append(GovernanceDocEntry(
            type="invariant",
            id=iid,
            description=meta.get("description", ""),
            domain=meta.get("domain", ""),
            severity=meta.get("severity", ""),
            tier=meta.get("priority", ""),
        ))

    for fid in kernel.feature_gates.list_all():
        doc.feature_gates.append(GovernanceDocEntry(
            type="feature_gate",
            id=fid,
            description=f"Feature gate: {fid}",
        ))

    readiness = kernel.check_readiness()
    for check in readiness.get("checks", []):
        doc.readiness_checks.append(GovernanceDocEntry(
            type="readiness_check",
            id=check.get("name", "unknown"),
            description=check.get("message", ""),
            details={"status": check.get("status", "")},
        ))

    for rid, rule in kernel.ui_rules.list_all().items():
        doc.ui_rules.append(GovernanceDocEntry(
            type="ui_rule",
            id=rid,
            description=rule.description,
            severity=rule.severity,
        ))

    return doc


def discovery_response(kernel: GovernanceKernel) -> dict:
    """Produce a full governance discovery response for the API."""
    doc = generate_documentation(kernel)
    health = kernel.health()

    return {
        "kernel_version": health["kernel_version"],
        "environment": health["environment_profile"],
        "summary": {
            "policies": len(doc.policies),
            "invariants": len(doc.invariants),
            "feature_gates": len(doc.feature_gates),
            "readiness_checks": len(doc.readiness_checks),
            "ui_rules": len(doc.ui_rules),
        },
        "failsafe_mode": health["failsafe_mode"],
        "degraded_tiers": health["degraded_tiers"],
        "policies": [
            {"id": p.id, "domain": p.domain, "tier": p.tier, "description": p.description}
            for p in doc.policies
        ],
        "invariants": [
            {"id": i.id, "domain": i.domain, "severity": i.severity, "description": i.description}
            for i in doc.invariants
        ],
        "feature_gates": doc.feature_gates,
        "ui_rules": [
            {"id": u.id, "severity": u.severity, "description": u.description}
            for u in doc.ui_rules
        ],
    }
