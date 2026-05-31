"""
Class 6: ReportTruthValidator — Report Consistency Guarantee.

GUARANTEE: ALL reports MUST derive from ledger as single source of truth.
Reports MUST be derived ONLY from ledger, never from cached aggregates
unless validated.

Detects:
  - Report total != Ledger-derived total
  - Cached aggregate divergence from ledger
  - Report generated from stale data
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class ReportValidationResult:
    report_name: str
    valid: bool
    report_total: Decimal
    ledger_total: Decimal
    drift: Decimal
    differences: List[str] = field(default_factory=list)


class ReportTruthValidator:
    """
    Validates that financial reports match the ledger (single source of truth).

    Mode:
      - LOG:   Log warnings
      - BLOCK: Raise AssertionError
    """

    MODE_LOG = 'LOG'
    MODE_BLOCK = 'BLOCK'

    def __init__(self, mode: str = 'BLOCK'):
        self.mode = mode
        self._violations: List[str] = []

    def validate_trial_balance(self, report_data: Dict[str, Any]) -> ReportValidationResult:
        """
        Validate a trial balance report against the actual ledger.
        report_data should have a 'totals' key with total_debits, total_credits.
        """
        from accounting.models import JournalEntryLine, Account
        from django.db.models import Sum

        total_debits = JournalEntryLine.objects.filter(
            entry__is_posted=True,
        ).aggregate(s=Sum('debit'))['s'] or Decimal('0')

        total_credits = JournalEntryLine.objects.filter(
            entry__is_posted=True,
        ).aggregate(s=Sum('credit'))['s'] or Decimal('0')

        report_debits = Decimal(str(report_data.get('total_debits', 0)))
        report_credits = Decimal(str(report_data.get('total_credits', 0)))

        diffs = []
        drift_debits = abs(report_debits - total_debits)
        drift_credits = abs(report_credits - total_credits)

        if drift_debits > Decimal('0.02'):
            diffs.append(
                f"Total debits: report={report_debits} ledger={total_debits} drift={drift_debits}"
            )
        if drift_credits > Decimal('0.02'):
            diffs.append(
                f"Total credits: report={report_credits} ledger={total_credits} drift={drift_credits}"
            )

        valid = len(diffs) == 0
        if not valid:
            msg = f"TRIAL BALANCE TRUTH VIOLATION: {'; '.join(diffs)}"
            self._violations.append(msg)
            if self.mode == self.MODE_BLOCK:
                raise AssertionError(msg)

        return ReportValidationResult(
            report_name='TrialBalance',
            valid=valid,
            report_total=report_debits,
            ledger_total=total_debits,
            drift=drift_debits,
            differences=diffs,
        )

    def validate_profit_loss(self, report_data: Dict[str, Any]) -> ReportValidationResult:
        """
        Validate P&L report against ledger.
        report_data should have 'total_revenue', 'total_expenses', 'net_income'.
        """
        from accounting.models import Account, JournalEntryLine
        from django.db.models import Sum

        # Calculate ledger totals from accounts mapped to P&L categories
        revenue_accounts = Account.objects.filter(
            code__startswith='4',
            is_active=True,
        )
        expense_accounts = Account.objects.filter(
            code__startswith='5',
            is_active=True,
        )

        ledger_revenue = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            account__in=revenue_accounts,
        ).aggregate(s=Sum('credit'))['s'] or Decimal('0')

        ledger_expenses = JournalEntryLine.objects.filter(
            entry__is_posted=True,
            account__in=expense_accounts,
        ).aggregate(s=Sum('debit'))['s'] or Decimal('0')

        rep_revenue = Decimal(str(report_data.get('total_revenue', 0)))
        rep_expenses = Decimal(str(report_data.get('total_expenses', 0)))

        diffs = []
        if abs(rep_revenue - ledger_revenue) > Decimal('0.02'):
            diffs.append(
                f"Revenue: report={rep_revenue} ledger={ledger_revenue}"
            )
        if abs(rep_expenses - ledger_expenses) > Decimal('0.02'):
            diffs.append(
                f"Expenses: report={rep_expenses} ledger={ledger_expenses}"
            )

        valid = len(diffs) == 0
        if not valid:
            msg = f"P&L TRUTH VIOLATION: {'; '.join(diffs)}"
            self._violations.append(msg)
            if self.mode == self.MODE_BLOCK:
                raise AssertionError(msg)

        return ReportValidationResult(
            report_name='ProfitLoss',
            valid=valid,
            report_total=rep_revenue - rep_expenses,
            ledger_total=ledger_revenue - ledger_expenses,
            drift=abs((rep_revenue - rep_expenses) - (ledger_revenue - ledger_expenses)),
            differences=diffs,
        )

    def validate_balance_sheet(self, report_data: Dict[str, Any]) -> ReportValidationResult:
        """
        Validate Balance Sheet report against ledger.
        report_data should have 'total_assets', 'total_liabilities', 'total_equity'.
        """
        from accounting.models import Account, JournalEntryLine
        from django.db.models import Sum

        asset_accounts = Account.objects.filter(
            code__startswith='1',
            is_active=True,
        )
        liability_accounts = Account.objects.filter(
            code__startswith='2',
            is_active=True,
        )
        equity_accounts = Account.objects.filter(
            code__startswith='3',
            is_active=True,
        )

        def _account_balance(accounts) -> Decimal:
            debits = JournalEntryLine.objects.filter(
                entry__is_posted=True,
                account__in=accounts,
            ).aggregate(s=Sum('debit'))['s'] or Decimal('0')
            credits = JournalEntryLine.objects.filter(
                entry__is_posted=True,
                account__in=accounts,
            ).aggregate(s=Sum('credit'))['s'] or Decimal('0')
            return debits - credits

        ledger_assets = _account_balance(asset_accounts)
        ledger_liabilities = _account_balance(liability_accounts)
        ledger_equity = _account_balance(equity_accounts)

        rep_assets = Decimal(str(report_data.get('total_assets', 0)))
        rep_liabilities = Decimal(str(report_data.get('total_liabilities', 0)))
        rep_equity = Decimal(str(report_data.get('total_equity', 0)))

        diffs = []
        if abs(rep_assets - ledger_assets) > Decimal('0.02'):
            diffs.append(f"Assets: report={rep_assets} ledger={ledger_assets}")
        if abs(rep_liabilities - ledger_liabilities) > Decimal('0.02'):
            diffs.append(f"Liabilities: report={rep_liabilities} ledger={ledger_liabilities}")
        if abs(rep_equity - ledger_equity) > Decimal('0.02'):
            diffs.append(f"Equity: report={rep_equity} ledger={ledger_equity}")

        valid = len(diffs) == 0
        if not valid:
            msg = f"BALANCE SHEET TRUTH VIOLATION: {'; '.join(diffs)}"
            self._violations.append(msg)
            if self.mode == self.MODE_BLOCK:
                raise AssertionError(msg)

        return ReportValidationResult(
            report_name='BalanceSheet',
            valid=valid,
            report_total=rep_assets,
            ledger_total=ledger_assets,
            drift=abs(rep_assets - ledger_assets),
            differences=diffs,
        )

    def validate_report_json(self, report_name: str, report_data: Dict[str, Any]) -> ReportValidationResult:
        """Dispatch validation to the appropriate method based on report name."""
        name_lower = report_name.lower().replace(' ', '_')
        if 'trial' in name_lower or 'balance' in name_lower and 'sheet' not in name_lower:
            return self.validate_trial_balance(report_data)
        elif 'profit' in name_lower or 'loss' in name_lower or 'income' in name_lower:
            return self.validate_profit_loss(report_data)
        elif 'balance' in name_lower and 'sheet' in name_lower:
            return self.validate_balance_sheet(report_data)
        else:
            return ReportValidationResult(
                report_name=report_name,
                valid=True,
                report_total=Decimal('0'),
                ledger_total=Decimal('0'),
                drift=Decimal('0'),
            )

    @property
    def has_violations(self) -> bool:
        return len(self._violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    def clear(self) -> None:
        self._violations.clear()


_validator_instance: Optional[ReportTruthValidator] = None


def get_report_validator(mode: str = 'BLOCK') -> ReportTruthValidator:
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ReportTruthValidator(mode=mode)
    return _validator_instance
