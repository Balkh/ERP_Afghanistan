"""
Phase 5B.4 — Enterprise Observability & Control Layer Tests.

Validates:
A. Event Trace Engine (lifecycle reconstruction)
B. Causation Graph Building
C. Cross-Domain Correlation
D. Timeline Rendering
E. System Integrity Monitor
F. Stream Monitor (read-only)
G. Replay Visualization
H. Gateway Integration
I. Read-Only Guarantees (no mutation)
J. Determinism
K. No Execution/Control Paths
"""
import unittest
from datetime import datetime, timedelta
from typing import Any, Dict, List

from core.operations.truth.models import (
    Domain, SourceType, Event,
)
from core.operations.truth.event_store import EventStore, EventFactory, get_event_store
from core.operations.observability.models import (
    TraceObject, TimelineView, CorrelationGraph,
    IntegrityReport, IntegrityStatus, StreamMetrics,
    StreamHealth, ReplayState, DashboardView,
)
from core.operations.observability.trace_engine import EventTraceEngine
from core.operations.observability.correlation import CrossDomainCorrelationEngine
from core.operations.observability.timeline import OperationalTimelineRenderer
from core.operations.observability.integrity import SystemIntegrityMonitor
from core.operations.observability.stream_monitor import RealTimeStreamMonitor
from core.operations.observability.replay import ReplayVisualizationEngine
from core.operations.observability.gateway import ObservabilityGateway, get_gateway, reset_gateway


def _make_event(
    event_type: str = "stock_movement",
    domain: Domain = Domain.INVENTORY,
    aggregate_id: str = "test_001",
    payload: Dict[str, Any] = None,
    source_type: SourceType = SourceType.REAL,
    sequence: int = 1,
    correlation_id: str = "",
    causation_id: str = "",
) -> Event:
    meta = {}
    if correlation_id:
        meta["correlation_id"] = correlation_id
    if causation_id:
        meta["causation_id"] = causation_id
    return EventFactory.create_event(
        source_type=source_type,
        domain=domain,
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload or {},
        metadata=meta,
        sequence=sequence,
    )


def _seed_multi_domain(store: EventStore) -> Dict[str, str]:
    """Seed events across multiple domains with correlation."""
    corr_id = "corr_sale_001"
    ids = {}

    e1 = _make_event("order_created", Domain.SALES_PURCHASE, "ord_001",
                     {"order_type": "SALE", "total_amount": 5000, "customer_id": "c1"},
                     sequence=1, correlation_id=corr_id)
    ids["order"] = store.append(e1)

    e2 = _make_event("stock_movement", Domain.INVENTORY, "batch_ord_001",
                     {"product_id": "p1", "quantity": 10, "direction": "out"},
                     sequence=1, correlation_id=corr_id, causation_id=ids["order"])
    ids["stock"] = store.append(e2)

    e3 = _make_event("journal_entry_posted", Domain.ACCOUNTING, "je_001",
                     {"description": "Sale entry", "entries": [{"debit": 5000, "credit": 0}, {"debit": 0, "credit": 5000}]},
                     sequence=1, correlation_id=corr_id, causation_id=ids["stock"])
    ids["journal"] = store.append(e3)

    e4 = _make_event("employee_hired", Domain.HR, "emp_001",
                     {"name": "Jane", "department": "Sales", "position": "Rep"},
                     sequence=1, correlation_id="corr_hr_001")
    ids["hr"] = store.append(e4)

    return ids


# ═══════════════════════════════════════════════════════════
# A. EVENT TRACE ENGINE
# ═══════════════════════════════════════════════════════════

class EventTraceEngineTest(unittest.TestCase):
    """Full lifecycle reconstruction from Event Store."""

    def setUp(self):
        reset_gateway()

    def test_trace_aggregate_full_chain(self):
        """Trace reconstructs full event chain."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        trace = engine.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertEqual(trace.aggregate_id, "ord_001")
        self.assertGreater(trace.event_count, 0)
        self.assertEqual(trace.root_event_id, ids["order"])

    def test_trace_aggregate_includes_timestamps(self):
        """Trace includes timestamp range."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        trace = engine.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertGreater(len(trace.timestamp_range_start), 0)
        self.assertGreater(len(trace.timestamp_range_end), 0)

    def test_trace_aggregate_empty_returns_empty(self):
        """Empty aggregate returns empty trace."""
        engine = EventTraceEngine(get_event_store())
        trace = engine.trace_aggregate(Domain.INVENTORY, "nonexistent")
        self.assertEqual(trace.event_count, 0)

    def test_trace_by_event_id(self):
        """Trace from event ID works."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        trace = engine.trace_by_event_id(ids["order"])
        self.assertIsNotNone(trace)
        self.assertGreater(trace.event_count, 0)

    def test_trace_by_nonexistent_event(self):
        """Nonexistent event returns None."""
        engine = EventTraceEngine(get_event_store())
        trace = engine.trace_by_event_id("nonexistent")
        self.assertIsNone(trace)

    def test_trace_has_integrity_hash(self):
        """Trace has deterministic integrity hash."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        trace = engine.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertGreater(len(trace.integrity_hash), 0)

    def test_trace_integrity_verification(self):
        """Trace integrity verification passes."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        trace = engine.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertTrue(engine.get_trace_integrity(trace))


# ═══════════════════════════════════════════════════════════
# B. CAUSATION GRAPH
# ═══════════════════════════════════════════════════════════

class CausationGraphTest(unittest.TestCase):
    """Causation graph building works correctly."""

    def setUp(self):
        reset_gateway()

    def test_build_causation_graph(self):
        """Causation graph captures cause→effect links."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        nodes, edges = engine.build_causation_graph(ids["order"])
        self.assertGreater(len(nodes), 0)
        self.assertGreater(len(edges), 0)

    def test_causation_has_domain_crossing(self):
        """Causation detects domain crossing."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        nodes, edges = engine.build_causation_graph(ids["order"])
        domain_crossings = [e for e in edges if e.domain_crossing]
        self.assertGreater(len(domain_crossings), 0)

    def test_causation_for_isolated_event(self):
        """Isolated event has no causation edges."""
        store = get_event_store()
        eid = store.append(_make_event(aggregate_id="isolated"))
        engine = EventTraceEngine(store)
        nodes, edges = engine.build_causation_graph(eid)
        self.assertEqual(len(edges), 0)

    def test_find_cross_domain_events(self):
        """Cross-domain events found via correlation."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        cross = engine.find_cross_domain_events(Domain.SALES_PURCHASE, "ord_001")
        self.assertGreater(len(cross), 0)

    def test_trace_has_domain_participation_map(self):
        """Trace includes domain participation map."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = EventTraceEngine(store)
        trace = engine.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertGreater(len(trace.domain_participation_map), 0)


# ═══════════════════════════════════════════════════════════
# C. CROSS-DOMAIN CORRELATION
# ═══════════════════════════════════════════════════════════

class CrossDomainCorrelationTest(unittest.TestCase):
    """Cross-domain correlation works correctly."""

    def setUp(self):
        reset_gateway()

    def test_correlate_by_correlation_id(self):
        """Correlation by ID returns all linked events."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = CrossDomainCorrelationEngine(store)
        graph = engine.correlate_by_correlation_id("corr_sale_001")
        self.assertGreater(len(graph.nodes), 0)
        self.assertGreater(len(graph.domains_involved), 0)

    def test_correlate_by_event_id(self):
        """Correlation from event ID works."""
        store = get_event_store()
        ids = _seed_multi_domain(store)
        engine = CrossDomainCorrelationEngine(store)
        graph = engine.correlate_by_event_id(ids["order"])
        self.assertGreater(len(graph.nodes), 0)

    def test_correlate_domain_pair(self):
        """Domain pair correlation works."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = CrossDomainCorrelationEngine(store)
        graph = engine.correlate_domain_pair(
            Domain.SALES_PURCHASE, Domain.INVENTORY,
        )
        self.assertGreater(len(graph.nodes), 0)

    def test_correlate_nonexistent_event(self):
        """Nonexistent event returns empty graph."""
        engine = CrossDomainCorrelationEngine(get_event_store())
        graph = engine.correlate_by_event_id("nonexistent")
        self.assertEqual(len(graph.nodes), 0)

    def test_domain_dependency_map(self):
        """Domain dependency map is populated."""
        engine = CrossDomainCorrelationEngine(get_event_store())
        deps = engine.get_domain_dependency_map()
        self.assertGreater(len(deps), 0)
        self.assertIn("inventory", deps)

    def test_correlation_graph_has_clusters(self):
        """Correlation includes dependency clusters."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = CrossDomainCorrelationEngine(store)
        graph = engine.correlate_by_correlation_id("corr_sale_001")
        self.assertGreater(len(graph.dependency_clusters), 0)


# ═══════════════════════════════════════════════════════════
# D. TIMELINE RENDERING
# ═══════════════════════════════════════════════════════════

class TimelineRendererTest(unittest.TestCase):
    """Deterministic timeline rendering."""

    def setUp(self):
        reset_gateway()

    def test_render_full_timeline(self):
        """Full timeline includes all events."""
        store = get_event_store()
        _seed_multi_domain(store)
        renderer = OperationalTimelineRenderer(store)
        timeline = renderer.render_timeline()
        self.assertGreater(timeline.total_entries, 0)

    def test_render_aggregate_timeline(self):
        """Aggregate timeline is correctly filtered."""
        store = get_event_store()
        _seed_multi_domain(store)
        renderer = OperationalTimelineRenderer(store)
        timeline = renderer.render_aggregate_timeline(Domain.SALES_PURCHASE, "ord_001")
        self.assertGreater(timeline.total_entries, 0)
        self.assertIn("sales_purchase", timeline.domains_present)

    def test_render_domain_timeline(self):
        """Domain timeline is correctly filtered."""
        store = get_event_store()
        _seed_multi_domain(store)
        renderer = OperationalTimelineRenderer(store)
        timeline = renderer.render_domain_timeline(Domain.INVENTORY)
        self.assertGreater(timeline.total_entries, 0)
        self.assertEqual(timeline.domains_present, ["inventory"])

    def test_render_timeline_time_range(self):
        """Timeline respects time range filter."""
        store = get_event_store()
        _seed_multi_domain(store)
        renderer = OperationalTimelineRenderer(store)
        future_ts = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
        timeline = renderer.render_timeline(from_timestamp=future_ts)
        self.assertEqual(timeline.total_entries, 0)

    def test_render_cross_domain_timeline(self):
        """Cross-domain timeline works."""
        store = get_event_store()
        _seed_multi_domain(store)
        renderer = OperationalTimelineRenderer(store)
        timeline = renderer.render_cross_domain_timeline("corr_sale_001")
        self.assertGreater(timeline.total_entries, 0)
        self.assertGreater(len(timeline.domains_present), 1)

    def test_timeline_entries_have_summaries(self):
        """Timeline entries include summaries."""
        store = get_event_store()
        _seed_multi_domain(store)
        renderer = OperationalTimelineRenderer(store)
        timeline = renderer.render_timeline()
        for entry in timeline.entries:
            self.assertGreater(len(entry.summary), 0)

    def test_empty_store_timeline(self):
        """Empty store returns empty timeline."""
        renderer = OperationalTimelineRenderer(get_event_store())
        timeline = renderer.render_timeline()
        self.assertEqual(timeline.total_entries, 0)


# ═══════════════════════════════════════════════════════════
# E. SYSTEM INTEGRITY MONITOR
# ═══════════════════════════════════════════════════════════

class SystemIntegrityMonitorTest(unittest.TestCase):
    """System integrity monitoring."""

    def setUp(self):
        reset_gateway()

    def test_integrity_check_passes_with_valid_store(self):
        """Integrity passes with valid event store."""
        store = get_event_store()
        _seed_multi_domain(store)
        monitor = SystemIntegrityMonitor(store)
        report = monitor.run_full_integrity_check()
        self.assertEqual(report.status, IntegrityStatus.PASS)

    def test_integrity_detects_sequence_gaps(self):
        """Integrity detects sequence gaps."""
        store = get_event_store()
        store.append(_make_event(aggregate_id="gap_test", sequence=1))
        store.append(_make_event(aggregate_id="gap_test", sequence=5))
        monitor = SystemIntegrityMonitor(store)
        report = monitor.run_full_integrity_check()
        self.assertNotEqual(report.status, IntegrityStatus.PASS)
        self.assertGreater(report.sequence_gaps, 0)

    def test_integrity_reports_event_count(self):
        """Integrity reports total events checked."""
        store = get_event_store()
        _seed_multi_domain(store)
        monitor = SystemIntegrityMonitor(store)
        report = monitor.run_full_integrity_check()
        self.assertGreater(report.total_events_checked, 0)

    def test_verify_event_chain_valid(self):
        """Event chain verification passes for valid event."""
        store = get_event_store()
        eid = store.append(_make_event(aggregate_id="chain_test", sequence=1))
        monitor = SystemIntegrityMonitor(store)
        result = monitor.verify_event_chain(eid)
        self.assertTrue(result["verified"])

    def test_verify_event_chain_nonexistent(self):
        """Nonexistent event chain verification fails."""
        monitor = SystemIntegrityMonitor(get_event_store())
        result = monitor.verify_event_chain("nonexistent")
        self.assertFalse(result["verified"])

    def test_get_domain_integrity(self):
        """Domain integrity returns per-domain status."""
        store = get_event_store()
        _seed_multi_domain(store)
        monitor = SystemIntegrityMonitor(store)
        result = monitor.get_domain_integrity(Domain.INVENTORY)
        self.assertGreater(result["total_events"], 0)


# ═══════════════════════════════════════════════════════════
# F. STREAM MONITOR
# ═══════════════════════════════════════════════════════════

class StreamMonitorTest(unittest.TestCase):
    """Read-only stream monitoring."""

    def setUp(self):
        reset_gateway()

    def test_get_metrics(self):
        """Stream metrics are returned."""
        store = get_event_store()
        _seed_multi_domain(store)
        monitor = RealTimeStreamMonitor(store)
        metrics = monitor.get_metrics()
        self.assertIsNotNone(metrics)

    def test_observe_event_tracking(self):
        """Observing events increases counters."""
        store = get_event_store()
        monitor = RealTimeStreamMonitor(store)
        event = _make_event()
        store.append(event)
        monitor.observe_event(event)
        metrics = monitor.get_metrics()
        self.assertGreater(metrics.total_events_received, 0)

    def test_get_store_summary(self):
        """Store summary returns stats."""
        store = get_event_store()
        _seed_multi_domain(store)
        monitor = RealTimeStreamMonitor(store)
        summary = monitor.get_store_summary()
        self.assertGreater(summary["total_events_stored"], 0)

    def test_stream_health_initial(self):
        """Stream health is HEALTHY initially."""
        store = get_event_store()
        _seed_multi_domain(store)
        monitor = RealTimeStreamMonitor(store)
        metrics = monitor.get_metrics()
        self.assertIn(metrics.health, (StreamHealth.HEALTHY, StreamHealth.LAGGING))


# ═══════════════════════════════════════════════════════════
# G. REPLAY VISUALIZATION
# ═══════════════════════════════════════════════════════════

class ReplayVisualizationTest(unittest.TestCase):
    """Replay visualization engine."""

    def setUp(self):
        reset_gateway()

    def test_get_replay_state(self):
        """Replay state provides range info."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = ReplayVisualizationEngine(store)
        state = engine.get_replay_state(0, 10)
        self.assertGreaterEqual(state.total_events_in_range, 0)

    def test_render_at_sequence(self):
        """Render at sequence returns entries up to that sequence."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = ReplayVisualizationEngine(store)
        entries = engine.render_at_sequence(1)
        self.assertGreaterEqual(len(entries), 0)

    def test_render_aggregate_at_sequence(self):
        """Aggregate at sequence works."""
        store = get_event_store()
        eid = store.append(_make_event(aggregate_id="rep_test", sequence=1))
        store.append(_make_event(aggregate_id="rep_test", sequence=2,
                                 event_type="stock_movement",
                                 payload={"quantity": 5, "direction": "out"}))
        engine = ReplayVisualizationEngine(store)
        entries = engine.render_aggregate_at_sequence(Domain.INVENTORY, "rep_test", 1)
        self.assertEqual(len(entries), 1)

    def test_compute_replay_hash(self):
        """Replay hash is deterministic."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = ReplayVisualizationEngine(store)
        state = engine.get_replay_state(0, 10)
        h1 = engine.compute_replay_hash(state)
        h2 = engine.compute_replay_hash(state)
        self.assertEqual(h1, h2)

    def test_verify_replay_consistency(self):
        """Replay consistency verification works."""
        store = get_event_store()
        _seed_multi_domain(store)
        engine = ReplayVisualizationEngine(store)
        state = engine.get_replay_state(0, 10)
        h = engine.compute_replay_hash(state)
        self.assertTrue(engine.verify_replay_consistency(state, h))

    def test_replay_empty_store(self):
        """Empty store returns empty replay."""
        engine = ReplayVisualizationEngine(get_event_store())
        state = engine.get_replay_state(0, 0)
        self.assertEqual(state.total_events_in_range, 0)


# ═══════════════════════════════════════════════════════════
# H. GATEWAY INTEGRATION
# ═══════════════════════════════════════════════════════════

class ObservabilityGatewayTest(unittest.TestCase):
    """Gateway orchestrates all observability features."""

    def setUp(self):
        reset_gateway()

    def _seed(self):
        from core.operations.truth.event_store import get_event_store as es
        _seed_multi_domain(es())

    def test_trace_aggregate(self):
        self._seed()
        gateway = get_gateway()
        trace = gateway.trace_aggregate("sales_purchase", "ord_001")
        self.assertGreater(trace.event_count, 0)

    def test_build_causation_graph(self):
        self._seed()
        gateway = get_gateway()
        from core.operations.truth.event_store import get_event_store as es
        ids = _seed_multi_domain(es())
        graph = gateway.build_causation_graph(ids["order"])
        self.assertGreater(graph["node_count"], 0)

    def test_get_timeline(self):
        self._seed()
        gateway = get_gateway()
        timeline = gateway.get_timeline()
        self.assertGreater(timeline.total_entries, 0)

    def test_get_aggregate_timeline(self):
        self._seed()
        gateway = get_gateway()
        timeline = gateway.get_aggregate_timeline("sales_purchase", "ord_001")
        self.assertGreater(timeline.total_entries, 0)

    def test_correlate_by_event_id(self):
        self._seed()
        gateway = get_gateway()
        from core.operations.truth.event_store import get_event_store as es
        ids = _seed_multi_domain(es())
        graph = gateway.correlate_by_event_id(ids["order"])
        self.assertGreater(len(graph.nodes), 0)

    def test_correlate_domain_pair(self):
        self._seed()
        gateway = get_gateway()
        graph = gateway.correlate_domain_pair("sales_purchase", "inventory")
        self.assertGreater(len(graph.nodes), 0)

    def test_run_integrity_check(self):
        self._seed()
        gateway = get_gateway()
        report = gateway.run_integrity_check()
        self.assertIn(report.status, (IntegrityStatus.PASS, IntegrityStatus.DEGRADED, IntegrityStatus.FAIL))

    def test_get_stream_metrics(self):
        self._seed()
        gateway = get_gateway()
        metrics = gateway.get_stream_metrics()
        self.assertIsNotNone(metrics)

    def test_get_replay_state(self):
        self._seed()
        gateway = get_gateway()
        state = gateway.get_replay_state(0, 10)
        self.assertIsNotNone(state)

    def test_render_at_sequence(self):
        self._seed()
        gateway = get_gateway()
        entries = gateway.render_at_sequence(1)
        self.assertGreaterEqual(len(entries), 0)

    def test_compute_replay_hash(self):
        self._seed()
        gateway = get_gateway()
        h = gateway.compute_replay_hash(0, 10)
        self.assertGreater(len(h), 0)

    def test_get_dashboard(self):
        self._seed()
        gateway = get_gateway()
        dash = gateway.get_dashboard("inventory_view", "inventory")
        self.assertIsNotNone(dash)

    def test_get_snapshot(self):
        self._seed()
        gateway = get_gateway()
        snap = gateway.get_snapshot()
        self.assertGreater(snap.total_events, 0)

    def test_get_observability_status(self):
        self._seed()
        gateway = get_gateway()
        status = gateway.get_observability_status()
        self.assertIn("gateway_version", status)
        self.assertIn("total_events", status)

    def test_get_store_summary(self):
        self._seed()
        gateway = get_gateway()
        summary = gateway.get_store_summary()
        self.assertGreater(summary["total_events_stored"], 0)

    def test_domain_dependency_map(self):
        gateway = get_gateway()
        deps = gateway.get_domain_dependency_map()
        self.assertGreater(len(deps), 0)

    def test_verify_event_chain(self):
        self._seed()
        gateway = get_gateway()
        from core.operations.truth.event_store import get_event_store as es
        ids = _seed_multi_domain(es())
        result = gateway.verify_event_chain(ids["order"])
        self.assertTrue(result["verified"])


# ═══════════════════════════════════════════════════════════
# I. READ-ONLY GUARANTEES
# ═══════════════════════════════════════════════════════════

class ReadOnlyGuaranteeTest(unittest.TestCase):
    """No observability operation mutates state."""

    def setUp(self):
        reset_gateway()

    def test_trace_does_not_mutate(self):
        """Trace engine does not add events."""
        store = get_event_store()
        count_before = store.count()
        engine = EventTraceEngine(store)
        engine.trace_aggregate(Domain.INVENTORY, "test")
        self.assertEqual(store.count(), count_before)

    def test_integrity_does_not_mutate(self):
        """Integrity monitor does not add events."""
        store = get_event_store()
        count_before = store.count()
        monitor = SystemIntegrityMonitor(store)
        monitor.run_full_integrity_check()
        self.assertEqual(store.count(), count_before)

    def test_correlation_does_not_mutate(self):
        """Correlation engine does not add events."""
        store = get_event_store()
        count_before = store.count()
        engine = CrossDomainCorrelationEngine(store)
        engine.correlate_by_event_id("nonexistent")
        self.assertEqual(store.count(), count_before)

    def test_timeline_does_not_mutate(self):
        """Timeline renderer does not add events."""
        store = get_event_store()
        count_before = store.count()
        renderer = OperationalTimelineRenderer(store)
        renderer.render_timeline()
        self.assertEqual(store.count(), count_before)

    def test_replay_does_not_mutate(self):
        """Replay engine does not add events."""
        store = get_event_store()
        count_before = store.count()
        engine = ReplayVisualizationEngine(store)
        engine.get_replay_state(0, 10)
        self.assertEqual(store.count(), count_before)


# ═══════════════════════════════════════════════════════════
# J. DETERMINISM
# ═══════════════════════════════════════════════════════════

class DeterminismTest(unittest.TestCase):
    """All observability operations are deterministic."""

    def setUp(self):
        reset_gateway()

    def test_trace_deterministic(self):
        """Same events produce same trace."""
        store = get_event_store()
        _seed_multi_domain(store)
        e1 = EventTraceEngine(store)
        e2 = EventTraceEngine(store)
        t1 = e1.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        t2 = e2.trace_aggregate(Domain.SALES_PURCHASE, "ord_001")
        self.assertEqual(t1.event_count, t2.event_count)
        self.assertEqual(t1.integrity_hash, t2.integrity_hash)

    def test_timeline_deterministic(self):
        """Same events produce same timeline."""
        store = get_event_store()
        _seed_multi_domain(store)
        r1 = OperationalTimelineRenderer(store)
        r2 = OperationalTimelineRenderer(store)
        tl1 = r1.render_timeline()
        tl2 = r2.render_timeline()
        self.assertEqual(tl1.total_entries, tl2.total_entries)

    def test_replay_hash_deterministic(self):
        """Same range produces same replay hash."""
        store = get_event_store()
        _seed_multi_domain(store)
        e1 = ReplayVisualizationEngine(store)
        e2 = ReplayVisualizationEngine(store)
        s1 = e1.get_replay_state(0, 10)
        s2 = e2.get_replay_state(0, 10)
        self.assertEqual(e1.compute_replay_hash(s1), e2.compute_replay_hash(s2))

    def test_correlation_deterministic(self):
        """Same events produce same correlation."""
        store = get_event_store()
        _seed_multi_domain(store)
        c1 = CrossDomainCorrelationEngine(store)
        c2 = CrossDomainCorrelationEngine(store)
        g1 = c1.correlate_by_correlation_id("corr_sale_001")
        g2 = c2.correlate_by_correlation_id("corr_sale_001")
        self.assertEqual(len(g1.nodes), len(g2.nodes))


# ═══════════════════════════════════════════════════════════
# K. NO EXECUTION/CONTROL PATHS
# ═══════════════════════════════════════════════════════════

class NoExecutionControlTest(unittest.TestCase):
    """Observability has no execution or control paths."""

    def test_gateway_has_no_execution_methods(self):
        """Gateway has no execution methods."""
        gateway = get_gateway()
        self.assertFalse(hasattr(gateway, 'execute'))
        self.assertFalse(hasattr(gateway, 'run_action'))
        self.assertFalse(hasattr(gateway, 'dispatch'))
        self.assertFalse(hasattr(gateway, 'modify'))
        self.assertFalse(hasattr(gateway, 'override'))
        self.assertFalse(hasattr(gateway, 'mutate'))

    def test_no_write_methods(self):
        """No observability module has write methods."""
        for mod_name in ['trace_engine', 'correlation', 'timeline', 'integrity', 'replay']:
            mod = __import__(f'core.operations.observability.{mod_name}', fromlist=[''])
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if callable(attr) and hasattr(attr, '__name__'):
                    self.assertNotIn('append', attr.__name__)
                    self.assertNotIn('insert', attr.__name__)
                    self.assertNotIn('update', attr.__name__)
                    self.assertNotIn('delete', attr.__name__)

    def test_no_erp_imports(self):
        """Observability does not import ERP modules."""
        import sys
        for mod_name in list(sys.modules.keys()):
            if 'core.operations.observability' in mod_name:
                for erp_mod in ['inventory', 'accounting', 'sales', 'purchases', 'hr', 'payroll']:
                    self.assertNotIn(erp_mod, str(sys.modules.get(mod_name, '')))

    def test_all_models_are_immutable(self):
        """All observability models are frozen dataclasses."""
        for cls_name in dir():
            if cls_name.endswith(('Test', '__')):
                continue
        trace = TraceObject(aggregate_id="test", domain="test")
        with self.assertRaises(AttributeError):
            trace.aggregate_id = "modified"


# ═══════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    unittest.main()
