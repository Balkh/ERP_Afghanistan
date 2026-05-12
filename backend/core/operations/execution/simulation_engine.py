"""
Phase 5B.1 (v2.0 Hardened) — Simulation Engine.

STRICTLY SEPARATED SIMULATION LAYER — NO EXECUTION CAPABILITY.
Processes simulation blueprints into deterministic hypothetical outcomes.
All operations are virtual — no database writes, no API calls, no state changes.

Pipeline:
1. Receive SimulationPlan from Plan Builder
2. Model each hypothetical step deterministically
3. Track per-step outcomes
4. Aggregate SimulationOutcome

RESPONSIBILITY: Deterministic hypothetical modeling only.
NOT responsible for: Real execution, state mutation, or system changes.
No side effects. Bounded output. Deterministic.
"""
from typing import Any, Dict, List
from core.operations.execution.models import SimulationPlan, SimulationStep, SimulationOutcome


SIMULATION_ENGINE_VERSION = "2.0.0"


def model_plan(plan: SimulationPlan) -> SimulationOutcome:
    """Model a simulation plan deterministically without side effects.

    Each hypothetical step is processed virtually:
    - BLOCKED steps are marked SKIPPED (governance blocked)
    - Read/query steps are marked MODELED (hypothetical success)
    - Mutation steps are marked MODELED but NOT applied (simulation only)
    - Unknown steps are marked MODELED with warning

    Args:
        plan: The SimulationPlan to model.

    Returns:
        A SimulationOutcome with per-step hypothetical outcomes.
    """
    step_outcomes: List[SimulationStep] = []
    steps_modeled = 0
    steps_failed = 0

    for step in plan.steps:
        result = _model_step(step)
        step_outcomes.append(result)
        if result.modeled_status == "MODELED":
            steps_modeled += 1
        elif result.modeled_status == "FAILED":
            steps_failed += 1

    return SimulationOutcome(
        plan_id=plan.plan_id,
        all_modeled_cleanly=steps_failed == 0,
        steps_modeled=steps_modeled,
        steps_failed=steps_failed,
        step_outcomes=step_outcomes,
        metadata={
            "engine_version": SIMULATION_ENGINE_VERSION,
            "action_type": plan.action_type,
            "domain": plan.domain,
            "total_hypothetical_steps": len(plan.steps),
            "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
        },
    )


def _model_step(step: SimulationStep) -> SimulationStep:
    """Model a single hypothetical step deterministically.

    Same step + same plan type = same modeled output.
    All outputs include explicit simulation context markers.
    """
    if step.modeled_status == "SKIPPED":
        return step

    step_type = step.step_type

    # Read-only / query phases — always model as clean
    if step_type in ("authentication", "authorization", "data_query",
                     "response_format", "safety_check", "availability_check",
                     "validation", "duplicate_check", "receipt_check",
                     "safety_analysis", "damage_assessment",
                     "snapshot", "checkpoint_lookup", "integrity_verify",
                     "identification", "inspect_events", "checkpoint_estimation"):
        return SimulationStep(
            step_id=step.step_id,
            step_type=step.step_type,
            description=step.description,
            modeled_status="MODELED",
            modeled_output={
                "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
                "phase_type": "read_only_estimation",
                "applied": False,
                "result": "MODELED AS CLEAN (hypothetical)",
            },
            metadata={"simulation_engine_version": SIMULATION_ENGINE_VERSION},
        )

    # Mutation phases — modeled but explicitly NOT applied
    if step_type in ("creation_model", "quantity_estimate", "allocation_model",
                     "batch_addition_model", "stock_estimate", "reversal_model",
                     "restoration_estimate", "simulate_events", "recovery_model",
                     "advance_tick", "set_origin", "accounting_estimate",
                     "completion_marker", "halt_modeling", "prepare",
                     "initialize", "recovery_model", "accounting_estimate"):
        return SimulationStep(
            step_id=step.step_id,
            step_type=step.step_type,
            description=step.description,
            modeled_status="MODELED",
            modeled_output={
                "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
                "phase_type": "mutation_estimation",
                "applied": False,
                "mutation_blocked_by_design": True,
                "reason": "No real execution permitted in simulation sandbox",
            },
            metadata={"simulation_engine_version": SIMULATION_ENGINE_VERSION},
        )

    # Fallback for unknown step types
    return SimulationStep(
        step_id=step.step_id,
        step_type=step.step_type,
        description=step.description,
        modeled_status="MODELED",
        modeled_output={
            "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
            "phase_type": "unknown",
            "applied": False,
            "warning": f"Unknown hypothetical step type: {step_type}",
        },
        metadata={"simulation_engine_version": SIMULATION_ENGINE_VERSION},
    )
