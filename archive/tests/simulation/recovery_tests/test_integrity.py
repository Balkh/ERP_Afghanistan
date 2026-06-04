"""Tests for integrity protection subpackage."""
from django.test import TestCase
from simulation.recovery.integrity.integrity_guard import IntegrityGuard
from simulation.recovery.integrity.corruption_detector import CorruptionDetector
from simulation.recovery.integrity.partial_state_detector import PartialStateDetector
from simulation.recovery.integrity.consistency_verifier import ConsistencyVerifier
from simulation.recovery.models import CorruptionType, IntegritySeverity


class TestIntegrityGuard(TestCase):
    def test_record_violation(self):
        guard = IntegrityGuard()
        result = guard.record_violation(
            CorruptionType.FINANCIAL, IntegritySeverity.HIGH,
            'accounting', 'Journal imbalance', 1)
        self.assertEqual(result['type'], 'financial')

    def test_violation_count(self):
        guard = IntegrityGuard()
        self.assertEqual(guard.get_violation_count(), 0)
        guard.record_violation(CorruptionType.FINANCIAL, IntegritySeverity.LOW, 'mod', 'desc', 1)
        self.assertEqual(guard.get_violation_count(), 1)

    def test_active_violations(self):
        guard = IntegrityGuard()
        guard.record_violation(CorruptionType.FINANCIAL, IntegritySeverity.HIGH, 'mod', 'desc', 1)
        active = guard.get_active_violations()
        self.assertEqual(len(active), 1)

    def test_low_severity_not_active(self):
        guard = IntegrityGuard()
        guard.record_violation(CorruptionType.FINANCIAL, IntegritySeverity.LOW, 'mod', 'desc', 1)
        active = guard.get_active_violations()
        self.assertEqual(len(active), 0)

    def test_clear(self):
        guard = IntegrityGuard()
        guard.record_violation(CorruptionType.FINANCIAL, IntegritySeverity.HIGH, 'mod', 'desc', 1)
        guard.clear()
        self.assertEqual(guard.get_violation_count(), 0)


class TestCorruptionDetector(TestCase):
    def test_detect_financial_no_corruption(self):
        detector = CorruptionDetector()
        result = detector.detect_financial_corruption(100, 100, 1)
        self.assertIsNone(result)

    def test_detect_financial_corruption(self):
        detector = CorruptionDetector()
        result = detector.detect_financial_corruption(100, 50, 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'financial')

    def test_detect_inventory_no_corruption(self):
        detector = CorruptionDetector()
        result = detector.detect_inventory_corruption(100, 100, 1)
        self.assertIsNone(result)

    def test_detect_inventory_corruption(self):
        detector = CorruptionDetector()
        result = detector.detect_inventory_corruption(100, 80, 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'inventory')

    def test_detect_orphan_none(self):
        detector = CorruptionDetector()
        result = detector.detect_orphan_state(0, 1)
        self.assertIsNone(result)

    def test_detect_orphan_found(self):
        detector = CorruptionDetector()
        result = detector.detect_orphan_state(5, 1)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'orphan_state')

    def test_detection_count(self):
        detector = CorruptionDetector()
        self.assertEqual(detector.get_detection_count(), 0)
        detector.detect_financial_corruption(100, 50, 1)
        self.assertEqual(detector.get_detection_count(), 1)

    def test_severity_scaling(self):
        detector = CorruptionDetector()
        small = detector.detect_financial_corruption(2, 0, 1)
        large = detector.detect_financial_corruption(2000, 0, 1)
        self.assertNotEqual(small['severity'], large['severity'])

    def test_clear(self):
        detector = CorruptionDetector()
        detector.detect_financial_corruption(100, 50, 1)
        detector.clear()
        self.assertEqual(detector.get_detection_count(), 0)


class TestPartialStateDetector(TestCase):
    def test_detect_partial_none(self):
        detector = PartialStateDetector()
        workflows = [{'workflow_id': 'wf_001', 'workflow_type': 'sales',
                       'current_step': 5, 'total_steps': 5, 'status': 'completed'}]
        result = detector.detect_partial_states(workflows)
        self.assertEqual(len(result), 0)

    def test_detect_partial_found(self):
        detector = PartialStateDetector()
        workflows = [{'workflow_id': 'wf_001', 'workflow_type': 'sales',
                       'current_step': 2, 'total_steps': 5, 'status': 'running'}]
        result = detector.detect_partial_states(workflows)
        self.assertEqual(len(result), 1)

    def test_detect_orphan_workflows(self):
        detector = PartialStateDetector()
        workflows = [{'workflow_id': 'wf_001', 'workflow_type': 'sales', 'status': 'running'}]
        result = detector.detect_orphan_workflows(workflows, set())
        self.assertEqual(len(result), 1)

    def test_detect_no_orphans(self):
        detector = PartialStateDetector()
        workflows = [{'workflow_id': 'wf_001', 'workflow_type': 'sales', 'status': 'running'}]
        result = detector.detect_orphan_workflows(workflows, {'wf_001'})
        self.assertEqual(len(result), 0)

    def test_clear(self):
        detector = PartialStateDetector()
        workflows = [{'workflow_id': 'wf_001', 'workflow_type': 'sales',
                       'current_step': 2, 'total_steps': 5, 'status': 'running'}]
        detector.detect_partial_states(workflows)
        detector.clear()


class TestConsistencyVerifier(TestCase):
    def test_verify_journal_balanced(self):
        verifier = ConsistencyVerifier()
        result = verifier.verify_journal_balance(100, 100)
        self.assertTrue(result['passed'])

    def test_verify_journal_unbalanced(self):
        verifier = ConsistencyVerifier()
        result = verifier.verify_journal_balance(100, 90)
        self.assertFalse(result['passed'])

    def test_verify_inventory_consistent(self):
        verifier = ConsistencyVerifier()
        records = [{'expected_qty': 10, 'actual_qty': 10}]
        result = verifier.verify_inventory_consistency(records)
        self.assertTrue(result['passed'])

    def test_verify_inventory_inconsistent(self):
        verifier = ConsistencyVerifier()
        records = [{'expected_qty': 10, 'actual_qty': 8}]
        result = verifier.verify_inventory_consistency(records)
        self.assertFalse(result['passed'])

    def test_verify_reconciliation_within_tolerance(self):
        verifier = ConsistencyVerifier()
        result = verifier.verify_reconciliation(100, 102, tolerance=5)
        self.assertTrue(result['passed'])

    def test_verify_reconciliation_exceeds_tolerance(self):
        verifier = ConsistencyVerifier()
        result = verifier.verify_reconciliation(100, 200, tolerance=5)
        self.assertFalse(result['passed'])

    def test_verify_all_checks(self):
        verifier = ConsistencyVerifier()
        journal = verifier.verify_journal_balance(100, 100)
        result = verifier.verify_all(journal)
        self.assertTrue(result['all_passed'])

    def test_verify_all_fails(self):
        verifier = ConsistencyVerifier()
        journal = verifier.verify_journal_balance(100, 50)
        result = verifier.verify_all(journal)
        self.assertFalse(result['all_passed'])

    def test_clear(self):
        verifier = ConsistencyVerifier()
        verifier.verify_journal_balance(100, 100)
        verifier.clear()
