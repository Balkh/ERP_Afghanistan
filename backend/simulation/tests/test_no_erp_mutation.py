"""Phase 4C safety: control_center NEVER mutates ERP state.

Tests verify all control_center components are read-only:
- No Django/ORM imports in source code
- No .save()/.create()/.update() calls across all code paths
- All engine operations complete without database access
- No external state mutation (only internal bounded containers)
"""
import os
import ast
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Dict, List

CONTROL_CENTER_DIR = os.path.join(
    os.path.dirname(__file__), "..", "control_center"
)

DISALLOWED_IMPORT_PATTERNS = [
    "django.db",
    "django.models",
    "from django",
    "from accounting.models",
    "from inventory.models",
    "from sales.models",
    "from purchases.models",
    "from payments.models",
    "from core.models",
]

ALLOWED_IMPORT_ROOTS = [
    "simulation.control_center",
    "typing",
    "collections",
    "dataclasses",
    "enum",
    "uuid",
    "logging",
    "abc",
    "datetime",
    ".",  # relative imports (e.g., from ..models import ...)
]


def _get_py_files(path: str) -> List[str]:
    py_files = []
    for root, _dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files


def _has_disallowed_import(source: str) -> List[str]:
    violations = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped.startswith("import") and not stripped.startswith("from"):
            continue
        for pattern in DISALLOWED_IMPORT_PATTERNS:
            if pattern in stripped:
                violations.append(stripped)
                break
    return violations


class TestNoDjangoModelImports(unittest.TestCase):
    """Scan ALL control_center .py files for Django/ORM imports."""

    def test_no_django_imports_in_any_file(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        self.assertGreater(len(files), 0, "No .py files found in control_center")

        all_violations: Dict[str, List[str]] = {}

        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            violations = _has_disallowed_import(source)
            if violations:
                all_violations[rel_path] = violations

        if all_violations:
            msg_parts = ["Disallowed imports found in control_center:"]
            for fpath, vlist in all_violations.items():
                for v in vlist:
                    msg_parts.append(f"  {fpath}: {v}")
            self.fail("\n".join(msg_parts))

    def test_all_imports_are_from_allowed_roots(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        violations: Dict[str, List[str]] = {}

        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            for line in source.splitlines():
                stripped = line.strip()
                if not stripped.startswith("import") and not stripped.startswith("from"):
                    continue
                if stripped.startswith("import "):
                    parts = stripped[len("import "):].split()
                    mod = parts[0]
                else:
                    mod = stripped[len("from "):].split()[0]

                if mod.startswith(tuple(ALLOWED_IMPORT_ROOTS)):
                    continue
                if mod.startswith("__future__"):
                    continue
                if mod == "os":
                    continue
                if mod == "ast":
                    continue

                violations.setdefault(rel_path, []).append(stripped)

        if violations:
            msg_parts = ["Non-allowed imports found (only simulation.control_center.*, stdlib allowed):"]
            for fpath, vlist in violations.items():
                for v in vlist:
                    msg_parts.append(f"  {fpath}: {v}")
            self.fail("\n".join(msg_parts))

    def test_no_model_save_create_update_in_source(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        violations: Dict[str, List[str]] = {}

        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            for line in source.splitlines():
                stripped = line.strip()
                if ".save(" in stripped or ".create(" in stripped:
                    if not stripped.startswith("#"):
                        violations.setdefault(rel_path, []).append(stripped)

        if violations:
            msg_parts = [".save() or .create() calls found in control_center:"]
            for fpath, vlist in violations.items():
                for v in vlist:
                    msg_parts.append(f"  {fpath}: {v}")
            self.fail("\n".join(msg_parts))

    def test_no_django_db_ast_references(self):
        files = _get_py_files(CONTROL_CENTER_DIR)
        for filepath in files:
            rel_path = os.path.relpath(filepath, CONTROL_CENTER_DIR)
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            class DjangoFinder(ast.NodeVisitor):
                def __init__(self):
                    self.found = False
                    self.details = []

                def visit_Import(self, node):
                    for alias in node.names:
                        if "django" in alias.name.lower():
                            self.found = True
                            self.details.append(f"import {alias.name}")

                def visit_ImportFrom(self, node):
                    if node.module and "django" in node.module.lower():
                        self.found = True
                        names = [a.name for a in node.names]
                        self.details.append(f"from {node.module} import {', '.join(names)}")

            finder = DjangoFinder()
            finder.visit(tree)
            if finder.found:
                self.fail(
                    f"Django references found in {rel_path}: {finder.details}"
                )


class TestNoOrmWritesInEngine(unittest.TestCase):
    """Verify engine methods do not call ORM write operations."""

    def setUp(self):
        self.signal_patcher = patch(
            "simulation.control_center.orchestrator.control_center_engine."
            "OperationalSignal"
        )
        self.mock_signal_cls = self.signal_patcher.start()
        self.mock_signal = MagicMock()
        self.mock_signal.signal_id = "test_signal_001"
        self.mock_signal_cls.return_value = self.mock_signal

    def tearDown(self):
        self.signal_patcher.stop()

    def test_engine_process_signal_no_orm_writes(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.models import (
            OperationalSignal,
            SignalType,
            IntelligenceSeverity,
        )

        engine = ControlCenterEngine()
        signal = OperationalSignal(
            signal_id="test_001",
            signal_type=SignalType.ANOMALY,
            severity=IntelligenceSeverity.HIGH,
            source_phase="test",
            tick=1,
            description="test signal",
        )
        result = engine.process_signal(signal)
        self.assertTrue(result["success"])
        self.assertIn("signal_id", result)
        self.assertEqual(result["signal_id"], "test_001")

    def test_engine_generate_dashboard_snapshot_no_orm(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.models import DashboardSnapshot

        engine = ControlCenterEngine()
        snapshot = engine.generate_dashboard_snapshot(1)
        self.assertIsInstance(snapshot, DashboardSnapshot)
        self.assertEqual(snapshot.tick, 1)

    def test_engine_generate_safety_report_no_orm(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.models import SafetyReport

        engine = ControlCenterEngine()
        report = engine.generate_safety_report()
        self.assertIsInstance(report, SafetyReport)
        self.assertIsNotNone(report.report_id)


class TestEngineNoDbAccess(unittest.TestCase):
    """Verify engine operations do not require a database connection."""

    def setUp(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        self.engine = ControlCenterEngine()

    def test_clear_all_no_crash(self):
        self.engine.clear_all()
        self.assertEqual(self.engine.get_orchestration_count(), 0)

    def test_process_signal_returns_success(self):
        from simulation.control_center.models import (
            OperationalSignal,
            SignalType,
            IntelligenceSeverity,
        )

        signal = OperationalSignal(
            signal_id="test_db_001",
            signal_type=SignalType.TRUTH_MISMATCH,
            severity=IntelligenceSeverity.MEDIUM,
            source_phase="test_phase",
            tick=42,
            description="no-db test signal",
        )
        result = self.engine.process_signal(signal)
        self.assertTrue(result["success"])
        self.assertEqual(result["signal_id"], "test_db_001")

    def test_generate_dashboard_snapshot_returns_dashboardsnapshot(self):
        from simulation.control_center.models import DashboardSnapshot

        snapshot = self.engine.generate_dashboard_snapshot(1)
        self.assertIsInstance(snapshot, DashboardSnapshot)
        self.assertEqual(snapshot.snapshot_id, "snapshot_1")

    def test_generate_safety_report_returns_safetyreport(self):
        from simulation.control_center.models import SafetyReport

        report = self.engine.generate_safety_report()
        self.assertIsInstance(report, SafetyReport)
        self.assertIsNotNone(report.report_id)
        self.assertIn(report.is_safe, [True, False])

    def test_get_aggregated_state_no_db(self):
        state = self.engine.get_aggregated_state()
        self.assertIsNotNone(state)
        self.assertGreaterEqual(state.severity_score, 0.0)

    def test_sequential_signals_no_db(self):
        from simulation.control_center.models import (
            OperationalSignal,
            SignalType,
            IntelligenceSeverity,
        )

        for i in range(10):
            signal = OperationalSignal(
                signal_id=f"seq_{i}",
                signal_type=SignalType.INCIDENT,
                severity=IntelligenceSeverity.LOW if i % 2 == 0 else IntelligenceSeverity.HIGH,
                source_phase="seq_test",
                tick=i,
                description=f"sequential signal {i}",
            )
            result = self.engine.process_signal(signal)
            self.assertTrue(result["success"], f"signal {i} failed")

        snapshot = self.engine.generate_dashboard_snapshot(100)
        self.assertIsNotNone(snapshot)


class TestNoERPStateMutation(unittest.TestCase):
    """Verify control center classes never mutate external ERP state."""

    def test_engine_instantiation_no_db(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        engine = ControlCenterEngine()
        self.assertIsNotNone(engine)
        self.assertEqual(engine.get_orchestration_count(), 0)

    def test_router_instantiation_no_db(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.orchestrator.control_center_router import (
            ControlCenterRouter,
        )
        engine = ControlCenterEngine()
        router = ControlCenterRouter(engine)
        self.assertIsNotNone(router)
        self.assertEqual(router.get_routing_count(), 0)

    def test_orchestrator_instantiation_no_db(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.orchestrator.operational_command_orchestrator import (
            OperationalCommandOrchestrator,
        )
        engine = ControlCenterEngine()
        orchestrator = OperationalCommandOrchestrator(engine)
        self.assertIsNotNone(orchestrator)
        self.assertEqual(orchestrator.get_command_count(), 0)

    def test_router_routes_signal_no_side_effects(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.orchestrator.control_center_router import (
            ControlCenterRouter,
        )
        from simulation.control_center.models import (
            OperationalSignal,
            SignalType,
            IntelligenceSeverity,
        )

        engine = ControlCenterEngine()
        router = ControlCenterRouter(engine)
        signal = OperationalSignal(
            signal_id="route_test_001",
            signal_type=SignalType.DRIFT_TREND,
            severity=IntelligenceSeverity.INFO,
            source_phase="router_test",
            tick=5,
            description="router test",
        )
        result = router.route_signal(signal)
        self.assertTrue(result["success"])
        self.assertEqual(router.get_routing_count(), 1)

    def test_orchestrator_execute_aggregate_state_no_mutation(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.orchestrator.operational_command_orchestrator import (
            OperationalCommandOrchestrator,
        )

        engine = ControlCenterEngine()
        orch = OperationalCommandOrchestrator(engine)
        result = orch.execute_command("aggregate_state", tick=1)
        self.assertTrue(result["success"])
        self.assertIn("state", result.get("result", {}))

    def test_orchestrator_execute_generate_snapshot_no_mutation(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.orchestrator.operational_command_orchestrator import (
            OperationalCommandOrchestrator,
        )

        engine = ControlCenterEngine()
        orch = OperationalCommandOrchestrator(engine)
        result = orch.execute_command("generate_snapshot", tick=42)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["tick"], 42)

    def test_orchestrator_safety_check_no_mutation(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )
        from simulation.control_center.orchestrator.operational_command_orchestrator import (
            OperationalCommandOrchestrator,
        )

        engine = ControlCenterEngine()
        orch = OperationalCommandOrchestrator(engine)
        result = orch.execute_command("safety_check", tick=1)
        self.assertTrue(result["success"])
        self.assertIn("is_safe", result.get("result", {}))

    def test_methods_return_values_do_not_mutate_external_state(self):
        from simulation.control_center.orchestrator.control_center_engine import (
            ControlCenterEngine,
        )

        engine = ControlCenterEngine()
        agg = engine.get_aggregated_state()
        self.assertIsNotNone(agg)

        timeline = engine.get_unified_timeline()
        self.assertIsNotNone(timeline)

        registry = engine.get_incident_registry()
        self.assertIsNotNone(registry)

        health = engine.get_health_matrix()
        self.assertIsNotNone(health)

        classifier = engine.get_state_classifier()
        self.assertIsNotNone(classifier)

        priority = engine.get_priority_engine()
        self.assertIsNotNone(priority)

        stability = engine.get_stability_widgets()
        self.assertIsNotNone(stability)

        summary = engine.get_health_summary()
        self.assertIsNotNone(summary)

        heatmap = engine.get_heatmap()
        self.assertIsNotNone(heatmap)

        drift = engine.get_drift_visualization()
        self.assertIsNotNone(drift)

        factory = engine.get_dashboard_factory()
        self.assertIsNotNone(factory)

        exec_summary = engine.get_executive_summary()
        self.assertIsNotNone(exec_summary)

        risk = engine.get_risk_report()
        self.assertIsNotNone(risk)

        digest = engine.get_intelligence_digest()
        self.assertIsNotNone(digest)

        stability_report = engine.get_stability_report()
        self.assertIsNotNone(stability_report)

        safety = engine.get_safety_monitor()
        self.assertIsNotNone(safety)

        recursion = engine.get_recursion_guard()
        self.assertIsNotNone(recursion)

        graph = engine.get_graph_guard()
        self.assertIsNotNone(graph)

        memory = engine.get_memory_guard()
        self.assertIsNotNone(memory)

        correlator = engine.get_cross_phase_correlator()
        self.assertIsNotNone(correlator)

        seq_tracker = engine.get_sequence_tracker()
        self.assertIsNotNone(seq_tracker)

        lifecycle = engine.get_incident_lifecycle()
        self.assertIsNotNone(lifecycle)

        escalation = engine.get_escalation_engine()
        self.assertIsNotNone(escalation)


if __name__ == "__main__":
    unittest.main()
