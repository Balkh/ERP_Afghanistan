"""
Phase 5A.5 — Event Storm Stability.

Validates runtime stability under:
- Telemetry floods (5000+ signals/second equivalent)
- Timeline bursts (rapid event injection)
- Incident explosion (CRITICAL severity cascade)
- Replay marker storms
- Correlated event cascades

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity


def _make_signal(signal_id: str, tick: int,
                 stype: SignalType = SignalType.ANOMALY,
                 severity: IntelligenceSeverity = IntelligenceSeverity.LOW,
                 source: str = "storm") -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id, signal_type=stype, severity=severity,
        source_phase=source, tick=tick,
        description=f"Storm {signal_id}", payload={"tick": tick},
        timestamp=float(tick),
    )


class TelemetryFloodTest(unittest.TestCase):
    """Runtime survives telemetry data floods."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_5000_rapid_signals(self):
        """5000 rapid-fire signals processed without crash."""
        for i in range(5000):
            sig = _make_signal(f"flood-{i}", i,
                               stype=SignalType.DRIFT_TREND,
                               severity=IntelligenceSeverity.INFO)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"], f"Flood signal {i} failed")

    def test_flood_does_not_overflow_timeline(self):
        """Timeline bounded after telemetry flood."""
        for i in range(5000):
            sig = _make_signal(f"floodtl-{i}", i)
            self.engine.process_signal(sig)
        timeline = self.engine.get_unified_timeline()
        self.assertLessEqual(timeline.get_event_count(), 1000)

    def test_flood_does_not_overflow_state(self):
        """State aggregator bounded after telemetry flood."""
        for i in range(5000):
            sig = _make_signal(f"floodst-{i}", i)
            self.engine.process_signal(sig)
        state = self.engine.get_aggregated_state()
        self.assertLessEqual(state.active_signals, 1000)

    def test_flood_after_clear_recovers(self):
        """Engine recovers after flood followed by clear."""
        for i in range(5000):
            sig = _make_signal(f"floodclr-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        for i in range(100):
            sig = _make_signal(f"floodrecover-{i}", i)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"])

    def test_flood_queries_stable(self):
        """Queries remain stable during flood."""
        for i in range(3000):
            sig = _make_signal(f"floodqr-{i}", i)
            self.engine.process_signal(sig)
            if i % 500 == 0:
                state = self.router.route_query("state")
                self.assertTrue(state["success"])


class TimelineBurstTest(unittest.TestCase):
    """Timeline survives burst injection."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_5000_burst_timeline_events(self):
        """Timeline handles 5000 burst events without overflow."""
        for i in range(5000):
            sig = _make_signal(f"bursttl-{i}", i)
            self.engine.process_signal(sig)
        result = self.router.route_query("timeline")
        self.assertTrue(result["success"])
        data = result["data"]
        self.assertLessEqual(data["event_count"], 1000)

    def test_burst_offset_limit(self):
        """Timeline pagination works after burst."""
        for i in range(3000):
            sig = _make_signal(f"burstpg-{i}", i)
            self.engine.process_signal(sig)
        result = self.router.route_query("timeline", {"limit": 50, "offset": 0})
        self.assertTrue(result["success"])
        events = result["data"].get("events", [])
        self.assertLessEqual(len(events), 50)

    def test_burst_dashboard_after_storm(self):
        """Dashboard generation works after burst."""
        for i in range(3000):
            sig = _make_signal(f"burstdash-{i}", i)
            self.engine.process_signal(sig)
        snap = self.engine.generate_dashboard_snapshot(3000)
        self.assertIsNotNone(snap)


class IncidentExplosionTest(unittest.TestCase):
    """Runtime survives incident burst (all CRITICAL)."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_1000_critical_incidents(self):
        """1000 CRITICAL incidents processed without crash."""
        for i in range(1000):
            sig = _make_signal(f"critical-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"], f"Critical signal {i} failed")

    def test_incident_count_bounded_after_explosion(self):
        """Incident registry bounded after explosion."""
        for i in range(1000):
            sig = _make_signal(f"incx-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            self.engine.process_signal(sig)
        registry = self.engine.get_incident_registry()
        self.assertLessEqual(registry.get_incident_count(), 500)

    def test_incident_query_after_explosion(self):
        """Incident queries succeed after explosion."""
        for i in range(1000):
            sig = _make_signal(f"incq-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            self.engine.process_signal(sig)
        result = self.router.route_query("incidents")
        self.assertTrue(result["success"])

    def test_mixed_severity_incidents(self):
        """Mixed severity incidents are handled correctly."""
        severities = [IntelligenceSeverity.INFO, IntelligenceSeverity.LOW,
                      IntelligenceSeverity.MEDIUM, IntelligenceSeverity.HIGH,
                      IntelligenceSeverity.CRITICAL]
        for i in range(500):
            sev = severities[i % len(severities)]
            sig = _make_signal(f"mixed-{i}", i,
                               stype=SignalType.ANOMALY,
                               severity=sev)
            self.engine.process_signal(sig)
        registry = self.engine.get_incident_registry()
        count = registry.get_incident_count()
        self.assertLessEqual(count, 500)


class CorrelatedEventCascadeTest(unittest.TestCase):
    """Runtime survives correlated event cascades."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_same_tick_cascade(self):
        """Multiple signals at same tick processed safely."""
        for i in range(1000):
            sig = _make_signal(f"cascade-{i}", 0,
                               stype=SignalType.ANOMALY,
                               severity=IntelligenceSeverity.MEDIUM)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"])

    def test_repeating_signal_id(self):
        """Repeating signal IDs do not cause crash."""
        for i in range(1000):
            sig = _make_signal("repeating-id", i)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"])

    def test_mixed_types_cascade(self):
        """Mixed signal types in cascade handled safely."""
        types = [SignalType.ANOMALY, SignalType.DRIFT_TREND,
                 SignalType.INTEGRITY_BREACH, SignalType.PREDICTIVE_WARNING,
                 SignalType.RECOVERY_EVENT, SignalType.ROOT_CAUSE]
        for i in range(600):
            st = types[i % len(types)]
            sig = _make_signal(f"mixedtype-{i}", i, stype=st)
            result = self.engine.process_signal(sig)
            self.assertTrue(result["success"])
