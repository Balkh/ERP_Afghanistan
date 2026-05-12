from typing import List, Dict


class AccountingValidator:
    def __init__(self):
        pass

    def check_balance(self, journal_entries: List[Dict]) -> Dict:
        try:
            if not journal_entries:
                return {
                    'passed': True,
                    'total_debits': 0.0,
                    'total_credits': 0.0,
                    'difference': 0.0,
                    'details': 'Empty entry list — trivially balanced.',
                }
            total_debits = sum(e.get('debit', 0.0) for e in journal_entries)
            total_credits = sum(e.get('credit', 0.0) for e in journal_entries)
            difference = round(total_debits - total_credits, 10)
            passed = abs(difference) < 1e-9
            return {
                'passed': passed,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'difference': difference,
                'details': 'Balanced' if passed else f'Imbalance: {difference}',
            }
        except Exception as e:
            return {
                'passed': False,
                'total_debits': 0.0,
                'total_credits': 0.0,
                'difference': 0.0,
                'details': f'Error checking balance: {e}',
            }

    def check_no_duplicates(self, entries: List[Dict]) -> Dict:
        try:
            seen = set()
            duplicate_ids = []
            for entry in entries:
                eid = entry.get('entry_id')
                if eid is None:
                    continue
                if eid in seen:
                    duplicate_ids.append(eid)
                else:
                    seen.add(eid)
            passed = len(duplicate_ids) == 0
            return {
                'passed': passed,
                'duplicate_ids': duplicate_ids,
                'count': len(duplicate_ids),
            }
        except Exception as e:
            return {
                'passed': False,
                'duplicate_ids': [],
                'count': 0,
                'details': f'Error checking duplicates: {e}',
            }

    def check_chronological(self, entries: List[Dict]) -> Dict:
        try:
            out_of_order = 0
            for i in range(1, len(entries)):
                if entries[i].get('tick', 0) < entries[i - 1].get('tick', 0):
                    out_of_order += 1
            passed = out_of_order == 0
            return {
                'passed': passed,
                'out_of_order': out_of_order,
            }
        except Exception as e:
            return {
                'passed': False,
                'out_of_order': 0,
                'details': f'Error checking chronological order: {e}',
            }
