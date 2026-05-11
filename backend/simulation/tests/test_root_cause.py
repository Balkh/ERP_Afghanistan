"""
Tests for Phase 3B — Root Cause Intelligence Engine.
Fully deterministic. No randomness. No ERP mutation.
"""
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from simulation.truth_engine.root_cause.models import (
    RootCause, RootCauseType, CausalChain, CausalLink,
    NodeType, EdgeType, DriftPattern, CausalGraph, Explanation,
)
from simulation.truth_engine.root_cause.correlator.event_correlator import (
    EventCorrelator,
)
from simulation.truth_engine.root_cause.classifier.root_cause_classifier import (
    RootCauseClassifier,
)
from simulation.truth_engine.root_cause.analyzer.causal_analyzer import (
    CausalAnalyzer,
)
from simulation.truth_engine.root_cause.patterns.drift_pattern_detector import (
    DriftPatternDetector,
)
from simulation.truth_engine.root_cause.explainer.explanation_engine import (
    RootCauseExplainer,
)
from simulation.truth_engine.root_cause.graph.causal_graph_builder import (
    CausalGraphBuilder,
)
from simulation.truth_engine.root_cause.history.drift_memory import (
    DriftMemoryStore,
)
from simulation.truth_engine.root_cause.engine import RootCauseEngine


class TestRootCauseModels(unittest.TestCase):
    """Root cause data model tests."""

    def test_root_cause_creation(self):
        rc = RootCause(
            cause_id='rc1',
            primary_type=RootCauseType.LOGIC_ERROR,
            confidence=0.85,
            mismatch_id='m1',
            description='Logic error in accounting',
        )
        self.assertEqual(rc.cause_id, 'rc1')
        self.assertEqual(rc.primary_type, RootCauseType.LOGIC_ERROR)
        self.assertEqual(rc.confidence, 0.85)

    def test_root_cause_to_dict(self):
        rc = RootCause(
            cause_id='rc1', primary_type=RootCauseType.CONCURRENCY_ISSUE,
            confidence=0.90, mismatch_id='m1',
            description='Concurrent access',
            secondary_types=[RootCauseType.TIMING_DESYNC],
            evidence_refs=['tick_1', 'inventory_mismatch'],
        )
        d = rc.to_dict()
        self.assertEqual(d['primary_type'], 'concurrency_issue')
        self.assertIn('timing_desync', d['secondary_types'])

    def test_causal_chain_creation(self):
        chain = CausalChain('chain1', 'm1', 5)
        self.assertEqual(chain.chain_id, 'chain1')
        self.assertEqual(chain.mismatch_id, 'm1')
        self.assertEqual(chain.tick, 5)

    def test_causal_chain_add_link(self):
        chain = CausalChain('c1', 'm1', 1)
        link = CausalLink('l1', 'src', 'tgt', NodeType.EVENT,
                          NodeType.MISMATCH, EdgeType.CAUSES)
        chain.add_link(link)
        self.assertEqual(len(chain.links), 1)

    def test_causal_chain_to_dict(self):
        chain = CausalChain('c1', 'm1', 2)
        d = chain.to_dict()
        self.assertEqual(d['chain_id'], 'c1')

    def test_causal_link_creation(self):
        link = CausalLink('l1', 'evt_1', 'm_1', NodeType.EVENT,
                          NodeType.MISMATCH, EdgeType.TRIGGERS, 0.9)
        self.assertEqual(link.link_id, 'l1')
        self.assertEqual(link.edge_type, EdgeType.TRIGGERS)
        self.assertEqual(link.confidence, 0.9)

    def test_drift_pattern_creation(self):
        dp = DriftPattern('p1', 'repeated_failure',
                          'Repeated issue', 'inventory',
                          matched_mismatch_ids=['m1', 'm2'])
        self.assertEqual(dp.pattern_id, 'p1')
        self.assertEqual(dp.occurrence_count, 1)

    def test_drift_pattern_to_dict(self):
        dp = DriftPattern('p1', 'load_sensitive',
                          'Load issue', 'accounting',
                          matched_mismatch_ids=['m1'])
        d = dp.to_dict()
        self.assertEqual(d['frequency'], 1)

    def test_causal_graph_add_node(self):
        g = CausalGraph()
        g.add_node('agent:bot1', NodeType.AGENT, 'Bot 1')
        self.assertIn('agent:bot1', g.nodes)
        self.assertEqual(g.nodes['agent:bot1']['label'], 'Bot 1')

    def test_causal_graph_add_edge(self):
        g = CausalGraph()
        link = CausalLink('l1', 'src', 'tgt', NodeType.EVENT,
                          NodeType.MISMATCH, EdgeType.CAUSES)
        g.add_edge(link)
        self.assertIn('l1', g.edges)

    def test_causal_graph_to_dict(self):
        g = CausalGraph()
        g.add_node('n1', NodeType.AGENT, 'Agent')
        link = CausalLink('l1', 'n1', 'n2', NodeType.AGENT,
                          NodeType.MISMATCH, EdgeType.CAUSES)
        g.add_edge(link)
        d = g.to_dict()
        self.assertEqual(len(d['nodes']), 1)
        self.assertEqual(len(d['edges']), 1)

    def test_explanation_creation(self):
        ts = datetime(2024, 1, 1)
        exp = Explanation('e1', 'm1', 'Problem',
                          ['Step 1', 'Step 2'], 0.85,
                          ['evidence1'], 'Fix it', ts)
        self.assertEqual(exp.explanation_id, 'e1')
        self.assertEqual(exp.confidence, 0.85)

    def test_explanation_to_dict(self):
        ts = datetime(2024, 1, 1)
        exp = Explanation('e1', 'm1', 'Problem', [], 0.9,
                          [], 'Recommend', ts)
        d = exp.to_dict()
        self.assertEqual(d['explanation_id'], 'e1')


class TestEventCorrelator(unittest.TestCase):
    """Event correlation tests."""

    def setUp(self):
        self.correlator = EventCorrelator()
        self.ts = datetime(2024, 1, 1)

    def _make_event(self, eid, etype):
        evt = MagicMock()
        evt.id = eid
        evt.type = etype
        evt.timestamp = self.ts
        return evt

    def test_correlate_returns_chain(self):
        events = [self._make_event('e1', 'workflow_completed')]
        chain = self.correlator.correlate(
            'm1', 'financial_mismatch', 'desc', 'accounting',
            1, events, {}, {}
        )
        self.assertIsNotNone(chain)
        self.assertEqual(chain.mismatch_id, 'm1')

    def test_correlate_links_events(self):
        events = [self._make_event('e1', 'workflow_completed')]
        chain = self.correlator.correlate(
            'm1', 'financial_mismatch', 'desc', 'accounting',
            1, events, {}, {}
        )
        self.assertGreater(len(chain.links), 0)

    def test_correlate_no_matching_events(self):
        chain = self.correlator.correlate(
            'm1', 'inventory_mismatch', 'desc', 'inventory',
            1, [], {}, {}
        )
        self.assertEqual(len(chain.links), 0)

    def test_correlate_empty_chain_on_irrelevant_events(self):
        events = [self._make_event('e1', 'simulation_started')]
        chain = self.correlator.correlate(
            'm1', 'financial_mismatch', 'desc', 'accounting',
            1, events, {}, {}
        )
        self.assertEqual(len(chain.links), 0)

    def test_correlate_high_confidence_for_failed_workflow(self):
        events = [self._make_event('e1', 'workflow_failed')]
        chain = self.correlator.correlate(
            'm1', 'workflow_incomplete', 'desc', 'workflow',
            1, events, {}, {}
        )
        self.assertGreater(chain.links[0].confidence, 0.8)

    def test_chain_count_increments(self):
        events = [self._make_event('e1', 'workflow_completed')]
        self.correlator.correlate('m1', 'financial_mismatch',
                                   'desc', 'accounting', 1, events, {}, {})
        self.assertEqual(self.correlator.chain_count, 1)

    def test_get_chain_returns_none_for_missing(self):
        self.assertIsNone(self.correlator.get_chain('nonexistent'))


class TestRootCauseClassifier(unittest.TestCase):
    """Root cause classification tests."""

    def setUp(self):
        self.classifier = RootCauseClassifier()

    def test_financial_mismatch_classifies(self):
        rc = self.classifier.classify(
            'm1', 'financial_mismatch', 'desc', 'accounting', 1
        )
        self.assertEqual(rc.primary_type, RootCauseType.LOGIC_ERROR)
        self.assertGreater(rc.confidence, 0.5)

    def test_inventory_mismatch_classifies(self):
        rc = self.classifier.classify(
            'm2', 'inventory_mismatch', 'desc', 'inventory', 2
        )
        self.assertEqual(rc.primary_type, RootCauseType.CONCURRENCY_ISSUE)

    def test_duplicate_entry_classifies(self):
        rc = self.classifier.classify(
            'm3', 'duplicate_entry', 'desc', 'accounting', 3
        )
        self.assertEqual(rc.primary_type, RootCauseType.LOGIC_ERROR)

    def test_workflow_incomplete_classifies(self):
        rc = self.classifier.classify(
            'm4', 'workflow_incomplete', 'desc', 'workflow', 4
        )
        self.assertEqual(rc.primary_type,
                         RootCauseType.WORKFLOW_DESIGN_FLAW)

    def test_state_drift_classifies(self):
        rc = self.classifier.classify(
            'm5', 'state_drift', 'desc', 'simulation', 5
        )
        self.assertEqual(rc.primary_type, RootCauseType.TIMING_DESYNC)

    def test_unknown_type_classifies(self):
        rc = self.classifier.classify(
            'm6', 'unknown_type', 'desc', 'unknown', 6
        )
        self.assertEqual(rc.primary_type, RootCauseType.UNKNOWN_CAUSE)

    def test_confidence_boosted_with_many_events(self):
        rc1 = self.classifier.classify(
            'm7', 'financial_mismatch', 'desc', 'accounting', 7,
            event_count=10
        )
        rc2 = self.classifier.classify(
            'm8', 'financial_mismatch', 'desc', 'accounting', 8,
            event_count=0
        )
        self.assertGreater(rc1.confidence, rc2.confidence)

    def test_mismatch_id_in_cause(self):
        rc = self.classifier.classify(
            'm9', 'financial_mismatch', 'desc', 'accounting', 9
        )
        self.assertEqual(rc.mismatch_id, 'm9')

    def test_classification_count(self):
        self.classifier.classify('m1', 'financial_mismatch',
                                  'desc', 'acc', 1)
        self.classifier.classify('m2', 'inventory_mismatch',
                                  'desc', 'inv', 2)
        self.assertEqual(self.classifier.classification_count, 2)


class TestCausalAnalyzer(unittest.TestCase):
    """Causal analysis tests."""

    def setUp(self):
        self.analyzer = CausalAnalyzer()

    def test_analyze_returns_analysis(self):
        ts = datetime(2024, 1, 1)
        chain = CausalChain('c1', 'm1', 1)
        chain.add_link(CausalLink('l1', 'src', 'tgt',
                      NodeType.EVENT, NodeType.MISMATCH, EdgeType.CAUSES))
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        result = self.analyzer.analyze(chain, rc, {}, {})
        self.assertEqual(result['chain_id'], 'c1')
        self.assertEqual(result['mismatch_id'], 'm1')

    def test_analyze_includes_dependency_chain(self):
        chain = CausalChain('c1', 'm1', 1)
        chain.add_link(CausalLink('l1', 'src', 'tgt',
                      NodeType.EVENT, NodeType.MISMATCH, EdgeType.CAUSES))
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        result = self.analyzer.analyze(chain, rc, {}, {})
        self.assertIn('dependency_chain', result)
        self.assertGreater(len(result['dependency_chain']), 0)

    def test_analyze_includes_event_sequence(self):
        chain = CausalChain('c1', 'm1', 1)
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        result = self.analyzer.analyze(chain, rc, {}, {})
        self.assertIn('event_sequence', result)

    def test_analyze_includes_agent_workflow_map(self):
        chain = CausalChain('c1', 'm1', 1)
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        result = self.analyzer.analyze(
            chain, rc, {'sales_bot': 5}, {'sales_workflow': 3}
        )
        self.assertIn('agent_workflow_map', result)
        self.assertEqual(
            result['agent_workflow_map']['agent_activity']['sales_bot'], 5
        )

    def test_analysis_count(self):
        chain = CausalChain('c1', 'm1', 1)
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        self.analyzer.analyze(chain, rc, {}, {})
        self.assertEqual(self.analyzer.analysis_count, 1)


class TestDriftPatternDetector(unittest.TestCase):
    """Pattern detection tests."""

    def setUp(self):
        self.detector = DriftPatternDetector()

    def test_no_patterns_with_empty_history(self):
        patterns = self.detector.detect([], 1)
        self.assertEqual(len(patterns), 0)

    def test_repeated_inventory_drift_detected(self):
        history = [
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm1',
             'tick': 1},
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm2',
             'tick': 2},
        ]
        patterns = self.detector.detect(history, 2)
        self.assertGreater(len(patterns), 0)
        pids = [p.pattern_id for p in patterns]
        self.assertIn('repeated_inventory_drift', pids)

    def test_payment_failure_under_load_detected(self):
        history = [
            {'mismatch_type': 'financial_mismatch', 'mismatch_id': 'm1',
             'tick': 1},
            {'mismatch_type': 'financial_mismatch', 'mismatch_id': 'm2',
             'tick': 2},
        ]
        patterns = self.detector.detect(history, 2)
        pids = [p.pattern_id for p in patterns]
        self.assertIn('payment_failure_under_load', pids)

    def test_journal_imbalance_detected(self):
        history = [
            {'mismatch_type': 'duplicate_entry', 'mismatch_id': 'm1',
             'tick': 1},
        ]
        patterns = self.detector.detect(history, 1)
        pids = [p.pattern_id for p in patterns]
        self.assertIn('journal_imbalance_concurrency', pids)

    def test_partial_workflow_detected(self):
        history = [
            {'mismatch_type': 'workflow_incomplete', 'mismatch_id': 'm1',
             'tick': 1},
            {'mismatch_type': 'workflow_incomplete', 'mismatch_id': 'm2',
             'tick': 2},
        ]
        patterns = self.detector.detect(history, 2)
        pids = [p.pattern_id for p in patterns]
        self.assertIn('partial_workflow_execution', pids)

    def test_single_mismatch_no_pattern(self):
        history = [
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm1',
             'tick': 1},
        ]
        patterns = self.detector.detect(history, 2)
        self.assertEqual(len(patterns), 0)

    def test_multiple_patterns_detected(self):
        history = [
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm1',
             'tick': 1},
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm2',
             'tick': 2},
            {'mismatch_type': 'financial_mismatch', 'mismatch_id': 'm3',
             'tick': 3},
            {'mismatch_type': 'financial_mismatch', 'mismatch_id': 'm4',
             'tick': 4},
        ]
        patterns = self.detector.detect(history, 4)
        self.assertGreaterEqual(len(patterns), 2)

    def test_occurrence_count_increments(self):
        history = [
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm1',
             'tick': 1},
        ]
        self.detector.detect(history, 1)
        history.append({'mismatch_type': 'inventory_mismatch',
                        'mismatch_id': 'm2', 'tick': 2})
        patterns = self.detector.detect(history, 2)
        for p in patterns:
            if p.pattern_id == 'repeated_inventory_drift':
                self.assertGreaterEqual(p.occurrence_count, 2)

    def test_state_drift_pattern_detected(self):
        history = [
            {'mismatch_type': 'state_drift', 'mismatch_id': 'm1',
             'tick': 1},
            {'mismatch_type': 'state_drift', 'mismatch_id': 'm2',
             'tick': 2},
        ]
        patterns = self.detector.detect(history, 2)
        pids = [p.pattern_id for p in patterns]
        self.assertIn('concurrent_access_conflict', pids)


class TestRootCauseExplainer(unittest.TestCase):
    """Explanation engine tests."""

    def setUp(self):
        self.explainer = RootCauseExplainer()

    def test_explain_returns_explanation(self):
        ts = datetime(2024, 1, 1)
        chain = CausalChain('c1', 'm1', 1)
        chain.add_link(CausalLink('l1', 'evt1', 'm1',
                      NodeType.EVENT, NodeType.MISMATCH, EdgeType.CAUSES,
                      metadata={'event_type': 'workflow_completed',
                               'event_timestamp': '2024-01-01'}))
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        exp = self.explainer.explain(
            'm1', 'financial_mismatch', 'desc', 'accounting', 1, rc, chain
        )
        self.assertEqual(exp.mismatch_id, 'm1')
        self.assertIn('Financial', exp.problem_summary)

    def test_explain_includes_evidence(self):
        chain = CausalChain('c1', 'm1', 1)
        rc = RootCause('rc1', RootCauseType.CONCURRENCY_ISSUE,
                       0.90, 'm1', 'desc')
        exp = self.explainer.explain(
            'm1', 'concurrency_issue', 'desc', 'inventory', 1, rc, chain
        )
        self.assertGreater(len(exp.evidence), 0)

    def test_explain_includes_recommendation(self):
        chain = CausalChain('c1', 'm1', 1)
        rc = RootCause('rc1', RootCauseType.WORKFLOW_DESIGN_FLAW,
                       0.85, 'm1', 'desc')
        exp = self.explainer.explain(
            'm1', 'workflow_incomplete', 'desc', 'workflow', 1, rc, chain
        )
        self.assertIn('Redesign', exp.recommendation)

    def test_explain_count(self):
        chain = CausalChain('c1', 'm1', 1)
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        self.explainer.explain('m1', 'mtype', 'desc', 'mod', 1, rc, chain)
        self.assertEqual(self.explainer.explanation_count, 1)


class TestCausalGraphBuilder(unittest.TestCase):
    """Causal graph tests."""

    def setUp(self):
        self.builder = CausalGraphBuilder()

    def test_build_returns_graph(self):
        graph = self.builder.build(
            'g1', [], [], [], {}, {}
        )
        self.assertIsNotNone(graph)
        self.assertEqual(len(graph.nodes), 0)

    def test_build_adds_mismatch_nodes(self):
        mismatches = [
            {'mismatch_id': 'm1', 'description': 'test mismatch',
             'mismatch_type': 'financial_mismatch'}
        ]
        graph = self.builder.build('g1', mismatches, [], [], {}, {})
        self.assertIn('m1', graph.nodes)

    def test_build_adds_agent_nodes(self):
        graph = self.builder.build(
            'g1', [], [], [], {'sales_bot': 5}, {}
        )
        self.assertIn('agent:sales_bot', graph.nodes)

    def test_build_adds_workflow_nodes(self):
        graph = self.builder.build(
            'g1', [], [], [], {}, {'sales_workflow': 3}
        )
        self.assertIn('workflow:sales_workflow', graph.nodes)

    def test_build_adds_root_cause_nodes(self):
        rc = RootCause('rc1', RootCauseType.LOGIC_ERROR, 0.85, 'm1', 'desc')
        graph = self.builder.build('g1', [], [], [rc], {}, {})
        self.assertIn('cause:rc1', graph.nodes)

    def test_graph_count(self):
        self.builder.build('g1', [], [], [], {}, {})
        self.builder.build('g2', [], [], [], {}, {})
        self.assertEqual(self.builder.graph_count, 2)


class TestDriftMemoryStore(unittest.TestCase):
    """Drift memory tests."""

    def setUp(self):
        self.memory = DriftMemoryStore()

    def test_record_drift(self):
        self.memory.record_drift(1, {'mismatch_type': 'financial_mismatch'})
        self.assertEqual(self.memory.get_drift_count(), 1)

    def test_get_drift_history_by_tick(self):
        self.memory.record_drift(1, {'mismatch_type': 'm1'})
        self.memory.record_drift(2, {'mismatch_type': 'm2'})
        history = self.memory.get_drift_history(since_tick=2)
        self.assertEqual(len(history), 1)

    def test_record_patterns(self):
        dp = DriftPattern('p1', 'repeated_failure', 'desc', 'inv')
        self.memory.record_patterns('run1', [dp])
        patterns = self.memory.get_pattern_history('run1')
        self.assertEqual(len(patterns), 1)

    def test_get_high_risk_workflows(self):
        rc = RootCause('rc1', RootCauseType.WORKFLOW_DESIGN_FLAW,
                       0.85, 'm1', 'desc')
        self.memory.record_drift(1, {'affected_module': 'accounting',
                                      'mismatch_type': 'workflow_incomplete'},
                                 root_cause=rc)
        self.memory.record_drift(2, {'affected_module': 'accounting',
                                      'mismatch_type': 'workflow_incomplete'},
                                 root_cause=rc)
        workflows = self.memory.get_high_risk_workflows(min_frequency=2)
        self.assertIn('accounting', workflows)

    def test_get_frequently_failing_agents(self):
        self.memory.record_drift(1, {'affected_module': 'inventory'})
        self.memory.record_drift(2, {'affected_module': 'inventory'})
        agents = self.memory.get_frequently_failing_agents(min_failures=2)
        self.assertIn('inventory', agents)

    def test_clear(self):
        self.memory.record_drift(1, {'mismatch_type': 'm1'})
        self.memory.clear()
        self.assertEqual(self.memory.get_drift_count(), 0)


class TestRootCauseEngine(unittest.TestCase):
    """RootCauseEngine orchestrator integration tests."""

    def setUp(self):
        self.engine = RootCauseEngine()

    def test_analyze_mismatch_returns_result(self):
        mismatch = {'mismatch_id': 'm1',
                    'mismatch_type': 'financial_mismatch',
                    'description': 'Journal entry mismatch',
                    'affected_module': 'accounting'}
        result = self.engine.analyze_mismatch(
            mismatch, [], {}, {}, 1
        )
        self.assertEqual(result['mismatch_id'], 'm1')
        self.assertIn('root_cause', result)
        self.assertIn('causal_chain', result)
        self.assertIn('explanation', result)

    def test_analyze_mismatch_includes_causal_chain(self):
        ts = datetime(2024, 1, 1)
        evt = MagicMock()
        evt.id = 'evt1'
        evt.type = 'workflow_completed'
        evt.timestamp = ts
        mismatch = {'mismatch_id': 'm1',
                    'mismatch_type': 'financial_mismatch',
                    'description': 'desc', 'affected_module': 'accounting'}
        result = self.engine.analyze_mismatch(
            mismatch, [evt], {'sales_workflow': 1},
            {'sales_bot': 3}, 1
        )
        self.assertGreater(
            len(result['causal_chain']['links']), 0
        )

    def test_analyze_mismatch_classifies_root_cause(self):
        mismatch = {'mismatch_id': 'm1',
                    'mismatch_type': 'duplicate_entry',
                    'description': 'Dup', 'affected_module': 'accounting'}
        result = self.engine.analyze_mismatch(mismatch, [], {}, {}, 1)
        rc = result['root_cause']
        self.assertEqual(rc['primary_type'], 'logic_error')

    def test_detect_patterns(self):
        self.engine.analyze_mismatch(
            {'mismatch_id': 'm1', 'mismatch_type': 'inventory_mismatch',
             'description': 'desc', 'affected_module': 'inventory'},
            [], {}, {}, 1
        )
        self.engine.analyze_mismatch(
            {'mismatch_id': 'm2', 'mismatch_type': 'inventory_mismatch',
             'description': 'desc', 'affected_module': 'inventory'},
            [], {}, {}, 2
        )
        patterns = self.engine.detect_patterns([
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm1',
             'tick': 1},
            {'mismatch_type': 'inventory_mismatch', 'mismatch_id': 'm2',
             'tick': 2},
        ])
        self.assertGreater(len(patterns), 0)

    def test_build_causal_graph(self):
        mismatch = {'mismatch_id': 'm1', 'mismatch_type': 'financial_mismatch',
                    'description': 'desc', 'affected_module': 'accounting'}
        self.engine.analyze_mismatch(mismatch, [], {}, {}, 1)
        graph = self.engine.build_causal_graph(
            's1', [mismatch], {}, {}
        )
        self.assertIsNotNone(graph)
        self.assertGreaterEqual(len(graph.nodes), 1)

    def test_record_run_patterns(self):
        self.engine.analyze_mismatch(
            {'mismatch_id': 'm1', 'mismatch_type': 'financial_mismatch',
             'description': 'desc', 'affected_module': 'accounting'},
            [], {}, {}, 1
        )
        dp = DriftPattern('p1', 'repeated_failure', 'desc', 'inv')
        self.engine.record_run_patterns('run1', [dp])
        patterns = self.engine.memory.get_pattern_history('run1')
        self.assertEqual(len(patterns), 1)
        self.assertEqual(self.engine.memory.get_drift_count(), 1)

    def test_get_drift_history(self):
        self.engine.analyze_mismatch(
            {'mismatch_id': 'm1', 'mismatch_type': 'financial_mismatch',
             'description': 'desc', 'affected_module': 'accounting'},
            [], {}, {}, 1
        )
        self.assertEqual(len(self.engine.get_drift_history()), 1)

    def test_get_high_risk_workflows(self):
        self.engine.analyze_mismatch(
            {'mismatch_id': 'm1', 'mismatch_type': 'workflow_incomplete',
             'description': 'desc', 'affected_module': 'accounting'},
            [], {'sales_workflow': 0}, {}, 1
        )
        self.engine.analyze_mismatch(
            {'mismatch_id': 'm2', 'mismatch_type': 'workflow_incomplete',
             'description': 'desc', 'affected_module': 'accounting'},
            [], {'sales_workflow': 0}, {}, 2
        )
        workflows = self.engine.get_high_risk_workflows(min_frequency=1)
        self.assertIn('accounting', workflows)

    def test_properties(self):
        self.assertIsNotNone(self.engine.correlator)
        self.assertIsNotNone(self.engine.classifier)
        self.assertIsNotNone(self.engine.analyzer)
        self.assertIsNotNone(self.engine.pattern_detector)
        self.assertIsNotNone(self.engine.explainer)
        self.assertIsNotNone(self.engine.graph_builder)
        self.assertIsNotNone(self.engine.memory)

    def test_no_mutation_of_input_data(self):
        mismatch = {'mismatch_id': 'm1',
                    'mismatch_type': 'financial_mismatch',
                    'description': 'desc', 'affected_module': 'accounting'}
        original_id = mismatch['mismatch_id']
        self.engine.analyze_mismatch(mismatch, [], {}, {}, 1)
        self.assertEqual(mismatch['mismatch_id'], original_id)


class TestNoERPMutation(unittest.TestCase):
    """Read-only verification for Phase 3B."""

    def test_no_erp_writes_in_root_cause(self):
        import os
        import ast
        rc_dir = os.path.join(
            os.path.dirname(__file__), '..',
            'truth_engine', 'root_cause'
        )
        forbidden = (
            '.save()', '.create(', '.update(', '.delete(',
            '.bulk_create(', 'cursor.execute',
        )
        for root, dirs, files in os.walk(rc_dir):
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

    def test_no_domain_imports_in_root_cause(self):
        import os
        rc_dir = os.path.join(
            os.path.dirname(__file__), '..',
            'truth_engine', 'root_cause'
        )
        domain_imports = (
            'from accounting', 'from sales', 'from purchases',
            'from inventory', 'from payments', 'from payroll',
        )
        for root, dirs, files in os.walk(rc_dir):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as fh:
                    content = fh.read()
                for imp in domain_imports:
                    if imp in content:
                        self.fail(
                            f"{fname}: contains domain import '{imp}'"
                        )


if __name__ == '__main__':
    unittest.main()
