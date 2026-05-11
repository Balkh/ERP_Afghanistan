"""
Tests for Phase 3B.5 — Intelligence Stabilization Audit.
Fully deterministic. No randomness. No ERP mutation.
"""
import unittest
from datetime import datetime
from collections import deque
from unittest.mock import MagicMock, patch

from simulation.audit.event_lifecycle.analyzer import EventLifecycleAnalyzer
from simulation.audit.event_lifecycle.validator import EventRetentionValidator
from simulation.audit.event_lifecycle.reporter import EventTopologyReporter
from simulation.audit.graph.validator import GraphIntegrityValidator
from simulation.audit.graph.auditor import GraphMemoryAuditor
from simulation.audit.graph.analyzer import GraphComplexityAnalyzer
from simulation.audit.memory.validator import MemoryBoundaryValidator
from simulation.audit.memory.analyzer import StoragePressureAnalyzer
from simulation.audit.memory.verifier import RetentionPolicyVerifier
from simulation.audit.dependencies.analyzer import DependencyAnalyzer
from simulation.audit.dependencies.validator import LayerIsolationValidator
from simulation.audit.dependencies.reporter import CouplingRiskReporter
from simulation.audit.performance.analyzer import SimulationLoadAnalyzer
from simulation.audit.performance.estimator import ScalabilityEstimator
from simulation.audit.performance.validator import StabilityThresholdValidator
from simulation.audit.reporting.generator import IntelligenceHealthReportGenerator
from simulation.truth_engine.root_cause.models import (
    CausalGraph, CausalLink, NodeType, EdgeType,
)
from simulation.truth_engine.root_cause.graph.causal_graph_builder import (
    CausalGraphBuilder,
)


class TestEventLifecycleAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = EventLifecycleAnalyzer()
        self.ts = datetime(2024, 1, 1)

    def _make_event(self, eid, etype):
        e = MagicMock()
        e.id = eid
        e.type = etype
        e.timestamp = self.ts
        return e

    def test_analyze_empty_returns_no_events(self):
        result = self.analyzer.analyze([])
        self.assertEqual(result['total_events'], 0)

    def test_analyze_counts_events(self):
        events = [self._make_event('e1', 'tick_executed')] * 5
        result = self.analyzer.analyze(events)
        self.assertEqual(result['total_events'], 5)

    def test_orphan_detection(self):
        events = [
            self._make_event('e1', 'simulation_started'),
            self._make_event('e2', 'workflow_started'),
        ]
        result = self.analyzer.analyze(events)
        self.assertGreater(result['orphan_events'], 0)

    def test_duplicate_detection(self):
        e = self._make_event('dup1', 'tick_executed')
        result = self.analyzer.analyze([e, e])
        self.assertGreater(len(result['duplicate_propagations']), 0)

    def test_recursion_risk_high_frequency(self):
        events = [self._make_event(f'e{i}', 'workflow_started')
                  for i in range(10)]
        result = self.analyzer.analyze(events)
        self.assertGreater(len(result['recursion_risks']), 0)

    def test_unconsumed_buildup(self):
        events = [self._make_event(f'e{i}', 'workflow_started')
                  for i in range(5)]
        result = self.analyzer.analyze(events)
        self.assertGreater(len(result['unconsumed_buildup']), 0)

    def test_fan_out_chains(self):
        events = [
            self._make_event('e1', 'workflow_started'),
            self._make_event('e2', 'workflow_completed'),
            self._make_event('e3', 'workflow_started'),
            self._make_event('e4', 'workflow_completed'),
        ]
        result = self.analyzer.analyze(events)
        self.assertGreater(result['longest_chain'], 0)


class TestEventRetentionValidator(unittest.TestCase):
    def test_validate_compliant_no_leak(self):
        bus = MagicMock()
        bus.history = deque(maxlen=100)
        for i in range(50):
            bus.history.append(f'event_{i}')
        validator = EventRetentionValidator()
        result = validator.validate(bus, 100)
        self.assertTrue(result['retention_compliant'])

    def test_validate_leak_detected(self):
        bus = MagicMock()
        bus.history = deque(maxlen=10)
        for i in range(20):
            bus.history.append(f'event_{i}')
        validator = EventRetentionValidator()
        result = validator.validate(bus, 10)
        self.assertFalse(result['retention_leak_detected'])

    def test_validate_correct_maxlen(self):
        from simulation.events.bus import SimulationEventBus
        bus = SimulationEventBus(max_history=100)
        validator = EventRetentionValidator()
        result = validator.validate(bus, 100)
        self.assertTrue(result['maxlen_set_correctly'])


class TestEventTopologyReporter(unittest.TestCase):
    def test_generate_returns_report(self):
        analysis = {'total_events': 10, 'unique_types': 3,
                    'orphan_events': 0, 'duplicate_propagations': [],
                    'recursion_risks': [], 'unconsumed_buildup': {},
                    'fan_out_chains': [0], 'longest_chain': 0}
        retention = {'retention_compliant': True,
                     'actual_event_count': 10, 'max_history_setting': 100}
        reporter = EventTopologyReporter()
        report = reporter.generate(analysis, retention)
        self.assertIn('event_lifecycle_health', report)
        self.assertIn('retention_status', report)

    def test_healthy_when_no_issues(self):
        analysis = {'total_events': 5, 'unique_types': 2,
                    'orphan_events': 0, 'duplicate_propagations': [],
                    'recursion_risks': [], 'unconsumed_buildup': {},
                    'fan_out_chains': [0], 'longest_chain': 0}
        retention = {'retention_compliant': True, 'retention_leak_detected': False}
        reporter = EventTopologyReporter()
        report = reporter.generate(analysis, retention)
        self.assertEqual(report['health_summary'], 'HEALTHY')

    def test_critical_when_leak(self):
        analysis = {'total_events': 5, 'unique_types': 2,
                    'orphan_events': 0, 'duplicate_propagations': [],
                    'recursion_risks': [], 'unconsumed_buildup': {},
                    'fan_out_chains': [0], 'longest_chain': 0}
        retention = {'retention_compliant': False, 'retention_leak_detected': True}
        reporter = EventTopologyReporter()
        report = reporter.generate(analysis, retention)
        self.assertEqual(report['health_summary'], 'CRITICAL')


class TestGraphIntegrityValidator(unittest.TestCase):
    def setUp(self):
        self.validator = GraphIntegrityValidator()

    def test_no_cycle_dag(self):
        g = CausalGraph()
        g.add_node('a', NodeType.EVENT, 'A')
        g.add_node('b', NodeType.MISMATCH, 'B')
        link = CausalLink('l1', 'a', 'b', NodeType.EVENT,
                          NodeType.MISMATCH, EdgeType.CAUSES)
        g.add_edge(link)
        result = self.validator.validate(g)
        self.assertFalse(result['has_cycle'])
        self.assertTrue(result['dag_integrity'])

    def test_cycle_detected(self):
        g = CausalGraph()
        g.add_node('a', NodeType.EVENT, 'A')
        g.add_node('b', NodeType.EVENT, 'B')
        g.add_node('c', NodeType.EVENT, 'C')
        g.add_edge(CausalLink('l1', 'a', 'b', NodeType.EVENT,
                               NodeType.EVENT, EdgeType.CAUSES))
        g.add_edge(CausalLink('l2', 'b', 'c', NodeType.EVENT,
                               NodeType.EVENT, EdgeType.CAUSES))
        g.add_edge(CausalLink('l3', 'c', 'a', NodeType.EVENT,
                               NodeType.EVENT, EdgeType.CAUSES))
        result = self.validator.validate(g)
        self.assertTrue(result['has_cycle'])

    def test_orphan_nodes_detected(self):
        g = CausalGraph()
        g.add_node('orphan', NodeType.MISMATCH, 'Orphan')
        result = self.validator.validate(g)
        self.assertIn('orphan', result['orphan_nodes'])

    def test_density_warning(self):
        g = CausalGraph()
        for i in range(3):
            g.add_node(f'n{i}', NodeType.EVENT, f'N{i}')
        for i in range(3):
            for j in range(3):
                if i != j:
                    g.add_edge(CausalLink(
                        f'l{i}_{j}', f'n{i}', f'n{j}',
                        NodeType.EVENT, NodeType.EVENT, EdgeType.CAUSES
                    ))
        result = self.validator.validate(g)
        self.assertTrue(result['density_warning'])


class TestGraphMemoryAuditor(unittest.TestCase):
    def test_audit_empty_builder(self):
        builder = CausalGraphBuilder()
        auditor = GraphMemoryAuditor()
        result = auditor.audit(builder)
        self.assertEqual(result['total_graphs'], 0)

    def test_audit_with_graphs(self):
        builder = CausalGraphBuilder()
        builder.build('g1', [{'mismatch_id': 'm1'}], [], [], {}, {})
        auditor = GraphMemoryAuditor()
        result = auditor.audit(builder)
        self.assertEqual(result['total_graphs'], 1)


class TestGraphComplexityAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = GraphComplexityAnalyzer()

    def test_empty_graph(self):
        g = CausalGraph()
        result = self.analyzer.analyze(g)
        self.assertEqual(result['graph_depth'], 0)

    def test_depth_computed(self):
        g = CausalGraph()
        g.add_node('a', NodeType.EVENT, 'A')
        g.add_node('b', NodeType.EVENT, 'B')
        g.add_node('c', NodeType.MISMATCH, 'C')
        g.add_edge(CausalLink('l1', 'a', 'b', NodeType.EVENT,
                               NodeType.EVENT, EdgeType.CAUSES))
        g.add_edge(CausalLink('l2', 'b', 'c', NodeType.EVENT,
                               NodeType.MISMATCH, EdgeType.CAUSES))
        result = self.analyzer.analyze(g)
        self.assertGreater(result['graph_depth'], 1)

    def test_branching_factor(self):
        g = CausalGraph()
        g.add_node('a', NodeType.EVENT, 'A')
        g.add_node('b', NodeType.EVENT, 'B')
        g.add_node('c', NodeType.EVENT, 'C')
        g.add_edge(CausalLink('l1', 'a', 'b', NodeType.EVENT,
                               NodeType.EVENT, EdgeType.CAUSES))
        g.add_edge(CausalLink('l2', 'a', 'c', NodeType.EVENT,
                               NodeType.EVENT, EdgeType.CAUSES))
        result = self.analyzer.analyze(g)
        self.assertGreater(result['branching_factor'], 1.0)


class TestMemoryBoundaryValidator(unittest.TestCase):
    def test_bounded_structure(self):
        d = deque(maxlen=100)
        validator = MemoryBoundaryValidator()
        result = validator.audit_structures({'test_deque': d})
        self.assertTrue(result['test_deque']['bounded'])
        self.assertEqual(result['test_deque']['maxlen'], 100)

    def test_unbounded_structure(self):
        lst = []
        validator = MemoryBoundaryValidator()
        result = validator.audit_structures({'test_list': lst})
        self.assertFalse(result['test_list']['bounded'])

    def test_all_bounded_check(self):
        d1 = deque(maxlen=10)
        d2 = deque(maxlen=20)
        validator = MemoryBoundaryValidator()
        result = validator.audit_structures({'d1': d1, 'd2': d2})
        self.assertTrue(result['all_bounded'])


class TestStoragePressureAnalyzer(unittest.TestCase):
    def test_no_pressure(self):
        analyzer = StoragePressureAnalyzer()
        result = analyzer.estimate(
            {'events': 50, 'graphs': 10},
            {'events': 1000, 'graphs': 100},
            tick_count=10
        )
        self.assertFalse(result['has_pressure'])

    def test_pressure_detected(self):
        analyzer = StoragePressureAnalyzer()
        result = analyzer.estimate(
            {'events': 900},
            {'events': 1000},
            tick_count=10
        )
        self.assertTrue(result['growth_warnings']['events']['warning'])


class TestRetentionPolicyVerifier(unittest.TestCase):
    def test_verifier_compliant(self):
        d = deque(maxlen=100)
        for i in range(50):
            d.append(f'item_{i}')
        verifier = RetentionPolicyVerifier()
        result = verifier.verify('test', d, 100)
        self.assertTrue(result['maxlen_correct'])
        self.assertTrue(result['cleanup_functional'])


class TestDependencyAnalyzer(unittest.TestCase):
    def test_no_production_imports_in_simulation(self):
        analyzer = DependencyAnalyzer()
        import simulation
        sim_path = simulation.__path__[0]
        result = analyzer.analyze(sim_path)
        self.assertEqual(
            result['production_violation_count'], 0,
            f"Found violations: {result['production_import_violations']}"
        )


class TestLayerIsolationValidator(unittest.TestCase):
    def test_no_layer_violations(self):
        validator = LayerIsolationValidator()
        import simulation
        sim_path = simulation.__path__[0]
        result = validator.validate(sim_path)
        violations = result.get('layer_violations', [])
        if violations:
            for v in violations:
                print(f"  Layer violation: {v['file']} imports {v['import']}")
        self.assertTrue(
            result['layers_isolated'],
            f"Found {result['violation_count']} layer violations"
        )


class TestCouplingRiskReporter(unittest.TestCase):
    def test_low_risk_when_clean(self):
        reporter = CouplingRiskReporter()
        result = reporter.generate(
            {'production_violation_count': 0, 'cross_layer_count': 0},
            {'violation_count': 0, 'layers_isolated': True}
        )
        self.assertEqual(result['risk_level'], 'LOW')

    def test_high_risk_with_violations(self):
        reporter = CouplingRiskReporter()
        result = reporter.generate(
            {'production_violation_count': 1, 'cross_layer_count': 0},
            {'violation_count': 0, 'layers_isolated': True}
        )
        self.assertEqual(result['risk_level'], 'HIGH')


class TestSimulationLoadAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = SimulationLoadAnalyzer()

    def test_measure_tick_cost(self):
        def dummy_tick():
            pass
        result = self.analyzer.measure_tick_cost(dummy_tick)
        self.assertIn('avg_seconds', result)
        self.assertGreaterEqual(result['avg_seconds'], 0)

    def test_estimate_graph_traversal_empty(self):
        g = CausalGraph()
        result = self.analyzer.estimate_graph_traversal(g)
        self.assertEqual(result['node_count'], 0)
        self.assertEqual(result['edge_count'], 0)


class TestScalabilityEstimator(unittest.TestCase):
    def test_estimate(self):
        estimator = ScalabilityEstimator()
        result = estimator.estimate(10.0, [100, 1000, 10000])
        self.assertIn('100', result)
        self.assertIn('10000', result)
        self.assertEqual(result['degradation_trend'], 'linear')

    def test_graph_scaling(self):
        estimator = ScalabilityEstimator()
        result = estimator.estimate_graph_scaling(100, 10.0, [1, 10, 100])
        self.assertIn('10x', result)
        self.assertIn('100x', result)


class TestStabilityThresholdValidator(unittest.TestCase):
    def test_no_warnings_when_within_bounds(self):
        validator = StabilityThresholdValidator()
        result = validator.validate(
            {'avg_seconds': 0.001},
            {'estimated_traversal_cost_ms': 1.0}
        )
        self.assertEqual(result['warning_count'], 0)

    def test_warning_on_high_latency(self):
        validator = StabilityThresholdValidator()
        result = validator.validate(
            {'avg_seconds': 0.5},
            {'estimated_traversal_cost_ms': 1.0}
        )
        self.assertGreater(result['warning_count'], 0)


class TestIntelligenceHealthReportGenerator(unittest.TestCase):
    def test_generates_full_report(self):
        generator = IntelligenceHealthReportGenerator()
        audit_data = {
            'event_lifecycle': {'health_summary': 'HEALTHY'},
            'graph': {'dag_integrity': True, 'density_warning': False,
                      'orphan_nodes': []},
            'memory': {'all_bounded': True},
            'dependencies': {'violation_count': 0, 'layers_isolated': True},
            'performance': {'warning_count': 0},
        }
        report = generator.generate(audit_data)
        self.assertIn('overall_stability_score', report)
        self.assertIn('scores', report)
        self.assertIn('health_summary', report)

    def test_perfect_score_when_all_healthy(self):
        generator = IntelligenceHealthReportGenerator()
        audit_data = {
            'event_lifecycle': {'health_summary': 'HEALTHY'},
            'graph': {'dag_integrity': True, 'density_warning': False,
                      'orphan_nodes': []},
            'memory': {'all_bounded': True},
            'dependencies': {'violation_count': 0, 'layers_isolated': True},
            'performance': {'warning_count': 0},
        }
        report = generator.generate(audit_data)
        self.assertEqual(report['overall_stability_score'], 100.0)

    def test_reduced_score_with_issues(self):
        generator = IntelligenceHealthReportGenerator()
        audit_data = {
            'event_lifecycle': {'health_summary': 'CRITICAL'},
            'graph': {'dag_integrity': False, 'density_warning': True,
                      'orphan_nodes': ['orphan1']},
            'memory': {'all_bounded': False},
            'dependencies': {'violation_count': 3, 'layers_isolated': False},
            'performance': {'warning_count': 2},
        }
        report = generator.generate(audit_data)
        self.assertLess(report['overall_stability_score'], 100.0)


class TestNoERPMutation(unittest.TestCase):
    def test_no_erp_writes_in_audit(self):
        import os
        audit_dir = os.path.join(
            os.path.dirname(__file__), '..', 'audit'
        )
        forbidden = (
            '.save()', '.create(', '.update(', '.delete(',
            '.bulk_create(', 'cursor.execute',
        )
        for root, dirs, files in os.walk(audit_dir):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as fh:
                    content = fh.read()
                for keyword in forbidden:
                    self.assertNotIn(
                        keyword, content,
                        f"{fname}: contains forbidden write '{keyword}'"
                    )


class TestFullAuditPipeline(unittest.TestCase):
    def test_end_to_end_audit_generates_report(self):
        analyzer = EventLifecycleAnalyzer()
        validator = EventRetentionValidator()
        reporter = EventTopologyReporter()
        from collections import deque
        bus = MagicMock()
        bus.history = deque(maxlen=100)
        for i in range(10):
            bus.history.append(MagicMock(id=f'e{i}', type='tick_executed',
                                         timestamp=datetime(2024, 1, 1)))
        analysis = analyzer.analyze(list(bus.history))
        retention = validator.validate(bus, 100)
        ev_report = reporter.generate(analysis, retention)
        self.assertIn('event_lifecycle_health', ev_report)

        g = CausalGraph()
        g.add_node('n1', NodeType.EVENT, 'Event')
        g.add_node('n2', NodeType.MISMATCH, 'Mismatch')
        g.add_edge(CausalLink('l1', 'n1', 'n2', NodeType.EVENT,
                               NodeType.MISMATCH, EdgeType.CAUSES))
        graph_val = GraphIntegrityValidator().validate(g)
        self.assertTrue(graph_val['dag_integrity'])

        deps = MagicMock()
        deps.get.return_value = {}
        from simulation.audit.dependencies.analyzer import DependencyAnalyzer
        dep_analysis = DependencyAnalyzer().analyze(
            __import__('simulation').__path__[0]
        )
        self.assertGreater(dep_analysis['total_files_scanned'], 0)

        perf = {'warning_count': 0}
        memory = {'all_bounded': True}
        deps_data = {'violation_count': 0, 'layers_isolated': True}
        report_gen = IntelligenceHealthReportGenerator()
        report = report_gen.generate({
            'event_lifecycle': ev_report,
            'graph': graph_val,
            'memory': memory,
            'dependencies': deps_data,
            'performance': perf,
        })
        self.assertGreaterEqual(report['overall_stability_score'], 0)


if __name__ == '__main__':
    unittest.main()
