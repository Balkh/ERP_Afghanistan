from decimal import Decimal
from datetime import date
from typing import Optional
from django.db.models import Sum

from accounting.models import JournalEntryLine, Account
from entities.models import Entity


class ConsolidatedReportingService:
    """
    Service for consolidated reporting across entities.
    """

    @staticmethod
    def get_consolidated_balance_sheet(
        as_of_date: date,
        entity_ids: list = None
    ) -> dict:
        """Get consolidated balance sheet."""
        entities = Entity.objects.filter(is_active=True)
        if entity_ids:
            entities = entities.filter(id__in=entity_ids)

        assets = Decimal('0.00')
        liabilities = Decimal('0.00')
        equity = Decimal('0.00')

        asset_accounts = Account.objects.filter(
            account_type='ASSET',
            is_active=True
        )
        liability_accounts = Account.objects.filter(
            account_type='LIABILITY',
            is_active=True
        )
        equity_accounts = Account.objects.filter(
            account_type='EQUITY',
            is_active=True
        )

        base_filter = dict(
            entry__is_posted=True,
            entry__entry_date__lte=as_of_date
        )

        for acc in asset_accounts:
            total = JournalEntryLine.objects.filter(
                account=acc, **base_filter
            ).aggregate(
                total=Sum('debit') - Sum('credit')
            )['total'] or Decimal('0.00')
            assets += abs(total)

        for acc in liability_accounts:
            total = JournalEntryLine.objects.filter(
                account=acc, **base_filter
            ).aggregate(
                total=Sum('credit') - Sum('debit')
            )['total'] or Decimal('0.00')
            liabilities += abs(total)

        for acc in equity_accounts:
            total = JournalEntryLine.objects.filter(
                account=acc, **base_filter
            ).aggregate(
                total=Sum('credit') - Sum('debit')
            )['total'] or Decimal('0.00')
            equity += abs(total)

        return {
            'as_of_date': as_of_date,
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'check': assets - liabilities - equity
        }

    @staticmethod
    def get_consolidated_cash_flow(
        start_date: date,
        end_date: date,
        entity_ids: list = None
    ) -> dict:
        """Get consolidated cash flow statement."""
        entities = Entity.objects.filter(is_active=True)
        if entity_ids:
            entities = entities.filter(id__in=entity_ids)

        from accounting.models import Account
        cash_accounts = Account.objects.filter(
            account_category__in=['CURRENT_ASSET', 'CASH'],
            is_active=True
        )

        opening = Decimal('0.00')
        closing = Decimal('0.00')
        inflows = Decimal('0.00')
        outflows = Decimal('0.00')

        for acc in cash_accounts:
            opening += JournalEntryLine.objects.filter(
                account=acc,
                entry__is_posted=True,
                entry__entry_date__lt=start_date
            ).aggregate(t=Sum('debit') - Sum('credit'))['t'] or Decimal('0.00')

            closing += JournalEntryLine.objects.filter(
                account=acc,
                entry__is_posted=True,
                entry__entry_date__lte=end_date
            ).aggregate(t=Sum('debit') - Sum('credit'))['t'] or Decimal('0.00')

        return {
            'period_start': start_date,
            'period_end': end_date,
            'opening_cash': abs(opening),
            'closing_cash': abs(closing),
            'net_change': abs(closing - opening)
        }

    @staticmethod
    def get_entity_performance_summary(
        start_date: date,
        end_date: date
    ) -> list:
        """Get performance summary for each entity."""
        entities = Entity.objects.filter(is_active=True)
        results = []

        for entity in entities:
            revenue = Decimal('0.00')
            expenses = Decimal('0.00')

            from accounting.models import Account
            revenue_accounts = Account.objects.filter(
                account_type='REVENUE',
                is_active=True
            )
            expense_accounts = Account.objects.filter(
                account_type='EXPENSE',
                is_active=True
            )

            for acc in revenue_accounts:
                revenue += JournalEntryLine.objects.filter(
                    account=acc,
                    entry__is_posted=True,
                    entry__entry_date__gte=start_date,
                    entry__entry_date__lte=end_date
                ).aggregate(t=Sum('credit'))['t'] or Decimal('0.00')

            for acc in expense_accounts:
                expenses += JournalEntryLine.objects.filter(
                    account=acc,
                    entry__is_posted=True,
                    entry__entry_date__gte=start_date,
                    entry__entry_date__lte=end_date
                ).aggregate(t=Sum('debit'))['t'] or Decimal('0.00')

            results.append({
                'entity_code': entity.code,
                'entity_name': entity.name,
                'entity_type': entity.entity_type,
                'revenue': revenue,
                'expenses': expenses,
                'net_income': revenue - expenses
            })

        return results