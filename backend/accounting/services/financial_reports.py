from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Union
from collections import defaultdict
from django.db import models
from django.db.models import Sum, Q, Count
from accounting.models import Account, JournalEntry, JournalEntryLine


class FinancialReportEngine:
    """
    Financial reporting engine.

    Generates:
    - Trial Balance
    - Profit & Loss (Income Statement)
    - Balance Sheet
    - Cash Flow Statement
    - Account Ledger
    - Account Summary
    """

    @staticmethod
    def get_trial_balance(as_of_date: Optional[date] = None, include_zero: bool = False, company_id: Optional[str] = None) -> dict:
        """
        Generate trial balance report.

        Lists all accounts with debit/credit totals.
        Total debits must equal total credits.
        """
        if as_of_date is None:
            as_of_date = date.today()

        base_filter = Q(account__is_active=True, entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=as_of_date)
        if company_id:
            base_filter = base_filter & Q(account__company_id=company_id)

        account_filter = Q(is_active=True)
        if company_id:
            account_filter = account_filter & Q(company_id=company_id)
        accounts = Account.objects.filter(account_filter).order_by('code')
        rows = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')

        by_type = defaultdict(list)

        for account in accounts:
            lines = JournalEntryLine.objects.filter(account=account).filter(base_filter)

            debit = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
            credit = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

            if debit == 0 and credit == 0 and not include_zero:
                continue

            if account.account_type in ['ASSET', 'EXPENSE']:
                net_balance = debit - credit
                balance_type = 'DEBIT' if net_balance >= 0 else 'CREDIT'
            else:
                net_balance = credit - debit
                balance_type = 'CREDIT' if net_balance >= 0 else 'DEBIT'

            row = {
                'account_code': account.code,
                'account_name': account.name,
                'account_type': account.account_type,
                'account_category': account.account_category,
                'total_debit': debit,
                'total_credit': credit,
                'net_balance': abs(net_balance),
                'balance_type': balance_type,
                'level': account.level,
                'parent_code': account.parent.code if account.parent else None,
            }
            rows.append(row)
            by_type[account.account_type].append(row)

            total_debit += debit
            total_credit += credit

        difference = abs(total_debit - total_credit)

        return {
            'report_type': 'Trial Balance',
            'as_of_date': as_of_date.isoformat(),
            'accounts': rows,
            'by_type': {k: v for k, v in by_type.items()},
            'total_debit': total_debit,
            'total_credit': total_credit,
            'difference': difference,
            'is_balanced': difference == Decimal('0.00'),
        }

    @staticmethod
    def get_profit_and_loss(
        start_date: date,
        end_date: date,
        compare_start: Optional[date] = None,
        compare_end: Optional[date] = None,
        group_by_category: bool = True,
        company_id: Optional[str] = None
    ) -> dict:
        """
        Generate Profit & Loss (Income Statement) with optional prior-period comparison.

        Revenue - COGS = Gross Profit
        Gross Profit - Expenses = Net Income
        """
        current = FinancialReportEngine._get_pnl_section(start_date, end_date, group_by_category, company_id)

        comparison = None
        if compare_start and compare_end:
            comparison = FinancialReportEngine._get_pnl_section(compare_start, compare_end, group_by_category, company_id)

        revenue_total = current.get('total_revenue', Decimal('0.00'))
        cogs_total = current.get('total_cogs', Decimal('0.00'))
        expense_total = current.get('total_expenses', Decimal('0.00'))

        gross_profit = revenue_total - cogs_total
        net_income = gross_profit - expense_total

        report = {
            'report_type': 'Profit & Loss',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'revenue': current.get('revenue', []),
            'total_revenue': revenue_total,
            'cogs': current.get('cogs', []),
            'total_cogs': cogs_total,
            'gross_profit': gross_profit,
            'expenses': current.get('expenses', []),
            'total_expenses': expense_total,
            'net_income': net_income,
            'is_profitable': net_income > 0,
        }

        if comparison:
            comp_revenue = comparison.get('total_revenue', Decimal('0.00'))
            comp_expenses = comparison.get('total_expenses', Decimal('0.00'))
            comp_cogs = comparison.get('total_cogs', Decimal('0.00'))
            comp_net = comp_revenue - comp_cogs - comp_expenses

            report['comparison'] = {
                'start_date': compare_start.isoformat(),
                'end_date': compare_end.isoformat(),
                'total_revenue': comp_revenue,
                'total_cogs': comp_cogs,
                'total_expenses': comp_expenses,
                'net_income': comp_net,
            }

            if comp_revenue != 0:
                report['revenue_growth_pct'] = float((revenue_total - comp_revenue) / comp_revenue * 100)
            if comp_net != 0:
                report['net_income_growth_pct'] = float((net_income - comp_net) / comp_net * 100)

        return report

    @staticmethod
    def _get_pnl_section(start_date: date, end_date: date, group_by_category: bool = True, company_id: Optional[str] = None) -> dict:
        """Get P&L data for a single period."""
        date_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)
        if company_id:
            date_filter = date_filter & Q(account__company_id=company_id)

        result = {'revenue': [], 'cogs': [], 'expenses': [], 'total_revenue': Decimal('0.00'), 'total_cogs': Decimal('0.00'), 'total_expenses': Decimal('0.00')}

        base_account_filter = Q(is_active=True)
        if company_id:
            base_account_filter = base_account_filter & Q(company_id=company_id)
        revenue_accounts = Account.objects.filter(base_account_filter & Q(account_type='REVENUE')).order_by('code')
        cogs_accounts = Account.objects.filter(base_account_filter & Q(account_category='COST_OF_GOODS_SOLD')).order_by('code')
        expense_accounts = Account.objects.filter(base_account_filter & Q(account_type='EXPENSE')).exclude(account_category='COST_OF_GOODS_SOLD').order_by('code')

        def process_accounts(accounts, target_key, total_key):
            grouped = defaultdict(lambda: {'accounts': [], 'total': Decimal('0.00')})

            account_ids = [a.id for a in accounts]
            if not account_ids:
                return grouped

            lines_agg = JournalEntryLine.objects.filter(
                account_id__in=account_ids
            ).filter(date_filter).values('account_id').annotate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )
            agg_map = {item['account_id']: item for item in lines_agg}

            for account in accounts:
                totals = agg_map.get(account.id, {})
                debit = totals.get('total_debit') or Decimal('0.00')
                credit = totals.get('total_credit') or Decimal('0.00')

                if account.account_type == 'REVENUE':
                    net = credit - debit
                elif account.account_category == 'COST_OF_GOODS_SOLD':
                    net = debit - credit
                else:
                    net = debit - credit

                if net != 0:
                    entry = {
                        'account_code': account.code,
                        'account_name': account.name,
                        'category': account.account_category or '',
                        'amount': net,
                    }

                    if group_by_category and account.account_category:
                        grouped[account.account_category]['accounts'].append(entry)
                        grouped[account.account_category]['total'] += net
                    else:
                        grouped['UNCATEGORIZED']['accounts'].append(entry)
                        grouped['UNCATEGORIZED']['total'] += net

                    result[total_key] += net

            if group_by_category:
                result[target_key] = [
                    {'category': cat, 'total': data['total'], 'accounts': data['accounts']}
                    for cat, data in grouped.items()
                ]
            else:
                result[target_key] = [a for data in grouped.values() for a in data['accounts']]

        process_accounts(revenue_accounts, 'revenue', 'total_revenue')
        process_accounts(cogs_accounts, 'cogs', 'total_cogs')
        process_accounts(expense_accounts, 'expenses', 'total_expenses')

        return result

    @staticmethod
    def get_balance_sheet(as_of_date: Optional[date] = None, include_net_income: bool = True, company_id: Optional[str] = None) -> dict:
        """
        Generate Balance Sheet report.

        Assets = Liabilities + Equity
        """
        if as_of_date is None:
            as_of_date = date.today()

        date_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=as_of_date)
        if company_id:
            date_filter = date_filter & Q(account__company_id=company_id)

        def calculate_balances(account_qs, is_positive_debit=False):
            sections = []
            total = Decimal('0.00')
            grouped = defaultdict(lambda: {'accounts': [], 'total': Decimal('0.00')})

            for account in account_qs:
                lines = JournalEntryLine.objects.filter(account=account).filter(date_filter)
                debit = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
                credit = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

                net = (debit - credit) if is_positive_debit else (credit - debit)

                if net != 0:
                    entry = {
                        'account_code': account.code,
                        'account_name': account.name,
                        'category': account.account_category or '',
                        'amount': net,
                    }
                    cat = account.account_category or 'UNCATEGORIZED'
                    grouped[cat]['accounts'].append(entry)
                    grouped[cat]['total'] += net
                    total += net

            sections = [
                {'category': cat, 'total': data['total'], 'accounts': data['accounts']}
                for cat, data in grouped.items()
            ]
            return sections, total

        base_account_filter = Q(is_active=True)
        if company_id:
            base_account_filter = base_account_filter & Q(company_id=company_id)

        asset_sections, total_assets = calculate_balances(
            Account.objects.filter(base_account_filter & Q(account_type='ASSET')).order_by('code'),
            is_positive_debit=True
        )
        liability_sections, total_liabilities = calculate_balances(
            Account.objects.filter(base_account_filter & Q(account_type='LIABILITY')).order_by('code')
        )
        equity_sections, total_equity = calculate_balances(
            Account.objects.filter(base_account_filter & Q(account_type='EQUITY')).order_by('code')
        )

        if include_net_income:
            start_of_year = date(as_of_date.year, 1, 1)
            pnl = FinancialReportEngine.get_profit_and_loss(start_of_year, as_of_date, company_id=company_id)
            net_income = pnl['net_income']

            if net_income != 0:
                equity_sections.append({
                    'category': 'NET_INCOME',
                    'total': net_income,
                    'accounts': [{
                        'account_code': 'RE',
                        'account_name': 'Retained Earnings (Current Year)',
                        'category': 'NET_INCOME',
                        'amount': net_income,
                    }],
                })
                total_equity += net_income

        total_liabilities_equity = total_liabilities + total_equity
        difference = abs(total_assets - total_liabilities_equity)

        return {
            'report_type': 'Balance Sheet',
            'as_of_date': as_of_date.isoformat(),
            'assets': {'sections': asset_sections, 'total': total_assets},
            'liabilities': {'sections': liability_sections, 'total': total_liabilities},
            'equity': {'sections': equity_sections, 'total': total_equity},
            'total_liabilities_equity': total_liabilities_equity,
            'difference': difference,
            'is_balanced': difference == Decimal('0.00'),
        }

    @staticmethod
    def get_cash_flow_statement(start_date: date, end_date: date, company_id: Optional[str] = None) -> dict:
        """
        Generate Cash Flow Statement using indirect method.

        Operating Activities (Net Income + Non-cash adjustments +/- Working capital changes)
        Investing Activities (Asset purchases/sales)
        Financing Activities (Debt, equity transactions)
        """
        date_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)
        if company_id:
            date_filter = date_filter & Q(account__company_id=company_id)

        # Net Income
        pnl = FinancialReportEngine.get_profit_and_loss(start_date, end_date, company_id=company_id)
        net_income = pnl['net_income']

        # Operating activities: changes in working capital
        working_capital_changes = []
        operating_total = net_income

        base_account_filter = Q(is_active=True)
        if company_id:
            base_account_filter = base_account_filter & Q(company_id=company_id)

        # AR changes (Asset type, increase = cash out)
        ar_accounts = Account.objects.filter(base_account_filter & Q(account_type='ASSET', account_category='CURRENT_ASSET'))
        for acc in ar_accounts:
            change = FinancialReportEngine._get_account_change(acc, start_date, end_date, company_id)
            if change != 0:
                working_capital_changes.append({
                    'account_code': acc.code,
                    'account_name': acc.name,
                    'change': -change,
                    'description': f'Change in {acc.name}',
                })
                operating_total -= change

        # AP changes (Liability type, increase = cash in)
        ap_accounts = Account.objects.filter(base_account_filter & Q(account_type='LIABILITY', account_category='CURRENT_LIABILITY'))
        for acc in ap_accounts:
            change = FinancialReportEngine._get_account_change(acc, start_date, end_date, company_id)
            if change != 0:
                working_capital_changes.append({
                    'account_code': acc.code,
                    'account_name': acc.name,
                    'change': change,
                    'description': f'Change in {acc.name}',
                })
                operating_total += change

        # Investing activities: changes in fixed assets
        investing_activities = []
        investing_total = Decimal('0.00')
        fa_accounts = Account.objects.filter(base_account_filter & Q(account_type='ASSET', account_category__in=['FIXED_ASSET', 'INTANGIBLE_ASSET']))
        for acc in fa_accounts:
            change = FinancialReportEngine._get_account_change(acc, start_date, end_date, company_id)
            if change != 0:
                investing_activities.append({
                    'account_code': acc.code,
                    'account_name': acc.name,
                    'change': -change,
                    'description': f'Change in {acc.name}',
                })
                investing_total -= change

        # Financing activities: changes in long-term liabilities and equity
        financing_activities = []
        financing_total = Decimal('0.00')
        lt_accounts = Account.objects.filter(base_account_filter & Q(account_type='LIABILITY', account_category='LONG_TERM_LIABILITY'))
        eq_accounts = Account.objects.filter(base_account_filter & Q(account_type='EQUITY'))
        for acc in list(lt_accounts) + list(eq_accounts):
            change = FinancialReportEngine._get_account_change(acc, start_date, end_date, company_id)
            if change != 0:
                is_equity = acc.account_type == 'EQUITY'
                financing_activities.append({
                    'account_code': acc.code,
                    'account_name': acc.name,
                    'change': change if is_equity else -change,
                    'description': f'Change in {acc.name}',
                })
                financing_total += change if is_equity else -change

        net_change = operating_total + investing_total + financing_total

        # Opening cash balance
        cash_accounts = Account.objects.filter(base_account_filter & Q(account_type='ASSET', account_category='CURRENT_ASSET'))
        opening_cash = Decimal('0.00')
        for acc in cash_accounts:
            cash_line_filter = Q(account=acc, entry__entry_date__lt=start_date, entry__is_posted=True, entry__is_active=True)
            if company_id:
                cash_line_filter = cash_line_filter & Q(account__company_id=company_id)
            lines = JournalEntryLine.objects.filter(cash_line_filter)
            d = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
            c = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
            opening_cash += d - c

        closing_cash = opening_cash + net_change

        return {
            'report_type': 'Cash Flow Statement',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'operating_activities': {
                'net_income': net_income,
                'working_capital_changes': working_capital_changes,
                'net_cash_from_operations': operating_total,
            },
            'investing_activities': {
                'items': investing_activities,
                'net_cash_from_investing': investing_total,
            },
            'financing_activities': {
                'items': financing_activities,
                'net_cash_from_financing': financing_total,
            },
            'net_change_in_cash': net_change,
            'opening_cash_balance': opening_cash,
            'closing_cash_balance': closing_cash,
        }

    @staticmethod
    def _get_account_change(account, start_date: date, end_date: date, company_id: Optional[str] = None) -> Decimal:
        """Get the net change in an account balance over a period."""
        before_filter = Q(account=account, entry__is_posted=True, entry__is_active=True, entry__entry_date__lt=start_date)
        during_filter = Q(account=account, entry__is_posted=True, entry__is_active=True, entry__entry_date__gte=start_date, entry__entry_date__lte=end_date)
        if company_id:
            before_filter = before_filter & Q(account__company_id=company_id)
            during_filter = during_filter & Q(account__company_id=company_id)

        is_asset = account.account_type in ['ASSET', 'EXPENSE']

        before_d = JournalEntryLine.objects.filter(before_filter).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        before_c = JournalEntryLine.objects.filter(before_filter).aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
        before_balance = (before_d - before_c) if is_asset else (before_c - before_d)

        during_d = JournalEntryLine.objects.filter(during_filter).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        during_c = JournalEntryLine.objects.filter(during_filter).aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
        during_change = (during_d - during_c) if is_asset else (during_c - during_d)

        return during_change

    @staticmethod
    def get_account_ledger(account_id, start_date: Optional[date] = None, end_date: Optional[date] = None, company_id: Optional[str] = None) -> dict:
        """Get ledger for an account with running balance."""
        try:
            account_filter = Q(id=account_id)
            if company_id:
                account_filter = account_filter & Q(company_id=company_id)
            account = Account.objects.get(account_filter)
        except Account.DoesNotExist:
            return {'error': 'Account not found', 'entries': []}

        line_filter = Q(account_id=account_id, entry__is_posted=True, entry__is_active=True)
        if company_id:
            line_filter = line_filter & Q(account__company_id=company_id)
        lines = JournalEntryLine.objects.filter(line_filter
        ).select_related('entry').order_by('entry__entry_date', 'entry__created_at')

        if start_date:
            lines = lines.filter(entry__entry_date__gte=start_date)
        if end_date:
            lines = lines.filter(entry__entry_date__lte=end_date)

        opening_debit = Decimal('0.00')
        opening_credit = Decimal('0.00')

        if start_date:
            opening_filter = Q(account_id=account_id, entry__is_posted=True, entry__is_active=True,
                               entry__entry_date__lt=start_date)
            if company_id:
                opening_filter = opening_filter & Q(account__company_id=company_id)
            opening_debit = JournalEntryLine.objects.filter(opening_filter
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

            opening_credit = JournalEntryLine.objects.filter(opening_filter
            ).aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

        if account.account_type in ['ASSET', 'EXPENSE']:
            running_balance = opening_debit - opening_credit
        else:
            running_balance = opening_credit - opening_debit

        opening_balance = running_balance

        ledger_entries = []
        for line in lines:
            if account.account_type in ['ASSET', 'EXPENSE']:
                running_balance += line.debit - line.credit
            else:
                running_balance += line.credit - line.debit

            ledger_entries.append({
                'entry_number': line.entry.entry_number,
                'entry_date': line.entry.entry_date.isoformat(),
                'entry_type': line.entry.entry_type,
                'description': line.description or line.entry.description,
                'reference': line.entry.reference,
                'debit': line.debit,
                'credit': line.credit,
                'running_balance': running_balance,
            })

        return {
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'opening_balance': opening_balance,
            'entries': ledger_entries,
            'closing_balance': running_balance,
            'total_debit': sum(e['debit'] for e in ledger_entries),
            'total_credit': sum(e['credit'] for e in ledger_entries),
            'entry_count': len(ledger_entries),
        }

    @staticmethod
    def get_account_summary(as_of_date: Optional[date] = None, company_id: Optional[str] = None) -> dict:
        """Get summary of all account balances by type."""
        if as_of_date is None:
            as_of_date = date.today()

        account_filter = Q(is_active=True)
        if company_id:
            account_filter = account_filter & Q(company_id=company_id)

        line_filter = Q(entry__is_posted=True, entry__is_active=True, entry__entry_date__lte=as_of_date)
        if company_id:
            line_filter = line_filter & Q(account__company_id=company_id)

        summary = {}
        for acc_type in ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE']:
            accounts = Account.objects.filter(account_filter & Q(account_type=acc_type))

            total_debit = Decimal('0.00')
            total_credit = Decimal('0.00')

            for account in accounts:
                lines = JournalEntryLine.objects.filter(
                    account=account, entry__is_posted=True, entry__is_active=True,
                    entry__entry_date__lte=as_of_date
                )
                if company_id:
                    lines = lines.filter(account__company_id=company_id)
                total_debit += lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
                total_credit += lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

            net = (total_debit - total_credit) if acc_type in ['ASSET', 'EXPENSE'] else (total_credit - total_debit)

            summary[acc_type] = {
                'total_debit': total_debit,
                'total_credit': total_credit,
                'net_balance': net,
                'account_count': accounts.count(),
            }

        return summary

    @staticmethod
    def get_ar_aging(as_of_date: Optional[date] = None, buckets: Optional[list] = None, company_id: Optional[str] = None) -> dict:
        """
        Accounts Receivable Aging Report.

        Shows outstanding customer invoices grouped by age buckets.
        """
        if as_of_date is None:
            as_of_date = date.today()
        if buckets is None:
            buckets = [0, 30, 60, 90]

        from sales.models import Customer, SalesInvoice

        customer_filter = Q(is_active=True)
        if company_id:
            customer_filter = customer_filter & Q(company_id=company_id)
        customers = Customer.objects.filter(customer_filter)
        aging_rows = []
        totals = {'current': Decimal('0.00'), 'age_1_30': Decimal('0.00'), 'age_31_60': Decimal('0.00'), 'age_61_90': Decimal('0.00'), 'age_90_plus': Decimal('0.00'), 'total': Decimal('0.00')}

        for customer in customers:
            invoices = SalesInvoice.objects.filter(
                customer=customer,
                status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
                is_active=True
            )

            current = Decimal('0.00')
            age_1_30 = Decimal('0.00')
            age_31_60 = Decimal('0.00')
            age_61_90 = Decimal('0.00')
            age_90_plus = Decimal('0.00')

            for inv in invoices:
                outstanding = inv.total_amount - inv.paid_amount
                if outstanding <= 0:
                    continue

                days_overdue = (as_of_date - inv.due_date).days

                if days_overdue <= 0:
                    current += outstanding
                elif days_overdue <= 30:
                    age_1_30 += outstanding
                elif days_overdue <= 60:
                    age_31_60 += outstanding
                elif days_overdue <= 90:
                    age_61_90 += outstanding
                else:
                    age_90_plus += outstanding

            customer_total = current + age_1_30 + age_31_60 + age_61_90 + age_90_plus

            if customer_total > 0:
                aging_rows.append({
                    'party_id': str(customer.id),
                    'party_name': customer.name,
                    'party_code': customer.code,
                    'current': current,
                    'age_1_30': age_1_30,
                    'age_31_60': age_31_60,
                    'age_61_90': age_61_90,
                    'age_90_plus': age_90_plus,
                    'total': customer_total,
                    'credit_limit': str(customer.credit_limit),
                })

                totals['current'] += current
                totals['age_1_30'] += age_1_30
                totals['age_31_60'] += age_31_60
                totals['age_61_90'] += age_61_90
                totals['age_90_plus'] += age_90_plus
                totals['total'] += customer_total

        aging_rows.sort(key=lambda x: x['total'], reverse=True)

        return {
            'report_type': 'Accounts Receivable Aging',
            'as_of_date': as_of_date.isoformat(),
            'buckets': buckets,
            'aging_rows': aging_rows,
            'totals': totals,
            'customer_count': len(aging_rows),
        }

    @staticmethod
    def get_ap_aging(as_of_date: Optional[date] = None, buckets: Optional[list] = None, company_id: Optional[str] = None) -> dict:
        """
        Accounts Payable Aging Report.

        Shows outstanding supplier invoices grouped by age buckets.
        """
        if as_of_date is None:
            as_of_date = date.today()
        if buckets is None:
            buckets = [0, 30, 60, 90]

        from purchases.models import Supplier, PurchaseInvoice

        supplier_filter = Q(is_active=True)
        if company_id:
            supplier_filter = supplier_filter & Q(company_id=company_id)
        suppliers = Supplier.objects.filter(supplier_filter)
        aging_rows = []
        totals = {'current': Decimal('0.00'), 'age_1_30': Decimal('0.00'), 'age_31_60': Decimal('0.00'), 'age_61_90': Decimal('0.00'), 'age_90_plus': Decimal('0.00'), 'total': Decimal('0.00')}

        for supplier in suppliers:
            invoices = PurchaseInvoice.objects.filter(
                supplier=supplier,
                status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
                is_active=True
            )

            current = Decimal('0.00')
            age_1_30 = Decimal('0.00')
            age_31_60 = Decimal('0.00')
            age_61_90 = Decimal('0.00')
            age_90_plus = Decimal('0.00')

            for inv in invoices:
                outstanding = inv.total_amount - inv.paid_amount
                if outstanding <= 0:
                    continue

                days_overdue = (as_of_date - inv.due_date).days

                if days_overdue <= 0:
                    current += outstanding
                elif days_overdue <= 30:
                    age_1_30 += outstanding
                elif days_overdue <= 60:
                    age_31_60 += outstanding
                elif days_overdue <= 90:
                    age_61_90 += outstanding
                else:
                    age_90_plus += outstanding

            supplier_total = current + age_1_30 + age_31_60 + age_61_90 + age_90_plus

            if supplier_total > 0:
                aging_rows.append({
                    'party_id': str(supplier.id),
                    'party_name': supplier.name,
                    'party_code': supplier.code,
                    'current': current,
                    'age_1_30': age_1_30,
                    'age_31_60': age_31_60,
                    'age_61_90': age_61_90,
                    'age_90_plus': age_90_plus,
                    'total': supplier_total,
                    'credit_limit': str(supplier.credit_limit),
                })

                totals['current'] += current
                totals['age_1_30'] += age_1_30
                totals['age_31_60'] += age_31_60
                totals['age_61_90'] += age_61_90
                totals['age_90_plus'] += age_90_plus
                totals['total'] += supplier_total

        aging_rows.sort(key=lambda x: x['total'], reverse=True)

        return {
            'report_type': 'Accounts Payable Aging',
            'as_of_date': as_of_date.isoformat(),
            'buckets': buckets,
            'aging_rows': aging_rows,
            'totals': totals,
            'supplier_count': len(aging_rows),
        }
