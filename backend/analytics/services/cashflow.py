"""
Cash Flow Engine for Pharmacy ERP.
Read-only analytical layer for cash flow statements.
Maps journal entries to cash flow categories.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, List
from django.db.models import Sum, Q, F
from django.db.models.functions import TruncMonth, TruncQuarter, TruncDay

from accounting.models import Account, JournalEntry, JournalEntryLine
from payments.models import FinancialTransaction


class CashFlowCategory:
    """
    Cash flow classification rules.
    Maps account codes to cash flow categories.
    """
    OPERATING = {
        'description': 'Operating Activities',
        'account_prefixes': ['1000', '1001', '1100', '1200', '2000', '2100', '5000', '6000'],
    }
    INVESTING = {
        'description': 'Investing Activities',
        'account_prefixes': ['1500', '1600', '1700'],
    }
    FINANCING = {
        'description': 'Financing Activities',
        'account_prefixes': ['3000', '3100', '4000'],
    }

    @staticmethod
    def classify_account(account_code: str) -> str:
        """Classify an account into a cash flow category."""
        for prefix in CashFlowCategory.OPERATING['account_prefixes']:
            if account_code.startswith(prefix):
                return 'OPERATING'
        for prefix in CashFlowCategory.INVESTING['account_prefixes']:
            if account_code.startswith(prefix):
                return 'INVESTING'
        for prefix in CashFlowCategory.FINANCING['account_prefixes']:
            if account_code.startswith(prefix):
                return 'FINANCING'
        return 'OPERATING'  # Default


class CashFlowStatementGenerator:
    """
    Generates cash flow statements from existing journal entries.
    Read-only - does not modify any transactional data.
    """

    @staticmethod
    def generate_statement(
        start_date: date,
        end_date: date,
        comparison_period: bool = False
    ) -> Dict:
        """
        Generate full cash flow statement.

        Args:
            start_date: Period start date
            end_date: Period end date
            comparison_period: Include prior period comparison

        Returns:
            Complete cash flow statement with operating, investing, financing sections
        """
        operating = CashFlowStatementGenerator._get_cash_flow_section(
            'OPERATING', start_date, end_date
        )
        investing = CashFlowStatementGenerator._get_cash_flow_section(
            'INVESTING', start_date, end_date
        )
        financing = CashFlowStatementGenerator._get_cash_flow_section(
            'FINANCING', start_date, end_date
        )

        net_cash_flow = operating['net_cash'] + investing['net_cash'] + financing['net_cash']

        result = {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
            },
            'operating_activities': operating,
            'investing_activities': investing,
            'financing_activities': financing,
            'net_cash_flow': net_cash_flow.quantize(Decimal('0.01')),
        }

        if comparison_period:
            days = (end_date - start_date).days
            prior_start = start_date - timedelta(days=days)
            prior_end = start_date - timedelta(days=1)

            prior_operating = CashFlowStatementGenerator._get_cash_flow_section(
                'OPERATING', prior_start, prior_end
            )
            prior_investing = CashFlowStatementGenerator._get_cash_flow_section(
                'INVESTING', prior_start, prior_end
            )
            prior_financing = CashFlowStatementGenerator._get_cash_flow_section(
                'FINANCING', prior_start, prior_end
            )

            result['prior_period'] = {
                'operating_activities': prior_operating,
                'investing_activities': prior_investing,
                'financing_activities': prior_financing,
                'net_cash_flow': (
                    prior_operating['net_cash'] +
                    prior_investing['net_cash'] +
                    prior_financing['net_cash']
                ).quantize(Decimal('0.01')),
            }

        return result

    @staticmethod
    def _get_cash_flow_section(
        category: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get cash flow for a specific category."""
        category_config = getattr(CashFlowCategory, category, CashFlowCategory.OPERATING)

        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
        )

        account_codes = []
        for prefix in category_config['account_prefixes']:
            account_codes.extend(
                Account.objects.filter(code__startswith=prefix, is_active=True)
                .values_list('id', flat=True)
            )

        base_filter &= Q(account_id__in=account_codes)

        inflows = JournalEntryLine.objects.filter(
            base_filter, credit__gt=0
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0')

        outflows = JournalEntryLine.objects.filter(
            base_filter, debit__gt=0
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

        net_cash = inflows - outflows

        # Get breakdown by account
        breakdown = JournalEntryLine.objects.filter(
            base_filter
        ).values(
            'account__code', 'account__name'
        ).annotate(
            total_inflow=Sum('credit'),
            total_outflow=Sum('debit')
        ).order_by('account__code')

        return {
            'category': category,
            'description': category_config['description'],
            'total_inflows': inflows.quantize(Decimal('0.01')),
            'total_outflows': outflows.quantize(Decimal('0.01')),
            'net_cash': net_cash.quantize(Decimal('0.01')),
            'breakdown': [
                {
                    'account_code': item['account__code'],
                    'account_name': item['account__name'],
                    'inflow': (item['total_inflow'] or Decimal('0')).quantize(Decimal('0.01')),
                    'outflow': (item['total_outflow'] or Decimal('0')).quantize(Decimal('0.01')),
                }
                for item in breakdown
            ]
        }

    @staticmethod
    def get_daily_cash_flow(
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get daily cash flow aggregation."""
        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
        )

        daily = JournalEntryLine.objects.filter(base_filter).annotate(
            day=TruncDay('entry__entry_date')
        ).values('day').annotate(
            inflow=Sum('credit'),
            outflow=Sum('debit')
        ).order_by('day')

        return [
            {
                'date': item['day'],
                'inflow': (item['inflow'] or Decimal('0')).quantize(Decimal('0.01')),
                'outflow': (item['outflow'] or Decimal('0')).quantize(Decimal('0.01')),
                'net': ((item['inflow'] or Decimal('0')) - (item['outflow'] or Decimal('0'))).quantize(Decimal('0.01')),
            }
            for item in daily
        ]

    @staticmethod
    def get_monthly_cash_flow(
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get monthly cash flow aggregation."""
        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
        )

        monthly = JournalEntryLine.objects.filter(base_filter).annotate(
            month=TruncMonth('entry__entry_date')
        ).values('month').annotate(
            inflow=Sum('credit'),
            outflow=Sum('debit')
        ).order_by('month')

        return [
            {
                'month': item['month'],
                'inflow': (item['inflow'] or Decimal('0')).quantize(Decimal('0.01')),
                'outflow': (item['outflow'] or Decimal('0')).quantize(Decimal('0.01')),
                'net': ((item['inflow'] or Decimal('0')) - (item['outflow'] or Decimal('0'))).quantize(Decimal('0.01')),
            }
            for item in monthly
        ]

    @staticmethod
    def get_cash_position(as_of_date: Optional[date] = None) -> Dict:
        """Get current cash position."""
        if as_of_date is None:
            as_of_date = date.today()

        base_filter = Q(
            entry__is_posted=True,
            entry__is_active=True,
            entry__entry_date__lte=as_of_date,
        )

        cash_accounts = Account.objects.filter(
            code__startswith='1000', is_active=True
        )

        total_cash = Decimal('0')
        cash_breakdown = []

        for account in cash_accounts:
            balance = JournalEntryLine.objects.filter(
                base_filter, account=account
            ).aggregate(
                debit=Sum('debit'),
                credit=Sum('credit')
            )
            account_balance = (balance['debit'] or Decimal('0')) - (balance['credit'] or Decimal('0'))
            total_cash += account_balance
            cash_breakdown.append({
                'account_code': account.code,
                'account_name': account.name,
                'balance': account_balance.quantize(Decimal('0.01')),
            })

        return {
            'as_of_date': as_of_date,
            'total_cash': total_cash.quantize(Decimal('0.01')),
            'breakdown': cash_breakdown,
        }
