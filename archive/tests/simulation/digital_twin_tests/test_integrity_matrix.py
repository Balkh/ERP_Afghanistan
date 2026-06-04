import unittest

from simulation.digital_twin.integrity.accounting_validator import AccountingValidator
from simulation.digital_twin.integrity.inventory_validator import InventoryValidator
from simulation.digital_twin.integrity.transaction_validator import TransactionValidator
from simulation.digital_twin.integrity.replay_validator import ReplayValidator
from simulation.digital_twin.integrity.audit_validator import AuditValidator
from simulation.digital_twin.integrity.matrix import IntegrityMatrix


class TestAccountingValidator(unittest.TestCase):
    def setUp(self):
        self.validator = AccountingValidator()

    def test_balance_equal(self):
        entries = [
            {'debit': 100.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 100.0},
        ]
        result = self.validator.check_balance(entries)
        self.assertTrue(result['passed'])
        self.assertEqual(result['total_debits'], 100.0)
        self.assertEqual(result['total_credits'], 100.0)
        self.assertAlmostEqual(result['difference'], 0.0)

    def test_balance_imbalance(self):
        entries = [
            {'debit': 100.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 50.0},
        ]
        result = self.validator.check_balance(entries)
        self.assertFalse(result['passed'])
        self.assertNotAlmostEqual(result['difference'], 0.0)

    def test_no_duplicates_unique(self):
        entries = [
            {'entry_id': 'E1'},
            {'entry_id': 'E2'},
            {'entry_id': 'E3'},
        ]
        result = self.validator.check_no_duplicates(entries)
        self.assertTrue(result['passed'])
        self.assertEqual(result['count'], 0)

    def test_no_duplicates_with_duplicates(self):
        entries = [
            {'entry_id': 'E1'},
            {'entry_id': 'E2'},
            {'entry_id': 'E1'},
            {'entry_id': 'E3'},
            {'entry_id': 'E2'},
        ]
        result = self.validator.check_no_duplicates(entries)
        self.assertFalse(result['passed'])
        self.assertGreater(result['count'], 0)

    def test_chronological_ordered(self):
        entries = [
            {'tick': 1},
            {'tick': 2},
            {'tick': 3},
        ]
        result = self.validator.check_chronological(entries)
        self.assertTrue(result['passed'])
        self.assertEqual(result['out_of_order'], 0)

    def test_chronological_unordered(self):
        entries = [
            {'tick': 1},
            {'tick': 3},
            {'tick': 2},
        ]
        result = self.validator.check_chronological(entries)
        self.assertFalse(result['passed'])
        self.assertGreater(result['out_of_order'], 0)

    def test_empty_lists_pass(self):
        self.assertTrue(self.validator.check_balance([])['passed'])
        self.assertTrue(self.validator.check_no_duplicates([])['passed'])
        self.assertTrue(self.validator.check_chronological([])['passed'])


class TestInventoryValidator(unittest.TestCase):
    def setUp(self):
        self.validator = InventoryValidator()

    def test_no_negative_all_positive(self):
        batches = [
            {'batch_id': 'B1', 'remaining_quantity': 10.0},
            {'batch_id': 'B2', 'remaining_quantity': 5.0},
        ]
        result = self.validator.check_no_negative(batches)
        self.assertTrue(result['passed'])
        self.assertEqual(result['count'], 0)

    def test_no_negative_with_negative(self):
        batches = [
            {'batch_id': 'B1', 'remaining_quantity': 10.0},
            {'batch_id': 'B2', 'remaining_quantity': -3.0},
            {'batch_id': 'B3', 'remaining_quantity': -1.0},
        ]
        result = self.validator.check_no_negative(batches)
        self.assertFalse(result['passed'])
        self.assertIn('B2', result['negative_batches'])
        self.assertIn('B3', result['negative_batches'])
        self.assertEqual(result['count'], 2)

    def test_fifo_correct(self):
        movements = [
            {'batch_id': 'B1', 'direction': 'IN', 'quantity': 10.0, 'tick': 1},
            {'batch_id': 'B1', 'direction': 'OUT', 'quantity': 5.0, 'tick': 2},
            {'batch_id': 'B1', 'direction': 'OUT', 'quantity': 5.0, 'tick': 3},
        ]
        result = self.validator.check_fifo(movements)
        self.assertTrue(result['passed'])
        self.assertEqual(result['count'], 0)

    def test_fifo_violation(self):
        movements = [
            {'batch_id': 'B1', 'direction': 'OUT', 'quantity': 5.0, 'tick': 1},
            {'batch_id': 'B1', 'direction': 'IN', 'quantity': 10.0, 'tick': 2},
        ]
        result = self.validator.check_fifo(movements)
        self.assertFalse(result['passed'])
        self.assertGreater(result['count'], 0)

    def test_batch_integrity(self):
        batches = [
            {'batch_id': 'B1', 'remaining_quantity': 10.0},
            {'batch_id': 'B2', 'remaining_quantity': -1.0},
            {'remaining_quantity': 5.0},
        ]
        result = self.validator.check_batch_integrity(batches)
        self.assertFalse(result['passed'])
        self.assertGreater(len(result['corrupted_batches']), 0)
        self.assertGreater(len(result['issues']), 0)


class TestTransactionValidator(unittest.TestCase):
    def setUp(self):
        self.validator = TransactionValidator()

    def test_atomicity_complete(self):
        transactions = [
            {
                'txn_id': 'T1',
                'status': 'committed',
                'steps': [
                    {'name': 'step1', 'completed': True},
                    {'name': 'step2', 'completed': True},
                ],
            }
        ]
        result = self.validator.check_atomicity(transactions)
        self.assertTrue(result['passed'])
        self.assertEqual(result['count'], 0)

    def test_atomicity_partial(self):
        transactions = [
            {
                'txn_id': 'T1',
                'status': 'committed',
                'steps': [
                    {'name': 'step1', 'completed': True},
                    {'name': 'step2', 'completed': False},
                ],
            }
        ]
        result = self.validator.check_atomicity(transactions)
        self.assertFalse(result['passed'])
        self.assertEqual(result['count'], 1)
        self.assertIn('T1', result['partial_txns'])

    def test_no_partial(self):
        transactions = [
            {
                'txn_id': 'T1',
                'status': 'committed',
                'entries': [
                    {'entry_id': 'E1', 'posted': True},
                    {'entry_id': 'E2', 'posted': True},
                ],
            },
            {
                'txn_id': 'T2',
                'status': 'committed',
                'entries': [
                    {'entry_id': 'E3', 'posted': True},
                    {'entry_id': 'E4', 'posted': False},
                ],
            },
        ]
        result = self.validator.check_no_partial(transactions)
        self.assertFalse(result['passed'])
        self.assertIn('T2', result['partial_txns'])


class TestReplayValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ReplayValidator()

    def test_determinism_identical(self):
        original = [
            {'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}},
            {'event_id': 'E2', 'type': 'update', 'tick': 2, 'payload': {}},
        ]
        replay = [
            {'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}},
            {'event_id': 'E2', 'type': 'update', 'tick': 2, 'payload': {}},
        ]
        result = self.validator.check_determinism(original, replay)
        self.assertTrue(result['passed'])
        self.assertEqual(result['match_percentage'], 100.0)

    def test_determinism_mismatch(self):
        original = [
            {'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}},
        ]
        replay = [
            {'event_id': 'E1', 'type': 'delete', 'tick': 1, 'payload': {}},
        ]
        result = self.validator.check_determinism(original, replay)
        self.assertFalse(result['passed'])
        self.assertLess(result['match_percentage'], 100.0)
        self.assertGreater(len(result['mismatches']), 0)

    def test_hashes(self):
        original_hashes = {'E1': 'abc', 'E2': 'def'}
        replay_hashes = {'E1': 'abc', 'E2': 'xyz'}
        result = self.validator.check_hashes(original_hashes, replay_hashes)
        self.assertFalse(result['passed'])
        self.assertEqual(result['matching'], 1)
        self.assertEqual(result['divergent'], 1)


class TestAuditValidator(unittest.TestCase):
    def setUp(self):
        self.validator = AuditValidator()

    def test_causal_traceability_complete(self):
        events = [
            {'event_id': 'E1', 'type': 'root', 'tick': 1, 'causal_parent': None},
            {'event_id': 'E2', 'type': 'child', 'tick': 2, 'causal_parent': 'E1'},
            {'event_id': 'E3', 'type': 'child', 'tick': 3, 'causal_parent': 'E2'},
        ]
        result = self.validator.check_causal_traceability(events)
        self.assertTrue(result['passed'])
        self.assertEqual(result['count'], 0)

    def test_causal_traceability_missing_parent(self):
        events = [
            {'event_id': 'E1', 'type': 'root', 'tick': 1, 'causal_parent': None},
            {'event_id': 'E2', 'type': 'child', 'tick': 2, 'causal_parent': 'E99'},
        ]
        result = self.validator.check_causal_traceability(events)
        self.assertFalse(result['passed'])
        self.assertEqual(result['count'], 1)

    def test_completeness(self):
        events = [
            {'event_id': 'E1', 'type': 'create', 'tick': 1},
            {'event_id': 'E3', 'type': 'update', 'tick': 3},
        ]
        result = self.validator.check_completeness(events)
        self.assertFalse(result['passed'])
        self.assertGreater(len(result['gaps']), 0)


class TestIntegrityMatrix(unittest.TestCase):
    def setUp(self):
        self.matrix = IntegrityMatrix(stop_on_violation=True, max_reports=10)

    def test_validate_all_valid(self):
        state = {
            'journal_entries': [
                {'debit': 100.0, 'credit': 0.0},
                {'debit': 0.0, 'credit': 100.0},
            ],
            'batches': [
                {'batch_id': 'B1', 'remaining_quantity': 10.0},
            ],
            'movements': [
                {'batch_id': 'B1', 'direction': 'IN', 'quantity': 10.0, 'tick': 1},
            ],
            'transactions': [
                {
                    'txn_id': 'T1',
                    'status': 'committed',
                    'steps': [{'name': 's1', 'completed': True}],
                },
            ],
            'original_events': [
                {'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}},
            ],
            'replay_events': [
                {'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}},
            ],
            'audit_events': [
                {'event_id': 'E1', 'type': 'root', 'tick': 1, 'causal_parent': None},
            ],
        }
        result = self.matrix.validate_all(state)
        self.assertTrue(result['all_pass'])
        self.assertEqual(len(result['violations']), 0)

    def test_validate_all_invalid(self):
        state = {
            'journal_entries': [
                {'debit': 100.0, 'credit': 0.0},
                {'debit': 0.0, 'credit': 50.0},
            ],
            'batches': [
                {'batch_id': 'B1', 'remaining_quantity': -5.0},
            ],
            'movements': [],
            'transactions': [],
            'audit_events': [],
        }
        result = self.matrix.validate_all(state)
        self.assertFalse(result['all_pass'])
        self.assertGreater(len(result['violations']), 0)

    def test_validate_accounting(self):
        entries = [
            {'debit': 100.0, 'credit': 0.0, 'entry_id': 'E1', 'tick': 1},
            {'debit': 0.0, 'credit': 100.0, 'entry_id': 'E2', 'tick': 2},
        ]
        result = self.matrix.validate_accounting(entries)
        self.assertTrue(result['all_pass'])
        self.assertEqual(result['domain'], 'accounting')
        self.assertEqual(len(result['checks']), 3)

    def test_validate_inventory(self):
        batches = [{'batch_id': 'B1', 'remaining_quantity': 10.0}]
        movements = [{'batch_id': 'B1', 'direction': 'IN', 'quantity': 10.0, 'tick': 1}]
        result = self.matrix.validate_inventory(batches, movements)
        self.assertTrue(result['all_pass'])
        self.assertEqual(result['domain'], 'inventory')
        self.assertEqual(len(result['checks']), 3)

    def test_validate_transactions(self):
        transactions = [
            {
                'txn_id': 'T1',
                'status': 'committed',
                'steps': [{'name': 's1', 'completed': True}],
            },
        ]
        result = self.matrix.validate_transactions(transactions)
        self.assertTrue(result['all_pass'])
        self.assertEqual(result['domain'], 'transactions')
        self.assertEqual(len(result['checks']), 3)

    def test_validate_replay(self):
        original = [{'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}}]
        replay = [{'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}}]
        result = self.matrix.validate_replay(original, replay)
        self.assertTrue(result['all_pass'])
        self.assertEqual(result['domain'], 'replay')

    def test_validate_replay_with_hashes(self):
        original = [{'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}}]
        replay = [{'event_id': 'E1', 'type': 'create', 'tick': 1, 'payload': {}}]
        result = self.matrix.validate_replay(
            original, replay,
            original_hashes={'E1': 'abc'}, replay_hashes={'E1': 'abc'},
        )
        self.assertTrue(result['all_pass'])
        self.assertEqual(len(result['checks']), 2)

    def test_validate_audit(self):
        events = [
            {'event_id': 'E1', 'type': 'root', 'tick': 1, 'causal_parent': None},
        ]
        result = self.matrix.validate_audit(events)
        self.assertTrue(result['all_pass'])
        self.assertEqual(result['domain'], 'audit')
        self.assertEqual(len(result['checks']), 3)

    def test_clear(self):
        state = {'journal_entries': []}
        self.matrix.validate_all(state)
        self.assertGreater(self.matrix.get_report_count(), 0)
        self.matrix.clear()
        self.assertEqual(self.matrix.get_report_count(), 0)

    def test_max_reports(self):
        matrix = IntegrityMatrix(stop_on_violation=True, max_reports=3)
        for _ in range(5):
            matrix.validate_all({'journal_entries': []})
        self.assertEqual(matrix.get_report_count(), 3)
