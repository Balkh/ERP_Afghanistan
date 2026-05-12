"""
Phase 5B.1 — Execution Sandbox Models.

Shared data structures for the controlled execution sandbox.
All models are immutable dataclasses — no mutation allowed.

These define:
- ExecutionPlan: structured plan derived from governance decision
- ExecutionStep: individual simulation step
- SimulationResult: outcome of simulated execution
- ImpactReport: estimated system impact
- TraceLog: immutable audit entry

No execution logic. Deterministic data structures only.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime


EXECUTION_SANDBOX_VERSION = "1.0.0"


@dataclass(frozen=True)
class ExecutionStep:
    """A single step in an execution plan.

    Immutable. Represents one hypothetical action.
    """
    step_id: str = ""
    step_type: str = "unknown"
    description: str = ""
    simulated_status: str = "PENDING"  # PENDING, SIMULATED, FAILED, SKIPPED
    simulated_output: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionPlan:
    """Structured execution plan derived from a governance DecisionResult.

    Immutable. Contains all steps needed for simulation.
    """
    plan_id: str = field(default_factory=lambda: f"plan_{uuid4().hex[:8]}")
    decision_id: str = ""
    action_type: str = ""
    domain: str = ""
    risk_level: str = "NONE"
    risk_score: int = 0
    policy_trace: Dict[str, Any] = field(default_factory=dict)
    steps: List[ExecutionStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationResult:
    """Result of simulating an execution plan.

    Immutable. No real execution occurs.
    """
    plan_id: str = ""
    success: bool = False
    steps_executed: int = 0
    steps_failed: int = 0
    step_results: List[ExecutionStep] = field(default_factory=list)
    simulated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImpactReport:
    """Estimated system impact of execution.

    Immutable. No actual system changes.
    """
    report_id: str = field(default_factory=lambda: f"impact_{uuid4().hex[:8]}")
    plan_id: str = ""
    financial_impact: Dict[str, Any] = field(default_factory=dict)
    inventory_impact: Dict[str, Any] = field(default_factory=dict)
    workflow_impact: Dict[str, Any] = field(default_factory=dict)
    domains_affected: List[str] = field(default_factory=list)
    risk_propagation: List[Dict[str, Any]] = field(default_factory=list)
    estimated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceLog:
    """Immutable execution trace entry.

    Stored in bounded deque for audit purposes.
    """
    trace_id: str = field(default_factory=lambda: f"trace_{uuid4().hex[:8]}")
    plan_id: str = ""
    decision_id: str = ""
    action_type: str = ""
    domain: str = ""
    risk_level: str = ""
    simulation_status: str = ""
    impact_summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)
