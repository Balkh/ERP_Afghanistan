"""
Production Optimization Tests
Budget vs Actual, Variance Analysis, Production KPIs.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from accounting.models import Account, Currency, JournalEntry, JournalEntryLine
from budgeting.models import Budget, BudgetLine
from sales.models import Customer, SalesInvoice
from purchases.models import Supplier, PurchaseInvoice
from production.services.optimization import (
    VarianceAnalysis, ProductionKPI, BudgetForecast
)


class VarianceAnalysisTests(TestCase):
    """Test variance analysis."""

    def test_get_budget_variance_not_found(self):
        """Test with non-existent budget."""
        result = VarianceAnalysis.get_budget_variance('invalid-id')
        self.assertIn('error', result)

    def test_get_budget_variance_empty(self):
        """Test variance with no lines."""
        budget = Budget.objects.create(
            name='Test Budget',
            fiscal_year=2025,
            period_type='ANNUAL',
            status='APPROVED',
            total_budgeted=Decimal('10000'),
            total_actual=Decimal('5000')
        )

        result = VarianceAnalysis.get_budget_variance(str(budget.id))

        self.assertEqual(result['budget_name'], 'Test Budget')
        self.assertEqual(result['fiscal_year'], 2025)

    def test_get_budget_variance_with_lines(self):
        """Test variance with budget lines."""
        account = Account.objects.filter(account_category='OPERATING_EXPENSE').first()
        if not account:
            account = Account.objects.create(
                code='5100', name='Operating Expenses', account_type='EXPENSE',
                account_category='OPERATING_EXPENSE', is_active=True
            )

        budget = Budget.objects.create(
            name='Sales Budget',
            fiscal_year=2025,
            period_type='ANNUAL',
            status='APPROVED',
            total_budgeted=Decimal('50000'),
            total_actual=Decimal('45000')
        )

        BudgetLine.objects.create(
            budget=budget,
            account=account,
            period='2025-ANNUAL',
            budgeted_amount=Decimal('20000'),
            actual_amount=Decimal('15000')
        )

        result = VarianceAnalysis.get_budget_variance(str(budget.id))

        self.assertEqual(result['total_budgeted'], Decimal('20000'))

    def test_department_variance_empty(self):
        """Test department variance with no budgets."""
        result = VarianceAnalysis.get_department_variance(2025)
        self.assertEqual(result['departments'], [])


class ProductionKPITests(TestCase):
    """Test production KPIs."""

    def test_production_efficiency_empty(self):
        """Test efficiency with no data."""
        kpi = ProductionKPI.get_production_efficiency(days=30)

        self.assertEqual(kpi['total_revenue'], Decimal('0'))
        self.assertEqual(kpi['total_purchases'], Decimal('0'))
        self.assertEqual(kpi['gross_profit'], Decimal('0'))

    def test_production_efficiency_with_data(self):
        """Test efficiency with sales data."""
        customer = Customer.objects.create(
            name='Test Customer', code='TC001', customer_type='RETAIL'
        )

        SalesInvoice.objects.create(
            invoice_number='EFF-001',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            payment_status='PAID',
            subtotal=Decimal('10000'),
            total_amount=Decimal('10000')
        )

        kpi = ProductionKPI.get_production_efficiency(days=30)

        self.assertEqual(kpi['total_revenue'], Decimal('10000'))

    def test_working_capital_metrics(self):
        """Test working capital metrics."""
        metrics = ProductionKPI.get_working_capital_metrics()

        self.assertIn('accounts_receivable', metrics)
        self.assertIn('accounts_payable', metrics)
        self.assertIn('net_working_capital', metrics)

    def test_turnover_ratios_empty(self):
        """Test turnover ratios with no data."""
        ratios = ProductionKPI.get_turnover_ratios(days=90)

        self.assertIn('inventory_turnover', ratios)
        self.assertIn('days_sales_outstanding', ratios)


class BudgetForecastTests(TestCase):
    """Test budget forecasting."""

    def test_forecast_revenue_no_data(self):
        """Test revenue forecast with no historical data."""
        result = BudgetForecast.forecast_revenue(fiscal_year=2025, months_ahead=3)

        self.assertEqual(result['fiscal_year'], 2025)
        self.assertEqual(result['monthly_average'], Decimal('0'))

    def test_forecast_revenue_with_data(self):
        """Test revenue forecast with historical data."""
        customer = Customer.objects.create(
            name='Forecast Customer', code='FC001', customer_type='RETAIL'
        )

        for i in range(1, 4):
            SalesInvoice.objects.create(
                invoice_number=f'FCINV-{i:03d}',
                customer=customer,
                order_date=date.today() - timedelta(days=30 * i),
                invoice_date=date.today() - timedelta(days=30 * i),
                due_date=date.today(),
                status='DISPATCHED',
                payment_status='PAID',
                subtotal=Decimal('5000'),
                total_amount=Decimal('5000')
            )

        result = BudgetForecast.forecast_revenue(fiscal_year=2025, months_ahead=3)

        self.assertEqual(result['fiscal_year'], 2025)
        self.assertGreater(len(result['forecasts']), 0)

    def test_forecast_expenses_no_data(self):
        """Test expense forecast with no data."""
        result = BudgetForecast.forecast_expenses(fiscal_year=2025, months_ahead=3)

        self.assertEqual(result['fiscal_year'], 2025)
        self.assertIn('forecasts', result)

    def test_budget_utilization_empty(self):
        """Test budget utilization with no budgets."""
        result = BudgetForecast.get_budget_utilization(fiscal_year=2025)

        self.assertEqual(result['fiscal_year'], 2025)
        self.assertEqual(result['budgets'], [])
        self.assertEqual(result['total_budgeted'], Decimal('0'))

    def test_budget_utilization_with_budgets(self):
        """Test budget utilization with data."""
        Budget.objects.create(
            name='Marketing Budget',
            fiscal_year=2025,
            period_type='ANNUAL',
            status='APPROVED',
            total_budgeted=Decimal('50000'),
            total_actual=Decimal('35000')
        )

        result = BudgetForecast.get_budget_utilization(fiscal_year=2025)

        self.assertEqual(result['total_budgeted'], Decimal('50000'))
        self.assertEqual(result['total_actual'], Decimal('35000'))
        self.assertEqual(result['overall_utilization'], Decimal('70'))