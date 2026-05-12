"""
Phase 5A.5 — Multi-Window Runtime Safety.

Validates that multiple independent engine instances
(analogous to multiple UI windows):
- Maintain shared-state isolation
- Do not interfere with each other
- Can coexist concurrently
- Produce independent deterministic results

Each "window" is represented by an independent ControlCenterEngine instance.

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity


def _make_signal(signal_id: str, tick: int,
                 stype: SignalType = SignalType.ANOMALY,
                 severity: IntelligenceSeverity = IntelligenceSeverity.LOW) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id, signal_type=stype, severity=severity,
        source_phase="multi_window", tick=tick,
        description=f"MW {signal_id}", payload={}, timestamp=float(tick),
    )


class ConcurrentDashboardIsolationTest(unittest.TestCase):
    """Multiple engine instances do not interfere."""

    def test_two_engines_independent(self):
        """Two independent engines process signals independently."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(500):
            sig = _make_signal(f"a-{i}", i)
            engine_a.process_signal(sig)
        for i in range(100):
            sig = _make_signal(f"b-{i}", i)
            engine_b.process_signal(sig)
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertGreater(state_a.active_signals, state_b.active_signals)

    def test_three_engines_no_cross_contamination(self):
        """Three engines maintain strict isolation."""
        engines = [ControlCenterEngine() for _ in range(3)]
        for idx, engine in enumerate(engines):
            for i in range(200 * (idx + 1)):
                sig = _make_signal(f"e{idx}-{i}", i)
                engine.process_signal(sig)
        counts = [e.get_aggregated_state().active_signals for e in engines]
        self.assertGreater(counts[2], counts[1])
        self.assertGreater(counts[1], counts[0])

    def test_engines_with_different_signals(self):
        """Different signal patterns on each engine produce different states."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(500):
            sig = _make_signal(f"high-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            engine_a.process_signal(sig)
        for i in range(500):
            sig = _make_signal(f"low-{i}", i,
                               stype=SignalType.DRIFT_TREND,
                               severity=IntelligenceSeverity.INFO)
            engine_b.process_signal(sig)
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertNotEqual(state_a.severity_score, state_b.severity_score)


class SharedTelemetryIsolationTest(unittest.TestCase):
    """Telemetry data from one engine does not leak to another."""

    def test_engine_clear_does_not_affect_others(self):
        """Clearing one engine does not affect another."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(500):
            sig = _make_signal(f"sa-{i}", i)
            engine_a.process_signal(sig)
        for i in range(500):
            sig = _make_signal(f"sb-{i}", i)
            engine_b.process_signal(sig)
        engine_a.clear()
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertEqual(state_a.active_signals, 0)
        self.assertGreater(state_b.active_signals, 0)

    def test_engine_reports_independent(self):
        """Safety reports from different engines are independent."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(1000):
            sig = _make_signal(f"ra-{i}", i)
            engine_a.process_signal(sig)
        report_a = engine_a.generate_safety_report("a")
        report_b = engine_b.generate_safety_report("b")
        self.assertNotEqual(report_a.recursion_depth, report_b.recursion_depth)


class IndependentRenderingSafetyTest(unittest.TestCase):
    """Each 'window' produces deterministic independent results."""

    def test_same_input_same_output(self):
        """Two engines with same input produce same output."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"iso-{i}", i)
            engine_a.process_signal(sig)
            engine_b.process_signal(sig)
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertEqual(state_a.active_signals, state_b.active_signals)
        self.assertEqual(state_a.severity_score, state_b.severity_score)

    def test_different_input_different_output(self):
        """Engines with different inputs produce different outputs."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(100):
            sig_a = _make_signal(f"da-{i}", i)
            sig_b = _make_signal(f"db-{i}", i)
            engine_a.process_signal(sig_a)
            if i < 50:
                engine_b.process_signal(sig_b)
        state_a = engine_a.get_aggregated_state()
        state_b = engine_b.get_aggregated_state()
        self.assertNotEqual(state_a.active_signals, state_b.active_signals)


class WindowLifecycleTest(unittest.TestCase):
    """Engine lifecycle (create/use/destroy) is safe."""

    def test_repeated_create_destroy(self):
        """Repeated engine creation and destruction is safe."""
        for _ in range(20):
            engine = ControlCenterEngine()
            for i in range(100):
                sig = _make_signal(f"lifecycle-{_}-{i}", i)
                engine.process_signal(sig)
            engine.clear()

    def test_many_engines_simultaneously(self):
        """Many engines coexist simultaneously."""
        engines = [ControlCenterEngine() for _ in range(20)]
        for idx, engine in enumerate(engines):
            for i in range(50):
                sig = _make_signal(f"me-{idx}-{i}", i)
                engine.process_signal(sig)
        for idx, engine in enumerate(engines):
            state = engine.get_aggregated_state()
            self.assertGreaterEqual(state.active_signals, 0,
                                    f"Engine {idx} has invalid state")


class NoEventAmplificationTest(unittest.TestCase):
    """Events from one engine do not amplify in another."""

    def test_no_duplicated_events(self):
        """Events are not duplicated across engine instances."""
        engine_a = ControlCenterEngine()
        engine_b = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"ne-{i}", i)
            engine_a.process_signal(sig)
        engine_b.process_signal(_make_signal("single", 0))
        timeline_a = engine_a.get_unified_timeline()
        timeline_b = engine_b.get_unified_timeline()
        self.assertGreater(timeline_a.get_event_count(), timeline_b.get_event_count())
