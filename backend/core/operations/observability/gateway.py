"""
Phase 5B.4 — Observability & Operational Control Gateway.

Read-only orchestration layer for the entire observability system.
Provides unified access to traces, timelines, correlations,
integrity monitoring, stream metrics, and replay visualization.

EVERYTHING IS OBSERVABLE. NOTHING IS CONTROLLABLE.
"""
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain, Event
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.observability.models import (
    TraceObject, TimelineView, CorrelationGraph,
    IntegrityReport, StreamMetrics, ReplayState,
    DashboardView, IntegrityStatus, StreamHealth,
    ObservabilitySnapshot,
)
from core.operations.observability.trace_engine import EventTraceEngine
from core.operations.observability.correlation import CrossDomainCorrelationEngine
from core.operations.observability.timeline import OperationalTimelineRenderer
from core.operations.observability.integrity import SystemIntegrityMonitor
from core.operations.observability.stream_monitor import RealTimeStreamMonitor
from core.operations.observability.replay import ReplayVisualizationEngine

logger = logging.getLogger('erp.observability.gateway')

OBSERVABILITY_GATEWAY_VERSION = "1.0.0"


class ObservabilityGateway:
    """Read-only observability gateway.

    All operations are:
    - Deterministic
    - Read-only
    - Audit-grade
    - Non-actionable
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._trace_engine = EventTraceEngine(self._store)
        self._correlation_engine = CrossDomainCorrelationEngine(self._store)
        self._timeline_renderer = OperationalTimelineRenderer(self._store)
        self._integrity_monitor = SystemIntegrityMonitor(self._store)
        self._stream_monitor = RealTimeStreamMonitor(self._store)
        self._replay_engine = ReplayVisualizationEngine(self._store)

    # ── Trace API ──

    def trace_aggregate(self, domain: str, aggregate_id: str) -> TraceObject:
        """Full event chain reconstruction by domain + aggregate."""
        return self._trace_engine.trace_aggregate(Domain(domain), aggregate_id)

    def trace_by_event_id(self, event_id: str) -> Optional[TraceObject]:
        """Trace from a specific event ID."""
        return self._trace_engine.trace_by_event_id(event_id)

    def build_causation_graph(self, event_id: str) -> Dict[str, Any]:
        """Build causation graph for an event."""
        nodes, edges = self._trace_engine.build_causation_graph(event_id)
        return {
            "nodes": [{
                "event_id": n.event_id,
                "event_type": n.event_type,
                "domain": n.domain,
                "aggregate_id": n.aggregate_id,
            } for n in nodes],
            "edges": [{
                "cause": e.cause_event_id,
                "effect": e.effect_event_id,
                "relationship": e.relationship,
                "domain_crossing": e.domain_crossing,
            } for e in edges],
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ── Timeline API ──

    def get_timeline(
        self,
        from_timestamp: str = "",
        to_timestamp: str = "",
        domains: Optional[List[str]] = None,
        source_types: Optional[List[str]] = None,
        max_entries: int = 1000,
    ) -> TimelineView:
        """Deterministic timeline of events."""
        domain_enums = [Domain(d) for d in domains] if domains else None
        return self._timeline_renderer.render_timeline(
            from_timestamp, to_timestamp, domain_enums, source_types, max_entries,
        )

    def get_aggregate_timeline(self, domain: str, aggregate_id: str) -> TimelineView:
        """Timeline for a single aggregate."""
        return self._timeline_renderer.render_aggregate_timeline(
            Domain(domain), aggregate_id,
        )

    def get_domain_timeline(
        self,
        domain: str,
        from_timestamp: str = "",
        to_timestamp: str = "",
        max_entries: int = 1000,
    ) -> TimelineView:
        """Timeline for a single domain."""
        return self._timeline_renderer.render_domain_timeline(
            Domain(domain), from_timestamp, to_timestamp, max_entries,
        )

    # ── Correlation API ──

    def correlate_by_event_id(self, event_id: str) -> CorrelationGraph:
        """Cross-domain correlation from event ID."""
        return self._correlation_engine.correlate_by_event_id(event_id)

    def correlate_by_correlation_id(self, correlation_id: str) -> CorrelationGraph:
        """Correlation by explicit correlation ID."""
        return self._correlation_engine.correlate_by_correlation_id(correlation_id)

    def correlate_domain_pair(self, domain_a: str, domain_b: str) -> CorrelationGraph:
        """Correlation between two domains."""
        return self._correlation_engine.correlate_domain_pair(
            Domain(domain_a), Domain(domain_b),
        )

    def get_domain_dependency_map(self) -> Dict[str, List[str]]:
        """Known domain dependency relationships."""
        return self._correlation_engine.get_domain_dependency_map()

    # ── Integrity API ──

    def run_integrity_check(self) -> IntegrityReport:
        """Full system integrity check."""
        return self._integrity_monitor.run_full_integrity_check()

    def get_domain_integrity(self, domain: str) -> Dict[str, Any]:
        """Domain-level integrity."""
        return self._integrity_monitor.get_domain_integrity(Domain(domain))

    def verify_event_chain(self, event_id: str) -> Dict[str, Any]:
        """Verify a single event chain."""
        return self._integrity_monitor.verify_event_chain(event_id)

    # ── Stream API ──

    def get_stream_metrics(self) -> StreamMetrics:
        """Current stream metrics."""
        return self._stream_monitor.get_metrics()

    def get_store_summary(self) -> Dict[str, Any]:
        """Event store summary."""
        return self._stream_monitor.get_store_summary()

    # ── Replay API ──

    def get_replay_state(
        self,
        from_sequence: int = 0,
        to_sequence: Optional[int] = None,
    ) -> ReplayState:
        """Replay state for a sequence range."""
        return self._replay_engine.get_replay_state(from_sequence, to_sequence)

    def render_at_sequence(self, sequence: int) -> List[Dict[str, Any]]:
        """System state at sequence N (time-travel)."""
        entries = self._replay_engine.render_at_sequence(sequence)
        return [{
            "event_id": e.event_id,
            "event_type": e.event_type,
            "domain": e.domain,
            "timestamp": e.timestamp,
            "summary": e.summary,
        } for e in entries]

    def compute_replay_hash(
        self,
        from_sequence: int,
        to_sequence: int,
    ) -> str:
        """Deterministic replay hash."""
        state = self._replay_engine.get_replay_state(from_sequence, to_sequence)
        return self._replay_engine.compute_replay_hash(state)

    # ── Dashboard API ──

    def get_dashboard(self, dashboard_type: str, domain: str = "") -> DashboardView:
        """Read-only dashboard view."""
        timeline = self._timeline_renderer.render_domain_timeline(Domain(domain)) if domain else None
        integrity = self._integrity_monitor.run_full_integrity_check()
        return DashboardView(
            dashboard_id=f"dash_{dashboard_type}",
            dashboard_type=dashboard_type,
            domain=domain,
            timeline=timeline,
            projections=self._build_projection_summary(),
            integrity=integrity,
            generated_at=integrity.verified_at,
        )

    # ── System Operations ──

    def get_snapshot(self) -> ObservabilitySnapshot:
        """Point-in-time snapshot of observability state."""
        integrity = self._integrity_monitor.run_full_integrity_check()
        metrics = self._stream_monitor.get_metrics()
        domain_counts = self._store.count_by_domain()
        return ObservabilitySnapshot(
            total_events=self._store.count(),
            integrity_status=integrity.status,
            stream_health=metrics.health,
            domain_event_counts=domain_counts,
        )

    def get_observability_status(self) -> Dict[str, Any]:
        """Comprehensive observability status."""
        integrity = self._integrity_monitor.run_full_integrity_check()
        metrics = self._stream_monitor.get_metrics()
        return {
            "gateway_version": OBSERVABILITY_GATEWAY_VERSION,
            "total_events": self._store.count(),
            "integrity": integrity.status.value,
            "stream_health": metrics.health.value,
            "anomaly_count": len(integrity.detected_anomalies),
            "events_per_second": metrics.events_per_second,
            "domain_counts": self._store.count_by_domain(),
            "source_counts": self._store.count_by_source(),
        }

    def _build_projection_summary(self) -> Dict[str, Any]:
        return {
            "inventory": len(self._store.get_by_domain(Domain.INVENTORY)),
            "accounting": len(self._store.get_by_domain(Domain.ACCOUNTING)),
            "hr": len(self._store.get_by_domain(Domain.HR)),
            "sales_purchase": len(self._store.get_by_domain(Domain.SALES_PURCHASE)),
        }

    def reset(self) -> None:
        """Reset gateway state. For testing only."""
        from core.operations.truth.event_store import reset_event_store
        reset_event_store()
        self._store = get_event_store()
        self._trace_engine = EventTraceEngine(self._store)
        self._correlation_engine = CrossDomainCorrelationEngine(self._store)
        self._timeline_renderer = OperationalTimelineRenderer(self._store)
        self._integrity_monitor = SystemIntegrityMonitor(self._store)
        self._stream_monitor = RealTimeStreamMonitor(self._store)
        self._replay_engine = ReplayVisualizationEngine(self._store)
        logger.info("ObservabilityGateway state reset")


_gateway: Optional[ObservabilityGateway] = None


def get_gateway() -> ObservabilityGateway:
    global _gateway
    if _gateway is None:
        _gateway = ObservabilityGateway()
    return _gateway


def reset_gateway() -> None:
    global _gateway
    from core.operations.truth.event_store import reset_event_store
    reset_event_store()
    _gateway = None
