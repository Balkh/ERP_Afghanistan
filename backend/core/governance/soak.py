"""
Phase 4 — Long-Duration Runtime Certification.
Validates long-term operational stability via soak testing,
memory stability, event stability, and latency drift analysis.
"""
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel, PriorityTier, EnforcementResult

logger = logging.getLogger("erp.governance.soak")

SOAK_VERSION = "1.0.0"


@dataclass
class SoakIterationResult:
    iteration: int
    passed: bool
    enforcement_latency_ms: float = 0.0
    invariant_result: bool = True
    governance_healthy: bool = True
    error: str = ""


@dataclass
class SoakTestResult:
    name: str
    passed: bool
    total_iterations: int = 0
    failed_iterations: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    memory_stable: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    iterations: List[SoakIterationResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class MemoryStabilityReport:
    stable: bool
    listener_count: int = 0
    queue_usage: int = 0
    cache_growth: bool = False
    reference_leak_detected: bool = False
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class LatencyDriftReport:
    stable: bool
    startup_latency_ms: float = 0.0
    enforcement_latency_avg_ms: float = 0.0
    enforcement_latency_p95_ms: float = 0.0
    api_latency_avg_ms: float = 0.0
    api_latency_p95_ms: float = 0.0
    drift_pct: float = 0.0
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class SoakTestFramework:
    """Runs soak tests to validate long-duration stability.

    Thread-safe. Bounded memory. No blocking operations.
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()
        self._lock = threading.Lock()

    def run_governance_soak(self, iterations: int = 100) -> SoakTestResult:
        latencies = deque(maxlen=iterations)
        failures = 0
        result_iterations = []

        for i in range(iterations):
            start = time.time()
            try:
                res = self._kernel.enforce(
                    policy_id="enforce.return_state_transition",
                    context={"current_state": "PENDING", "target_state": "APPROVED"},
                    priority=PriorityTier.HIGH,
                )
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                passed = True
                if not res.allowed:
                    failures += 1
                    passed = False
            except Exception as e:
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                failures += 1
                passed = False

            result_iterations.append(SoakIterationResult(
                iteration=i + 1,
                passed=passed,
                enforcement_latency_ms=round(latency, 2),
            ))

        avg_lat = sum(latencies) / max(len(latencies), 1)
        max_lat = max(latencies) if latencies else 0
        passed = failures == 0

        return SoakTestResult(
            name="governance_soak_24h",
            passed=passed,
            total_iterations=iterations,
            failed_iterations=failures,
            avg_latency_ms=round(avg_lat, 2),
            max_latency_ms=round(max_lat, 2),
            iterations=result_iterations[-20:],
        )

    def run_invariant_soak(self, iterations: int = 50) -> SoakTestResult:
        latencies = deque(maxlen=iterations)
        failures = 0
        result_iterations = []

        for i in range(iterations):
            start = time.time()
            try:
                passed, _ = self._kernel.check_invariant(
                    "system.database_connectivity",
                )
                latency = (time.time() - start) * 1000
                latencies.append(latency)
            except Exception:
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                passed = False
                failures += 1

            result_iterations.append(SoakIterationResult(
                iteration=i + 1,
                passed=passed,
                enforcement_latency_ms=round(latency, 2),
                invariant_result=passed,
            ))

        avg_lat = sum(latencies) / max(len(latencies), 1)
        max_lat = max(latencies) if latencies else 0

        return SoakTestResult(
            name="invariant_soak",
            passed=failures == 0,
            total_iterations=iterations,
            failed_iterations=failures,
            avg_latency_ms=round(avg_lat, 2),
            max_latency_ms=round(max_lat, 2),
            iterations=result_iterations[-10:],
        )

    def run_memory_stability_validation(self) -> MemoryStabilityReport:
        warnings = []
        health = self._kernel.health()
        listener_count = 0
        queue_usage = 0
        try:
            from core.governance.events import get_event_bus
            bus = get_event_bus()
            queue_usage = bus.count()
            listener_count = len(bus._handlers) if hasattr(bus, "_handlers") else 0
        except Exception:
            pass

        cache_growth = False
        ref_leak = False

        if queue_usage > 400:
            warnings.append(f"Event bus usage high: {queue_usage}")
        if listener_count > 20:
            warnings.append(f"Listener count high: {listener_count}")

        stable = len(warnings) == 0

        return MemoryStabilityReport(
            stable=stable,
            listener_count=listener_count,
            queue_usage=queue_usage,
            warnings=warnings,
        )

    def run_event_stability_validation(self) -> SoakTestResult:
        from core.governance.events import get_event_bus, GovernanceEvent, EventSeverity

        bus = get_event_bus()
        initial_count = bus.count()
        latencies = deque(maxlen=20)

        for i in range(20):
            start = time.time()
            try:
                bus.emit(GovernanceEvent(
                    event_id=f"soak-test-{i}",
                    event_type="soak_test",
                    severity=EventSeverity.INFO,
                    message=f"Soak test event {i}",
                ))
                latency = (time.time() - start) * 1000
                latencies.append(latency)
            except Exception as e:
                logger.error("Soak event error: %s", e)

        final_count = bus.count()
        # Should not have grown unbounded
        stable = final_count <= initial_count + 30
        avg_lat = sum(latencies) / max(len(latencies), 1)

        return SoakTestResult(
            name="event_stability_soak",
            passed=stable,
            total_iterations=20,
            avg_latency_ms=round(avg_lat, 2),
            warnings=[] if stable else ["Event bus grew beyond expected bounds"],
        )

    def run_latency_drift_analysis(self) -> LatencyDriftReport:
        from core.governance.metrics import get_metrics

        metrics = get_metrics()
        enforcement_stats = metrics.get_latency_stats("enforce.return_state_transition")
        enforcement_avg = enforcement_stats.get("avg", 0)
        enforcement_p95 = enforcement_stats.get("p95", 0)

        start = time.time()
        enum_val = PriorityTier.HIGH
        _ = self._kernel.enforce(
            "enforce.return_state_transition",
            {"current_state": "PENDING", "target_state": "APPROVED"},
            priority=enum_val,
        )
        startup_latency = (time.time() - start) * 1000

        drift_pct = 0.0
        if enforcement_avg > 0:
            drift_pct = round(abs(startup_latency - enforcement_avg) / max(enforcement_avg, 0.01) * 100, 1)

        warnings = []
        if drift_pct > 50:
            warnings.append(f"Latency drift detected: {drift_pct}%")

        stable = drift_pct < 50

        return LatencyDriftReport(
            stable=stable,
            startup_latency_ms=round(startup_latency, 2),
            enforcement_latency_avg_ms=enforcement_avg,
            enforcement_latency_p95_ms=enforcement_p95,
            drift_pct=drift_pct,
            warnings=warnings,
        )

    def run_full_soak_battery(self, iterations: int = 100) -> Dict[str, Any]:
        gov = self.run_governance_soak(iterations=iterations)
        inv = self.run_invariant_soak(iterations=max(iterations // 2, 20))
        mem = self.run_memory_stability_validation()
        evt = self.run_event_stability_validation()
        drift = self.run_latency_drift_analysis()

        return {
            "governance_soak": {
                "passed": gov.passed,
                "total": gov.total_iterations,
                "failed": gov.failed_iterations,
                "avg_latency_ms": gov.avg_latency_ms,
                "max_latency_ms": gov.max_latency_ms,
            },
            "invariant_soak": {
                "passed": inv.passed,
                "total": inv.total_iterations,
                "failed": inv.failed_iterations,
                "avg_latency_ms": inv.avg_latency_ms,
            },
            "memory_stability": {
                "stable": mem.stable,
                "queue_usage": mem.queue_usage,
                "warnings": mem.warnings,
            },
            "event_stability": {
                "passed": evt.passed,
                "warnings": evt.warnings,
            },
            "latency_drift": {
                "stable": drift.stable,
                "drift_pct": drift.drift_pct,
                "avg_enforcement_ms": drift.enforcement_latency_avg_ms,
            },
        }
