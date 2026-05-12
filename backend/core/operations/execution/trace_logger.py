"""
Phase 5B.1 — Sandbox Trace Logger.

Maintains full audit trace of simulated execution.
All traces are immutable and stored in bounded memory.

Responsibilities:
- Record all simulation traces
- Maintain decision lineage
- Enforce bounded memory (maxlen)
- Provide replay-safe trace format

No mutation of past traces. Bounded memory only.
"""
from collections import deque
from typing import Any, Dict, List, Optional
from core.operations.execution.models import (
    ExecutionPlan, SimulationResult, ImpactReport, TraceLog,
)


TRACE_LOGGER_VERSION = "1.0.0"
MAX_TRACES = 500


class SandboxTraceLogger:
    """Bounded, immutable trace logger for execution sandbox.

    Stores traces in a deque with maxlen=500.
    All operations are read-only — traces cannot be modified after creation.
    """

    def __init__(self, max_traces: int = MAX_TRACES):
        self._traces: deque = deque(maxlen=max_traces)
        self._max_traces = max_traces

    def record(self, plan: ExecutionPlan, simulation: SimulationResult,
               impact: ImpactReport) -> TraceLog:
        """Record a complete execution trace.

        Creates and stores an immutable TraceLog.
        Oldest traces are evicted when maxlen is exceeded (no manual cleanup needed).

        Returns:
            The immutable TraceLog entry.
        """
        trace = TraceLog(
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            action_type=plan.action_type,
            domain=plan.domain,
            risk_level=plan.risk_level,
            simulation_status="SIMULATED" if simulation.success else "FAILED",
            impact_summary={
                "financial_severity": impact.financial_impact.get("severity", "unknown"),
                "inventory_severity": impact.inventory_impact.get("severity", "unknown"),
                "workflow_severity": impact.workflow_impact.get("severity", "unknown"),
                "domains_affected": impact.domains_affected,
                "steps_executed": simulation.steps_executed,
                "steps_failed": simulation.steps_failed,
            },
            metadata={
                "logger_version": TRACE_LOGGER_VERSION,
                "trace_count": len(self._traces) + 1,
            },
        )
        self._traces.append(trace)
        return trace

    def get_traces(self, limit: int = 100) -> List[TraceLog]:
        """Get the most recent traces.

        Args:
            limit: Maximum number of traces to return (capped at 100).

        Returns:
            List of immutable TraceLog entries (most recent first).
        """
        actual_limit = min(limit, 100)
        return list(self._traces)[-actual_limit:][::-1]

    def get_trace_count(self) -> int:
        """Get the total number of traces stored."""
        return len(self._traces)

    def clear(self) -> None:
        """Clear all traces."""
        self._traces.clear()

    def get_bounded_maxlen(self) -> int:
        """Get the maximum number of traces."""
        return self._max_traces
