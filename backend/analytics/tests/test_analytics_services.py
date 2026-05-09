"""
Tests for Analytics Services.
Tests Cost Center, Cash Flow, Profitability, KPI, Dashboard, and Report engines.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Product, Category, Warehouse, Batch, Unit
from sales.models import Customer, SalesInvoice, SalesItem
from purchases.models import Supplier, PurchaseInvoice, PurchaseItem

from analytics.services.costing import CostCenter, CostAllocationEngine, CostAggregator
from analytics.services.cashflow import CashFlowCategory, CashFlowStatementGenerator
from analytics.services.profitability import (
    ProductProfitabilityAnalyzer,
    CustomerProfitabilityAnalyzer,
    SupplierProfitabilityAnalyzer,
    WarehouseProfitabilityAnalyzer,
)
from analytics.services.kpi import KPICalculator
from analytics.services.dashboard import DashboardAggregator
from analytics.services.reports import ReportGenerator


class TestCostCenter(TestCase):
    """Test cost center definitions."""

    def test_cost_centers_defined(self):
        """Verify all expected cost centers are defined."""
        self.assertIn('CC_PHARMACY', CostCenter.COST_CENTERS)
        self.assertIn('CC_WHOLESALE', CostCenter.COST_CENTERS)
        self.assertIn('CC_ADMIN', CostCenter.COST_CENTERS)
        self.assertIn('CC_WAREHOUSE', CostCenter.COST_CENTERS)
        self.assertIn('CC_SALES', CostCenter.COST_CENTERS)

    def test_cost_center_has_required_fields(self):
        """Verify each cost center has name and accounts."""
        for cc_code, cc_config in CostCenter.COST_CENTERS.items():
            self.assertIn('name', cc_config)
            self.assertIn('accounts', cc_config)
            self.assertIsInstance(cc_config['accounts'], list)


class TestCostAllocationEngine(TestCase):
    """Test cost allocation calculations."""

    def test_allocate_by_percentage(self):
        """Test percentage-based allocation."""
        result = CostAllocationEngine.allocate_by_percentage(
            Decimal('1000'),
            {'CC_A': Decimal('60'), 'CC_B': Decimal('40')}
        )
        self.assertEqual(result['CC_A'], Decimal('600.00'))
        self.assertEqual(result['CC_B'], Decimal('400.00'))

    def test_allocate_by_quantity(self):
        """Test quantity-based allocation."""
        result = CostAllocationEngine.allocate_by_quantity(
            Decimal('1000'),
            {'CC_A': 3, 'CC_B': 2}
        )
        self.assertEqual(result['CC_A'], Decimal('600.00'))
        self.assertEqual(result['CC_B'], Decimal('400.00'))

    def test_allocate_by_quantity_zero(self):
        """Test allocation with zero quantities."""
        result = CostAllocationEngine.allocate_by_quantity(
            Decimal('1000'),
            {'CC_A': 0, 'CC_B': 0}
        )
        self.assertEqual(result['CC_A'], Decimal('0'))
        self.assertEqual(result['CC_B'], Decimal('0'))

    def test_allocate_fixed_split(self):
        """Test fixed amount allocation."""
        result = CostAllocationEngine.allocate_fixed_split(
            Decimal('1000'),
            {'CC_A': Decimal('600'), 'CC_B': Decimal('400')}
        )
        self.assertEqual(result['CC_A'], Decimal('600'))
        self.assertEqual(result['CC_B'], Decimal('400'))

    def test_allocate_fixed_split_with_remainder(self):
        """Test fixed allocation with remainder distribution."""
        result = CostAllocationEngine.allocate_fixed_split(
            Decimal('1200'),
            {'CC_A': Decimal('500'), 'CC_B': Decimal('500')}
        )
        total = result['CC_A'] + result['CC_B']
        self.assertAlmostEqual(total, Decimal('1200'), places=2)


class TestCashFlowCategory(TestCase):
    """Test cash flow classification."""

    def test_classify_operating(self):
        """Test operating account classification."""
        self.assertEqual(CashFlowCategory.classify_account('1000'), 'OPERATING')
        self.assertEqual(CashFlowCategory.classify_account('5000'), 'OPERATING')

    def test_classify_investing(self):
        """Test investing account classification."""
        self.assertEqual(CashFlowCategory.classify_account('1500'), 'INVESTING')
        self.assertEqual(CashFlowCategory.classify_account('1600'), 'INVESTING')

    def test_classify_financing(self):
        """Test financing account classification."""
        self.assertEqual(CashFlowCategory.classify_account('3000'), 'FINANCING')
        self.assertEqual(CashFlowCategory.classify_account('4000'), 'FINANCING')

    def test_classify_default(self):
        """Test default classification."""
        self.assertEqual(CashFlowCategory.classify_account('9999'), 'OPERATING')


class TestProductProfitabilityAnalyzer(TestCase):
    """Test product profitability analysis."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name='Test Category',
            description='Test'
        )
        self.unit = Unit.objects.create(
            name='Box',
            symbol='box',
            description='Test unit'
        )
        self.product = Product.objects.create(
            name='Test Product',
            generic_name='Test Generic',
            brand_name='Test Brand',
            category=self.category,
            unit=self.unit,
            strength='100mg',
            form='Tablet',
            manufacturer='Test Mfg',
            barcode='1234567890',
            sku='TP001',
            is_active=True
        )
        self.customer = Customer.objects.create(
            name='Test Customer',
            code='TC001',
            phone='123456'
        )
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='TS001',
            contact_person='John',
            phone='123456'
        )

    def test_analyze_product_no_data(self):
        """Test analysis with no sales data."""
        result = ProductProfitabilityAnalyzer.analyze_product(str(self.product.id))
        self.assertEqual(result['product_id'], str(self.product.id))
        self.assertEqual(result['revenue']['gross_revenue'], Decimal('0'))

    def test_get_top_products_empty(self):
        """Test top products with no data."""
        result = ProductProfitabilityAnalyzer.get_top_products()
        self.assertIsInstance(result, list)


class TestCustomerProfitabilityAnalyzer(TestCase):
    """Test customer profitability analysis."""

    def setUp(self):
        """Set up test data."""
        self.customer = Customer.objects.create(
            name='Test Customer',
            code='TC001',
            phone='123456'
        )

    def test_analyze_customer_no_data(self):
        """Test analysis with no invoice data."""
        result = CustomerProfitabilityAnalyzer.analyze_customer(str(self.customer.id))
        self.assertEqual(result['customer_id'], str(self.customer.id))
        self.assertEqual(result['revenue']['gross_revenue'], Decimal('0'))

    def test_get_top_customers_empty(self):
        """Test top customers with no data."""
        result = CustomerProfitabilityAnalyzer.get_top_customers()
        self.assertIsInstance(result, list)


class TestSupplierProfitabilityAnalyzer(TestCase):
    """Test supplier profitability analysis."""

    def setUp(self):
        """Set up test data."""
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='TS001',
            contact_person='John',
            phone='123456'
        )

    def test_analyze_supplier_no_data(self):
        """Test analysis with no purchase data."""
        result = SupplierProfitabilityAnalyzer.analyze_supplier(str(self.supplier.id))
        self.assertEqual(result['supplier_id'], str(self.supplier.id))
        self.assertEqual(result['costs']['gross_cost'], Decimal('0'))


class TestKPICalculator(TestCase):
    """Test KPI calculations."""

    def test_get_gross_margin_no_data(self):
        """Test gross margin with no data."""
        result = KPICalculator.get_gross_margin()
        self.assertEqual(result['gross_margin_pct'], Decimal('0'))

    def test_get_net_margin_no_data(self):
        """Test net margin with no data."""
        result = KPICalculator.get_net_margin()
        self.assertEqual(result['net_margin_pct'], Decimal('0'))

    def test_get_inventory_turnover_no_data(self):
        """Test inventory turnover with no data."""
        result = KPICalculator.get_inventory_turnover()
        self.assertEqual(result['inventory_turnover'], Decimal('0'))

    def test_get_sales_velocity_no_data(self):
        """Test sales velocity with no data."""
        result = KPICalculator.get_sales_velocity()
        self.assertEqual(result['total_revenue'], Decimal('0'))

    def test_get_all_kpis_summary(self):
        """Test comprehensive KPI summary."""
        result = KPICalculator.get_all_kpis_summary()
        self.assertIn('period', result)
        self.assertIn('profitability', result)
        self.assertIn('efficiency', result)
        self.assertIn('sales', result)
        self.assertIn('risk', result)

    def test_batch_expiry_risk_no_data(self):
        """Test batch expiry risk with no data."""
        result = KPICalculator.get_batch_expiry_risk()
        self.assertEqual(result['at_risk_batch_count'], 0)
        self.assertEqual(result['expired_batch_count'], 0)


class TestDashboardAggregator(TestCase):
    """Test dashboard aggregation."""

    def test_executive_summary(self):
        """Test executive summary dashboard."""
        result = DashboardAggregator.get_executive_summary()
        self.assertIn('financial', result)
        self.assertIn('counts', result)
        self.assertIn('alerts', result)

    def test_sales_dashboard(self):
        """Test sales dashboard."""
        result = DashboardAggregator.get_sales_dashboard()
        self.assertIn('summary', result)
        self.assertIn('daily_trend', result)
        self.assertIn('top_products', result)

    def test_inventory_dashboard(self):
        """Test inventory dashboard."""
        result = DashboardAggregator.get_inventory_dashboard()
        self.assertIn('summary', result)
        self.assertIn('alerts', result)
        self.assertIn('warehouse_distribution', result)

    def test_financial_dashboard(self):
        """Test financial dashboard."""
        result = DashboardAggregator.get_financial_dashboard()
        self.assertIn('performance', result)
        self.assertIn('position', result)
        self.assertIn('monthly_trend', result)

    def test_hr_dashboard(self):
        """Test HR dashboard (graceful fallback)."""
        result = DashboardAggregator.get_hr_dashboard()
        self.assertIn('summary', result)
        self.assertIn('attendance_today', result)


class TestReportGenerator(TestCase):
    """Test report generation."""

    def test_generate_cost_center_report_dict(self):
        """Test cost center report in dict format."""
        result = ReportGenerator.generate_cost_center_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'cost_center_summary')

    def test_generate_cost_center_report_csv(self):
        """Test cost center report in CSV format."""
        result = ReportGenerator.generate_cost_center_report(format='csv')
        self.assertIn('Cost Center', result)

    def test_generate_cost_center_report_text(self):
        """Test cost center report in text format."""
        result = ReportGenerator.generate_cost_center_report(format='text')
        self.assertIn('COST CENTER SUMMARY REPORT', result)

    def test_generate_cash_flow_report_dict(self):
        """Test cash flow report in dict format."""
        result = ReportGenerator.generate_cash_flow_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'cash_flow_statement')

    def test_generate_cash_flow_report_text(self):
        """Test cash flow report in text format."""
        result = ReportGenerator.generate_cash_flow_report(format='text')
        self.assertIn('CASH FLOW STATEMENT', result)

    def test_generate_profitability_report_dict(self):
        """Test profitability report in dict format."""
        result = ReportGenerator.generate_profitability_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'profitability_summary')

    def test_generate_profitability_report_csv(self):
        """Test profitability report in CSV format."""
        result = ReportGenerator.generate_profitability_report(format='csv')
        self.assertIn('PRODUCT PROFITABILITY', result)

    def test_generate_kpi_report_dict(self):
        """Test KPI report in dict format."""
        result = ReportGenerator.generate_kpi_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'kpi_summary')

    def test_generate_kpi_report_text(self):
        """Test KPI report in text format."""
        result = ReportGenerator.generate_kpi_report(format='text')
        self.assertIn('KEY PERFORMANCE INDICATORS', result)

    def test_generate_inventory_report_dict(self):
        """Test inventory report in dict format."""
        result = ReportGenerator.generate_inventory_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'inventory_status')

    def test_generate_inventory_report_csv(self):
        """Test inventory report in CSV format."""
        result = ReportGenerator.generate_inventory_report(format='csv')
        self.assertIn('Product', result)

    def test_generate_sales_report_dict(self):
        """Test sales report in dict format."""
        result = ReportGenerator.generate_sales_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'sales_analysis')

    def test_generate_sales_report_csv(self):
        """Test sales report in CSV format."""
        result = ReportGenerator.generate_sales_report(format='csv')
        self.assertIn('Invoice', result)

    def test_generate_comprehensive_report_dict(self):
        """Test comprehensive report in dict format."""
        result = ReportGenerator.generate_comprehensive_report(format='dict')
        self.assertIn('report_type', result)
        self.assertEqual(result['report_type'], 'comprehensive_analytics')
        self.assertIn('sections', result)
        self.assertIn('cash_flow', result['sections'])
        self.assertIn('profitability', result['sections'])
        self.assertIn('kpi', result['sections'])

    def test_generate_comprehensive_report_text(self):
        """Test comprehensive report in text format."""
        result = ReportGenerator.generate_comprehensive_report(format='text')
        self.assertIn('COMPREHENSIVE ANALYTICS REPORT', result)

    def test_generate_comprehensive_report_csv(self):
        """Test comprehensive report in CSV format."""
        result = ReportGenerator.generate_comprehensive_report(format='csv')
        self.assertIsInstance(result, str)
