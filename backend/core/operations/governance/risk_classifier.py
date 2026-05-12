"""
Phase 5B.0 — Risk Classification Engine.

Assigns deterministic risk levels to actions before any execution consideration.

Risk Levels (immutable from Phase 5A.5.5):
    NONE (0) — Read-only operations
    LOW (1) — Config changes with no ERP impact
    MEDIUM (2) — Operational config changes
    HIGH (3) — Operational state changes
    CRITICAL (4) — ERP mutation or execution

Deterministic scoring. No ML. No runtime adaptation.
"""
from typing import Any, Dict
from core.operations.governance.models import ActionIntent, RiskClassificationResult
from core.operations.governance.interceptor import ACTION_TYPE_REGISTRY
from core.operations.policy.authority import get_risk_level




RISK_CLASSIFIER_VERSION = "1.0.0"

# Domain → base risk score mapping
DOMAIN_RISK_SCORES = {
    "observability_read": 0,
    "replay_operations": 2,
    "domain_operations": 3,
    "erp_mutation": 4,
    "system_operations": 4,
    "security_operations": 4,
    "governance_operations": 3,
}

# Action type → risk score override (higher specificity takes precedence)
ACTION_RISK_OVERRIDES = {
    "replay_execute": 4,
    "replay_start": 2,
    "replay_pause": 0,
    "replay_resume": 0,
    "replay_step": 0,
    "inventory_dispatch": 4,
    "inventory_receive": 4,
    "inventory_transfer": 3,
    "inventory_adjust": 3,
    "accounting_journal_entry": 4,
    "system_rollback": 4,
    "system_recover": 4,
}


def classify(action: ActionIntent) -> RiskClassificationResult:
    """Classify the risk level of an action.

    Deterministic — same action always produces same risk classification.

    Args:
        action: The ActionIntent to classify.

    Returns:
        A RiskClassificationResult with risk level and score.
    """
    # Check action-specific override first
    if action.action_type in ACTION_RISK_OVERRIDES:
        base_score = ACTION_RISK_OVERRIDES[action.action_type]
    else:
        base_score = DOMAIN_RISK_SCORES.get(action.domain, 1)

    # Forbidden domains get maximum risk
    if action.domain in ("erp_mutation", "system_operations", "security_operations", "domain_operations"):
        base_score = max(base_score, 4)

    risk_level = _score_to_level(base_score)
    risk_info = get_risk_level(risk_level)

    justifications = []
    if action.action_type in ACTION_RISK_OVERRIDES:
        justifications.append(f"Action-specific override: {action.action_type} → score {base_score}")
    else:
        justifications.append(f"Domain-based score: {action.domain} → score {base_score}")

    if action.domain in ("erp_mutation", "system_operations", "security_operations", "domain_operations"):
        justifications.append("Action domain is forbidden")

    return RiskClassificationResult(
        risk_level=risk_level,
        risk_score=base_score,
        justification="; ".join(justifications),
        metadata={
            "classifier_version": RISK_CLASSIFIER_VERSION,
            "domain": action.domain,
            "action_type": action.action_type,
            "source": action.source,
        },
    )


def _score_to_level(score: int) -> str:
    """Convert a risk score to a risk level string."""
    if score >= 4:
        return "CRITICAL"
    elif score >= 3:
        return "HIGH"
    elif score >= 2:
        return "MEDIUM"
    elif score >= 1:
        return "LOW"
    return "NONE"
