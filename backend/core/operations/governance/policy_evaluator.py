"""
Phase 5B.0 — Policy Evaluation Engine Hook.

Connects intercepted actions to the Phase 5A.5.5 policy registry.
Evaluates actions against all relevant policies deterministically.

Pipeline:
1. Receive ActionIntent
2. Map action domain to relevant policies
3. Evaluate each policy against the action
4. Aggregate results into PolicyEvaluationResult

Deterministic evaluation. No policy mutation. No side effects.
"""
from typing import Any, Dict, List
from core.operations.governance.models import ActionIntent, PolicyEvaluationResult
from core.operations.policy.registry import (
    get_all_policies, evaluate_policy,
    get_policies_by_enforcement,
)


POLICY_EVALUATOR_VERSION = "1.0.0"

# Action domain → relevant policy IDs
DOMAIN_POLICY_MAP = {
    "replay_operations": [],
    "observability_read": ["OBS-001", "OBS-002", "OBS-003"],
    "erp_mutation": ["GOV-001", "GOV-002"],
    "domain_operations": ["GOV-001", "GOV-002"],
    "system_operations": ["GOV-001", "GOV-002"],
    "security_operations": ["GOV-001", "GOV-002"],
    "governance_operations": ["GOV-003", "GOV-004"],
}


def evaluate(action: ActionIntent) -> PolicyEvaluationResult:
    """Evaluate an action against all relevant governance policies.

    Args:
        action: The ActionIntent to evaluate.

    Returns:
        A PolicyEvaluationResult with compliance status and violated rules.
    """
    domain = action.domain
    policy_ids = DOMAIN_POLICY_MAP.get(domain, [])
    all_policies = get_all_policies()
    relevant_policies = [p for p in all_policies if p["policy_id"] in policy_ids]



    violated_rules: List[str] = []
    overall_compliance = "PASS"

    for policy in relevant_policies:
        policy_context = _build_policy_context(action)
        result = evaluate_policy(policy, policy_context)
        if not result.get("allowed", True):
            violated_rules.append(
                f"{policy['policy_id']}: {policy['name']} — {result.get('reason', 'denied')}"
            )

    if violated_rules:
        overall_compliance = "FAIL"

    return PolicyEvaluationResult(
        policy_id="|".join(p["policy_id"] for p in relevant_policies) if relevant_policies else "NONE",
        policy_name=f"Domain: {domain}",
        compliance=overall_compliance,
        violated_rules=violated_rules,
        metadata={
            "evaluator_version": POLICY_EVALUATOR_VERSION,
            "domain": domain,
            "action_type": action.action_type,
            "policies_evaluated": len(relevant_policies),
        },
    )


def _build_policy_context(action: ActionIntent) -> Dict[str, Any]:
    """Build a policy evaluation context from an ActionIntent."""
    context: Dict[str, Any] = {
        "action_type": action.action_type,
        "domain": action.domain,
        "source": action.source,
        "method": action.context.get("method", "GET"),
    }
    # API and UI sources imply authenticated users with IsAuthenticated authority
    if action.source in ("api", "ui"):
        context["authorities"] = ["IsAuthenticated"]
    return context
