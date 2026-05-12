"""
Phase 5B.1 — Simulation Executor (No Side Effect Mode).

Simulates execution behavior WITHOUT affecting system state.
All operations are virtual — no database writes, no API calls,
no persistent state changes.

Pipeline:
1. Receive ExecutionPlan
2. Simulate each step virtually
3. Track step outcomes
4. Aggregate SimulationResult

Deterministic simulation. No side effects. Bounded output.
"""
from typing import Any, Dict, List
from core.operations.execution.models import ExecutionPlan, ExecutionStep, SimulationResult


SIMULATOR_VERSION = "1.0.0"


def simulate(plan: ExecutionPlan) -> SimulationResult:
    """Simulate an execution plan without side effects.

    Each step is processed virtually:
    - BLOCKED steps are marked SKIPPED
    - Query/read steps are marked SIMULATED (success)
    - Mutation steps are marked SIMULATED (success) but NOT executed
    - Unknown steps are marked SIMULATED with warning

    Args:
        plan: The ExecutionPlan to simulate.

    Returns:
        A SimulationResult with per-step outcomes.
    """
    step_results: List[ExecutionStep] = []
    steps_executed = 0
    steps_failed = 0

    for step in plan.steps:
        result = _simulate_step(step, plan)
        step_results.append(result)
        if result.simulated_status == "SIMULATED":
            steps_executed += 1
        elif result.simulated_status == "FAILED":
            steps_failed += 1

    return SimulationResult(
        plan_id=plan.plan_id,
        success=steps_failed == 0,
        steps_executed=steps_executed,
        steps_failed=steps_failed,
        step_results=step_results,
        metadata={
            "simulator_version": SIMULATOR_VERSION,
            "action_type": plan.action_type,
            "domain": plan.domain,
            "total_steps": len(plan.steps),
        },
    )


def _simulate_step(step: ExecutionStep, plan: ExecutionPlan) -> ExecutionStep:
    """Simulate a single execution step.

    Deterministic — same step + same plan = same simulated output.
    """
    if step.simulated_status == "SKIPPED":
        return step

    step_type = step.step_type

    # Read-only / query steps always succeed
    if step_type in ("authenticate_request", "validate_permissions", "query_data",
                     "format_response", "validate_session", "validate_stock",
                     "validate_product", "check_duplicates", "validate_receipt",
                     "assess_damage", "identify_transaction", "validate_rollback",
                     "validate_step", "capture_state", "checkpoint_state",
                     "load_recovery_checkpoint", "verify_replay"):
        return ExecutionStep(
            step_id=step.step_id,
            step_type=step.step_type,
            description=step.description,
            simulated_status="SIMULATED",
            simulated_output={
                "simulated": True,
                "executed": False,
                "read_only": True,
                "result": "OK (simulated read)",
            },
            metadata={"simulation_version": SIMULATOR_VERSION},
        )

    # Mutation steps are simulated but NOT executed
    if step_type in ("create_record", "update_quantities", "allocate_batches",
                     "add_batches", "reverse_entries", "restore_state",
                     "execute_events", "execute_recovery", "advance_tick",
                     "set_start_tick", "create_journal", "finalize_dispatch",
                     "pause_execution", "prepare_environment",
                     "initialize_session", "execute_recovery",
                     "load_events"):
        return ExecutionStep(
            step_id=step.step_id,
            step_type=step.step_type,
            description=step.description,
            simulated_status="SIMULATED",
            simulated_output={
                "simulated": True,
                "executed": False,
                "mutation_blocked": True,
                "reason": "No real execution in simulation sandbox",
            },
            metadata={"simulation_version": SIMULATOR_VERSION},
        )

    # Fallback for unknown step types
    return ExecutionStep(
        step_id=step.step_id,
        step_type=step.step_type,
        description=step.description,
        simulated_status="SIMULATED",
        simulated_output={
            "simulated": True,
            "executed": False,
            "warning": f"Unknown step type: {step_type}",
        },
        metadata={"simulation_version": SIMULATOR_VERSION},
    )
