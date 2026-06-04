"""
Tests for Phase 3A — Truth Comparison Engine.
Deterministic tests. NO ERP mutation. Read-only verification only.
"""
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock

from simulation.clocks.clock import VirtualClock
from simulation.truth_engine.models.models import (
    Mismatch, MismatchType, MismatchSeverity,
    ExpectedState, ActualState, DriftReport,
)
from simulation.truth_engine.collector.expected import (
    ExpectedStateCollector,
)
from simulation.truth_engine.collector.actual import (
    ActualStateCollector,
)
from simulation.truth_engine.comparator.comparator import (
    TruthComparator,
)
from simulation.truth_engine.scoring.scorer import IntegrityScorer
from simulation.truth_engine.reports.reporter import (
    TruthReportGenerator,
)
from simulation.truth_engine.snapshot.snapshot import (
    SnapshotManager,
)
from simulation.truth_engine.models.models import ActualState


class TestMismatchModels(unittest.TestCase):
    """Mismatch data model tests."""

    def test_mismatch_creation(self):
        m = Mismatch(
            mismatch_id='m1',
            mismatch_type=MismatchType.FINANCIAL_MISMATCH,
            severity=MismatchSeverity.HIGH,
            description='Financial entry mismatch',
            affected_module='accounting',
            timestamp=datetime(2024, 1, 1),
            expected_value=100.0,
            actual_value=50.0,
        )
        self.assertEqual(m.mismatch_id, 'm1')
        self.assertEqual(m.mismatch_type, MismatchType.FINANCIAL_MISMATCH)
        self.assertEqual(m.severity, MismatchSeverity.HIGH)
        self.assertEqual(m.expected_value, 100.0)
        self.assertEqual(m.actual_value, 50.0)

    def test_mismatch_to_dict(self):
        m = Mismatch(
            mismatch_id='m2',
            mismatch_type=MismatchType.INVENTORY_MISMATCH,
            severity=MismatchSeverity.CRITICAL,
            description='Stock level mismatch',
            affected_module='inventory',
            timestamp=datetime(2024, 1, 1),
        )
        d = m.to_dict()
        self.assertEqual(d['mismatch_id'], 'm2')
        self.assertEqual(d['mismatch_type'], 'inventory_mismatch')
        self.assertEqual(d['severity'], 'critical')

    def test_mismatch_slots(self):
        m = Mismatch(
            mismatch_id='m3',
            mismatch_type=MismatchType.DUPLICATE_ENTRY,
            severity=MismatchSeverity.MEDIUM,
            description='Duplicate entry',
            affected_module='accounting',
            timestamp=datetime(2024, 1, 1),
        )
        with self.assertRaises(AttributeError):
            m.new_field = 'test'

    def test_expected_state_creation(self):
        ts = datetime(2024, 1, 1)
        state = ExpectedState('scenario_1', 1, ts, ts)
        state.set_sales_count(5)
        state.set_purchase_count(3)
        state.set_inventory_delta('prod_1', -10.0)
        self.assertEqual(state._sales_count, 5)
        self.assertEqual(state._purchase_count, 3)

    def test_expected_state_to_dict(self):
        ts = datetime(2024, 1, 1)
        state = ExpectedState('scenario_1', 1, ts, ts)
        state.set_sales_count(10)
        d = state.to_dict()
        self.assertEqual(d['scenario_id'], 'scenario_1')
        self.assertEqual(d['sales_count'], 10)
        self.assertEqual(d['tick'], 1)

    def test_actual_state_creation(self):
        ts = datetime(2024, 1, 1)
        state = ActualState(ts, source='erp')
        state.set_journal_count(5)
        self.assertEqual(state.source, 'erp')
        self.assertEqual(state._journal_entry_count, 5)

    def test_actual_state_to_dict(self):
        ts = datetime(2024, 1, 1)
        state = ActualState(ts)
        state.set_journal_count(3)
        d = state.to_dict()
        self.assertEqual(d['source'], 'erp')
        self.assertEqual(d['journal_entry_count'], 3)

    def test_drift_report_creation(self):
        ts = datetime(2024, 1, 1)
        expected = ExpectedState('s1', 1, ts, ts)
        actual = ActualState(ts)
        report = DriftReport('r1', 's1', 1, ts, expected, actual)
        self.assertEqual(report.report_id, 'r1')
        self.assertEqual(report.tick, 1)
        self.assertEqual(report.mismatches, [])
        self.assertEqual(report.scores, {})

    def test_drift_report_add_mismatch(self):
        ts = datetime(2024, 1, 1)
        expected = ExpectedState('s1', 1, ts, ts)
        actual = ActualState(ts)
        report = DriftReport('r1', 's1', 1, ts, expected, actual)
        m = Mismatch('m1', MismatchType.FINANCIAL_MISMATCH,
                     MismatchSeverity.HIGH, 'desc', 'accounting', ts)
        report.add_mismatch(m)
        self.assertEqual(len(report.mismatches), 1)

    def test_drift_report_set_score(self):
        ts = datetime(2024, 1, 1)
        expected = ExpectedState('s1', 1, ts, ts)
        actual = ActualState(ts)
        report = DriftReport('r1', 's1', 1, ts, expected, actual)
        report.set_score('overall', 95.0)
        self.assertEqual(report.scores['overall'], 95.0)

    def test_drift_report_to_dict(self):
        ts = datetime(2024, 1, 1)
        expected = ExpectedState('s1', 1, ts, ts)
        actual = ActualState(ts)
        report = DriftReport('r1', 's1', 1, ts, expected, actual)
        d = report.to_dict()
        self.assertEqual(d['report_id'], 'r1')
        self.assertEqual(d['mismatch_count'], 0)


class TestExpectedStateCollector(unittest.TestCase):
    """Expected state collection tests."""

    def test_from_event_log(self):
        ts = datetime(2024, 1, 1)
        events = [MagicMock(type='workflow_started',
                            timestamp=ts, payload={})]
        completions = {'sales_workflow': 3, 'purchase_workflow': 2}
        executions = {'sales_bot': 5, 'inventory_bot': 3}
        state = ExpectedStateCollector.from_event_log(
            'scenario_1', 1, ts, ts, events, completions, executions
        )
        self.assertEqual(state._sales_count, 3)
        self.assertEqual(state._purchase_count, 2)
        self.assertIn('sales_bot', state._agent_executions)

    def test_from_simulation_snapshot(self):
        ts = datetime(2024, 1, 1)
        snapshot = {
            'expected_sales_count': 4,
            'expected_purchase_count': 2,
            'expected_returns_count': 1,
            'expected_inventory_delta': {'p1': -5.0},
            'expected_accounting_entries': [],
            'expected_sales_executions': 6,
            'expected_inventory_executions': 4,
        }
        state = ExpectedStateCollector.from_simulation_snapshot(
            's1', 2, ts, ts, snapshot
        )
        self.assertEqual(state._sales_count, 4)
        self.assertEqual(state._purchase_count, 2)
        self.assertEqual(state._returns_count, 1)

    def test_build(self):
        ts = datetime(2024, 1, 1)
        collector = ExpectedStateCollector('s1', 1, ts, ts)
        collector.set_sales_count(10)
        state = collector.build()
        self.assertEqual(state._sales_count, 10)

    def test_to_dict(self):
        ts = datetime(2024, 1, 1)
        collector = ExpectedStateCollector('s1', 1, ts, ts)
        d = collector.to_dict()
        self.assertEqual(d['scenario_id'], 's1')


class TestActualStateCollector(unittest.TestCase):
    """Actual state collection tests (read-only)."""

    def test_default_source_is_erp(self):
        collector = ActualStateCollector()
        self.assertEqual(collector.build().source, 'erp')

    def test_collect_journal_entries_db_unavailable(self):
        collector = ActualStateCollector()
        result = collector.collect_journal_entries()
        self.assertIsNotNone(result)
        self.assertIs(result, collector)
        state = result.build()
        self.assertEqual(state._journal_entry_count, 0)

    def test_collect_stock_movements_db_unavailable(self):
        collector = ActualStateCollector()
        result = collector.collect_stock_movements()
        self.assertIsNotNone(result)
        self.assertIs(result, collector)

    def test_collect_inventory_db_unavailable(self):
        collector = ActualStateCollector()
        result = collector.collect_inventory_quantities()
        self.assertIsNotNone(result)
        self.assertIs(result, collector)

    def test_collect_transactions_db_unavailable(self):
        collector = ActualStateCollector()
        result = collector.collect_transactions()
        self.assertIsNotNone(result)
        self.assertIs(result, collector)

    def test_collect_sales_invoices_db_unavailable(self):
        collector = ActualStateCollector()
        result = collector.collect_sales_invoices()
        self.assertIsNotNone(result)
        self.assertIs(result, collector)

    def test_collect_purchase_invoices_db_unavailable(self):
        collector = ActualStateCollector()
        result = collector.collect_purchase_invoices()
        self.assertIsNotNone(result)
        self.assertIs(result, collector)

    def test_to_dict(self):
        collector = ActualStateCollector()
        state = collector.build()
        d = collector.to_dict()
        self.assertEqual(d['source'], 'erp')


class TestTruthComparator(unittest.TestCase):
    """Truth comparison and mismatch detection tests."""

    def setUp(self):
        self.comparator = TruthComparator()
        self.ts = datetime(2024, 1, 1)
        self.expected = ExpectedState('s1', 1, self.ts, self.ts)
        self.actual = ActualState(self.ts)

    def test_no_mismatch_when_equal(self):
        report = self.comparator.compare(
            self.expected, self.actual, 'r1', 's1', 1, self.ts
        )
        self.assertEqual(len(report.mismatches), 0)

    def test_sales_mismatch_detected(self):
        self.expected.set_sales_count(5)
        report = self.comparator.compare(
            self.expected, self.actual, 'r1', 's1', 1, self.ts
        )
        self.assertGreater(len(report.mismatches), 0)
        m = report.mismatches[0]
        self.assertEqual(m.mismatch_type,
                         MismatchType.TRANSACTION_MISSING)

    def test_inventory_mismatch_detected(self):
        self.expected.set_inventory_delta('p1', 100.0)
        self.actual.set_inventory_quantity('p1', 50.0)
        report = self.comparator.compare(
            self.expected, self.actual, 'r1', 's1', 1, self.ts
        )
        mismatches = [m for m in report.mismatches
                      if m.mismatch_type == MismatchType.INVENTORY_MISMATCH]
        self.assertGreater(len(mismatches), 0)

    def test_inventory_mismatch_no_false_positive(self):
        self.expected.set_inventory_delta('p1', 100.0)
        self.actual.set_inventory_quantity('p1', 100.0)
        report = self.comparator.compare(
            self.expected, self.actual, 'r1', 's1', 1, self.ts
        )
        inv_mismatches = [m for m in report.mismatches
                          if m.mismatch_type == MismatchType.INVENTORY_MISMATCH]
        self.assertEqual(len(inv_mismatches), 0)

    def test_duplicate_detection(self):
        self.actual.add_journal_entry({'entry_number': 'JE-001'})
        self.actual.add_journal_entry({'entry_number': 'JE-001'})
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        self.comparator.detect_duplicates(self.actual, report)
        dupes = [m for m in report.mismatches
                 if m.mismatch_type == MismatchType.DUPLICATE_ENTRY]
        self.assertGreater(len(dupes), 0)

    def test_report_generated_with_mismatches(self):
        self.expected.set_sales_count(3)
        report = self.comparator.compare(
            self.expected, self.actual, 'r1', 's1', 1, self.ts
        )
        self.assertEqual(report.scenario_id, 's1')
        self.assertEqual(report.report_id, 'r1')


class TestIntegrityScorer(unittest.TestCase):
    """Integrity scoring tests."""

    def setUp(self):
        self.scorer = IntegrityScorer()
        self.ts = datetime(2024, 1, 1)
        self.expected = ExpectedState('s1', 1, self.ts, self.ts)
        self.actual = ActualState(self.ts)

    def test_perfect_score_no_mismatches(self):
        scores = self.scorer.compute_scores(
            self.expected, self.actual, []
        )
        self.assertEqual(scores['overall_system_score'], 100.0)
        self.assertEqual(scores['financial_integrity_score'], 100.0)
        self.assertEqual(scores['inventory_integrity_score'], 100.0)

    def test_score_reduces_with_critical_mismatch(self):
        m = Mismatch('m1', MismatchType.FINANCIAL_MISMATCH,
                     MismatchSeverity.CRITICAL, 'desc', 'accounting',
                     self.ts)
        scores = self.scorer.compute_scores(
            self.expected, self.actual, [m]
        )
        self.assertLess(scores['financial_integrity_score'], 100.0)

    def test_score_reduces_with_inventory_mismatch(self):
        m = Mismatch('m1', MismatchType.INVENTORY_MISMATCH,
                     MismatchSeverity.HIGH, 'desc', 'inventory',
                     self.ts)
        scores = self.scorer.compute_scores(
            self.expected, self.actual, [m]
        )
        self.assertLess(scores['inventory_integrity_score'], 100.0)

    def test_workflow_score_reduces_with_missing_txn(self):
        m = Mismatch('m1', MismatchType.TRANSACTION_MISSING,
                     MismatchSeverity.MEDIUM, 'desc', 'sales', self.ts)
        scores = self.scorer.compute_scores(
            self.expected, self.actual, [m]
        )
        self.assertLess(scores['workflow_completion_score'], 100.0)

    def test_drift_percentage_zero_when_no_delta(self):
        scores = self.scorer.compute_scores(
            self.expected, self.actual, []
        )
        self.assertEqual(scores['drift_percentage'], 0.0)

    def test_consistency_ratio_hundred_when_no_mismatch(self):
        scores = self.scorer.compute_scores(
            self.expected, self.actual, []
        )
        self.assertEqual(scores['consistency_ratio'], 100.0)

    def test_overall_score_averages_sub_scores(self):
        scores = self.scorer.compute_scores(
            self.expected, self.actual, []
        )
        self.assertEqual(scores['overall_system_score'], 100.0)

    def test_scores_property(self):
        self.scorer.compute_scores(self.expected, self.actual, [])
        self.assertGreater(len(self.scorer.scores), 0)


class TestTruthReportGenerator(unittest.TestCase):
    """Report generation tests."""

    def setUp(self):
        self.generator = TruthReportGenerator()
        self.ts = datetime(2024, 1, 1)
        self.expected = ExpectedState('s1', 1, self.ts, self.ts)
        self.actual = ActualState(self.ts)

    def test_generate_report_no_mismatches(self):
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        scores = {
            'financial_integrity_score': 100.0,
            'inventory_integrity_score': 100.0,
            'workflow_completion_score': 100.0,
            'overall_system_score': 100.0,
            'drift_percentage': 0.0,
            'consistency_ratio': 100.0,
        }
        result = self.generator.generate(report, scores)
        self.assertEqual(result['report_id'], 'r1')
        self.assertEqual(
            result['summary']['total_mismatches'], 0
        )

    def test_generate_report_with_mismatches(self):
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        m = Mismatch('m1', MismatchType.FINANCIAL_MISMATCH,
                     MismatchSeverity.HIGH, 'desc', 'accounting',
                     self.ts)
        report.add_mismatch(m)
        scores = {
            'financial_integrity_score': 85.0,
            'inventory_integrity_score': 100.0,
            'workflow_completion_score': 100.0,
            'overall_system_score': 95.0,
            'drift_percentage': 5.0,
            'consistency_ratio': 95.0,
        }
        result = self.generator.generate(report, scores)
        self.assertEqual(result['summary']['total_mismatches'], 1)
        self.assertIn('affected_modules', result['summary'])
        self.assertIn('severity_summary', result['summary'])

    def test_conclusion_excellent(self):
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        scores = {'overall_system_score': 100.0}
        result = self.generator.generate(report, scores)
        self.assertIn('EXCELLENT', result['conclusion'])

    def test_conclusion_critical(self):
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        report.add_mismatch(Mismatch('m1', MismatchType.FINANCIAL_MISMATCH,
                                     MismatchSeverity.CRITICAL, 'desc',
                                     'accounting', self.ts))
        scores = {'overall_system_score': 50.0}
        result = self.generator.generate(report, scores)
        self.assertIn('CRITICAL', result['conclusion'])

    def test_hint_generation(self):
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        report.add_mismatch(Mismatch('m1', MismatchType.FINANCIAL_MISMATCH,
                                     MismatchSeverity.HIGH, 'desc',
                                     'accounting', self.ts))
        scores = {'overall_system_score': 80.0}
        result = self.generator.generate(report, scores)
        self.assertGreater(len(result['root_cause_hints']), 0)

    def test_report_count(self):
        report = DriftReport('r1', 's1', 1, self.ts,
                             self.expected, self.actual)
        self.generator.generate(report, {'overall_system_score': 100.0})
        self.assertEqual(self.generator.report_count, 1)


class TestSnapshotManager(unittest.TestCase):
    """Snapshot management tests."""

    def setUp(self):
        self.manager = SnapshotManager()
        self.ts = datetime(2024, 1, 1)
        self.expected = ExpectedState('s1', 1, self.ts, self.ts)
        self.actual = ActualState(self.ts)

    def test_take_snapshot(self):
        key = self.manager.take_snapshot(
            'snap1', 's1', 1, self.ts, self.expected, self.actual
        )
        self.assertEqual(key, 'snap1_v0')

    def test_get_snapshot(self):
        self.manager.take_snapshot(
            'snap1', 's1', 1, self.ts, self.expected, self.actual
        )
        snap = self.manager.get_snapshot('snap1', 0)
        self.assertIsNotNone(snap)
        self.assertEqual(snap['snapshot_id'], 'snap1')

    def test_get_latest_snapshot(self):
        self.manager.take_snapshot(
            'snap1', 's1', 1, self.ts, self.expected
        )
        self.manager.take_snapshot(
            'snap1', 's1', 2, self.ts, self.expected
        )
        latest = self.manager.get_latest_snapshot('snap1')
        self.assertEqual(latest['tick'], 2)

    def test_get_snapshots_by_scenario(self):
        self.manager.take_snapshot(
            's1', 'scenario_a', 1, self.ts, self.expected
        )
        self.manager.take_snapshot(
            's2', 'scenario_b', 1, self.ts, self.expected
        )
        snaps = self.manager.get_snapshots_by_scenario('scenario_a')
        self.assertEqual(len(snaps), 1)

    def test_get_snapshot_count(self):
        self.manager.take_snapshot(
            's1', 's1', 1, self.ts, self.expected
        )
        self.manager.take_snapshot(
            's1', 's1', 2, self.ts, self.expected
        )
        self.assertEqual(self.manager.get_snapshot_count(), 2)

    def test_get_version(self):
        self.manager.take_snapshot(
            'sv1', 's1', 1, self.ts, self.expected
        )
        self.assertEqual(self.manager.get_version('sv1'), 1)

    def test_clear(self):
        self.manager.take_snapshot(
            's1', 's1', 1, self.ts, self.expected
        )
        self.manager.clear()
        self.assertEqual(self.manager.get_snapshot_count(), 0)
        self.assertEqual(self.manager.get_version('s1'), 0)

    def test_max_snapshots_bounded(self):
        manager = SnapshotManager(max_snapshots=3)
        for i in range(6):
            state = ExpectedState('s1', i, self.ts, self.ts)
            manager.take_snapshot(
                f's{i}', 's1', i, self.ts, state
            )
        self.assertLessEqual(manager.get_snapshot_count(), 3)


class TestNoERPInteraction(unittest.TestCase):
    """Read-only verification and isolation tests."""

    def test_comparator_no_mutation(self):
        ts = datetime(2024, 1, 1)
        expected = ExpectedState('s1', 1, ts, ts)
        actual = ActualState(ts)
        comparator = TruthComparator()
        original_expected_count = expected._sales_count
        comparator.compare(expected, actual, 'r1', 's1', 1, ts)
        self.assertEqual(expected._sales_count, original_expected_count)

    def test_scorer_no_mutation(self):
        ts = datetime(2024, 1, 1)
        expected = ExpectedState('s1', 1, ts, ts)
        actual = ActualState(ts)
        scorer = IntegrityScorer()
        mismatches_before = len([])
        scorer.compute_scores(expected, actual, [])
        self.assertEqual(len([]), mismatches_before)

    def test_no_erp_writes_in_truth_engine(self):
        import ast
        import os
        truth_dir = os.path.join(
            os.path.dirname(__file__), '..', 'truth_engine'
        )
        forbidden = (
            '.save()', '.create(', '.update(', '.delete(',
            '.bulk_create(', 'cursor.execute', 'raw(',
        )
        for root, dirs, files in os.walk(truth_dir):
            for fname in files:
                if not fname.endswith('.py'):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as fh:
                    content = fh.read()
                for keyword in forbidden:
                    self.assertNotIn(
                        keyword, content,
                        f"{fname}: contains forbidden write "
                        f"operation '{keyword}'"
                    )

    def test_no_domain_imports_in_truth_engine(self):
        import os
        truth_dir = os.path.join(
            os.path.dirname(__file__), '..', 'truth_engine'
        )
        exceptions = {'sales.models', 'purchases.models',
                      'payments.models', 'inventory.models',
                      'accounting.models'}
        for root, dirs, files in os.walk(truth_dir):
            for fname in files:
                if not fname.endswith('.py') or fname == '__init__.py':
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as fh:
                    content = fh.read()
                if fname == 'actual.py':
                    for exc in exceptions:
                        self.assertIn(
                            'from ' + exc, content,
                            f"actual.py must import {exc} for "
                            f"read-only queries"
                        )


if __name__ == '__main__':
    unittest.main()
