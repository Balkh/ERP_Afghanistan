"""
Financial Integrity Monitor.
Validates accounting data consistency and detects anomalies.
"""
from decimal import Decimal
from django.db.models import Sum
from accounting.models import Account, JournalEntry, JournalEntryLine


class FinancialIntegrityMonitor:
    """Monitor accounting integrity."""

    @staticmethod
    def check_unbalanced_journals() -> dict:
        """Detect unbalanced journal entries."""
        result = {
            'status': 'ok',
            'issues': [],
            'total_checked': 0,
            'balanced': 0,
            'unbalanced': 0
        }

        try:
            entries = JournalEntry.objects.filter(is_posted=True)
            result['total_checked'] = entries.count()

            for entry in entries:
                lines = JournalEntryLine.objects.filter(entry=entry)
                total_debit = sum(line.debit or Decimal('0.00') for line in lines)
                total_credit = sum(line.credit or Decimal('0.00') for line in lines)

                if total_debit != total_credit:
                    result['unbalanced'] += 1
                    result['issues'].append({
                        'entry_id': str(entry.id),
                        'entry_number': entry.entry_number,
                        'debit_total': str(total_debit),
                        'credit_total': str(total_credit),
                        'difference': str(total_debit - total_credit)
                    })
                else:
                    result['balanced'] += 1

            if result['unbalanced'] > 0:
                result['status'] = 'error'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_orphan_lines() -> dict:
        """Detect journal lines referencing deleted entries."""
        result = {
            'status': 'ok',
            'issues': [],
            'orphan_count': 0
        }

        try:
            # The FK is non-nullable with CASCADE, but this detects
            # lines whose entry_id points to a non-existent JournalEntry
            orphans = JournalEntryLine.objects.filter(
                entry__isnull=False
            ).exclude(
                entry_id__in=JournalEntry.objects.values('id')
            )
            result['orphan_count'] = orphans.count()

            if result['orphan_count'] > 0:
                result['status'] = 'error'
                result['issues'] = [
                    {'line_id': str(line.id)} for line in orphans[:100]
                ]
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_duplicate_postings() -> dict:
        """Detect potential duplicate journal entries."""
        result = {
            'status': 'ok',
            'issues': [],
            'duplicates_found': 0
        }

        try:
            from django.db.models import Count
            duplicates = JournalEntry.objects.values(
                'entry_type', 'description', 'entry_date'
            ).annotate(
                count=Count('id')
            ).filter(count__gt=1)

            result['duplicates_found'] = len(duplicates)
            if result['duplicates_found'] > 0:
                result['status'] = 'warning'
                result['issues'] = list(duplicates[:10])
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_account_balances() -> dict:
        """Validate account balance consistency."""
        result = {
            'status': 'ok',
            'accounts_checked': 0,
            'issues': []
        }

        try:
            from django.db.models import Sum, F
            accounts = Account.objects.filter(is_active=True)
            result['accounts_checked'] = accounts.count()

            for account in accounts:
                balance = account.balance
                if balance < 0 and account.account_type in ['ASSET', 'REVENUE']:
                    result['issues'].append({
                        'account_id': str(account.id),
                        'account_name': account.name,
                        'balance': str(balance),
                        'type': account.account_type
                    })

            if len(result['issues']) > 0:
                result['status'] = 'warning'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_reversal_chains() -> dict:
        """Validate reversal entry chains."""
        result = {
            'status': 'ok',
            'reversals_checked': 0,
            'broken_chains': 0,
            'issues': []
        }

        try:
            reversals = JournalEntry.objects.filter(
                original_entry__isnull=False,
                entry_type='REVERSAL'
            )
            result['reversals_checked'] = reversals.count()

            for entry in reversals:
                try:
                    original = entry.original_entry
                except Exception:
                    result['broken_chains'] += 1
                    result['issues'].append({
                        'reversal_id': str(entry.id),
                        'original_id': None,
                        'reason': 'Original entry not accessible (deleted or broken FK)'
                    })
                    continue
                if not original or original.reversed_by_entry is None:
                    result['broken_chains'] += 1
                    result['issues'].append({
                        'reversal_id': str(entry.id),
                        'original_id': str(original.id) if original else None
                    })

            if result['broken_chains'] > 0:
                result['status'] = 'warning'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def run_full_audit() -> dict:
        """Run complete financial integrity audit."""
        return {
            'unbalanced_journals': FinancialIntegrityMonitor.check_unbalanced_journals(),
            'orphan_lines': FinancialIntegrityMonitor.check_orphan_lines(),
            'duplicate_postings': FinancialIntegrityMonitor.check_duplicate_postings(),
            'account_balances': FinancialIntegrityMonitor.check_account_balances(),
            'reversal_chains': FinancialIntegrityMonitor.check_reversal_chains()
        }