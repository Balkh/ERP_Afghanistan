from typing import List, Dict


class TransactionValidator:
    def __init__(self):
        pass

    def check_atomicity(self, transactions: List[Dict]) -> Dict:
        try:
            partial_txns = []
            for txn in transactions:
                status = txn.get('status', '')
                steps = txn.get('steps', [])
                completed_steps = sum(1 for s in steps if s.get('completed', False))
                if status == 'committed' and completed_steps < len(steps):
                    partial_txns.append(txn.get('txn_id', 'unknown'))
            passed = len(partial_txns) == 0
            return {
                'passed': passed,
                'partial_txns': partial_txns,
                'count': len(partial_txns),
            }
        except Exception as e:
            return {
                'passed': False,
                'partial_txns': [],
                'count': 0,
                'details': f'Error checking atomicity: {e}',
            }

    def check_no_partial(self, transactions: List[Dict]) -> Dict:
        try:
            partial_txns = []
            for txn in transactions:
                status = txn.get('status', '')
                entries = txn.get('entries', [])
                posted = sum(1 for e in entries if e.get('posted', False))
                if status == 'committed' and 0 < posted < len(entries):
                    partial_txns.append(txn.get('txn_id', 'unknown'))
                elif status == 'failed' and posted > 0:
                    partial_txns.append(txn.get('txn_id', 'unknown'))
            passed = len(partial_txns) == 0
            return {
                'passed': passed,
                'partial_txns': partial_txns,
            }
        except Exception as e:
            return {
                'passed': False,
                'partial_txns': [],
                'details': f'Error checking partial state: {e}',
            }

    def check_rollback(self, transactions: List[Dict]) -> Dict:
        try:
            incomplete_rollbacks = []
            for txn in transactions:
                status = txn.get('status', '')
                if status == 'rolled_back':
                    compensating_entries = txn.get('compensating_entries', [])
                    original_entries = txn.get('entries', [])
                    if not compensating_entries and original_entries:
                        incomplete_rollbacks.append(txn.get('txn_id', 'unknown'))
            passed = len(incomplete_rollbacks) == 0
            return {
                'passed': passed,
                'incomplete_rollbacks': incomplete_rollbacks,
            }
        except Exception as e:
            return {
                'passed': False,
                'incomplete_rollbacks': [],
                'details': f'Error checking rollback: {e}',
            }
