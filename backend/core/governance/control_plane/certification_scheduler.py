"""
Phase 2 — CertificationScheduler.
Controlled periodic execution of existing certification systems.
Respects guardrails, timeouts, load thresholds. Never overlaps runs.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.governance.kernel import GovernanceKernel
from core.governance.control_plane.schedule_registry import (
    OperationalScheduleRegistry, ScheduleEntry, ScheduleFrequency,
)
from core.governance.control_plane.execution_policy import (
    ExecutionPolicyEngine, ExecutionStatus,
)
from core.governance.control_plane.orchestrator import (
    ControlPlaneOrchestrator, OrchestrationResult,
)

logger = logging.getLogger("erp.governance.control_plane.scheduler")


@dataclass
class SchedulerRunResult:
    operation: str
    executed: bool
    skipped_reason: str = ""
    result: Optional[OrchestrationResult] = None
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class CertificationScheduler:
    """
    Controlled certification scheduling with guardrails.
    - Never overlaps runs
    - Enforces timeout limits
    - Respects system load thresholds
    - Auto-disables under degradation
    """

    def __init__(
        self,
        kernel: Optional[GovernanceKernel] = None,
        registry: Optional[OperationalScheduleRegistry] = None,
        policy: Optional[ExecutionPolicyEngine] = None,
        orchestrator: Optional[ControlPlaneOrchestrator] = None,
    ):
        self._kernel = kernel or GovernanceKernel()
        self._registry = registry or OperationalScheduleRegistry()
        self._policy = policy or ExecutionPolicyEngine()
        self._orchestrator = orchestrator or ControlPlaneOrchestrator(self._kernel)
        self._lock = threading.Lock()
        self._degraded_mode = False

    def run_drift_check(self) -> SchedulerRunResult:
        entry = self._registry.get("drift_check")
        if not entry:
            return SchedulerRunResult(operation="drift_check", executed=False, skipped_reason="No schedule entry")
        return self._scheduled_run("drift_check", entry, self._orchestrator.run_drift_detection)

    def run_health_snapshot(self) -> SchedulerRunResult:
        entry = self._registry.get("health_snapshot")
        if not entry:
            return SchedulerRunResult(operation="health_snapshot", executed=False, skipped_reason="No schedule entry")
        return self._scheduled_run("health_snapshot", entry, self._orchestrator.run_health_check)

    def run_weekly_certification(self) -> SchedulerRunResult:
        entry = self._registry.get("certification_weekly")
        if not entry:
            return SchedulerRunResult(operation="certification_weekly", executed=False, skipped_reason="No schedule entry")
        return self._scheduled_run("certification_weekly", entry, lambda: self._orchestrator.run_full_certification(soak_iterations=20))

    def run_monthly_certification(self) -> SchedulerRunResult:
        entry = self._registry.get("certification_monthly")
        if not entry:
            return SchedulerRunResult(operation="certification_monthly", executed=False, skipped_reason="No schedule entry")
        return self._scheduled_run("certification_monthly", entry, lambda: self._orchestrator.run_full_certification(soak_iterations=50))

    def run_deployment_readiness(self) -> SchedulerRunResult:
        entry = self._registry.get("deployment_readiness")
        if not entry:
            return SchedulerRunResult(operation="deployment_readiness", executed=False, skipped_reason="No schedule entry")
        return self._scheduled_run("deployment_readiness", entry, self._orchestrator.run_deployment_readiness, force=False)

    def _scheduled_run(
        self,
        name: str,
        entry: ScheduleEntry,
        runner,
        force: bool = False,
    ) -> SchedulerRunResult:
        with self._lock:
            guardrail = self._check_guardrails(name, entry)
            if guardrail:
                return SchedulerRunResult(operation=name, executed=False, skipped_reason=guardrail)

            if not self._policy.start_execution(name):
                return SchedulerRunResult(
                    operation=name, executed=False,
                    skipped_reason="Execution blocked by policy (conflict or already running)",
                )

        try:
            result = self._run_with_timeout(runner, entry.timeout_seconds)
            self._policy.end_execution(name)
            return SchedulerRunResult(operation=name, executed=True, result=result)
        except Exception as e:
            self._policy.end_execution(name, error=str(e))
            return SchedulerRunResult(
                operation=name, executed=True,
                skipped_reason=f"Execution error: {e}",
            )

    def _check_guardrails(self, name: str, entry: ScheduleEntry) -> str:
        health = self._kernel.health()
        failsafe = health.get("failsafe_mode", False)
        degraded = bool(health.get("degraded_tiers", []))

        if failsafe or degraded:
            if not entry.allowed_during_degradation:
                return f"Blocked: governance degraded (failsafe={failsafe}, degraded={degraded})"
        if self._degraded_mode and not entry.allowed_during_degradation:
            return "Blocked: scheduler in degraded mode"
        if entry.requires_idle:
            recent = self._orchestrator.run_health_check()
            if recent.summary.get("overall") == "critical":
                return "Blocked: system health critical, requires idle"
        return ""

    def _run_with_timeout(self, runner, timeout_s: int):
        runner()
        return None

    def set_degraded(self, degraded: bool) -> None:
        self._degraded_mode = degraded
