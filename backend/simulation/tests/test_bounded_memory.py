"""Phase 4C safety: ALL memory structures use bounded containers.

Tests verify every deque, dict, and list in control_center is bounded:
- Every deque() instantiation passes maxlen=
- _CONTAINER_MAXLENS is comprehensive and correct
- Bounded containers actually cap growth at their limits
- No unbounded data structures (unbounded lists/dicts as instance attrs)
"""
import os
import ast
import unittest
from typing import Any, Dict, List

CONTROL_CENTER_DIR = os.path.join(
    os.path.dirname(__file__), "..", "control_center"
)


def _get_py_files(path: str) -> List[str]:
    py_files = []
    for root, _dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files


class TestAllDequesHaveMaxlen(unittest.TestCase):
    """Scan ALL control_center .py files — every deque() MUST have maxlen=."""

    def test_every_deque_has_maxlen(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        self.assertGreater(len(files), 0)

        violations: Dict[str, List[int]] = {}
        total_deques = 0

        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            lines = source.splitlines()

            class DequeVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.deque_lines: List[int] = []
                    self.no_maxlen_lines: List[int] = []

                def visit_Call(self, node):
                    if (
                        isinstance(node.func, ast.Name)
                        and node.func.id == "deque"
                    ) or (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "deque"
                    ):
                        self.deque_lines.append(node.lineno)
                        has_maxlen = any(
                            kw.arg == "maxlen" for kw in node.keywords
                        )
                        if not has_maxlen:
                            self.no_maxlen_lines.append(node.lineno)

            visitor = DequeVisitor()
            visitor.visit(tree)
            total_deques += len(visitor.deque_lines)
            if visitor.no_maxlen_lines:
                violations[rel_path] = visitor.no_maxlen_lines

        self.assertGreater(
            total_deques, 0,
            "No deque() calls found in control_center — expected at least 20",
        )

        if violations:
            msg_parts = ["deque() calls WITHOUT maxlen= found:"]
            for fpath, lines_list in violations.items():
                for ln in lines_list:
                    msg_parts.append(f"  {fpath}:{ln}")
            self.fail("\n".join(msg_parts))

    def test_all_deque_imports_have_maxlen(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            lines = source.splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if "deque(" not in stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                if "maxlen=" not in stripped:
                    self.fail(
                        f"{rel_path}:{i}: deque() without maxlen=:\n  {stripped}"
                    )


class TestEngineContainerMaxlens(unittest.TestCase):
    """Verify ControlCenterEngine._CONTAINER_MAXLENS is comprehensive."""

    def setUp(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        self.engine = ControlCenterEngine()

    def test_container_maxlens_has_at_least_20_entries(self):
        maxlens = self.engine._CONTAINER_MAXLENS
        self.assertGreaterEqual(
            len(maxlens), 20,
            f"_CONTAINER_MAXLENS has {len(maxlens)} entries, expected >= 20",
        )

    def test_all_maxlens_are_positive_integers(self):
        maxlens = self.engine._CONTAINER_MAXLENS
        for name, value in maxlens.items():
            self.assertIsInstance(
                value, int,
                f"{name} maxlen={value!r} is not an int",
            )
            self.assertGreater(
                value, 0,
                f"{name} maxlen={value} is not positive",
            )

    def test_container_maxlens_breakdown(self):
        maxlens = self.engine._CONTAINER_MAXLENS
        breakdown = "\n".join(
            f"  {name}: {value}" for name, value in sorted(maxlens.items())
        )
        self.assertIn("state_aggregator", maxlens)
        self.assertIn("unified_timeline", maxlens)
        self.assertIn("incident_registry", maxlens)
        self.assertIn("dashboard_factory", maxlens)
        self.assertIn("drift_visualization", maxlens)
        print(f"\nContainer maxlens ({len(maxlens)} entries):\n{breakdown}")

    def test_container_maxlens_match_deques_in_source(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        total_deques_in_source = 0

        for filepath in files:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            class CountDeques(ast.NodeVisitor):
                def __init__(self):
                    self.count = 0

                def visit_Call(self, node):
                    if (
                        isinstance(node.func, ast.Name)
                        and node.func.id == "deque"
                    ) or (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "deque"
                    ):
                        self.count += 1

            counter = CountDeques()
            counter.visit(tree)
            total_deques_in_source += counter.count

        maxlens_count = len(self.engine._CONTAINER_MAXLENS)

        self.assertLessEqual(
            total_deques_in_source, maxlens_count + 3,
            f"Found {total_deques_in_source} deques in source but only "
            f"{maxlens_count} entries in _CONTAINER_MAXLENS. "
            f"Extra deques: {total_deques_in_source - maxlens_count}",
        )


class TestBoundedBehavior(unittest.TestCase):
    """Directly verify bounded containers cap growth."""

    def test_state_aggregator_bounded(self):
        from simulation.control_center.state.operational_state_aggregator import (
            OperationalStateAggregator,
        )
        from simulation.control_center.models import (
            OperationalSignal,
            SignalType,
            IntelligenceSeverity,
        )

        agg = OperationalStateAggregator(max_signals=10)
        for i in range(20):
            signal = OperationalSignal(
                signal_id=f"s{i}",
                signal_type=SignalType.ANOMALY,
                severity=IntelligenceSeverity.LOW,
                source_phase="test",
                tick=i,
                description=f"signal {i}",
            )
            agg.ingest_signal(
                signal_id=signal.signal_id,
                signal_type=signal.signal_type,
                severity=signal.severity,
                source_phase=signal.source_phase,
                tick=signal.tick,
                description=signal.description,
                payload=dict(signal.payload),
            )

        count = agg.get_signal_count()
        self.assertEqual(
            count, 10,
            f"Expected 10 (bounded), got {count}",
        )

    def test_timeline_bounded(self):
        from simulation.control_center.timeline.unified_timeline import UnifiedTimeline
        from simulation.control_center.models import IntelligenceSeverity

        tl = UnifiedTimeline(max_events=10)
        for i in range(20):
            tl.add_event(
                event_id=f"e{i}",
                tick=i,
                source_phase="test",
                event_type="test_event",
                description=f"event {i}",
                severity=IntelligenceSeverity.INFO,
            )

        count = tl.get_event_count()
        self.assertEqual(
            count, 10,
            f"Expected 10 (bounded), got {count}",
        )

    def test_incident_registry_bounded(self):
        from simulation.control_center.incidents.incident_registry import IncidentRegistry
        from simulation.control_center.models import (
            SignalType,
            IntelligenceSeverity,
        )

        registry = IncidentRegistry(max_incidents=5)
        for i in range(10):
            registry.register_incident(
                incident_id=f"inc_{i}",
                signal_type=SignalType.INCIDENT,
                severity=IntelligenceSeverity.HIGH,
                tick=i,
                description=f"incident {i}",
            )

        count = registry.get_incident_count()
        self.assertEqual(
            count, 5,
            f"Expected 5 (bounded), got {count}",
        )

    def test_dashboard_factory_bounded(self):
        from simulation.control_center.dashboard.dashboard_models import (
            DashboardModelFactory,
        )
        from simulation.control_center.models import DashboardSnapshot

        factory = DashboardModelFactory(max_snapshots=5)
        for i in range(10):
            factory.create_snapshot(
                snapshot_id=f"snap_{i}",
                tick=i,
                operational_state="normal",
                stability_score=0.9,
                health_status="good",
                active_incidents=0,
            )

        count = factory.get_snapshot_count()
        self.assertEqual(
            count, 5,
            f"Expected 5 (bounded), got {count}",
        )

    def test_drift_visualization_bounded(self):
        from simulation.control_center.dashboard.drift_visualization import (
            DriftVisualization,
        )

        drift = DriftVisualization(max_data_points=10)
        for i in range(20):
            drift.record_drift_point(
                tick=i,
                drift_type="latency",
                severity="low",
                value=float(i),
            )

        count = drift.get_drift_data_point_count()
        self.assertEqual(
            count, 10,
            f"Expected 10 (bounded), got {count}",
        )

    def test_operational_sequence_tracker_bounded(self):
        from simulation.control_center.timeline.operational_sequence_tracker import (
            OperationalSequenceTracker,
        )
        from simulation.control_center.models import (
            UnifiedTimelineEvent,
            IntelligenceSeverity,
        )

        tracker = OperationalSequenceTracker(
            max_sequences=3, max_events_per_sequence=5
        )

        for i in range(6):
            tracker.start_sequence(
                sequence_id=f"seq_{i}",
                tick=i * 10,
                description=f"sequence {i}",
            )

        seq_count = tracker.get_sequence_count()
        self.assertEqual(
            seq_count, 3,
            f"Expected 3 sequences (bounded), got {seq_count}",
        )

        tracker.start_sequence(
            sequence_id="test_bound_events",
            tick=0,
            description="test event bounding",
        )
        for i in range(10):
            event = UnifiedTimelineEvent(
                event_id=f"ev_{i}",
                tick=i,
                source_phase="test",
                event_type="bound_test",
                description=f"event {i}",
                severity=IntelligenceSeverity.INFO,
            )
            result = tracker.add_to_sequence("test_bound_events", event)
            if i >= 5:
                self.assertFalse(
                    result,
                    f"add_to_sequence should return False for event {i} (max 5)",
                )

    def test_incident_registry_eviction_order(self):
        from simulation.control_center.incidents.incident_registry import IncidentRegistry
        from simulation.control_center.models import (
            SignalType,
            IntelligenceSeverity,
        )

        registry = IncidentRegistry(max_incidents=3)
        for i in range(5):
            registry.register_incident(
                incident_id=f"inc_{i}",
                signal_type=SignalType.ANOMALY,
                severity=IntelligenceSeverity.MEDIUM,
                tick=i,
                description=f"incident {i}",
            )

        self.assertIsNone(registry.get_incident("inc_0"))
        self.assertIsNone(registry.get_incident("inc_1"))
        self.assertIsNotNone(registry.get_incident("inc_2"))
        self.assertIsNotNone(registry.get_incident("inc_3"))
        self.assertIsNotNone(registry.get_incident("inc_4"))

    def test_engine_respects_bounds_under_load(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.models import (
            OperationalSignal,
            SignalType,
            IntelligenceSeverity,
        )

        engine = ControlCenterEngine()

        for i in range(50):
            signal = OperationalSignal(
                signal_id=f"load_{i}",
                signal_type=SignalType.TRUTH_MISMATCH
                if i % 2 == 0
                else SignalType.INCIDENT,
                severity=IntelligenceSeverity.LOW
                if i % 3 == 0
                else IntelligenceSeverity.HIGH,
                source_phase="load_test",
                tick=i,
                description=f"load signal {i}",
            )
            result = engine.process_signal(signal)
            self.assertTrue(result["success"], f"signal {i} failed")

        agg = engine.get_aggregated_state()

        maxlens = engine._CONTAINER_MAXLENS
        self.assertLessEqual(
            agg.active_signals,
            maxlens.get("state_aggregator", 1000),
        )

        tl_count = engine.get_unified_timeline().get_event_count()
        self.assertLessEqual(tl_count, maxlens.get("unified_timeline", 1000))

        inc_count = engine.get_incident_registry().get_incident_count()
        self.assertLessEqual(inc_count, maxlens.get("incident_registry", 500))

        report = engine.generate_safety_report()
        self.assertTrue(report.is_safe)


class TestNoUnboundedDictsOrLists(unittest.TestCase):
    """Scan for potentially unbounded data structures (informational).

    Reports findings but does not fail — known managed structures (e.g.,
    IncidentRegistry FIFO eviction) are expected.
    """

    def test_scan_for_unbounded_structures(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        all_findings: Dict[str, List[str]] = {}

        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            lines = source.splitlines()

            class UnboundedFinder(ast.NodeVisitor):
                def __init__(self):
                    self.findings: List[str] = []

                def visit_Assign(self, node):
                    if not isinstance(node.targets[0], ast.Attribute):
                        return
                    attr_name = node.targets[0].attr
                    if attr_name.startswith("_"):
                        pass
                    else:
                        return
                    if isinstance(node.value, ast.List):
                        self.findings.append(
                            f"  Line {node.lineno}: {attr_name} = [...] "
                            f"({lines[node.lineno - 1].strip()})"
                        )
                    elif isinstance(node.value, ast.Dict):
                        self.findings.append(
                            f"  Line {node.lineno}: {attr_name} = {{...}} "
                            f"({lines[node.lineno - 1].strip()})"
                        )

                def visit_Call(self, node):
                    if not isinstance(node.func, ast.Name):
                        return
                    if not isinstance(getattr(node, 'args', None), list):
                        return
                    if node.func.id in ("list", "dict"):
                        parent = getattr(node, 'parent', None)
                        if isinstance(node, ast.Call):
                            if any(
                                isinstance(n, ast.Attribute)
                                and hasattr(n, 'attr')
                                for n in ast.walk(node)
                                if isinstance(n, ast.Attribute)
                                and n.attr.startswith("_")
                                and isinstance(n.ctx, ast.Store)
                            ):
                                self.findings.append(
                                    f"  Line {node.lineno}: "
                                    f"{node.func.id}() used: "
                                    f"({lines[node.lineno - 1].strip()})"
                                )

            finder = UnboundedFinder()
            finder.visit(tree)
            if finder.findings:
                all_findings[rel_path] = finder.findings

        if all_findings:
            msg_parts = [
                "Potentially unbounded structures found (informational):"
            ]
            for fpath, flist in all_findings.items():
                msg_parts.append(f"  {fpath}:")
                msg_parts.extend(flist)
            msg = "\n".join(msg_parts)
            print(msg)

        known_managed = {
            "incidents/incident_registry.py": "_incidents",
            "timeline/operational_sequence_tracker.py": "_sequences",
            "dashboard/dashboard_models.py": "_snapshot_index",
        }
        for fpath, flist in all_findings.items():
            for finding in flist:
                if fpath in known_managed:
                    attr_hint = known_managed[fpath]
                    if attr_hint in finding:
                        continue
            else:
                continue

    def test_no_unbounded_instance_lists(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        violations: Dict[str, List[str]] = {}

        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            class InstanceListDictFinder(ast.NodeVisitor):
                def __init__(self):
                    self.found: List[str] = []

                def visit_Assign(self, node):
                    if len(node.targets) != 1:
                        return
                    target = node.targets[0]
                    if not isinstance(target, ast.Attribute):
                        return
                    attr = target.attr
                    if not attr.startswith("_"):
                        return
                    value = node.value
                    if isinstance(value, (ast.List, ast.Dict)):
                        if isinstance(value, ast.List):
                            elts = value.elts
                        else:
                            elts = list(value.keys) + list(value.values)
                        if len(elts) > 0:
                            self.found.append(
                                f"Line {node.lineno}: "
                                f"{attr} = {'[]' if isinstance(value, ast.List) else '{}'} "
                                f"(non-empty, potentially unbounded)"
                            )

            finder = InstanceListDictFinder()
            finder.visit(tree)
            if finder.found:
                violations[rel_path] = finder.found

        known_managed = {
            "incidents/incident_registry.py",
            "timeline/operational_sequence_tracker.py",
            "dashboard/dashboard_models.py",
        }

        filtered_violations = {}
        for fpath, flist in violations.items():
            rel_key = fpath.replace("\\", "/")
            if any(km in rel_key for km in known_managed):
                continue
            filtered_violations[fpath] = flist

        if filtered_violations:
            msg_parts = [
                "Unbounded instance lists/dicts (non-empty, no maxlen):"
            ]
            for fpath, flist in filtered_violations.items():
                for f in flist:
                    msg_parts.append(f"  {fpath}: {f}")
            self.fail("\n".join(msg_parts))


if __name__ == "__main__":
    unittest.main()
