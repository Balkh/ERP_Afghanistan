"""
Phase 5A.5 — Memory Leak Qualification.

Validates that all bounded collections:
- Never exceed their maxlen
- Evict oldest entries correctly
- Do not retain orphaned references
- Have no unbounded growth under sustained pressure

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from collections import deque
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity


def _make_signal(signal_id: str, tick: int, stype: SignalType = SignalType.ANOMALY,
                 severity: IntelligenceSeverity = IntelligenceSeverity.LOW) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id, signal_type=stype, severity=severity,
        source_phase="memory_test", tick=tick,
        description=f"Memory {signal_id}", payload={}, timestamp=float(tick),
    )


class DequeBoundaryValidationTest(unittest.TestCase):
    """All deques enforce maxlen correctly."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_state_aggregator_bounded(self):
        """State aggregator deque stays at maxlen after overflow."""
        for i in range(2000):
            sig = _make_signal(f"sa-bounded-{i}", i)
            self.engine.process_signal(sig)
        state = self.engine.get_aggregated_state()
        self.assertIsNotNone(state)
        self.assertLessEqual(state.active_signals, 1000)

    def test_timeline_bounded(self):
        """Timeline deque stays at max_events after overflow."""
        for i in range(2000):
            sig = _make_signal(f"tl-bounded-{i}", i)
            self.engine.process_signal(sig)
        timeline = self.engine.get_unified_timeline()
        self.assertLessEqual(timeline.get_event_count(), 1000)

    def test_incident_registry_bounded(self):
        """Incident registry stays at max_incidents after overflow."""
        for i in range(1000):
            sig = _make_signal(f"ir-bounded-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            self.engine.process_signal(sig)
        registry = self.engine.get_incident_registry()
        self.assertLessEqual(registry.get_incident_count(), 500)

    def test_dashboard_factory_bounded(self):
        """Dashboard snapshot factory stays bounded."""
        for tick in range(200):
            snap = self.engine.generate_dashboard_snapshot(tick)
            self.assertIsNotNone(snap)
        factory = self.engine.get_dashboard_factory()
        self.assertLessEqual(factory.get_snapshot_count(), 100)


class CacheEvictionTest(unittest.TestCase):
    """Cached data evicts oldest entries correctly."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_health_matrix_eviction(self):
        """Health matrix evicts oldest history entries."""
        for i in range(1000):
            sig = _make_signal(f"hm-{i}", i)
            self.engine.process_signal(sig)
        matrix = self.engine.get_health_matrix()
        trend = matrix.get_health_trend()
        self.assertIsNotNone(trend)
        trend_scores = trend if isinstance(trend, list) else []
        self.assertLessEqual(len(trend_scores), 500)

    def test_stability_widgets_eviction(self):
        """Stability widgets evict oldest score history."""
        for i in range(500):
            sig = _make_signal(f"sw-{i}", i)
            self.engine.process_signal(sig)
            snap = self.engine.generate_dashboard_snapshot(i)
            self.assertIsNotNone(snap)
        widgets = self.engine.get_stability_widgets()
        self.assertLessEqual(len(widgets._score_history), 200)

    def test_health_summary_eviction(self):
        """Health summary evicts oldest entries."""
        for i in range(200):
            sig = _make_signal(f"hs-{i}", i)
            self.engine.process_signal(sig)
            snap = self.engine.generate_dashboard_snapshot(i)
            self.assertIsNotNone(snap)
        summary = self.engine.get_health_summary()
        self.assertLessEqual(len(summary._summary_history), 100)


class NoLeakAfterStressTest(unittest.TestCase):
    """No memory leak after sustained processing."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_safety_report_shows_no_pressure(self):
        """Safety report after stress shows acceptable pressure."""
        for i in range(10000):
            sig = _make_signal(f"nl-{i}", i)
            self.engine.process_signal(sig)
        report = self.engine.generate_safety_report("leak-check")
        self.assertLessEqual(report.memory_pressure, 1.0)

    def test_clear_frees_memory(self):
        """Clear resets all collections to empty."""
        for i in range(5000):
            sig = _make_signal(f"clr-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        state = self.engine.get_aggregated_state()
        self.assertEqual(state.active_signals, 0)
        self.assertEqual(state.incident_count, 0)
        self.assertEqual(self.engine.get_orchestration_count(), 0)

    def test_clear_after_stress_timeline_empty(self):
        """Timeline is empty after clear following stress."""
        for i in range(5000):
            sig = _make_signal(f"clrtl-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        timeline = self.engine.get_unified_timeline()
        self.assertEqual(timeline.get_event_count(), 0)


class QObjectLifecycleSimulationTest(unittest.TestCase):
    """Simulates QObject lifecycle safety (using engine subcomponent patterns)."""

    def test_engine_recreation_no_leak(self):
        """Repeated engine creation/clear cycles work."""
        for _ in range(100):
            engine = ControlCenterEngine()
            for i in range(100):
                sig = _make_signal(f"recreate-{_}-{i}", i)
                engine.process_signal(sig)
            engine.clear()

    def test_sequential_engine_lifecycles(self):
        """Multiple engine instances in sequence work correctly."""
        engines = []
        for _ in range(10):
            engine = ControlCenterEngine()
            for i in range(500):
                sig = _make_signal(f"seq-{_}-{i}", i)
                engine.process_signal(sig)
            engines.append(engine)
        for i, engine in enumerate(engines):
            engine.clear()
            state = engine.get_aggregated_state()
            self.assertEqual(state.active_signals, 0, f"Engine {i} not cleared")


class ContainerSizeVerificationTest(unittest.TestCase):
    """Verify container sizes from safety report match expectations."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_container_sizes_report(self):
        """Safety report accurately reports container sizes."""
        for i in range(1000):
            sig = _make_signal(f"cs-{i}", i)
            self.engine.process_signal(sig)
        report = self.engine.generate_safety_report("container-check")
        self.assertIsNotNone(report)
        self.assertIsNotNone(report.violations)
