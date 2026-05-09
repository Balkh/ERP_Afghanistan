from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List
from django.db.models import Sum, Count
from django.utils import timezone

from accounting.models import JournalEntryLine
from tax.models import TaxReturn, TaxTransaction, TaxRate


class TaxReportingService:
    """
    Service for tax reporting and return preparation.
    """

    @staticmethod
    def calculate_period_summary(
        start_date: date,
        end_date: date
    ) -> dict:
        """
        Calculate tax summary for a period from journal entries.

        Args:
            start_date: Period start
            end_date: Period end

        Returns:
            Dictionary with period summary
        """
        from accounting.models import Account

        output_tax_accounts = Account.objects.filter(
            name__icontains='Output Tax'
        )
        input_tax_accounts = Account.objects.filter(
            name__icontains='Input Tax'
        )

        output_total = Decimal('0.00')
        if output_tax_accounts.exists():
            lines = JournalEntryLine.objects.filter(
                account__in=output_tax_accounts,
                entry__is_posted=True,
                entry__entry_date__gte=start_date,
                entry__entry_date__lte=end_date
            )
            output_total = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

        input_total = Decimal('0.00')
        if input_tax_accounts.exists():
            lines = JournalEntryLine.objects.filter(
                account__in=input_tax_accounts,
                entry__is_posted=True,
                entry__entry_date__gte=start_date,
                entry__entry_date__lte=end_date
            )
            input_total = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

        return {
            'period_start': start_date,
            'period_end': end_date,
            'output_tax_collected': output_total,
            'input_tax_claimed': input_total,
            'net_tax': output_total - input_total,
        }

    @staticmethod
    def prepare_tax_return(
        period_start: date,
        period_end: date,
        transactions: List[TaxTransaction] = None
    ) -> TaxReturn:
        """
        Prepare a tax return for a period.

        Args:
            period_start: Start of period
            period_end: End of period
            transactions: Optional list of tax transactions

        Returns:
            Created TaxReturn instance
        """
        sales_total = Decimal('0.00')
        purchase_total = Decimal('0.00')
        tax_collected = Decimal('0.00')
        tax_claimed = Decimal('0.00')

        if transactions:
            for tx in transactions:
                if tx.transaction_type == 'SALE':
                    sales_total += tx.base_amount
                    tax_collected += tx.tax_amount
                elif tx.transaction_type == 'PURCHASE':
                    purchase_total += tx.base_amount
                    tax_claimed += tx.tax_amount
        else:
            summary = TaxReportingService.calculate_period_summary(
                period_start, period_end
            )
            tax_collected = summary['output_tax_collected']
            tax_claimed = summary['input_tax_claimed']

        tax_return = TaxReturn.objects.create(
            period_start=period_start,
            period_end=period_end,
            status='DRAFT',
            gross_sales=sales_total + purchase_total,
            exempt_sales=Decimal('0.00'),
            taxable_sales=sales_total,
            output_tax=tax_collected,
            input_tax=tax_claimed,
        )
        tax_return.calculate_net_tax()
        tax_return.save()

        return tax_return

    @staticmethod
    def get_outstanding_returns() -> List[TaxReturn]:
        """
        Get tax returns that need to be filed.

        Returns:
            List of pending TaxReturn instances
        """
        return TaxReturn.objects.filter(
            status__in=['DRAFT', 'FILED']
        ).order_by('period_end')

    @staticmethod
    def get_tax_liability_report(
        start_date: date,
        end_date: date
    ) -> dict:
        """
        Generate tax liability report for a period.

        Args:
            start_date: Report start
            end_date: Report end

        Returns:
            Dictionary with liability details
        """
        returns = TaxReturn.objects.filter(
            period_start__gte=start_date,
            period_end__lte=end_date
        ).exclude(status='DRAFT')

        total_output = returns.aggregate(total=Sum('output_tax'))['total'] or Decimal('0.00')
        total_input = returns.aggregate(total=Sum('input_tax'))['total'] or Decimal('0.00')
        total_net = returns.aggregate(total=Sum('net_tax'))['total'] or Decimal('0.00')

        paid_returns = returns.filter(status='PAID').count()
        filed_returns = returns.filter(status='FILED').count()
        pending_returns = returns.filter(status__in=['DRAFT', 'ADJUSTED']).count()

        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_output_tax': total_output,
            'total_input_tax': total_input,
            'total_net_liability': total_net,
            'returns_count': returns.count(),
            'paid_returns': paid_returns,
            'filed_returns': filed_returns,
            'pending_returns': pending_returns,
            'returns': [
                {
                    'id': str(r.id),
                    'period': r.period_display,
                    'net_tax': r.net_tax,
                    'status': r.status
                }
                for r in returns
            ]
        }

    @staticmethod
    def validate_return(tax_return: TaxReturn) -> List[str]:
        """
        Validate a tax return for completeness.

        Args:
            tax_return: TaxReturn to validate

        Returns:
            List of validation issues
        """
        issues = []

        if tax_return.output_tax < 0:
            issues.append('Output tax cannot be negative.')

        if tax_return.input_tax < 0:
            issues.append('Input tax cannot be negative.')

        if tax_return.net_tax < 0:
            issues.append('Net tax calculation shows negative value.')

        expected_net = tax_return.output_tax - tax_return.input_tax
        if tax_return.net_tax != expected_net:
            issues.append('Net tax does not match output - input.')

        return issues