"""
Phase 5B.1 (v2.0 Hardened) — Simulation Trace Logger.

STRICTLY SEPARATED FORENSIC RECORDING — NOT SYSTEM STATE SOURCE.
Maintains immutable audit trail of simulation cycles.
All traces are stored in bounded memory (deque with maxlen).

Responsibilities:
- Record all simulation traces immutably
- Maintain decision lineage from Governance Layer
- Enforce bounded memory (maxlen=500)
- Provide replay-safe forensic format

NOT responsible for: System state representation, decision storage, execution recording.
No mutation of past traces. Bounded memory only.
"""
from collections import deque
from typing import Any, Dict, List
from core.operations.execution.models import (
    SimulationPlan, SimulationOutcome, ImpactAnalysisReport, SimulationTrace,
)


SIMULATION_TRACE_VERSION = "2.0.0"
MAX_TRACES = 500


class SimulationTraceLogger:
    """Bounded, immutable forensic trace logger for the simulation sandbox.

    Stores traces in a deque with maxlen=500.
    All operations are read-only — traces cannot be modified after creation.
    Oldest entries are automatically evicted when capacity is exceeded.
    """

    def __init__(self, max_traces: int = MAX_TRACES):
        self._traces: deque = deque(maxlen=max_traces)
        self._max_traces = max_traces

    def record(self, plan: SimulationPlan, outcome: SimulationOutcome,
               impact: ImpactAnalysisReport) -> SimulationTrace:
        """Record a complete simulation cycle as an immutable forensic trace.

        Args:
            plan: The SimulationPlan that was modeled.
            outcome: The SimulationOutcome from the Simulation Engine.
            impact: The ImpactAnalysisReport from the Impact Analysis layer.

        Returns:
            An immutable SimulationTrace entry.
        """
        trace = SimulationTrace(
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            action_type=plan.action_type,
            domain=plan.domain,
            risk_level=plan.risk_level,
            modeling_status="MODELED_CLEANLY" if outcome.all_modeled_cleanly else "MODELED_WITH_ISSUES",
            impact_summary={
                "financial_severity": impact.financial_estimate.get("severity", "unknown"),
                "inventory_severity": impact.inventory_estimate.get("severity", "unknown"),
                "workflow_severity": impact.workflow_estimate.get("severity", "unknown"),
                "domains_affected": impact.domains_affected,
                "steps_modeled": outcome.steps_modeled,
                "steps_failed": outcome.steps_failed,
            },
            metadata={
                "logger_version": SIMULATION_TRACE_VERSION,
                "trace_count": len(self._traces) + 1,
                "simulation_context": "SIMULATION_CONTEXT_ONLY__NO_REAL_EXECUTION",
            },
        )
        self._traces.append(trace)
        return trace

    def get_traces(self, limit: int = 100) -> List[SimulationTrace]:
        """Get the most recent simulation traces.

        Args:
            limit: Maximum number of traces to return (capped at 100).

        Returns:
            List of immutable SimulationTrace entries (most recent first).
        """
        actual_limit = min(limit, 100)
        return list(self._traces)[-actual_limit:][::-1]

    def get_trace_count(self) -> int:
        """Get the total number of traces stored."""
        return len(self._traces)

    def clear(self) -> None:
        """Clear all stored traces."""
        self._traces.clear()

    def get_bounded_maxlen(self) -> int:
        """Get the maximum number of traces permitted (architectural bound)."""
        return self._max_traces
