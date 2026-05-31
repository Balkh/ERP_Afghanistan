"""
Phase 7 — Enterprise Operational Observability.
Operational health dashboard, incident reconstruction, noise-safe telemetry,
and environment-aware sampling.
"""
import logging
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.governance.kernel import GovernanceKernel, PriorityTier, AuditEntry
from core.governance.events import GovernanceEvent, EventSeverity
from core.governance.metrics import get_metrics

logger = logging.getLogger("erp.governance.observability")

OBSERVABILITY_VERSION = "1.0.0"


@dataclass
class OperationalHealth:
    overall: str  # healthy | degraded | critical
    governance: Dict[str, Any] = field(default_factory=dict)
    invariants: Dict[str, Any] = field(default_factory=dict)
    deployment: Dict[str, Any] = field(default_factory=dict)
    memory: Dict[str, Any] = field(default_factory=dict)
    latency: Dict[str, Any] = field(default_factory=dict)
    recovery: Dict[str, Any] = field(default_factory=dict)
    score: float = 100.0
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class IncidentReconstruction:
    event_chain: List[Dict[str, Any]] = field(default_factory=list)
    policy_chain: List[Dict[str, Any]] = field(default_factory=list)
    workflow_chain: List[Dict[str, Any]] = field(default_factory=list)
    financial_causality: List[Dict[str, Any]] = field(default_factory=list)
    reconstruction_complete: bool = True
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class NoiseSafeTelemetry:
    total_events_captured: int = 0
    dedup_events_filtered: int = 0
    sampled_events: int = 0
    alert_count: int = 0
    duplicate_alerts_prevented: int = 0
    bounded: bool = True
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


class _AlertDeduplicator:
    """Prevents duplicate alerts within a time window."""

    def __init__(self, window_seconds: float = 300.0, max_entries: int = 100):
        self._window = window_seconds
        self._max = max_entries
        self._seen: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_duplicate(self, alert_key: str) -> bool:
        now = time.time()
        with self._lock:
            last = self._seen.get(alert_key)
            if last and (now - last) < self._window:
                return True
            self._seen[alert_key] = now
            if len(self._seen) > self._max:
                oldest = min(self._seen.keys(), key=lambda k: self._seen[k])
                del self._seen[oldest]
            return False


class OperationalHealthDashboard:
    """Aggregates governance, deployment, and recovery health into a single dashboard."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def get_health(self) -> OperationalHealth:
        warnings = []
        health = self._kernel.health()

        gov_status = {
            "initialized": health.get("initialized", False),
            "policies": health.get("policies", 0),
            "invariants": health.get("invariants", 0),
            "failsafe": health.get("failsafe_mode", False),
            "degraded_tiers": health.get("degraded_tiers", []),
        }

        inv_results = self._kernel.run_invariant_scan()
        inv_failures = [r for r in inv_results if not r["passed"]]
        inv_status = {
            "total": len(inv_results),
            "passed": sum(1 for r in inv_results if r["passed"]),
            "failed": len(inv_failures),
            "failures": inv_failures[:5],
        }

        if inv_failures:
            warnings.append(f"{len(inv_failures)} invariant(s) failing")
        if gov_status["failsafe"]:
            warnings.append("Governance in failsafe mode")
        if gov_status["degraded_tiers"]:
            warnings.append(f"Degraded tiers: {gov_status['degraded_tiers']}")

        # Memory health
        from core.governance.events import get_event_bus
        bus = get_event_bus()
        mem_status = {
            "event_bus_usage": bus.count(),
            "event_bus_capacity": 500,
            "audit_entries": health.get("audit_entries", 0),
            "audit_capacity": health.get("audit_capacity", 1000),
        }

        # Latency trends
        metrics = get_metrics()
        latency_status = {
            "total_enforcements": metrics.snapshot().get("total_enforcements", 0),
        }
        for pid in ("enforce.return_state_transition", "enforce.sales_state_transition",
                     "enforce.purchase_state_transition", "enforce.je_debit_equals_credit"):
            stats = metrics.get_latency_stats(pid)
            if stats.get("count", 0) > 0:
                latency_status[pid] = stats

        # Deployment health
        try:
            from core.governance.deployment import DeploymentValidator
            dv = DeploymentValidator(self._kernel)
            dep_report = dv.run_all()
            dep_status = {
                "overall": dep_report.overall,
                "operational_risk": dep_report.operational_risk,
                "blockers": dep_report.blockers,
            }
        except Exception as e:
            dep_status = {"error": str(e)}

        # Recovery health
        try:
            from core.governance.backup_recovery import RecoveryReadinessAssessor
            ra = RecoveryReadinessAssessor(self._kernel)
            rec_score = ra.assess()
            rec_status = {
                "score": rec_score.overall_score,
                "governance_recoverable": rec_score.governance_recoverable,
                "accounting_recoverable": rec_score.accounting_recoverable,
            }
        except Exception as e:
            rec_status = {"error": str(e)}

        score = 100.0
        if inv_failures:
            score -= len(inv_failures) * 10
        if gov_status["failsafe"]:
            score -= 20
        if gov_status["degraded_tiers"]:
            score -= 15
        if dep_status.get("blockers"):
            score -= 25
        score = max(0, score)

        overall = "critical" if score < 50 else ("degraded" if score < 80 else "healthy")

        return OperationalHealth(
            overall=overall,
            governance=gov_status,
            invariants=inv_status,
            deployment=dep_status,
            memory=mem_status,
            latency=latency_status,
            recovery=rec_status,
            score=round(score, 1),
            warnings=warnings,
        )


class IncidentReconstructor:
    """Enables reconstruction of incidents from governance audit trails."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()

    def reconstruct(self, correlation_id: str = "") -> IncidentReconstruction:
        audit_entries = self._kernel.get_recent_audit(limit=200)

        if correlation_id:
            relevant = [e for e in audit_entries if e.correlation_id == correlation_id]
        else:
            relevant = audit_entries[-20:]

        event_chain = [
            {
                "correlation_id": e.correlation_id,
                "action": e.action,
                "policy_id": e.policy_id,
                "result": e.result,
                "reason": e.reason,
                "latency_ms": e.latency_ms,
                "timestamp": e.timestamp,
            }
            for e in relevant
        ]

        policy_chain = list(dict.fromkeys(e.policy_id for e in relevant if e.policy_id))

        workflow_chain = [
            {
                "entity": e.affected_entity,
                "action": e.action,
                "result": e.result,
                "timestamp": e.timestamp,
            }
            for e in relevant if e.affected_entity
        ]

        financial_entries = [
            {
                "correlation_id": e.correlation_id,
                "policy_id": e.policy_id,
                "result": e.result,
                "reason": e.reason,
                "timestamp": e.timestamp,
            }
            for e in relevant
            if "je_" in e.policy_id or "accounting" in e.policy_id or "balance" in e.reason.lower()
        ]

        return IncidentReconstruction(
            event_chain=event_chain,
            policy_chain=[
                {"policy_id": pid, "sequence": idx}
                for idx, pid in enumerate(policy_chain)
            ],
            workflow_chain=workflow_chain,
            financial_causality=financial_entries,
        )


class NoiseSafeTelemetryManager:
    """Environment-aware, bounded telemetry with dedup and sampling."""

    def __init__(self, kernel: Optional[GovernanceKernel] = None):
        self._kernel = kernel or GovernanceKernel()
        self._alert_dedup = _AlertDeduplicator()
        self._total: int = 0
        self._dedup_filtered: int = 0
        self._sampled: int = 0
        self._alert_count: int = 0
        self._lock = threading.Lock()

    def record_event(self, event: GovernanceEvent) -> bool:
        """Return True if event should be processed, False if suppressed."""
        profile = self._kernel.environment.profile
        sampling = self._kernel.environment.sampling_rate()

        with self._lock:
            self._total += 1

        if profile == "production" and event.severity not in (
            EventSeverity.ERROR, EventSeverity.CRITICAL, EventSeverity.WARNING
        ):
            with self._lock:
                self._sampled += 1
            return False

        if profile == "production" and sampling < 1.0:
            import random
            if random.random() > sampling:
                with self._lock:
                    self._sampled += 1
                return False

        return True

    def record_alert(self, alert_key: str) -> bool:
        """Return True if alert is not a duplicate, False if suppressed."""
        with self._lock:
            self._alert_count += 1
        if self._alert_dedup.is_duplicate(alert_key):
            with self._lock:
                self._dedup_filtered += 1
            return False
        return True

    def get_summary(self) -> NoiseSafeTelemetry:
        with self._lock:
            return NoiseSafeTelemetry(
                total_events_captured=self._total,
                dedup_events_filtered=self._dedup_filtered,
                sampled_events=self._sampled,
                alert_count=self._alert_count,
                duplicate_alerts_prevented=self._dedup_filtered,
            )
