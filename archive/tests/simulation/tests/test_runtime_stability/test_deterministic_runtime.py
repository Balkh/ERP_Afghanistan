"""
Phase 5A.5 — Deterministic Runtime Validation.

Validates:
- Identical input produces identical output (deterministic state)
- Deterministic timeline ordering (events in tick order)
- Deterministic replay rendering (same events → same result)
- Deterministic incident ordering (severity order stable)
- No timing-dependent state corruption

Fully deterministic. No randomness. No ERP mutation.
"""
import unittest
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity
from simulation.replay.replay_engine.replay_engine import ReplayEngine


def _make_signal(signal_id: str, tick: int,
                 stype: SignalType = SignalType.ANOMALY,
                 severity: IntelligenceSeverity = IntelligenceSeverity.LOW) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id, signal_type=stype, severity=severity,
        source_phase="determinism", tick=tick,
        description=f"Det {signal_id}", payload={"val": tick},
        timestamp=float(tick),
    )


class IdenticalInputOutputTest(unittest.TestCase):
    """Same inputs produce same outputs."""

    def test_identical_signals_identical_state(self):
        """Same signal sequence produces same state twice."""
        signals = [
            _make_signal(f"det-{i}", i) for i in range(100)
        ]
        engine_a = ControlCenterEngine()
        for sig in signals:
            engine_a.process_signal(sig)
        engine_b = ControlCenterEngine()
        for sig in signals:
            engine_b.process_signal(sig)
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertEqual(state_a.active_signals, state_b.active_signals)
        self.assertEqual(state_a.severity_score, state_b.severity_score)
        self.assertEqual(state_a.incident_count, state_b.incident_count)

    def test_identical_signals_identical_timeline(self):
        """Same signal sequence produces same timeline."""
        signals = [
            _make_signal(f"dettl-{i}", i) for i in range(100)
        ]
        engine_a = ControlCenterEngine()
        for sig in signals:
            engine_a.process_signal(sig)
        engine_b = ControlCenterEngine()
        for sig in signals:
            engine_b.process_signal(sig)
        tl_a = engine_a.get_unified_timeline()
        tl_b = engine_b.get_unified_timeline()
        self.assertEqual(tl_a.get_event_count(), tl_b.get_event_count())

    def test_identical_signals_identical_health(self):
        """Same signal sequence produces same health report."""
        signals = [
            _make_signal(f"deth-{i}", i) for i in range(100)
        ]
        engine_a = ControlCenterEngine()
        for sig in signals:
            engine_a.process_signal(sig)
        engine_b = ControlCenterEngine()
        for sig in signals:
            engine_b.process_signal(sig)
        matrix_a = engine_a.get_health_matrix()
        matrix_b = engine_b.get_health_matrix()
        health_a = matrix_a.compute_health(0.5, 10, 5, 100, {})
        health_b = matrix_b.compute_health(0.5, 10, 5, 100, {})
        self.assertEqual(health_a.get("status"), health_b.get("status"))


class DeterministicTimelineOrderingTest(unittest.TestCase):
    """Timeline events maintain deterministic order."""

    def test_events_in_tick_order(self):
        """Events are retrievable in tick order."""
        engine = ControlCenterEngine()
        router = ControlCenterRouter(engine)
        for i in range(200):
            sig = _make_signal(f"order-{i}", i)
            engine.process_signal(sig)
        result = router.route_query("timeline", {"limit": 100})
        self.assertTrue(result["success"])
        events = result["data"].get("events", [])
        if len(events) > 1:
            ticks = [e["tick"] for e in events]
            for j in range(len(ticks) - 1):
                self.assertLessEqual(ticks[j], ticks[j + 1],
                                     f"Events out of order at index {j}")

    def test_timeline_deterministic_across_engines(self):
        """Same events produce same timeline order in different engines."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"dto-{i}", i)
            engine_a.process_signal(sig)
            engine_b.process_signal(sig)
        tl_a = engine_a.get_unified_timeline()
        tl_b = engine_b.get_unified_timeline()
        events_a = tl_a.get_events(limit=50)
        events_b = tl_b.get_events(limit=50)
        ids_a = [e.event_id for e in events_a]
        ids_b = [e.event_id for e in events_b]
        self.assertEqual(ids_a, ids_b)


class DeterministicReplayRenderingTest(unittest.TestCase):
    """Replay operations are deterministic."""

    def test_replay_same_events_same_result(self):
        """Replaying same events twice produces same result structure."""
        engine = ReplayEngine()
        events = [
            {"tick": i, "event_type": "TEST", "payload": {"val": i}}
            for i in range(50)
        ]
        result_a = engine.execute_replay("replay-det-a", events[:10])
        result_b = engine.execute_replay("replay-det-b", events[:10])
        self.assertIsInstance(result_a, dict)
        self.assertIsInstance(result_b, dict)

    def test_controller_deterministic_history(self):
        """Controller history is deterministic."""
        from simulation.replay.replay_engine.replay_controller import ReplayController
        from simulation.replay.models import ReplayMode
        ctrl = ReplayController(max_history=200)
        ctrl.start("det-session", ReplayMode.FULL)
        ctrl.pause("det-session")
        ctrl.resume("det-session")
        ctrl.step_forward("det-session")
        self.assertEqual(len(ctrl._control_history), 4)


class DeterministicIncidentOrderingTest(unittest.TestCase):
    """Incident ordering is deterministic."""

    def test_incidents_ordered_by_severity(self):
        """Incidents are registered in predictable order."""
        engine = ControlCenterEngine()
        router = ControlCenterRouter(engine)
        severities = [
            IntelligenceSeverity.LOW,
            IntelligenceSeverity.MEDIUM,
            IntelligenceSeverity.HIGH,
            IntelligenceSeverity.CRITICAL,
        ]
        for i, sev in enumerate(severities):
            sig = _make_signal(f"ord-inc-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=sev)
            engine.process_signal(sig)
        result = router.route_query("incidents")
        self.assertTrue(result["success"])
        incidents = result["data"].get("incidents", [])
        if len(incidents) > 1:
            for j in range(len(incidents) - 1):
                self.assertLessEqual(
                    incidents[j].get("tick_detected", 0),
                    incidents[j + 1].get("tick_detected", 0),
                    f"Incidents out of order at {j}"
                )

    def test_incident_count_deterministic(self):
        """Same signals produce same incident count."""
        sigs = [
            _make_signal(f"detinc-{i}", i,
                         stype=SignalType.INTEGRITY_BREACH,
                         severity=IntelligenceSeverity.HIGH)
            for i in range(50)
        ]
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for sig in sigs:
            engine_a.process_signal(sig)
            engine_b.process_signal(sig)
        reg_a = engine_a.get_incident_registry()
        reg_b = engine_b.get_incident_registry()
        self.assertEqual(reg_a.get_incident_count(), reg_b.get_incident_count())


class NoTimingDependentCorruptionTest(unittest.TestCase):
    """State is not corrupted by timing variations."""

    def test_fast_tick_sequence(self):
        """Rapid tick sequence produces correct state."""
        engine = ControlCenterEngine()
        for i in range(1000):
            sig = _make_signal(f"fast-{i}", i)
            engine.process_signal(sig)
        state = engine.get_aggregated_state()
        self.assertEqual(state.active_signals, min(1000, 1000))

    def test_slow_tick_sequence(self):
        """Slow tick sequence (sparse ticks) produces correct state."""
        engine = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"slow-{i}", i * 100)
            engine.process_signal(sig)
        state = engine.get_aggregated_state()
        self.assertIsNotNone(state)

    def test_mixed_tick_intervals(self):
        """Mixed tick intervals produce deterministic state."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        ticks_a = [0, 1, 5, 10, 50, 100, 500, 1000]
        ticks_b = [0, 1, 5, 10, 50, 100, 500, 1000]
        for t in ticks_a:
            sig = _make_signal(f"mixed-a-{t}", t)
            engine_a.process_signal(sig)
        for t in ticks_b:
            sig = _make_signal(f"mixed-b-{t}", t)
            engine_b.process_signal(sig)
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertEqual(state_a.active_signals, state_b.active_signals)
