"""
Phase 5B.1 (v2.0 Hardened) — Simulation Plan Builder.

GOVERNANCE LAYER OUTPUT PROCESSOR — STRICTLY SEPARATED FROM SIMULATION.
Converts governance DecisionResult into structured simulation blueprints.

Pipeline:
1. Receive DecisionResult from Governance Layer (Phase 5B.0)
2. Extract action intent, risk, policy context
3. Build hypothetical step-by-step simulation blueprint
4. Return immutable SimulationPlan

RESPONSIBILITY: Plan specification only.
NOT responsible for: Modeling, execution, or decision-making.
NO execution logic. NO side effects. Deterministic output.
"""
from typing import Any, Dict, List
from core.operations.execution.models import SimulationPlan, SimulationStep
from core.operations.governance.models import DecisionResult


SIMULATION_PLAN_BUILDER_VERSION = "2.0.0"

# Action type → hypothetical step definitions for simulation modeling only
ACTION_SIMULATION_TEMPLATES = {
    "replay_execute": [
        {"phase": "validate", "description": "[SIMULATION] Would validate replay session exists"},
        {"phase": "inspect_events", "description": "[SIMULATION] Would inspect replay events from session"},
        {"phase": "checkpoint_estimation", "description": "[SIMULATION] Would estimate pre-execution state checkpoint"},
        {"phase": "simulate_events", "description": "[SIMULATION] Would simulate replay event processing order"},
        {"phase": "verify_integrity", "description": "[SIMULATION] Would verify replay execution integrity"},
    ],
    "replay_start": [
        {"phase": "initialize", "description": "[SIMULATION] Would initialize replay session parameters"},
        {"phase": "set_origin", "description": "[SIMULATION] Would set replay start tick"},
        {"phase": "prepare", "description": "[SIMULATION] Would prepare replay environment"},
    ],
    "replay_pause": [
        {"phase": "snapshot", "description": "[SIMULATION] Would capture current replay state"},
        {"phase": "halt_modeling", "description": "[SIMULATION] Would pause replay modeling"},
    ],
    "replay_step": [
        {"phase": "safety_check", "description": "[SIMULATION] Would verify step forward is safe"},
        {"phase": "advance_tick", "description": "[SIMULATION] Would advance to next tick position"},
    ],
    "inventory_dispatch": [
        {"phase": "availability_check", "description": "[SIMULATION] Would verify sufficient stock available"},
        {"phase": "allocation_model", "description": "[SIMULATION] Would model inventory batch allocation"},
        {"phase": "quantity_estimate", "description": "[SIMULATION] Would estimate stock quantity changes"},
        {"phase": "accounting_estimate", "description": "[SIMULATION] Would estimate accounting journal entry"},
        {"phase": "completion_marker", "description": "[SIMULATION] Would mark dispatch as complete"},
    ],
    "inventory_receive": [
        {"phase": "receipt_check", "description": "[SIMULATION] Would validate purchase receipt"},
        {"phase": "batch_addition_model", "description": "[SIMULATION] Would model new inventory batch addition"},
        {"phase": "stock_estimate", "description": "[SIMULATION] Would estimate stock quantity change"},
        {"phase": "accounting_estimate", "description": "[SIMULATION] Would estimate accounting journal entry"},
    ],
    "erp_create_product": [
        {"phase": "validation", "description": "[SIMULATION] Would validate product data"},
        {"phase": "duplicate_check", "description": "[SIMULATION] Would check for duplicate barcode/SKU"},
        {"phase": "creation_model", "description": "[SIMULATION] Would model product record creation"},
    ],
    "system_rollback": [
        {"phase": "identification", "description": "[SIMULATION] Would identify transaction to roll back"},
        {"phase": "safety_analysis", "description": "[SIMULATION] Would analyze rollback safety"},
        {"phase": "reversal_model", "description": "[SIMULATION] Would model journal entry reversal"},
        {"phase": "restoration_estimate", "description": "[SIMULATION] Would estimate pre-transaction restoration"},
    ],
    "system_recover": [
        {"phase": "damage_assessment", "description": "[SIMULATION] Would assess system damage scope"},
        {"phase": "checkpoint_lookup", "description": "[SIMULATION] Would locate recovery checkpoint"},
        {"phase": "recovery_model", "description": "[SIMULATION] Would model recovery procedure execution"},
    ],
    "observability_read": [
        {"phase": "authentication", "description": "[SIMULATION] Would authenticate API request"},
        {"phase": "authorization", "description": "[SIMULATION] Would validate read permissions"},
        {"phase": "data_query", "description": "[SIMULATION] Would query observability data"},
        {"phase": "response_format", "description": "[SIMULATION] Would format standardized response"},
    ],
}


def build_simulation_plan(decision: DecisionResult) -> SimulationPlan:
    """Build a simulation blueprint from a governance DecisionResult.

    PURE SPECIFICATION — not executable in any runtime context.
    All descriptions use subjunctive mood to indicate hypothetical nature.

    Args:
        decision: The DecisionResult from Governance Layer (Phase 5B.0).

    Returns:
        An immutable SimulationPlan with deterministic hypothetical step sequence.
    """
    audit = decision.audit_entry
    action_type = audit.get("action_type", "unknown")
    domain = audit.get("domain", "unknown")
    decision_value = decision.decision

    steps = _build_hypothetical_steps(action_type, decision_value)

    return SimulationPlan(
        decision_id=decision.action_id,
        action_type=action_type,
        domain=domain,
        risk_level=audit.get("risk_level", "NONE"),
        risk_score=audit.get("risk_score", 0),
        policy_trace={
            "policy_compliance": audit.get("policy_compliance", "NOT_EVALUATED"),
            "policy_violations": audit.get("policy_violations", []),
        },
        steps=steps,
        metadata={
            "builder_version": SIMULATION_PLAN_BUILDER_VERSION,
            "governance_decision": decision_value,
            "source": audit.get("source", "unknown"),
            "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
        },
    )


def _build_hypothetical_steps(action_type: str, decision: str) -> List[SimulationStep]:
    """Build deterministic hypothetical step list for an action type.

    If the decision is BLOCKED, returns a single step indicating modeling is blocked.
    """
    if decision == "BLOCKED":
        return [
            SimulationStep(
                step_id="step_blocked",
                step_type="blocked",
                description=f"[SIMULATION] Action {action_type} is BLOCKED — no modeling possible",
                modeled_status="SKIPPED",
                modeled_output={
                    "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
                    "reason": "BLOCKED by governance enforcement layer",
                    "applied": False,
                },
            )
        ]

    template = ACTION_SIMULATION_TEMPLATES.get(action_type, [])
    if not template:
        return [
            SimulationStep(
                step_id="step_unknown",
                step_type="unknown",
                description=f"[SIMULATION] No simulation template for action type: {action_type}",
                modeled_status="PENDING",
            )
        ]

    return [
        SimulationStep(
            step_id=f"step_{i}_{s['phase']}",
            step_type=s["phase"],
            description=s["description"],
            modeled_status="PENDING",
        )
        for i, s in enumerate(template)
    ]


def get_supported_simulation_templates() -> Dict[str, List[Dict[str, str]]]:
    """Return all registered simulation templates."""
    return dict(ACTION_SIMULATION_TEMPLATES)
