"""
Phase 7 — OperationalHealthLoop.
Stable, bounded feedback loop of system health.
Aggregates health snapshots, computes stability score (0-100),
and provides safe alerting logic (bounded, deduplicated, no alert storms).
"""
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel

logger = logging.getLogger("erp.governance.control_plane.health_loop")

MAX_SNAPSHOT_HISTORY = 30
ALERT_WINDOW_SECONDS = 300
MAX_ALERTS_PER_WINDOW = 5

STABILITY_WEIGHTS = {
    "governance_health": 25,
    "invariant_integrity": 25,
    "deployment_readiness": 15,
    "memory_stability": 10,
    "latency_stability": 10,
    "recovery_readiness": 10,
    "drift_status": 5,
}


@dataclass
class HealthSnapshot:
    governance_score: float = 100.0
    invariant_score: float = 100.0
    deployment_score: float = 100.0
    memory_score: float = 100.0
    latency_score: float = 100.0
    recovery_score: float = 100.0
    drift_score: float = 100.0
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class StabilityScore:
    overall: float  # 0-100
    governance_score: float = 100.0
    invariant_score: float = 100.0
    deployment_score: float = 100.0
    memory_score: float = 100.0
    latency_score: float = 100.0
    recovery_score: float = 100.0
    drift_score: float = 100.0
    trend: str = "stable"  # improving | stable | degrading
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class _BoundedAlertGate:
    """Prevents alert storms within a time window."""

    def __init__(self, window_seconds: float = ALERT_WINDOW_SECONDS, max_alerts: int = MAX_ALERTS_PER_WINDOW):
        self._window = window_seconds
        self._max = max_alerts
        self._timestamps: deque = deque()

    def allow(self) -> bool:
        now = time.time()
        while self._timestamps and (now - self._timestamps[0]) > self._window:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._max:
            return False
        self._timestamps.append(now)
        return True

    def reset(self) -> None:
        self._timestamps.clear()


class OperationalHealthLoop:
    """
    Stable, bounded health feedback loop.
    - Aggregates health snapshots from existing systems
    - Computes single composite stability score (0-100)
    - Provides safe alerting logic (bounded, deduplicated, no storm risk)
    """

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()
        self._lock = threading.Lock()
        self._snapshots: deque = deque(maxlen=MAX_SNAPSHOT_HISTORY)
        self._alert_gate = _BoundedAlertGate()
        self._last_stability: Optional[StabilityScore] = None

    def collect_snapshot(self) -> HealthSnapshot:
        warnings = []
        governance_score = 100.0
        invariant_score = 100.0
        deployment_score = 100.0
        memory_score = 100.0
        latency_score = 100.0
        recovery_score = 100.0
        drift_score = 100.0

        # Governance
        try:
            health = self._kernel.health()
            if health.get("failsafe_mode"):
                governance_score -= 30
                warnings.append("Governance in failsafe mode")
            if health.get("degraded_tiers", []):
                governance_score -= 15
                warnings.append(f"Degraded tiers: {health['degraded_tiers']}")
            if health.get("policies", 0) < 4:
                governance_score -= 20
        except Exception as e:
            governance_score = 0
            warnings.append(f"Governance check error: {e}")

        # Invariants
        try:
            inv_results = self._kernel.run_invariant_scan()
            failures = [r for r in inv_results if not r["passed"]]
            if failures:
                invariant_score -= len(failures) * 15
                warnings.append(f"{len(failures)} invariant(s) failing")
        except Exception as e:
            invariant_score = 0
            warnings.append(f"Invariant scan error: {e}")

        # Deployment
        try:
            from core.governance.deployment import DeploymentValidator
            dv = DeploymentValidator(self._kernel)
            dep = dv.run_all()
            if dep.blockers:
                deployment_score -= len(dep.blockers) * 20
            if dep.operational_risk == "high":
                deployment_score -= 20
            elif dep.operational_risk == "medium":
                deployment_score -= 10
        except Exception as e:
            deployment_score = 0
            warnings.append(f"Deployment check error: {e}")

        # Memory (from event bus)
        try:
            from core.governance.events import get_event_bus
            bus = get_event_bus()
            usage = bus.count()
            if usage > 400:
                memory_score -= 30
                warnings.append(f"Event bus near capacity: {usage}/500")
            elif usage > 300:
                memory_score -= 10
        except Exception:
            pass

        # Latency (from metrics)
        try:
            from core.governance.metrics import get_metrics
            metrics = get_metrics()
            snap = metrics.snapshot()
            total = snap.get("total_enforcements", 0)
            if snap.get("total_latency_ms", 0) > 0 and total > 0:
                avg = snap["total_latency_ms"] / total
                if avg > 200:
                    latency_score -= 30
                    warnings.append(f"High average latency: {avg:.1f}ms")
                elif avg > 100:
                    latency_score -= 10
        except Exception:
            pass

        # Recovery
        try:
            from core.governance.backup_recovery import RecoveryReadinessAssessor
            ra = RecoveryReadinessAssessor(self._kernel)
            rec = ra.assess()
            recovery_score = rec.overall_score
            if rec.overall_score < 50:
                warnings.append("Low recovery readiness score")
        except Exception as e:
            recovery_score = 0
            warnings.append(f"Recovery check error: {e}")

        # Drift
        try:
            from core.governance.maintainability import OperationalDriftDetector
            odd = OperationalDriftDetector()
            odd.take_config_snapshot()
            odd.take_policy_snapshot(self._kernel)
            drift = odd.run(self._kernel)
            if drift.drifting:
                drift_score -= 50
                warnings.extend(drift.warnings[:2])
        except Exception:
            pass

        gov_score = max(0, governance_score)
        inv_score = max(0, invariant_score)
        dep_score = max(0, deployment_score)
        mem_score = max(0, memory_score)
        lat_score = max(0, latency_score)
        rec_score = max(0, recovery_score)
        drf_score = max(0, drift_score)

        snapshot = HealthSnapshot(
            governance_score=gov_score,
            invariant_score=inv_score,
            deployment_score=dep_score,
            memory_score=mem_score,
            latency_score=lat_score,
            recovery_score=rec_score,
            drift_score=drf_score,
            warnings=warnings,
        )

        with self._lock:
            self._snapshots.append(snapshot)

        return snapshot

    def compute_stability(self) -> StabilityScore:
        snapshot = self.collect_snapshot()
        warnings = list(snapshot.warnings)

        weighted = (
            snapshot.governance_score * STABILITY_WEIGHTS["governance_health"]
            + snapshot.invariant_score * STABILITY_WEIGHTS["invariant_integrity"]
            + snapshot.deployment_score * STABILITY_WEIGHTS["deployment_readiness"]
            + snapshot.memory_score * STABILITY_WEIGHTS["memory_stability"]
            + snapshot.latency_score * STABILITY_WEIGHTS["latency_stability"]
            + snapshot.recovery_score * STABILITY_WEIGHTS["recovery_readiness"]
            + snapshot.drift_score * STABILITY_WEIGHTS["drift_status"]
        ) / sum(STABILITY_WEIGHTS.values())
        overall = round(max(0, min(100, weighted)), 1)

        # Trend detection (compare with previous)
        trend = "stable"
        if self._last_stability:
            diff = overall - self._last_stability.overall
            if diff > 5:
                trend = "improving"
            elif diff < -5:
                trend = "degrading"
                warnings.append("Stability score declining")

        stability = StabilityScore(
            overall=overall,
            governance_score=snapshot.governance_score,
            invariant_score=snapshot.invariant_score,
            deployment_score=snapshot.deployment_score,
            memory_score=snapshot.memory_score,
            latency_score=snapshot.latency_score,
            recovery_score=snapshot.recovery_score,
            drift_score=snapshot.drift_score,
            trend=trend,
            warnings=warnings,
        )
        self._last_stability = stability
        return stability

    def safe_alert(self, message: str) -> bool:
        logger.warning("Health alert: %s", message)
        return self._alert_gate.allow()

    def get_history(self, limit: int = 10) -> List[HealthSnapshot]:
        with self._lock:
            return list(self._snapshots)[-limit:]

    def get_last_stability(self) -> Optional[StabilityScore]:
        return self._last_stability
