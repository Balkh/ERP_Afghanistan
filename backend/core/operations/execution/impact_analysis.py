"""
Phase 5B.1 (v2.0 Hardened) — Impact Analysis.

STRICTLY DESCRIPTIVE ESTIMATION — NO DECISION-MAKING AUTHORITY.
Estimates hypothetical system effects of a simulated plan WITHOUT
making any system changes. All estimates are deterministic lookups —
no learning, no runtime adaptation, no decision influence.

Pipeline:
1. Receive SimulationPlan + SimulationOutcome (from Simulation Engine)
2. Look up estimated financial/inventory/workflow effects
3. Map hypothetical risk propagation across domains
4. Return ImpactAnalysisReport

RESPONSIBILITY: Informational estimation only.
NOT responsible for: Decision-making, execution recommendations, or governance.
"""
from typing import Any, Dict, List
from core.operations.execution.models import SimulationPlan, SimulationOutcome, ImpactAnalysisReport


IMPACT_ANALYSIS_VERSION = "2.0.0"

# Action type → hypothetical financial estimates
FINANCIAL_ESTIMATES = {
    "replay_execute": {"type": "read_only", "severity": "none", "description": "Hypothetical: No financial impact (read-only replay)"},
    "replay_start": {"type": "read_only", "severity": "none", "description": "Hypothetical: No financial impact"},
    "replay_pause": {"type": "read_only", "severity": "none", "description": "Hypothetical: No financial impact"},
    "replay_step": {"type": "read_only", "severity": "none", "description": "Hypothetical: No financial impact"},
    "inventory_dispatch": {"type": "financial_mutation", "severity": "high", "description": "Hypothetical: Would create COGS journal entry"},
    "inventory_receive": {"type": "financial_mutation", "severity": "high", "description": "Hypothetical: Would create inventory journal entry"},
    "erp_create_product": {"type": "data_mutation", "severity": "low", "description": "Hypothetical: Would create product record"},
    "system_rollback": {"type": "financial_mutation", "severity": "critical", "description": "Hypothetical: Would reverse journal entries"},
    "system_recover": {"type": "financial_mutation", "severity": "critical", "description": "Hypothetical: Would execute recovery procedures"},
    "observability_read": {"type": "read_only", "severity": "none", "description": "Hypothetical: No financial impact (read-only query)"},
}

INVENTORY_ESTIMATES = {
    "replay_execute": {"type": "read_only", "severity": "none", "description": "Hypothetical: No inventory impact"},
    "replay_start": {"type": "read_only", "severity": "none", "description": "Hypothetical: No inventory impact"},
    "inventory_dispatch": {"type": "inventory_mutation", "severity": "high", "description": "Hypothetical: Would decrease stock by allocated quantity"},
    "inventory_receive": {"type": "inventory_mutation", "severity": "high", "description": "Hypothetical: Would increase stock by received quantity"},
    "erp_create_product": {"type": "data_mutation", "severity": "low", "description": "Hypothetical: Would create product catalog entry"},
    "system_rollback": {"type": "inventory_mutation", "severity": "critical", "description": "Hypothetical: Would revert inventory changes"},
    "observability_read": {"type": "read_only", "severity": "none", "description": "Hypothetical: No inventory impact"},
}

WORKFLOW_ESTIMATES = {
    "replay_execute": {"type": "workflow_mutation", "severity": "medium", "description": "Hypothetical: Would create replay session events"},
    "replay_start": {"type": "workflow_mutation", "severity": "low", "description": "Hypothetical: Would initialize replay session"},
    "replay_pause": {"type": "workflow_mutation", "severity": "low", "description": "Hypothetical: Would pause replay session"},
    "replay_step": {"type": "workflow_mutation", "severity": "low", "description": "Hypothetical: Would advance replay tick"},
    "inventory_dispatch": {"type": "workflow_mutation", "severity": "high", "description": "Hypothetical: Would complete dispatch workflow"},
    "inventory_receive": {"type": "workflow_mutation", "severity": "high", "description": "Hypothetical: Would complete receive workflow"},
    "system_rollback": {"type": "workflow_mutation", "severity": "critical", "description": "Hypothetical: Would execute rollback workflow"},
    "system_recover": {"type": "workflow_mutation", "severity": "critical", "description": "Hypothetical: Would execute recovery workflow"},
    "observability_read": {"type": "read_only", "severity": "none", "description": "Hypothetical: No workflow impact"},
}

DOMAIN_PROPAGATION = {
    "replay_execute": ["replay", "timeline"],
    "replay_start": ["replay"],
    "replay_pause": ["replay"],
    "replay_step": ["replay"],
    "inventory_dispatch": ["inventory", "accounting", "sales"],
    "inventory_receive": ["inventory", "accounting", "purchases"],
    "erp_create_product": ["inventory"],
    "system_rollback": ["accounting", "inventory", "payments"],
    "system_recover": ["accounting", "inventory", "payments", "replay"],
    "observability_read": [],
}


def estimate_impact(plan: SimulationPlan, outcome: SimulationOutcome) -> ImpactAnalysisReport:
    """Estimate the hypothetical impact of a simulated plan.

    Purely descriptive — no decision influence or execution recommendation.

    Args:
        plan: The SimulationPlan that was modeled.
        outcome: The SimulationOutcome from the Simulation Engine.

    Returns:
        An ImpactAnalysisReport with estimated effects per domain.
    """
    action_type = plan.action_type

    financial = FINANCIAL_ESTIMATES.get(action_type, {"type": "unknown", "severity": "unknown", "description": "Unknown hypothetical impact"})
    inventory = INVENTORY_ESTIMATES.get(action_type, {"type": "unknown", "severity": "unknown", "description": "Unknown hypothetical impact"})
    workflow = WORKFLOW_ESTIMATES.get(action_type, {"type": "unknown", "severity": "unknown", "description": "Unknown hypothetical impact"})
    domains = DOMAIN_PROPAGATION.get(action_type, [])
    risk_propagation = _build_risk_propagation(plan.risk_level, domains)

    return ImpactAnalysisReport(
        plan_id=plan.plan_id,
        financial_estimate=financial,
        inventory_estimate=inventory,
        workflow_estimate=workflow,
        domains_affected=domains,
        risk_propagation=risk_propagation,
        metadata={
            "analysis_version": IMPACT_ANALYSIS_VERSION,
            "action_type": action_type,
            "modeling_clean": outcome.all_modeled_cleanly,
            "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
        },
    )


def _build_risk_propagation(risk_level: str, domains: List[str]) -> List[Dict[str, Any]]:
    """Build deterministic hypothetical risk propagation map."""
    return [
        {
            "domain": domain,
            "hypothetical_risk_level": risk_level,
            "propagation_type": "direct" if i < 2 else "secondary",
        }
        for i, domain in enumerate(domains)
    ]
