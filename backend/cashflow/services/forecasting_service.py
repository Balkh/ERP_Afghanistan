from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List, Dict
from django.db.models import Sum

from accounting.models import JournalEntryLine, Account
from accounting.services.journal_engine import JournalEngine
from cashflow.models import CashFlowForecast, CashFlowItem, CashFlowScenario


class CashFlowForecastingService:
    """Service for cash flow forecasting and analysis."""

    @staticmethod
    def get_historical_cash_flow(
        start_date: date,
        end_date: date,
        account: Account = None
    ) -> List[Dict]:
        """Get historical cash flow data."""
        from accounting.models import Account
        
        cash_accounts = Account.objects.filter(
            account_category__in=['CURRENT_ASSET', 'CASH']
        )
        if account:
            cash_accounts = [account]

        results = []
        current = start_date
        
        while current <= end_date:
            day_inflows = Decimal('0.00')
            day_outflows = Decimal('0.00')

            for acc in cash_accounts:
                lines = JournalEntryLine.objects.filter(
                    account=acc,
                    entry__is_posted=True,
                    entry__entry_date=current
                )
                day_inflows += lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')
                day_outflows += lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')

            results.append({
                'date': current,
                'inflows': day_inflows,
                'outflows': day_outflows,
                'net': day_inflows - day_outflows
            })
            current += timedelta(days=1)

        return results

    @staticmethod
    def generate_forecast(
        start_date: date,
        end_date: date,
        forecast_type: str = 'MONTHLY'
    ) -> Dict:
        """Generate forecast based on historical patterns."""
        from accounting.models import Currency
        
        currency = Currency.objects.filter(is_active=True).first()
        if not currency:
            currency = Currency.objects.create(
                code='USD', name='US Dollar', symbol='$', is_active=True
            )
        
        forecast = CashFlowForecast.objects.create(
            name=f'Generated Forecast {start_date}',
            forecast_type=forecast_type,
            start_date=start_date,
            end_date=end_date,
            currency=currency
        )

        historical = CashFlowForecastingService.get_historical_cash_flow(
            start_date - timedelta(days=90),
            start_date - timedelta(days=1)
        )

        avg_inflow = sum(h['inflows'] for h in historical) / max(len(historical), 1)
        avg_outflow = sum(h['outflows'] for h in historical) / max(len(historical), 1)

        if forecast_type == 'DAILY':
            days = (end_date - start_date).days + 1
            step = 1
        elif forecast_type == 'WEEKLY':
            days = ((end_date - start_date).days // 7) + 1
            step = 7
        else:
            days = ((end_date.year - start_date.year) * 12 + end_date.month - start_date.month) + 1
            step = 30

        current = start_date
        for _ in range(min(days, 30)):
            CashFlowItem.objects.create(
                forecast=forecast,
                category='OTHER_INCOME' if avg_inflow > avg_outflow else 'OTHER_EXPENSE',
                item_type='INFLOW' if avg_inflow > avg_outflow else 'OUTFLOW',
                description='Projected cash flow',
                expected_date=current,
                amount=abs(avg_inflow - avg_outflow),
                probability=Decimal('80.00')
            )
            current += timedelta(days=step)
            if current > end_date:
                break

        return {
            'id': str(forecast.id),
            'items_count': forecast.items.count(),
            'start_date': forecast.start_date,
            'end_date': forecast.end_date
        }

    @staticmethod
    def get_forecast_summary(forecast: CashFlowForecast) -> Dict:
        """Get summary of a forecast."""
        items = forecast.items.all()

        total_inflow = sum(
            i.amount for i in items if i.item_type == 'INFLOW'
        )
        total_outflow = sum(
            i.amount for i in items if i.item_type == 'OUTFLOW'
        )
        weighted_inflow = sum(
            i.weighted_amount for i in items if i.item_type == 'INFLOW'
        )
        weighted_outflow = sum(
            i.weighted_amount for i in items if i.item_type == 'OUTFLOW'
        )

        return {
            'forecast_id': str(forecast.id),
            'total_inflow': total_inflow,
            'total_outflow': total_outflow,
            'net_position': total_inflow - total_outflow,
            'weighted_inflow': weighted_inflow,
            'weighted_outflow': weighted_outflow,
            'weighted_net': weighted_inflow - weighted_outflow,
            'items_count': items.count(),
            'actual_count': items.filter(is_actual=True).count()
        }

    @staticmethod
    def run_scenario_analysis(scenario: CashFlowScenario) -> Dict:
        """Run what-if analysis based on scenario."""
        historical = CashFlowForecastingService.get_historical_cash_flow(
            scenario.start_date - timedelta(days=90),
            scenario.start_date - timedelta(days=1)
        )

        base_inflow = sum(h['inflows'] for h in historical) / max(len(historical), 1)
        base_outflow = sum(h['outflows'] for h in historical) / max(len(historical), 1)

        adjusted_inflow = base_inflow * (1 + scenario.sales_growth_rate / 100)
        adjusted_outflow = base_outflow

        expected_inflow = adjusted_inflow * scenario.collection_rate / 100
        expected_outflow = adjusted_outflow * scenario.payment_rate / 100

        days = (scenario.end_date - scenario.start_date).days

        return {
            'scenario': scenario.name,
            'type': scenario.scenario_type,
            'period_days': days,
            'daily_inflow': expected_inflow,
            'daily_outflow': expected_outflow,
            'total_inflow': expected_inflow * days,
            'total_outflow': expected_outflow * days,
            'net_position': (expected_inflow - expected_outflow) * days
        }

    @staticmethod
    def get_receivables_forecast(days_ahead: int = 30) -> Dict:
        """Forecast incoming cash from receivables."""
        from sales.models import SalesInvoice
        
        pending_invoices = SalesInvoice.objects.filter(
            status__in=['DISPATCHED', 'PARTIAL_PAID'],
            payment_status__in=['UNPAID', 'PARTIAL']
        )

        forecast = []
        for inv in pending_invoices:
            due_date = inv.due_date if inv.due_date else inv.invoice_date + timedelta(days=30)
            if due_date <= date.today() + timedelta(days=days_ahead):
                forecast.append({
                    'invoice_id': str(inv.id),
                    'customer': str(inv.customer),
                    'amount': inv.total_amount,
                    'due_date': due_date,
                    'days_until_due': (due_date - date.today()).days
                })

        return {
            'total_pending': sum(f['amount'] for f in forecast),
            'invoices': forecast
        }

    @staticmethod
    def get_payables_forecast(days_ahead: int = 30) -> Dict:
        """Forecast outgoing cash for payables."""
        from purchases.models import PurchaseInvoice
        
        pending_invoices = PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PARTIAL_RECEIVED'],
            payment_status__in=['UNPAID', 'PARTIAL']
        )

        forecast = []
        for inv in pending_invoices:
            due_date = inv.due_date if inv.due_date else inv.invoice_date + timedelta(days=30)
            if due_date <= date.today() + timedelta(days=days_ahead):
                forecast.append({
                    'invoice_id': str(inv.id),
                    'supplier': str(inv.supplier),
                    'amount': inv.total_amount,
                    'due_date': due_date,
                    'days_until_due': (due_date - date.today()).days
                })

        return {
            'total_pending': sum(f['amount'] for f in forecast),
            'invoices': forecast
        }