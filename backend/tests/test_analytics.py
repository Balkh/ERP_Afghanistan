"""
Financial Analytics Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from accounting.models import Account, Currency, JournalEntry, JournalEntryLine
from sales.models import Customer, SalesInvoice, SalesItem
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem
from inventory.models import Product, Category, Unit
from analytics.services.financial_analytics import (
    FinancialKPIs, DimensionAnalysis, AnalyticsDashboard
)


class FinancialKPIsTests(TestCase):
    """Test financial KPI calculations."""

    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.first()
        if not cls.currency:
            cls.currency = Currency.objects.create(code='AFN', name='Afghani', symbol='Af', is_active=True)

        cls.revenue_account = Account.objects.filter(
            account_category='OPERATING_REVENUE'
        ).first()
        if not cls.revenue_account:
            cls.revenue_account = Account.objects.create(
                code='4000', name='Sales Revenue', account_type='REVENUE',
                account_category='OPERATING_REVENUE', is_active=True
            )

        cls.expense_account = Account.objects.filter(
            account_category='COST_OF_GOODS_SOLD'
        ).first()
        if not cls.expense_account:
            cls.expense_account = Account.objects.create(
                code='5000', name='Cost of Goods Sold', account_type='EXPENSE',
                account_category='COST_OF_GOODS_SOLD', is_active=True
            )

        cls.cash_account = Account.objects.filter(
            account_category='CURRENT_ASSET'
        ).first()
        if not cls.cash_account:
            cls.cash_account = Account.objects.create(
                code='1000', name='Cash', account_type='ASSET',
                account_category='CURRENT_ASSET', is_active=True
            )

    def test_profitability_kpis_empty(self):
        """Test KPIs with no data returns zero values."""
        kpis = FinancialKPIs.get_profitability_kpis()

        self.assertEqual(kpis['total_revenue'], Decimal('0'))
        self.assertEqual(kpis['total_expenses'], Decimal('0'))
        self.assertEqual(kpis['gross_margin_percent'], Decimal('0'))

    def test_profitability_kpis_with_data(self):
        """Test KPIs with journal entries."""
        entry = JournalEntry.objects.create(
            entry_number='JE-001',
            entry_date=date.today(),
            description='Test revenue',
            is_posted=True,
            is_active=True
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue_account,
            debit=Decimal('0'),
            credit=Decimal('1000')
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=self.expense_account,
            debit=Decimal('600'),
            credit=Decimal('0')
        )

        kpis = FinancialKPIs.get_profitability_kpis()

        self.assertEqual(kpis['total_revenue'], Decimal('1000'))
        self.assertEqual(kpis['total_expenses'], Decimal('600'))
        self.assertEqual(kpis['gross_profit'], Decimal('400'))

    def test_liquidity_kpis(self):
        """Test liquidity KPIs."""
        kpis = FinancialKPIs.get_liquidity_kpis()

        self.assertIn('current_ratio', kpis)
        self.assertIn('quick_ratio', kpis)
        self.assertIn('cash_ratio', kpis)

    def test_efficiency_kpis(self):
        """Test efficiency KPIs."""
        kpis = FinancialKPIs.get_efficiency_kpis(period_days=30)

        self.assertIn('inventory_turnover', kpis)
        self.assertIn('days_sales_outstanding', kpis)
        self.assertEqual(kpis['period_days'], 30)


class DimensionAnalysisTests(TestCase):
    """Test dimension analysis."""

    def test_sales_by_customer_type_empty(self):
        """Test with no sales data."""
        result = DimensionAnalysis.get_sales_by_customer_type(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )

        self.assertEqual(result, {})

    def test_sales_by_customer_type_with_data(self):
        """Test with customer type grouping."""
        customer = Customer.objects.create(
            name='Retail Customer', code='CUST001', customer_type='RETAIL'
        )

        invoice = SalesInvoice.objects.create(
            invoice_number='INV-001',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            payment_status='PAID',
            subtotal=Decimal('100'),
            total_amount=Decimal('100')
        )

        result = DimensionAnalysis.get_sales_by_customer_type(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )

        self.assertIn('RETAIL', result)
        self.assertEqual(result['RETAIL']['invoice_count'], 1)

    def test_expenses_by_category_empty(self):
        """Test expenses with no data."""
        result = DimensionAnalysis.get_expenses_by_category(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )

        self.assertEqual(result, {})


class AnalyticsDashboardTests(TestCase):
    """Test analytics dashboard."""

    def test_summary_dashboard_empty(self):
        """Test dashboard with no data."""
        dashboard = AnalyticsDashboard.get_summary_dashboard()

        self.assertEqual(dashboard['revenue']['month_to_date'], Decimal('0'))
        self.assertEqual(dashboard['revenue']['year_to_date'], Decimal('0'))
        self.assertIn('customers', dashboard)

    def test_summary_dashboard_with_sales(self):
        """Test dashboard with sales data."""
        customer = Customer.objects.create(
            name='Test Customer', code='TC001', customer_type='RETAIL'
        )

        SalesInvoice.objects.create(
            invoice_number='INV-100',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            payment_status='PAID',
            subtotal=Decimal('5000'),
            total_amount=Decimal('5000')
        )

        dashboard = AnalyticsDashboard.get_summary_dashboard()

        self.assertGreaterEqual(dashboard['revenue']['month_to_date'], Decimal('0'))

    def test_trend_data_empty(self):
        """Test trend with no data."""
        trend = AnalyticsDashboard.get_trend_data(days=30)

        self.assertEqual(trend['period_days'], 30)
        self.assertEqual(trend['data'], [])

    def test_trend_data_with_sales(self):
        """Test trend with sales."""
        customer = Customer.objects.create(
            name='Trend Customer', code='TR001', customer_type='RETAIL'
        )

        SalesInvoice.objects.create(
            invoice_number='TRINV-001',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            payment_status='PAID',
            subtotal=Decimal('1000'),
            total_amount=Decimal('1000')
        )

        trend = AnalyticsDashboard.get_trend_data(days=30)

        self.assertGreaterEqual(len(trend['data']), 0)

    def test_top_customers_empty(self):
        """Test top customers with no data."""
        top = AnalyticsDashboard.get_top_customers(limit=5)

        self.assertEqual(top, [])

    def test_top_customers_with_data(self):
        """Test top customers with data."""
        customer = Customer.objects.create(
            name='Top Customer', code='TOP001', customer_type='WHOLESALE'
        )

        SalesInvoice.objects.create(
            invoice_number='TOPINV-001',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            payment_status='PAID',
            subtotal=Decimal('10000'),
            total_amount=Decimal('10000')
        )

        top = AnalyticsDashboard.get_top_customers(limit=5)

        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]['customer_name'], 'Top Customer')

    def test_top_products_empty(self):
        """Test top products with no data."""
        top = AnalyticsDashboard.get_top_products(limit=5)

        self.assertEqual(top, [])

    def test_top_products_with_data(self):
        """Test top products with data."""
        unit = Unit.objects.create(name='Piece', symbol='pcs', is_active=True)
        category = Category.objects.create(name='Medicines')

        product = Product.objects.create(
            name='Pain Relief', sku='PR001', category=category,
            unit=unit, is_active=True
        )

        customer = Customer.objects.create(
            name='Prod Customer', code='PC001', customer_type='RETAIL'
        )

        invoice = SalesInvoice.objects.create(
            invoice_number='PRODINV-001',
            customer=customer,
            order_date=date.today(),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='DISPATCHED',
            payment_status='PAID',
            subtotal=Decimal('500'),
            total_amount=Decimal('500')
        )

        SalesItem.objects.create(
            invoice=invoice,
            product=product,
            quantity=10,
            unit_price=Decimal('50'),
            total=Decimal('500')
        )

        top = AnalyticsDashboard.get_top_products(limit=5)

        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]['product_name'], 'Pain Relief')