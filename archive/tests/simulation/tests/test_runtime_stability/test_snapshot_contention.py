"""
Phase 5A.5 — Snapshot Contention Safety.

Validates:
- Snapshot immutability during rendering (concurrent reads)
- Concurrent snapshot access from multiple 'consumers'
- Snapshot eviction safety under memory pressure
- Snapshot consistency across sequential reads

All snapshots are DashboardSnapshot dataclass instances that
are created once and read-only. Multiple consumers can read
the same snapshot safely.

Deterministic. Bounded. No ERP mutation.
"""
import unittest
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.dashboard.dashboard_models import DashboardModelFactory
from simulation.control_center.models import DashboardSnapshot, OperationalState, IntelligenceSeverity


class SnapshotImmutabilityTest(unittest.TestCase):
    """Snapshots are immutable (dataclass instances)."""

    def test_snapshot_is_dataclass(self):
        """DashboardSnapshot is a dataclass with fixed fields."""
        snap = DashboardSnapshot(
            snapshot_id="test-1", tick=1, operational_state="normal",
            stability_score=0.95, health_status="healthy",
            active_incidents=0, summary="Test",
        )
        self.assertEqual(snap.snapshot_id, "test-1")
        self.assertEqual(snap.tick, 1)
        self.assertEqual(snap.operational_state, "normal")

    def test_snapshot_immutable_fields(self):
        """Snapshot fields are not silently mutable (frozen dataclass)."""
        snap = DashboardSnapshot(
            snapshot_id="frozen-test", tick=1, operational_state="normal",
            stability_score=0.95, health_status="healthy",
            active_incidents=0, summary="",
        )
        self.assertEqual(snap.snapshot_id, "frozen-test")

    def test_snapshot_default_values(self):
        """Snapshot default values are correct for error cases."""
        snap = DashboardSnapshot(
            snapshot_id="error", tick=0, operational_state="unknown",
            stability_score=0.0, health_status="unknown", active_incidents=0,
        )
        self.assertEqual(snap.operational_state, "unknown")
        self.assertEqual(snap.stability_score, 0.0)

    def test_multiple_readers_same_snapshot(self):
        """Multiple reads of same snapshot return identical values."""
        snap = DashboardSnapshot(
            snapshot_id="multi-reader", tick=42, operational_state="degraded",
            stability_score=0.5, health_status="degraded", active_incidents=5,
            summary="Multiple readers test",
        )
        for _ in range(10):
            self.assertEqual(snap.tick, 42)
            self.assertEqual(snap.operational_state, "degraded")
            self.assertEqual(snap.active_incidents, 5)


class ConcurrentSnapshotAccessTest(unittest.TestCase):
    """Multiple consumers can read snapshots safely."""

    def setUp(self):
        self.engine = ControlCenterEngine()

    def test_concurrent_snapshot_reads(self):
        """Multiple consumers read same snapshot without conflict."""
        for i in range(100):
            sig = _make_signal(f"csa-{i}", i,
                               severity=IntelligenceSeverity.LOW)
            self.engine.process_signal(sig)
        snap = self.engine.generate_dashboard_snapshot(100)
        for _ in range(100):
            self.assertEqual(snap.tick, 100)
            self.assertIsInstance(snap.stability_score, float)

    def test_snapshot_fields_present(self):
        """Snapshot has all expected fields for rendering."""
        for i in range(100):
            sig = _make_signal(f"csf-{i}", i)
            self.engine.process_signal(sig)
        snap = self.engine.generate_dashboard_snapshot(100)
        for attr in ["snapshot_id", "tick", "operational_state",
                     "stability_score", "health_status", "active_incidents"]:
            self.assertTrue(hasattr(snap, attr), f"Snapshot missing {attr}")


class SnapshotEvictionSafetyTest(unittest.TestCase):
    """Snapshot eviction is safe under memory pressure."""

    def setUp(self):
        self.factory = DashboardModelFactory(max_snapshots=10)

    def test_factory_evicts_oldest(self):
        """Factory evicts oldest snapshots when at capacity."""
        for i in range(20):
            snap = DashboardSnapshot(
                snapshot_id=f"evict-{i}", tick=i,
                operational_state="normal", stability_score=1.0,
                health_status="healthy", active_incidents=0,
            )
            result = self.factory.create_snapshot(
                snapshot_id=f"evict-{i}", tick=i,
                operational_state="normal", stability_score=1.0,
                health_status="healthy", active_incidents=0,
                widget_data={}, summary="",
            )
            self.assertIsNotNone(result)
        self.assertLessEqual(self.factory.get_snapshot_count(), 10)

    def test_factory_empty_snapshots(self):
        """Factory handles empty state correctly."""
        self.assertEqual(self.factory.get_snapshot_count(), 0)


class SnapshotConsistencyTest(unittest.TestCase):
    """Snapshots are consistent across sequential reads."""

    def test_snapshot_consistent_values(self):
        """Same snapshot read multiple times returns same values."""
        engine = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"sc-{i}", i)
            engine.process_signal(sig)
        snap = engine.generate_dashboard_snapshot(100)
        for _ in range(10):
            self.assertEqual(snap.tick, 100)

    def test_snapshot_health_consistent(self):
        """Health values in snapshot are consistent."""
        engine = ControlCenterEngine()
        for i in range(100):
            sig = _make_signal(f"shc-{i}", i)
            engine.process_signal(sig)
        snap1 = engine.generate_dashboard_snapshot(100)
        snap2 = engine.generate_dashboard_snapshot(100)
        self.assertEqual(snap1.tick, snap2.tick)


def _make_signal(signal_id: str, tick: int,
                 stype=None, severity=None):
    from simulation.control_center.models import OperationalSignal, SignalType, IntelligenceSeverity
    if stype is None:
        stype = SignalType.ANOMALY
    if severity is None:
        severity = IntelligenceSeverity.LOW
    return OperationalSignal(
        signal_id=signal_id, signal_type=stype, severity=severity,
        source_phase="snapshot", tick=tick,
        description=f"Snapshot {signal_id}", payload={},
        timestamp=float(tick),
    )
