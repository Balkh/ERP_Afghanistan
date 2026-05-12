"""
Phase 5B.0 — Execution Decision Gate.

Final gate BEFORE any action proceeds to execution.

Decision types:
    BLOCKED — Action is forbidden and will not proceed
    SIMULATION_ONLY — Action may be simulated but not executed
    REQUIRE_APPROVAL — Action requires approval before execution
    SAFE_PASS — Action is safe to pass (no execution in this phase)

THIS PHASE DOES NOT EXECUTE ACTIONS.
All decisions result in BLOCK or simulation routing only.

Pipeline:
1. Receive ActionIntent + PolicyEvaluationResult + RiskClassificationResult
2. Apply decision rules
3. Return DecisionResult
4. (No execution occurs)
"""
from typing import Any, Dict
from core.operations.governance.models import (
    ActionIntent, PolicyEvaluationResult, RiskClassificationResult, DecisionResult,
)
FORBIDDEN_DOMAINS = {"erp_mutation", "system_operations", "security_operations", "domain_operations"}


DECISION_GATE_VERSION = "1.0.0"


def decide(
    action: ActionIntent,
    policy_result: PolicyEvaluationResult,
    risk_result: RiskClassificationResult,
) -> DecisionResult:
    """Make a final decision on an action.

    Args:
        action: The intercepted ActionIntent.
        policy_result: Policy evaluation result.
        risk_result: Risk classification result.

    Returns:
        A DecisionResult with decision type and reasoning.

    Raises:
        ValueError: If inputs are inconsistent.
    """
    if action.action_id is None:
        raise ValueError("Action must have a valid action_id")

    # Rule 1: Forbidden domain actions are always BLOCKED
    if action.domain in FORBIDDEN_DOMAINS:
        return DecisionResult(
            decision="BLOCKED",
            action_id=action.action_id,
            reasoning=(
                f"Action '{action.action_type}' is in the forbidden-action registry. "
                f"Risk level: {risk_result.risk_level}. "
                f"Policy compliance: {policy_result.compliance}."
            ),
            audit_entry=_build_audit_entry(action, policy_result, risk_result, "BLOCKED"),
            metadata={
                "gate_version": DECISION_GATE_VERSION,
                "reason_category": "forbidden_action",
            },
        )

    # Rule 2: Policy FAIL leads to BLOCKED
    if policy_result.compliance == "FAIL":
        return DecisionResult(
            decision="BLOCKED",
            action_id=action.action_id,
            reasoning=(
                f"Action '{action.action_type}' failed policy evaluation. "
                f"Violations: {policy_result.violated_rules}"
            ),
            audit_entry=_build_audit_entry(action, policy_result, risk_result, "BLOCKED"),
            metadata={
                "gate_version": DECISION_GATE_VERSION,
                "reason_category": "policy_violation",
            },
        )

    # Rule 3: CRITICAL risk actions are BLOCKED (no governance execution yet)
    if risk_result.risk_level == "CRITICAL":
        return DecisionResult(
            decision="BLOCKED",
            action_id=action.action_id,
            reasoning=(
                f"Action '{action.action_type}' has CRITICAL risk level. "
                f"Governance execution not available in current phase."
            ),
            audit_entry=_build_audit_entry(action, policy_result, risk_result, "BLOCKED"),
            metadata={
                "gate_version": DECISION_GATE_VERSION,
                "reason_category": "critical_risk_no_execution",
            },
        )

    # Rule 4: HIGH risk actions REQUIRE_APPROVAL (routed, not executed)
    if risk_result.risk_level == "HIGH":
        return DecisionResult(
            decision="REQUIRE_APPROVAL",
            action_id=action.action_id,
            reasoning=(
                f"Action '{action.action_type}' has HIGH risk. "
                f"Approval required before any execution consideration."
            ),
            audit_entry=_build_audit_entry(action, policy_result, risk_result, "REQUIRE_APPROVAL"),
            metadata={
                "gate_version": DECISION_GATE_VERSION,
                "reason_category": "high_risk_requires_approval",
            },
        )

    # Rule 5: MEDIUM risk actions are SIMULATION_ONLY
    if risk_result.risk_level == "MEDIUM":
        return DecisionResult(
            decision="SIMULATION_ONLY",
            action_id=action.action_id,
            reasoning=(
                f"Action '{action.action_type}' has MEDIUM risk. "
                f"Simulation-only routing (no execution)."
            ),
            audit_entry=_build_audit_entry(action, policy_result, risk_result, "SIMULATION_ONLY"),
            metadata={
                "gate_version": DECISION_GATE_VERSION,
                "reason_category": "medium_risk_simulation_only",
            },
        )

    # Rule 6: NONE/LOW risk actions are SAFE_PASS (no execution)
    return DecisionResult(
        decision="SAFE_PASS",
        action_id=action.action_id,
        reasoning=(
            f"Action '{action.action_type}' has {risk_result.risk_level} risk. "
            f"Safe to pass (no execution in current phase)."
        ),
        audit_entry=_build_audit_entry(action, policy_result, risk_result, "SAFE_PASS"),
        metadata={
            "gate_version": DECISION_GATE_VERSION,
            "reason_category": "safe_pass",
        },
    )


def _build_audit_entry(
    action: ActionIntent,
    policy_result: PolicyEvaluationResult,
    risk_result: RiskClassificationResult,
    decision: str,
) -> Dict[str, Any]:
    """Build an audit trail entry for the decision."""
    return {
        "action_id": action.action_id,
        "action_type": action.action_type,
        "domain": action.domain,
        "source": action.source,
        "decision": decision,
        "risk_level": risk_result.risk_level,
        "risk_score": risk_result.risk_score,
        "policy_compliance": policy_result.compliance,
        "policy_violations": policy_result.violated_rules,
        "simulated": True,
        "executed": False,
    }
