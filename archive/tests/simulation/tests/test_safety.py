"""Tests for control center safety subpackage."""
import unittest

from simulation.control_center.models import SafetyReport
from simulation.control_center.safety.recursion_guard import RecursionGuard
from simulation.control_center.safety.graph_explosion_guard import GraphExplosionGuard
from simulation.control_center.safety.memory_pressure_guard import MemoryPressureGuard
from simulation.control_center.safety.orchestration_safety_monitor import (
    OrchestrationSafetyMonitor,
)


class TestRecursionGuard(unittest.TestCase):
    def setUp(self):
        self.guard = RecursionGuard(max_depth=10)

    def test_depth_within_limit(self):
        result = self.guard.check_depth(5)
        self.assertTrue(result['safe'])
        self.assertFalse(result['violation'])
        self.assertEqual(result['depth'], 5)
        self.assertEqual(result['max_depth'], 10)

    def test_depth_exceeds_max(self):
        result = self.guard.check_depth(15)
        self.assertFalse(result['safe'])
        self.assertTrue(result['violation'])

    def test_record_call_increments_call_count(self):
        self.assertEqual(self.guard.get_call_count(), 0)
        self.guard.record_call('func_a', 3)
        self.assertEqual(self.guard.get_call_count(), 1)
        self.guard.record_call('func_b', 5)
        self.assertEqual(self.guard.get_call_count(), 2)

    def test_default_max_depth(self):
        default_guard = RecursionGuard()
        result = default_guard.check_depth(50)
        self.assertTrue(result['safe'])
        result = default_guard.check_depth(150)
        self.assertFalse(result['safe'])

    def test_clear(self):
        self.guard.record_call('f', 1)
        self.guard.record_call('g', 2)
        self.assertEqual(self.guard.get_call_count(), 2)
        self.guard.clear()
        self.assertEqual(self.guard.get_call_count(), 0)

    def test_record_call_returns_dict(self):
        record = self.guard.record_call('main', 7)
        self.assertEqual(record['caller'], 'main')
        self.assertEqual(record['depth'], 7)

    def test_get_max_depth(self):
        self.assertEqual(self.guard.get_max_depth(), 10)


class TestGraphExplosionGuard(unittest.TestCase):
    def setUp(self):
        self.guard = GraphExplosionGuard(max_nodes=100, max_edges=500)

    def test_within_limits(self):
        result = self.guard.check_graph_size(node_count=10, edge_count=20)
        self.assertTrue(result['safe'])
        self.assertEqual(len(result['violations']), 0)
        self.assertEqual(result['node_count'], 10)
        self.assertEqual(result['edge_count'], 20)

    def test_node_count_exceeds_max(self):
        result = self.guard.check_graph_size(node_count=200, edge_count=20)
        self.assertFalse(result['safe'])
        self.assertIn('node_count', result['violations'][0])

    def test_edge_count_exceeds_max(self):
        result = self.guard.check_graph_size(node_count=10, edge_count=1000)
        self.assertFalse(result['safe'])
        self.assertIn('edge_count', result['violations'][0])

    def test_detect_cycle_finds_cycle(self):
        adjacency = {'A': ['B'], 'B': ['C'], 'C': ['A']}
        result = self.guard.detect_cycle(adjacency)
        self.assertTrue(result['has_cycle'])
        self.assertFalse(result['aborted'])

    def test_no_cycle_in_acyclic_graph(self):
        adjacency = {'A': ['B'], 'B': ['C'], 'C': []}
        result = self.guard.detect_cycle(adjacency)
        self.assertFalse(result['has_cycle'])
        self.assertFalse(result['aborted'])

    def test_max_traversal_abort(self):
        adjacency = {str(i): [str(i + 1)] for i in range(200)}
        result = self.guard.detect_cycle(adjacency, max_traversal=10)
        self.assertTrue(result['aborted'])

    def test_record_graph_check_and_get_check_count(self):
        self.assertEqual(self.guard.get_check_count(), 0)
        self.guard.record_graph_check(10, 20, True)
        self.assertEqual(self.guard.get_check_count(), 1)
        self.guard.clear()
        self.assertEqual(self.guard.get_check_count(), 0)

    def test_context_in_check_result(self):
        result = self.guard.check_graph_size(10, 20, context='phase3a')
        self.assertEqual(result['context'], 'phase3a')


class TestMemoryPressureGuard(unittest.TestCase):
    def setUp(self):
        self.guard = MemoryPressureGuard(max_pressure_threshold=0.9)

    def test_empty_containers(self):
        result = self.guard.check_pressure(
            container_sizes={}, container_maxlens={},
        )
        self.assertTrue(result['safe'])
        self.assertEqual(result['pressure'], 0.0)

    def test_within_threshold(self):
        result = self.guard.check_pressure(
            container_sizes={'buf': 5},
            container_maxlens={'buf': 100},
        )
        self.assertTrue(result['safe'])
        self.assertEqual(result['pressure'], 0.05)

    def test_exceeds_threshold(self):
        result = self.guard.check_pressure(
            container_sizes={'buf': 95},
            container_maxlens={'buf': 100},
        )
        self.assertFalse(result['safe'])
        self.assertEqual(len(result['violations']), 1)
        self.assertIn('buf', result['violations'][0])

    def test_pressure_is_average_of_ratios(self):
        result = self.guard.check_pressure(
            container_sizes={'a': 10, 'b': 90},
            container_maxlens={'a': 100, 'b': 100},
        )
        self.assertAlmostEqual(result['pressure'], 0.5)

    def test_history_tracking(self):
        self.assertEqual(len(self.guard.get_pressure_history()), 0)
        self.guard.check_pressure({'b': 1}, {'b': 10})
        self.assertEqual(len(self.guard.get_pressure_history()), 1)
        self.guard.check_pressure({'b': 9}, {'b': 10})
        self.assertEqual(len(self.guard.get_pressure_history()), 2)

    def test_get_current_pressure(self):
        self.assertEqual(self.guard.get_current_pressure(), 0.0)
        self.guard.check_pressure({'b': 5}, {'b': 10})
        self.assertEqual(self.guard.get_current_pressure(), 0.5)

    def test_get_check_count(self):
        self.assertEqual(self.guard.get_check_count(), 0)
        self.guard.check_pressure({'b': 1}, {'b': 10})
        self.assertEqual(self.guard.get_check_count(), 1)

    def test_clear(self):
        self.guard.check_pressure({'b': 1}, {'b': 10})
        self.guard.clear()
        self.assertEqual(self.guard.get_check_count(), 0)
        self.assertEqual(self.guard.get_current_pressure(), 0.0)


class TestOrchestrationSafetyMonitor(unittest.TestCase):
    def setUp(self):
        self.recursion_guard = RecursionGuard(max_depth=5)
        self.graph_guard = GraphExplosionGuard(max_nodes=50, max_edges=200)
        self.memory_guard = MemoryPressureGuard(max_pressure_threshold=0.9)
        self.monitor = OrchestrationSafetyMonitor(max_reports=10)
        self.monitor._recursion_guard = self.recursion_guard
        self.monitor._graph_guard = self.graph_guard
        self.monitor._memory_guard = self.memory_guard

    def test_all_guards_pass(self):
        report = self.monitor.perform_safety_check(
            report_id='safe-1', current_depth=2, node_count=10,
            edge_count=20, container_sizes={'buf': 5},
            container_maxlens={'buf': 100}, context='test',
        )
        self.assertIsInstance(report, SafetyReport)
        self.assertTrue(report.is_safe)
        self.assertEqual(len(report.violations), 0)

    def test_recursion_exceeded(self):
        report = self.monitor.perform_safety_check(
            report_id='rec-1', current_depth=10, node_count=10,
            edge_count=20, container_sizes={'buf': 5},
            container_maxlens={'buf': 100},
        )
        self.assertFalse(report.is_safe)
        violation_text = ' '.join(report.violations).lower()
        self.assertIn('recursion', violation_text)

    def test_graph_exceeded(self):
        report = self.monitor.perform_safety_check(
            report_id='graph-1', current_depth=2, node_count=100,
            edge_count=1000, container_sizes={'buf': 5},
            container_maxlens={'buf': 100},
        )
        self.assertFalse(report.is_safe)
        violation_text = ' '.join(report.violations).lower()
        self.assertIn('node_count', violation_text)

    def test_memory_exceeded(self):
        report = self.monitor.perform_safety_check(
            report_id='mem-1', current_depth=2, node_count=10,
            edge_count=20, container_sizes={'buf': 95},
            container_maxlens={'buf': 100},
        )
        self.assertFalse(report.is_safe)
        violation_text = ' '.join(report.violations).lower()
        self.assertIn('pressure', violation_text)

    def test_get_report(self):
        self.monitor.perform_safety_check(
            'r1', 2, 10, 20, {'b': 5}, {'b': 100},
        )
        retrieved = self.monitor.get_report('r1')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.report_id, 'r1')

    def test_get_latest_report(self):
        self.assertIsNone(self.monitor.get_latest_report())
        self.monitor.perform_safety_check(
            'r1', 2, 10, 20, {'b': 5}, {'b': 100},
        )
        self.monitor.perform_safety_check(
            'r2', 2, 10, 20, {'b': 5}, {'b': 100},
        )
        latest = self.monitor.get_latest_report()
        self.assertEqual(latest.report_id, 'r2')

    def test_get_all_reports_and_count(self):
        self.assertEqual(self.monitor.get_report_count(), 0)
        self.monitor.perform_safety_check(
            'r1', 2, 10, 20, {'b': 5}, {'b': 100},
        )
        self.assertEqual(self.monitor.get_report_count(), 1)
        self.assertEqual(len(self.monitor.get_all_reports()), 1)

    def test_clear(self):
        self.monitor.perform_safety_check(
            'r1', 2, 10, 20, {'b': 5}, {'b': 100},
        )
        self.monitor.clear()
        self.assertEqual(self.monitor.get_report_count(), 0)
        self.assertIsNone(self.monitor.get_latest_report())
        self.assertEqual(self.recursion_guard.get_call_count(), 0)

    def test_report_fields(self):
        report = self.monitor.perform_safety_check(
            'check-1', 3, 15, 30, {'buf': 10}, {'buf': 100},
        )
        self.assertEqual(report.recursion_depth, 3)
        self.assertEqual(report.graph_size, 45)
        self.assertAlmostEqual(report.memory_pressure, 0.1)


if __name__ == '__main__':
    unittest.main()
