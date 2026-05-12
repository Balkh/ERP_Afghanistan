import datetime
from typing import List, Dict, Optional
from collections import deque

from .accounting_validator import AccountingValidator
from .inventory_validator import InventoryValidator
from .transaction_validator import TransactionValidator
from .replay_validator import ReplayValidator
from .audit_validator import AuditValidator


class IntegrityMatrix:
    def __init__(self, stop_on_violation: bool = True, max_reports: int = 100):
        self.stop_on_violation = stop_on_violation
        self._reports: deque = deque(maxlen=max_reports)
        self._accounting = AccountingValidator()
        self._inventory = InventoryValidator()
        self._transactions = TransactionValidator()
        self._replay = ReplayValidator()
        self._audit = AuditValidator()

    def _make_check_result(self, name: str, result: Dict) -> Dict:
        return {
            'name': name,
            'passed': result.get('passed', False),
            'details': result.get('details', ''),
            'subchecks': [result],
        }

    def validate_accounting(self, entries: List[Dict]) -> Dict:
        try:
            balance = self._accounting.check_balance(entries)
            duplicates = self._accounting.check_no_duplicates(entries)
            chronological = self._accounting.check_chronological(entries)
            all_pass = balance['passed'] and duplicates['passed'] and chronological['passed']
            return {
                'domain': 'accounting',
                'all_pass': all_pass,
                'checks': [
                    self._make_check_result('balance', balance),
                    self._make_check_result('no_duplicates', duplicates),
                    self._make_check_result('chronological', chronological),
                ],
            }
        except Exception as e:
            return {
                'domain': 'accounting',
                'all_pass': False,
                'checks': [],
                'error': str(e),
            }

    def validate_inventory(self, batches: List[Dict], movements: List[Dict]) -> Dict:
        try:
            no_negative = self._inventory.check_no_negative(batches)
            fifo = self._inventory.check_fifo(movements)
            batch_integrity = self._inventory.check_batch_integrity(batches)
            all_pass = no_negative['passed'] and fifo['passed'] and batch_integrity['passed']
            return {
                'domain': 'inventory',
                'all_pass': all_pass,
                'checks': [
                    self._make_check_result('no_negative', no_negative),
                    self._make_check_result('fifo', fifo),
                    self._make_check_result('batch_integrity', batch_integrity),
                ],
            }
        except Exception as e:
            return {
                'domain': 'inventory',
                'all_pass': False,
                'checks': [],
                'error': str(e),
            }

    def validate_transactions(self, transactions: List[Dict]) -> Dict:
        try:
            atomicity = self._transactions.check_atomicity(transactions)
            no_partial = self._transactions.check_no_partial(transactions)
            rollback = self._transactions.check_rollback(transactions)
            all_pass = atomicity['passed'] and no_partial['passed'] and rollback['passed']
            return {
                'domain': 'transactions',
                'all_pass': all_pass,
                'checks': [
                    self._make_check_result('atomicity', atomicity),
                    self._make_check_result('no_partial', no_partial),
                    self._make_check_result('rollback', rollback),
                ],
            }
        except Exception as e:
            return {
                'domain': 'transactions',
                'all_pass': False,
                'checks': [],
                'error': str(e),
            }

    def validate_replay(
        self,
        original: List[Dict],
        replay: List[Dict],
        original_hashes: Optional[Dict] = None,
        replay_hashes: Optional[Dict] = None,
    ) -> Dict:
        try:
            determinism = self._replay.check_determinism(original, replay)
            checks = [self._make_check_result('determinism', determinism)]
            if original_hashes is not None and replay_hashes is not None:
                hashes = self._replay.check_hashes(original_hashes, replay_hashes)
                checks.append(self._make_check_result('hashes', hashes))
            all_pass = all(c['passed'] for c in checks)
            return {
                'domain': 'replay',
                'all_pass': all_pass,
                'checks': checks,
            }
        except Exception as e:
            return {
                'domain': 'replay',
                'all_pass': False,
                'checks': [],
                'error': str(e),
            }

    def validate_audit(self, events: List[Dict]) -> Dict:
        try:
            causal = self._audit.check_causal_traceability(events)
            completeness = self._audit.check_completeness(events)
            chronological = self._audit.check_chronological(events)
            all_pass = causal['passed'] and completeness['passed'] and chronological['passed']
            return {
                'domain': 'audit',
                'all_pass': all_pass,
                'checks': [
                    self._make_check_result('causal_traceability', causal),
                    self._make_check_result('completeness', completeness),
                    self._make_check_result('chronological', chronological),
                ],
            }
        except Exception as e:
            return {
                'domain': 'audit',
                'all_pass': False,
                'checks': [],
                'error': str(e),
            }

    def validate_all(self, state: Dict) -> Dict:
        violations = []
        checks = []

        try:
            if 'journal_entries' in state:
                r = self.validate_accounting(state.get('journal_entries', []))
                checks.append(r)
                if not r['all_pass']:
                    violations.append(f"Accounting violation: {r['domain']}")
        except Exception as e:
            checks.append({'domain': 'accounting', 'all_pass': False, 'error': str(e)})
            violations.append(f"Accounting error: {e}")

        try:
            if 'batches' in state or 'movements' in state:
                r = self.validate_inventory(
                    state.get('batches', []),
                    state.get('movements', []),
                )
                checks.append(r)
                if not r['all_pass']:
                    violations.append(f"Inventory violation: {r['domain']}")
        except Exception as e:
            checks.append({'domain': 'inventory', 'all_pass': False, 'error': str(e)})
            violations.append(f"Inventory error: {e}")

        try:
            if 'transactions' in state:
                r = self.validate_transactions(state.get('transactions', []))
                checks.append(r)
                if not r['all_pass']:
                    violations.append(f"Transaction violation: {r['domain']}")
        except Exception as e:
            checks.append({'domain': 'transactions', 'all_pass': False, 'error': str(e)})
            violations.append(f"Transaction error: {e}")

        try:
            if 'original_events' in state or 'replay_events' in state:
                r = self.validate_replay(
                    state.get('original_events', []),
                    state.get('replay_events', []),
                    state.get('original_hashes'),
                    state.get('replay_hashes'),
                )
                checks.append(r)
                if not r['all_pass']:
                    violations.append(f"Replay violation: {r['domain']}")
        except Exception as e:
            checks.append({'domain': 'replay', 'all_pass': False, 'error': str(e)})
            violations.append(f"Replay error: {e}")

        try:
            if 'audit_events' in state:
                r = self.validate_audit(state.get('audit_events', []))
                checks.append(r)
                if not r['all_pass']:
                    violations.append(f"Audit violation: {r['domain']}")
        except Exception as e:
            checks.append({'domain': 'audit', 'all_pass': False, 'error': str(e)})
            violations.append(f"Audit error: {e}")

        all_pass = len(violations) == 0

        result = {
            'all_pass': all_pass,
            'checks': checks,
            'violations': violations,
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'stop_on_violation': self.stop_on_violation,
        }

        self._reports.append(result)

        return result

    def get_report_count(self) -> int:
        return len(self._reports)

    def clear(self) -> None:
        self._reports.clear()
