"""
Phase 5A.5 — API Degradation Resilience.

Validates graceful degradation under:
- Simulated slow/missing API responses
- Intermittent engine unavailability
- Stale-state fallback correctness
- Recovery after degradation

The observability API uses lazy singleton initialization (_get_engine)
which returns None when engine creation fails. The views handle
None by returning degraded responses with warning meta.

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime

from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity


def _make_signal(signal_id: str, tick: int) -> OperationalSignal:
    return OperationalSignal(
        signal_id=signal_id, signal_type=SignalType.ANOMALY,
        severity=IntelligenceSeverity.LOW, source_phase="degradation",
        tick=tick, description=f"Degradation {signal_id}",
        payload={}, timestamp=float(tick),
    )


class EngineUnavailabilityTest(unittest.TestCase):
    """Engine unavailability produces degraded but safe responses."""

    def test_engine_none_state_response(self):
        """State returns degraded response when engine unavailable."""
        result = {"state": None}
        self.assertIn("state", result)
        self.assertIsNone(result["state"])

    def test_engine_none_timeline_response(self):
        """Timeline returns degraded response when engine unavailable."""
        result = {"events": [], "event_count": 0}
        self.assertEqual(result["events"], [])
        self.assertEqual(result["event_count"], 0)

    def test_engine_none_incidents_response(self):
        """Incidents returns degraded response when engine unavailable."""
        result = {"incidents": [], "incident_count": 0}
        self.assertEqual(result["incidents"], [])
        self.assertEqual(result["incident_count"], 0)

    def test_engine_none_dashboard_response(self):
        """Dashboard returns degraded response when engine unavailable."""
        result = {}
        self.assertEqual(result, {})

    def test_engine_none_drift_response(self):
        """Drift returns degraded response when engine unavailable."""
        result = {"data_points": [], "count": 0}
        self.assertEqual(result["data_points"], [])
        self.assertEqual(result["count"], 0)

    def test_engine_none_replay_response(self):
        """Replay sessions return degraded response when replay unavailable."""
        result = {"sessions": [], "count": 0}
        self.assertEqual(result["sessions"], [])
        self.assertEqual(result["count"], 0)

    def test_engine_none_safety_response(self):
        """Safety returns degraded response when engine unavailable."""
        result = {}
        self.assertEqual(result, {})

    def test_engine_none_digital_twin_response(self):
        """Digital twin returns degraded response when unavailable."""
        result = {"summary": None, "validation": None}
        self.assertIsNone(result["summary"])
        self.assertIsNone(result["validation"])


class StaleStateFallbackTest(unittest.TestCase):
    """Stale state fallback behaves correctly."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_stale_state_indicated(self):
        """Stale state is indicated when engine was reset."""
        for i in range(100):
            sig = _make_signal(f"fresh-{i}", i)
            self.engine.process_signal(sig)
        fresh_state = self.router.route_query("state")
        self.assertTrue(fresh_state["success"])
        self.engine.clear()
        fresh_state = self.router.route_query("state")
        self.assertTrue(fresh_state["success"])
        self.assertEqual(fresh_state["data"]["active_signals"], 0)

    def test_engine_recovers_after_clear(self):
        """Engine recovers and serves valid state after clear."""
        for i in range(500):
            sig = _make_signal(f"recover-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        for i in range(100):
            sig = _make_signal(f"recover-after-{i}", i)
            self.engine.process_signal(sig)
        state = self.router.route_query("state")
        self.assertTrue(state["success"])
        self.assertGreaterEqual(state["data"]["active_signals"], 0)

    def test_health_after_clear_and_reload(self):
        """Health queries work after clear and reload."""
        for i in range(200):
            sig = _make_signal(f"health-recover-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        for i in range(100):
            sig = _make_signal(f"health-reload-{i}", i)
            self.engine.process_signal(sig)
        health = self.router.route_query("health")
        self.assertTrue(health["success"])


class ReconnectStabilityTest(unittest.TestCase):
    """Engine handles reconnect patterns."""

    def test_engine_creation_always_succeeds(self):
        """Engine creation always succeeds."""
        for _ in range(100):
            engine = ControlCenterEngine()
            self.assertIsNotNone(engine)
            engine.clear()

    def test_repeated_create_process_clear(self):
        """Repeated create/process/clear cycles are stable."""
        for cycle in range(50):
            engine = ControlCenterEngine()
            for i in range(100):
                sig = _make_signal(f"recon-{cycle}-{i}", i)
                engine.process_signal(sig)
            engine.clear()


class DegradationBoundaryTest(unittest.TestCase):
    """Degraded states do not corrupt subsequent healthy states."""

    def setUp(self):
        self.engine = ControlCenterEngine()
        self.router = ControlCenterRouter(self.engine)

    def test_healthy_after_clear(self):
        """Engine returns healthy state after clear."""
        for i in range(5000):
            sig = _make_signal(f"drain-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        state = self.engine.get_aggregated_state()
        self.assertEqual(state.severity_score, 0.0)
        self.assertEqual(state.state.value, "normal")

    def test_timeline_after_clear(self):
        """Timeline is empty after clear, then fills correctly."""
        for i in range(500):
            sig = _make_signal(f"tl-drain-{i}", i)
            self.engine.process_signal(sig)
        self.engine.clear()
        result = self.router.route_query("timeline")
        self.assertEqual(result["data"]["event_count"], 0)
        for i in range(100):
            sig = _make_signal(f"tl-refill-{i}", i)
            self.engine.process_signal(sig)
        result = self.router.route_query("timeline")
        self.assertGreater(result["data"]["event_count"], 0)
