"""Financial risk estimation — estimates financial exposure from detected corruption."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.recovery.models import FinancialRiskEstimate, IntegritySeverity


class FinancialRiskEstimator:
    def __init__(self, max_history: int = 100):
        self._estimates: deque = deque(maxlen=max_history)

    def estimate_exposure(self, journal_balance_diff: float,
                          affected_accounts: Optional[List[str]] = None,
                          pending_transactions: int = 0) -> Dict[str, Any]:
        affected_accounts = affected_accounts or []
        exposure = abs(journal_balance_diff)
        potential_je_corrections = pending_transactions + len(affected_accounts)
        if exposure > 10000 or potential_je_corrections > 20:
            risk = IntegritySeverity.CRITICAL
        elif exposure > 1000 or potential_je_corrections > 10:
            risk = IntegritySeverity.HIGH
        elif exposure > 100 or potential_je_corrections > 5:
            risk = IntegritySeverity.MEDIUM
        elif exposure > 0:
            risk = IntegritySeverity.LOW
        else:
            risk = IntegritySeverity.INFO
        estimate = FinancialRiskEstimate(
            estimated_exposure=exposure, risk_level=risk,
            affected_accounts=affected_accounts,
            potential_je_corrections=potential_je_corrections,
        )
        self._estimates.append({
            'exposure': exposure, 'risk_level': risk.value,
            'je_corrections': potential_je_corrections,
        })
        return {
            'estimated_exposure': exposure, 'risk_level': risk.value,
            'affected_accounts': affected_accounts,
            'potential_je_corrections': potential_je_corrections,
        }

    def clear(self):
        self._estimates.clear()
