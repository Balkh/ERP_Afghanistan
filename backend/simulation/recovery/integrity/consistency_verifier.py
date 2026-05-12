"""Consistency verification — checks consistency across system boundaries."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import IntegritySeverity


class ConsistencyVerifier:
    def __init__(self, max_history: int = 200):
        self._verification_history: deque = deque(maxlen=max_history)

    def verify_journal_balance(self, debits: float, credits: float) -> Dict[str, Any]:
        difference = abs(debits - credits)
        is_balanced = difference < 0.001
        severity = (IntegritySeverity.CRITICAL if difference > 1000
                    else IntegritySeverity.HIGH if difference > 100
                    else IntegritySeverity.MEDIUM if difference > 1
                    else IntegritySeverity.INFO)
        result = {
            'check': 'journal_balance', 'passed': is_balanced,
            'debits': debits, 'credits': credits, 'difference': difference,
            'severity': severity.value,
        }
        self._verification_history.append(result)
        return result

    def verify_inventory_consistency(self, stock_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        inconsistencies = 0
        for rec in stock_records:
            expected = rec.get('expected_qty', 0)
            actual = rec.get('actual_qty', 0)
            if abs(expected - actual) > 0.001:
                inconsistencies += 1
        passed = inconsistencies == 0
        severity = (IntegritySeverity.CRITICAL if inconsistencies > 5
                    else IntegritySeverity.HIGH if inconsistencies > 2
                    else IntegritySeverity.MEDIUM if inconsistencies > 0
                    else IntegritySeverity.INFO)
        result = {
            'check': 'inventory_consistency', 'passed': passed,
            'records_checked': len(stock_records),
            'inconsistencies': inconsistencies,
            'severity': severity.value,
        }
        self._verification_history.append(result)
        return result

    def verify_reconciliation(self, system_balance: float, expected_balance: float,
                              tolerance: float = 0.0) -> Dict[str, Any]:
        gap = abs(system_balance - expected_balance)
        passed = gap <= tolerance
        severity = (IntegritySeverity.CRITICAL if gap > tolerance * 5
                    else IntegritySeverity.HIGH if gap > tolerance * 2
                    else IntegritySeverity.MEDIUM if gap > tolerance
                    else IntegritySeverity.INFO)
        result = {
            'check': 'reconciliation', 'passed': passed,
            'gap': gap, 'tolerance': tolerance,
            'severity': severity.value,
        }
        self._verification_history.append(result)
        return result

    def verify_all(self, journal_balance: Dict[str, Any],
                   inventory_results: Optional[List[Dict[str, Any]]] = None,
                   reconciliation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        inventory_results = inventory_results or []
        checks = [journal_balance]
        if inventory_results:
            checks.append(self.verify_inventory_consistency(inventory_results))
        if reconciliation:
            checks.append(self.verify_reconciliation(
                reconciliation.get('system_balance', 0),
                reconciliation.get('expected_balance', 0),
                reconciliation.get('tolerance', 0),
            ))
        failed = [c for c in checks if not c.get('passed', True)]
        return {
            'all_passed': len(failed) == 0,
            'checks_performed': len(checks),
            'checks_failed': len(failed),
            'failed_checks': [c['check'] for c in failed],
            'details': checks,
        }

    def clear(self):
        self._verification_history.clear()
