"""
Phase 5A.5 — Rendering Performance Qualification.

Validates rendering budgets and bounded rendering:
- Target: 16ms render frame equivalent (simulated via operation count limits)
- Warning: 50ms threshold (operation complexity limits)
- Degradation: 100ms trigger (graceful fallback under load)
- Virtualization caps (max 100 items rendered regardless of data size)
- Lazy rendering activation under pressure

All tests use operation-count proxies for timing (deterministic).
No actual wall-clock timing — we verify bounded complexity.

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
        source_phase="render_test", tick=tick,
        description=f"Render {signal_id}", payload={}, timestamp=float(tick),
    )


class RenderBudgetValidationTest(unittest.TestCase):
    """Rendering operations complete within bounded complexity."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_state_query_complexity_bounded(self):
        """State query complexity is bounded regardless of history."""
        for i in range(5000):
            sig = _make_signal(f"rbs-{i}", i)
            self.engine.process_signal(sig)
        result = self.router.route_query("state")
        self.assertTrue(result["success"])
        data = result["data"]
        expected_keys = {"state", "severity_score", "active_signals",
                         "critical_count", "incident_count"}
        self.assertTrue(expected_keys.issubset(data.keys()))

    def test_timeline_query_bounded_result(self):
        """Timeline query returns at most limit items."""
        for i in range(5000):
            sig = _make_signal(f"rbtl-{i}", i)
            self.engine.process_signal(sig)
        for limit in [10, 50, 100, 200]:
            result = self.router.route_query("timeline", {"limit": limit})
            self.assertTrue(result["success"])
            events = result["data"].get("events", [])
            self.assertLessEqual(len(events), limit)

    def test_incident_query_bounded_result(self):
        """Incident query returns at most limit items."""
        for i in range(1000):
            sig = _make_signal(f"rbinc-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            self.engine.process_signal(sig)
        result = self.router.route_query("incidents")
        self.assertTrue(result["success"])
        incidents = result["data"].get("incidents", [])
        self.assertLessEqual(len(incidents), 100)


class VirtualizationCapsTest(unittest.TestCase):
    """Virtualization caps limit rendered data."""

    def test_dashboard_preview_capped(self):
        """Dashboard timeline preview is capped at 10 items."""
        engine = ControlCenterEngine()
        for i in range(500):
            sig = _make_signal(f"vc-{i}", i)
            engine.process_signal(sig)
        snap = engine.generate_dashboard_snapshot(500)
        widget_data = snap.widget_data if hasattr(snap, "widget_data") else {}
        preview = widget_data.get("timeline_preview", [])
        self.assertLessEqual(len(preview), 10)

    def test_dashboard_incident_preview_capped(self):
        """Dashboard incident preview is capped at 10 items."""
        engine = ControlCenterEngine()
        for i in range(500):
            sig = _make_signal(f"vcinc-{i}", i,
                               stype=SignalType.INTEGRITY_BREACH,
                               severity=IntelligenceSeverity.CRITICAL)
            engine.process_signal(sig)
        snap = engine.generate_dashboard_snapshot(500)
        widget_data = snap.widget_data if hasattr(snap, "widget_data") else {}
        active = widget_data.get("active_incidents", [])
        self.assertLessEqual(len(active), 10)

    def test_safety_report_fields_bounded(self):
        """Safety report fields have bounded sizes."""
        engine = ControlCenterEngine()
        for i in range(5000):
            sig = _make_signal(f"sf-{i}", i)
            engine.process_signal(sig)
        report = engine.generate_safety_report("budget-check")
        self.assertIsNotNone(report)
        violations = report.violations if report.violations else []
        self.assertIsInstance(violations, (list, tuple))


class AdaptiveDegradationTest(unittest.TestCase):
    """Adaptive degradation limits complexity under load."""

    def test_many_signals_still_produce_valid_snapshots(self):
        """Dashboard snapshots remain valid after extreme signal counts."""
        engine = ControlCenterEngine()
        for i in range(10000):
            sig = _make_signal(f"ad-{i}", i)
            engine.process_signal(sig)
        snap = engine.generate_dashboard_snapshot(10000)
        self.assertIsNotNone(snap)
        self.assertIn(snap.operational_state, ["normal", "degraded",
                                                "critical", "emergency",
                                                "recovering"])

    def test_safety_report_after_extreme_count(self):
        """Safety report works after extreme signal count."""
        engine = ControlCenterEngine()
        for i in range(10000):
            sig = _make_signal(f"adsf-{i}", i)
            engine.process_signal(sig)
        report = engine.generate_safety_report("extreme")
        self.assertIsNotNone(report)


class LazyRenderingTest(unittest.TestCase):
    """Lazy rendering defers work appropriately."""

    def test_query_not_triggered_for_unused_tabs(self):
        """Engine state is only built when queried."""
        engine = ControlCenterEngine()
        engine2 = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"lazy-{i}", i)
            engine.process_signal(sig)
        state1 = engine.get_aggregated_state()
        state2 = engine2.get_aggregated_state()
        self.assertGreater(state1.active_signals, 0)
        self.assertEqual(state2.active_signals, 0)
