from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db.models import Sum, Q
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from budgeting.models import Budget, BudgetLine


class BudgetCalculator:
    """
    Service for calculating budget amounts and variances.
    Uses existing journal entries for actual amounts.
    """

    @staticmethod
    def calculate_actual_for_account(
        account: Account,
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Calculate actual amount spent/received for an account.

        Args:
            account: Account to calculate for
            start_date: Start of period
            end_date: End of period

        Returns:
            Actual amount from journal entries
        """
        lines = JournalEntryLine.objects.filter(
            account=account,
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date
        )

        if account.account_type in ['ASSET', 'EXPENSE']:
            debit_total = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
            credit_total = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
            return debit_total - credit_total
        else:
            credit_total = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
            debit_total = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
            return credit_total - debit_total

    @staticmethod
    def update_budget_line_actuals(budget_line: BudgetLine) -> BudgetLine:
        """
        Update actual amount for a budget line based on journal entries.

        Args:
            budget_line: BudgetLine to update

        Returns:
            Updated BudgetLine
        """
        start_date, end_date = BudgetCalculator.parse_period(budget_line.period)
        if not start_date or not end_date:
            return budget_line

        actual = BudgetCalculator.calculate_actual_for_account(
            budget_line.account,
            start_date,
            end_date
        )

        budget_line.actual_amount = actual
        budget_line.save()
        return budget_line

    @staticmethod
    def update_budget_totals(budget: Budget) -> Budget:
        """
        Recalculate budget totals from all lines.

        Args:
            budget: Budget to update

        Returns:
            Updated Budget
        """
        lines = budget.lines.all()

        total_budgeted = lines.aggregate(
            total=Sum('budgeted_amount')
        )['total'] or Decimal('0.00')

        total_actual = lines.aggregate(
            total=Sum('actual_amount')
        )['total'] or Decimal('0.00')

        budget.total_budgeted = total_budgeted
        budget.total_actual = total_actual
        budget.save()
        return budget

    @staticmethod
    def parse_period(period_code: str) -> tuple[Optional[date], Optional[date]]:
        """
        Parse period code into start and end dates.

        Args:
            period_code: Period code (e.g., 2025-01, 2025-Q1, 2025)

        Returns:
            Tuple of (start_date, end_date)
        """
        try:
            if '-Q' in period_code:
                year, quarter_part = period_code.split('-Q')
                quarter = int(quarter_part)
                start_month = (quarter - 1) * 3 + 1
                start = date(int(year), start_month, 1)
                if quarter == 4:
                    end = date(int(year), 12, 31)
                else:
                    from datetime import timedelta
                    end = date(int(year), start_month + 3, 1) - timedelta(days=1)
                return start, end

            elif '-' in period_code and len(period_code) == 7:
                year, month = period_code.split('-')
                start = date(int(year), int(month), 1)
                if int(month) == 12:
                    end = date(int(year), 12, 31)
                else:
                    from datetime import timedelta
                    end = date(int(year), int(month) + 1, 1) - timedelta(days=1)
                return start, end

            elif period_code.isdigit():
                year = int(period_code)
                return date(year, 1, 1), date(year, 12, 31)

        except (ValueError, IndexError):
            pass

        return None, None

    @staticmethod
    def validate_budget_line(
        budgeted_amount: Decimal,
        account: Account
    ) -> List[str]:
        """
        Validate budget line data.

        Returns:
            List of validation errors
        """
        errors = []

        if budgeted_amount < 0:
            errors.append('Budgeted amount cannot be negative.')

        if not account.is_active:
            errors.append('Cannot budget for inactive account.')

        return errors

    @staticmethod
    def get_periods_for_year(fiscal_year: int, period_type: str) -> List[str]:
        """
        Get list of period codes for a fiscal year.

        Args:
            fiscal_year: Year (e.g., 2025)
            period_type: MONTHLY, QUARTERLY, or ANNUAL

        Returns:
            List of period codes
        """
        if period_type == 'MONTHLY':
            return [f"{fiscal_year}-{str(m).zfill(2)}" for m in range(1, 13)]
        elif period_type == 'QUARTERLY':
            return [f"{fiscal_year}-Q{q}" for q in range(1, 5)]
        else:
            return [str(fiscal_year)]