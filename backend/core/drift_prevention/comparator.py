from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from accounting.models import JournalEntry, JournalEntryLine


class DriftComparator:
    """Deep structural comparison between JournalEngine and JournalGateway outputs.

    Compares actual JournalEntry objects created by both paths at the line level.
    """

    @staticmethod
    def compare_results(
        engine_result: Dict[str, Any],
        gateway_result: Optional[Dict[str, Any]],
        module: str,
        operation: str,
    ) -> Dict[str, Any]:
        """Compare JournalEngine and JournalGateway execution results.

        Returns:
            Dict with keys:
            - has_differences: bool
            - engine_entries: list of entry dicts
            - gateway_entries: list of entry dicts (empty if gateway failed)
            - differences: list of diff dicts
            - total_differences: int
        """
        differences = []
        engine_entries = []
        gateway_entries = []

        engine_success = engine_result.get('success', False) if engine_result else False
        gateway_success = gateway_result.get('success', False) if gateway_result else False

        if engine_success:
            engine_id = engine_result.get('entry_id')
            engine_entries = DriftComparator._fetch_entry_details(engine_id)

        if gateway_success:
            gateway_id = gateway_result.get('entry_id')
            gateway_entries = DriftComparator._fetch_entry_details(gateway_id)

        if not engine_success and not gateway_success:
            return {
                'has_differences': False,
                'engine_entries': [],
                'gateway_entries': [],
                'differences': [],
                'total_differences': 0,
            }

        if engine_success and not gateway_success:
            gateway_error = gateway_result.get('error', 'Unknown') if gateway_result else 'No gateway result'
            differences.append({
                'type': 'gateway_failure',
                'severity': 'CRITICAL',
                'field': 'gateway_result',
                'engine': 'success',
                'gateway': f'failed: {gateway_error}',
            })
            return {
                'has_differences': True,
                'engine_entries': engine_entries,
                'gateway_entries': [],
                'differences': differences,
                'total_differences': 1,
            }

        if not engine_success and gateway_success:
            differences.append({
                'type': 'engine_failure',
                'severity': 'CRITICAL',
                'field': 'engine_result',
                'engine': 'failed',
                'gateway': 'success',
            })
            return {
                'has_differences': True,
                'engine_entries': [],
                'gateway_entries': gateway_entries,
                'differences': differences,
                'total_differences': 1,
            }

        diffs = DriftComparator._compare_entries(engine_entries, gateway_entries)
        differences.extend(diffs)

        return {
            'has_differences': len(differences) > 0,
            'engine_entries': engine_entries,
            'gateway_entries': gateway_entries,
            'differences': differences,
            'total_differences': len(differences),
        }

    @staticmethod
    def _fetch_entry_details(entry_id: str) -> List[Dict[str, Any]]:
        """Fetch journal entry details with all lines."""
        try:
            entry = JournalEntry.objects.get(id=entry_id)
            lines = JournalEntryLine.objects.filter(entry=entry).order_by('id')
            return [{
                'entry_id': str(entry.id),
                'entry_number': entry.entry_number,
                'entry_type': entry.entry_type,
                'entry_date': str(entry.entry_date),
                'description': entry.description,
                'reference': entry.reference or '',
                'is_posted': entry.is_posted,
                'total_debit': float(sum(l.debit for l in lines)),
                'total_credit': float(sum(l.credit for l in lines)),
                'line_count': lines.count(),
                'lines': [
                    {
                        'account_id': str(l.account_id),
                        'account_code': l.account.code,
                        'account_name': l.account.name,
                        'debit': float(l.debit),
                        'credit': float(l.credit),
                        'description': l.description or '',
                    }
                    for l in lines
                ],
            }]
        except JournalEntry.DoesNotExist:
            return []
        except Exception:
            return []

    @staticmethod
    def _compare_entries(
        engine_entries: List[Dict[str, Any]],
        gateway_entries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        differences = []

        if not engine_entries and not gateway_entries:
            return differences

        if not engine_entries:
            differences.append({
                'type': 'missing_engine_entry',
                'severity': 'CRITICAL',
                'field': 'entry',
                'engine': 'none',
                'gateway': 'present',
            })
            return differences

        if not gateway_entries:
            differences.append({
                'type': 'missing_gateway_entry',
                'severity': 'CRITICAL',
                'field': 'entry',
                'engine': 'present',
                'gateway': 'none',
            })
            return differences

        for i, engine_entry in enumerate(engine_entries):
            if i >= len(gateway_entries):
                differences.append({
                    'type': 'extra_engine_entry',
                    'severity': 'CRITICAL',
                    'field': f'entry[{i}]',
                    'engine': 'present',
                    'gateway': 'none',
                })
                continue

            gateway_entry = gateway_entries[i]
            diffs = DriftComparator._compare_single_entry(engine_entry, gateway_entry, i)
            differences.extend(diffs)

        if len(gateway_entries) > len(engine_entries):
            for i in range(len(engine_entries), len(gateway_entries)):
                differences.append({
                    'type': 'extra_gateway_entry',
                    'severity': 'CRITICAL',
                    'field': f'entry[{i}]',
                    'engine': 'none',
                    'gateway': 'present',
                })

        return differences

    @staticmethod
    def _compare_single_entry(
        engine_entry: Dict[str, Any],
        gateway_entry: Dict[str, Any],
        index: int,
    ) -> List[Dict[str, Any]]:
        differences = []

        prefix = f'entry[{index}]'

        comparisons = [
            ('entry_type', 'Minor'),
            ('entry_date', 'Minor'),
            ('description', 'Minor'),
            ('reference', 'Minor'),
            ('is_posted', 'Minor'),
        ]

        for field, default_severity in comparisons:
            engine_val = engine_entry.get(field)
            gateway_val = gateway_entry.get(field)
            if str(engine_val) != str(gateway_val):
                severity = 'HIGH' if field in ('entry_type', 'entry_date') else default_severity
                differences.append({
                    'type': f'{field}_mismatch',
                    'severity': severity,
                    'field': f'{prefix}.{field}',
                    'engine': str(engine_val),
                    'gateway': str(gateway_val),
                })

        if abs(engine_entry.get('total_debit', 0) - gateway_entry.get('total_debit', 0)) > 0.001:
            differences.append({
                'type': 'total_debit_mismatch',
                'severity': 'CRITICAL',
                'field': f'{prefix}.total_debit',
                'engine': engine_entry.get('total_debit'),
                'gateway': gateway_entry.get('total_debit'),
            })

        if abs(engine_entry.get('total_credit', 0) - gateway_entry.get('total_credit', 0)) > 0.001:
            differences.append({
                'type': 'total_credit_mismatch',
                'severity': 'CRITICAL',
                'field': f'{prefix}.total_credit',
                'engine': engine_entry.get('total_credit'),
                'gateway': gateway_entry.get('total_credit'),
            })

        engine_lines = engine_entry.get('lines', [])
        gateway_lines = gateway_entry.get('lines', [])

        if len(engine_lines) != len(gateway_lines):
            differences.append({
                'type': 'line_count_mismatch',
                'severity': 'HIGH',
                'field': f'{prefix}.line_count',
                'engine': len(engine_lines),
                'gateway': len(gateway_lines),
            })

        for li in range(max(len(engine_lines), len(gateway_lines))):
            if li >= len(engine_lines):
                differences.append({
                    'type': 'extra_gateway_line',
                    'severity': 'CRITICAL',
                    'field': f'{prefix}.lines[{li}]',
                    'engine': 'none',
                    'gateway': 'present',
                })
                continue
            if li >= len(gateway_lines):
                differences.append({
                    'type': 'extra_engine_line',
                    'severity': 'CRITICAL',
                    'field': f'{prefix}.lines[{li}]',
                    'engine': 'present',
                    'gateway': 'none',
                })
                continue

            el = engine_lines[li]
            gl = gateway_lines[li]
            line_diffs = DriftComparator._compare_lines(el, gl, prefix, li)
            differences.extend(line_diffs)

        return differences

    @staticmethod
    def _compare_lines(
        engine_line: Dict[str, Any],
        gateway_line: Dict[str, Any],
        entry_prefix: str,
        line_index: int,
    ) -> List[Dict[str, Any]]:
        differences = []
        prefix = f'{entry_prefix}.lines[{line_index}]'

        if engine_line.get('account_code') != gateway_line.get('account_code'):
            differences.append({
                'type': 'account_mismatch',
                'severity': 'CRITICAL',
                'field': f'{prefix}.account_code',
                'engine': engine_line.get('account_code'),
                'gateway': gateway_line.get('account_code'),
            })

        if abs(engine_line.get('debit', 0) - gateway_line.get('debit', 0)) > 0.001:
            differences.append({
                'type': 'debit_mismatch',
                'severity': 'CRITICAL',
                'field': f'{prefix}.debit',
                'engine': engine_line.get('debit'),
                'gateway': gateway_line.get('debit'),
            })

        if abs(engine_line.get('credit', 0) - gateway_line.get('credit', 0)) > 0.001:
            differences.append({
                'type': 'credit_mismatch',
                'severity': 'CRITICAL',
                'field': f'{prefix}.credit',
                'engine': engine_line.get('credit'),
                'gateway': gateway_line.get('credit'),
            })

        if engine_line.get('description', '') != gateway_line.get('description', ''):
            differences.append({
                'type': 'line_description_mismatch',
                'severity': 'LOW',
                'field': f'{prefix}.description',
                'engine': engine_line.get('description', ''),
                'gateway': gateway_line.get('description', ''),
            })

        return differences
