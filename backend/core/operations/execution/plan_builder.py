"""
Phase 5B.1 — Execution Plan Builder.

Converts governance DecisionResult into structured execution plans.
Defines hypothetical action sequences for simulation-only execution.

Pipeline:
1. Receive DecisionResult from Phase 5B.0
2. Extract action intent, risk, policy context
3. Build step-by-step execution plan
4. Return immutable ExecutionPlan

NO execution logic. NO side effects. Deterministic output.
"""
from typing import Any, Dict, List, Optional
from core.operations.execution.models import ExecutionPlan, ExecutionStep
from core.operations.governance.models import DecisionResult


PLAN_BUILDER_VERSION = "1.0.0"

# Action type → simulated step definitions
ACTION_STEP_TEMPLATES = {
    "replay_execute": [
        {"step_type": "validate_session", "description": "Validate replay session exists"},
        {"step_type": "load_events", "description": "Load replay events from session"},
        {"step_type": "checkpoint_state", "description": "Create pre-execution state checkpoint"},
        {"step_type": "execute_events", "description": "Execute replay events in order"},
        {"step_type": "verify_replay", "description": "Verify replay execution integrity"},
    ],
    "replay_start": [
        {"step_type": "initialize_session", "description": "Initialize replay session parameters"},
        {"step_type": "set_start_tick", "description": "Set replay start tick"},
        {"step_type": "prepare_environment", "description": "Prepare replay environment"},
    ],
    "replay_pause": [
        {"step_type": "capture_state", "description": "Capture current replay state"},
        {"step_type": "pause_execution", "description": "Pause replay execution"},
    ],
    "replay_step": [
        {"step_type": "validate_step", "description": "Validate step forward is safe"},
        {"step_type": "advance_tick", "description": "Advance to next tick"},
    ],
    "inventory_dispatch": [
        {"step_type": "validate_stock", "description": "Validate sufficient stock available"},
        {"step_type": "allocate_batches", "description": "Allocate inventory batches"},
        {"step_type": "update_quantities", "description": "Update stock quantities"},
        {"step_type": "create_journal", "description": "Create accounting journal entry"},
        {"step_type": "finalize_dispatch", "description": "Finalize dispatch"},
    ],
    "inventory_receive": [
        {"step_type": "validate_receipt", "description": "Validate purchase receipt"},
        {"step_type": "add_batches", "description": "Add new inventory batches"},
        {"step_type": "update_quantities", "description": "Update stock quantities"},
        {"step_type": "create_journal", "description": "Create accounting journal entry"},
    ],
    "erp_create_product": [
        {"step_type": "validate_product", "description": "Validate product data"},
        {"step_type": "check_duplicates", "description": "Check for duplicate barcode/SKU"},
        {"step_type": "create_record", "description": "Create product database record"},
    ],
    "system_rollback": [
        {"step_type": "identify_transaction", "description": "Identify transaction to roll back"},
        {"step_type": "validate_rollback", "description": "Validate rollback is safe"},
        {"step_type": "reverse_entries", "description": "Reverse journal entries"},
        {"step_type": "restore_state", "description": "Restore pre-transaction state"},
    ],
    "system_recover": [
        {"step_type": "assess_damage", "description": "Assess system damage scope"},
        {"step_type": "load_recovery_checkpoint", "description": "Load recovery checkpoint"},
        {"step_type": "execute_recovery", "description": "Execute recovery procedures"},
    ],
    "observability_read": [
        {"step_type": "authenticate_request", "description": "Authenticate API request"},
        {"step_type": "validate_permissions", "description": "Validate read permissions"},
        {"step_type": "query_data", "description": "Query observability data"},
        {"step_type": "format_response", "description": "Format standardized response"},
    ],
}


def build_plan(decision: DecisionResult) -> ExecutionPlan:
    """Build an execution plan from a governance DecisionResult.

    Args:
        decision: The DecisionResult from Phase 5B.0.

    Returns:
        An immutable ExecutionPlan with deterministic step sequence.
    """
    audit = decision.audit_entry
    action_type = audit.get("action_type", "unknown")
    domain = audit.get("domain", "unknown")
    decision_value = decision.decision

    steps = _build_steps(action_type, decision_value)

    return ExecutionPlan(
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
            "plan_builder_version": PLAN_BUILDER_VERSION,
            "decision": decision_value,
            "source": audit.get("source", "unknown"),
        },
    )


def _build_steps(action_type: str, decision: str) -> List[ExecutionStep]:
    """Build deterministic step list for an action type.

    If the decision is BLOCKED, returns only one step indicating blocked status.
    """
    if decision == "BLOCKED":
        return [
            ExecutionStep(
                step_id="step_blocked",
                step_type="blocked",
                description=f"Action {action_type} is BLOCKED — no execution possible",
                simulated_status="SKIPPED",
                simulated_output={"reason": "BLOCKED by governance enforcement"},
            )
        ]

    template = ACTION_STEP_TEMPLATES.get(action_type, [])
    if not template:
        return [
            ExecutionStep(
                step_id="step_unknown",
                step_type="unknown",
                description=f"No execution template for action type: {action_type}",
                simulated_status="PENDING",
            )
        ]

    return [
        ExecutionStep(
            step_id=f"step_{i}_{s['step_type']}",
            step_type=s["step_type"],
            description=s["description"],
            simulated_status="PENDING",
        )
        for i, s in enumerate(template)
    ]


def get_supported_action_templates() -> Dict[str, List[Dict[str, str]]]:
    """Return all registered action step templates."""
    return dict(ACTION_STEP_TEMPLATES)
