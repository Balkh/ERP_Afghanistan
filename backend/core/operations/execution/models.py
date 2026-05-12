"""
Phase 5B.1 (v2.0 Hardened) — Simulation Sandbox Models.

Shared data structures for the deterministic simulation sandbox.
All models are immutable dataclasses — no mutation allowed.

Strict semantic separation:
- SimulationPlan:     pure specification blueprint (NOT executable)
- SimulationStep:     single hypothetical modeling step
- SimulationOutcome:  deterministic modeling result (NOT real outcome)
- ImpactAnalysisReport: descriptive estimation only (NOT decision input)
- SimulationTrace:    immutable forensic record (NOT system truth)

SIMULATION CONTEXT ONLY — NO EXECUTION PERMITTED.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime


SIMULATION_SANDBOX_VERSION = "2.0.0"
SIMULATION_CONTEXT_MARKER = "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION"


@dataclass(frozen=True)
class SimulationStep:
    """A single hypothetical step in a simulation plan.

    Immutable. Represents one modeled action with zero side effects.
    All outputs are explicitly marked as simulation-only.
    """
    step_id: str = ""
    step_type: str = "unknown"
    description: str = ""
    modeled_status: str = "PENDING"  # PENDING, MODELED, FAILED, SKIPPED
    modeled_output: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationPlan:
    """Structured simulation blueprint derived from a governance DecisionResult.

    PURE SPECIFICATION ONLY — NOT EXECUTABLE IN ANY RUNTIME CONTEXT.
    Immutable. Contains all hypothetical steps for modeling.
    """
    plan_id: str = field(default_factory=lambda: f"simplan_{uuid4().hex[:8]}")
    decision_id: str = ""
    action_type: str = ""
    domain: str = ""
    risk_level: str = "NONE"
    risk_score: int = 0
    policy_trace: Dict[str, Any] = field(default_factory=dict)
    steps: List[SimulationStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationOutcome:
    """Deterministic modeling outcome from simulating a plan.

    Represents hypothetical results only — no real system state changed.
    Immutable. Bounded output.
    """
    plan_id: str = ""
    all_modeled_cleanly: bool = False
    steps_modeled: int = 0
    steps_failed: int = 0
    step_outcomes: List[SimulationStep] = field(default_factory=list)
    modeled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImpactAnalysisReport:
    """Purely descriptive estimation of hypothetical system effects.

    STRICTLY INFORMATIONAL — NO DECISION INFLUENCE PERMITTED.
    No execution recommendations allowed.
    """
    report_id: str = field(default_factory=lambda: f"impact_{uuid4().hex[:8]}")
    plan_id: str = ""
    financial_estimate: Dict[str, Any] = field(default_factory=dict)
    inventory_estimate: Dict[str, Any] = field(default_factory=dict)
    workflow_estimate: Dict[str, Any] = field(default_factory=dict)
    domains_affected: List[str] = field(default_factory=list)
    risk_propagation: List[Dict[str, Any]] = field(default_factory=list)
    estimated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationTrace:
    """Immutable forensic record of a simulation cycle.

    Bounded memory structure — NOT system state source.
    Used only for replay and audit purposes.
    """
    trace_id: str = field(default_factory=lambda: f"strace_{uuid4().hex[:8]}")
    plan_id: str = ""
    decision_id: str = ""
    action_type: str = ""
    domain: str = ""
    risk_level: str = ""
    modeling_status: str = ""
    impact_summary: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)
