"""
Phase 5B.1 — Execution Impact Analyzer.

Predicts system impact of execution WITHOUT making any system changes.
All estimates are deterministic — no learning, no adaptation.

Pipeline:
1. Receive ExecutionPlan + SimulationResult
2. Estimate financial/inventory/workflow impact
3. Map risk propagation across domains
4. Return ImpactReport

No system mutation. Deterministic estimation only.
"""
from typing import Any, Dict, List
from core.operations.execution.models import ExecutionPlan, SimulationResult, ImpactReport


IMPACT_ANALYZER_VERSION = "1.0.0"

# Action type → estimated impact mappings
FINANCIAL_IMPACT_MAP = {
    "replay_execute": {"type": "read_only", "severity": "none", "description": "No financial impact (read-only replay)"},
    "replay_start": {"type": "read_only", "severity": "none", "description": "No financial impact"},
    "replay_pause": {"type": "read_only", "severity": "none", "description": "No financial impact"},
    "replay_step": {"type": "read_only", "severity": "none", "description": "No financial impact"},
    "inventory_dispatch": {"type": "financial_mutation", "severity": "high", "description": "Would create COGS journal entry"},
    "inventory_receive": {"type": "financial_mutation", "severity": "high", "description": "Would create inventory journal entry"},
    "erp_create_product": {"type": "data_mutation", "severity": "low", "description": "Would create product record"},
    "system_rollback": {"type": "financial_mutation", "severity": "critical", "description": "Would reverse journal entries"},
    "system_recover": {"type": "financial_mutation", "severity": "critical", "description": "Would execute recovery procedures"},
    "observability_read": {"type": "read_only", "severity": "none", "description": "No financial impact (read-only query)"},
}

INVENTORY_IMPACT_MAP = {
    "replay_execute": {"type": "read_only", "severity": "none", "description": "No inventory impact"},
    "replay_start": {"type": "read_only", "severity": "none", "description": "No inventory impact"},
    "inventory_dispatch": {"type": "inventory_mutation", "severity": "high", "description": "Would decrease stock by allocated quantity"},
    "inventory_receive": {"type": "inventory_mutation", "severity": "high", "description": "Would increase stock by received quantity"},
    "erp_create_product": {"type": "data_mutation", "severity": "low", "description": "Would create product catalog entry"},
    "system_rollback": {"type": "inventory_mutation", "severity": "critical", "description": "Would revert inventory changes"},
    "observability_read": {"type": "read_only", "severity": "none", "description": "No inventory impact"},
}

WORKFLOW_IMPACT_MAP = {
    "replay_execute": {"type": "workflow_mutation", "severity": "medium", "description": "Would create replay session events"},
    "replay_start": {"type": "workflow_mutation", "severity": "low", "description": "Would initialize replay session"},
    "replay_pause": {"type": "workflow_mutation", "severity": "low", "description": "Would pause replay session"},
    "replay_step": {"type": "workflow_mutation", "severity": "low", "description": "Would advance replay tick"},
    "inventory_dispatch": {"type": "workflow_mutation", "severity": "high", "description": "Would complete dispatch workflow"},
    "inventory_receive": {"type": "workflow_mutation", "severity": "high", "description": "Would complete receive workflow"},
    "system_rollback": {"type": "workflow_mutation", "severity": "critical", "description": "Would execute rollback workflow"},
    "system_recover": {"type": "workflow_mutation", "severity": "critical", "description": "Would execute recovery workflow"},
    "observability_read": {"type": "read_only", "severity": "none", "description": "No workflow impact"},
}

DOMAIN_PROPAGATION_MAP = {
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


def analyze(plan: ExecutionPlan, simulation: SimulationResult) -> ImpactReport:
    """Analyze the estimated impact of an execution plan.

    Args:
        plan: The ExecutionPlan to analyze.
        simulation: The SimulationResult from simulating the plan.

    Returns:
        An ImpactReport with estimated impact per domain.
    """
    action_type = plan.action_type

    financial = FINANCIAL_IMPACT_MAP.get(action_type, {"type": "unknown", "severity": "unknown", "description": "Unknown impact"})
    inventory = INVENTORY_IMPACT_MAP.get(action_type, {"type": "unknown", "severity": "unknown", "description": "Unknown impact"})
    workflow = WORKFLOW_IMPACT_MAP.get(action_type, {"type": "unknown", "severity": "unknown", "description": "Unknown impact"})
    domains = DOMAIN_PROPAGATION_MAP.get(action_type, [])
    risk_propagation = _build_risk_propagation(action_type, plan.risk_level, domains)

    return ImpactReport(
        plan_id=plan.plan_id,
        financial_impact=financial,
        inventory_impact=inventory,
        workflow_impact=workflow,
        domains_affected=domains,
        risk_propagation=risk_propagation,
        metadata={
            "analyzer_version": IMPACT_ANALYZER_VERSION,
            "action_type": action_type,
            "simulation_success": simulation.success,
        },
    )


def _build_risk_propagation(action_type: str, risk_level: str, domains: List[str]) -> List[Dict[str, Any]]:
    """Build deterministic risk propagation map."""
    return [
        {
            "domain": domain,
            "risk_level": risk_level,
            "propagation_type": "direct" if domain in domains[:2] else "secondary",
        }
        for domain in domains
    ]
