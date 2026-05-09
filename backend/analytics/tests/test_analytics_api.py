"""
Tests for Analytics API endpoints.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse


class TestAnalyticsAPIEndpoints(TestCase):
    """Test analytics API endpoint availability and response structure."""

    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

    def _data(self, response):
        return response.json().get('data', {}).get('data', response.json().get('data', {}))

    def test_cost_centers_endpoint(self):
        """Test cost centers endpoint returns valid response."""
        response = self.client.get('/api/analytics/cost-centers/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('cost_centers', data)
        self.assertIn('period', data)

    def test_cash_flow_endpoint(self):
        """Test cash flow endpoint returns valid response."""
        response = self.client.get('/api/analytics/cash-flow/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('period', data)
        self.assertIn('operating_activities', data)

    def test_cash_position_endpoint(self):
        """Test cash position endpoint returns valid response."""
        response = self.client.get('/api/analytics/cash-position/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('as_of_date', data)
        self.assertIn('total_cash', data)

    def test_profitability_products_endpoint(self):
        """Test profitability products endpoint returns valid response."""
        response = self.client.get('/api/analytics/profitability/products/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('products', data)

    def test_profitability_customers_endpoint(self):
        """Test profitability customers endpoint returns valid response."""
        response = self.client.get('/api/analytics/profitability/customers/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('customers', data)

    def test_kpis_endpoint(self):
        """Test KPIs summary endpoint returns valid response."""
        response = self.client.get('/api/analytics/kpi/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('period', data)
        self.assertIn('profitability', data)
        self.assertIn('efficiency', data)

    def test_kpi_gross_margin_endpoint(self):
        """Test gross margin KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/gross-margin/')
        self.assertEqual(response.status_code, 200)

    def test_kpi_net_margin_endpoint(self):
        """Test net margin KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/net-margin/')
        self.assertEqual(response.status_code, 200)

    def test_kpi_inventory_turnover_endpoint(self):
        """Test inventory turnover KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/inventory-turnover/')
        self.assertEqual(response.status_code, 200)

    def test_kpi_cash_conversion_cycle_endpoint(self):
        """Test cash conversion cycle KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/cash-conversion-cycle/')
        self.assertEqual(response.status_code, 200)

    def test_kpi_sales_velocity_endpoint(self):
        """Test sales velocity KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/sales-velocity/')
        self.assertEqual(response.status_code, 200)

    def test_kpi_expiry_risk_endpoint(self):
        """Test expiry risk KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/expiry-risk/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_executive_endpoint(self):
        """Test executive dashboard endpoint."""
        response = self.client.get('/api/analytics/dashboard/executive/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('financial', data)
        self.assertIn('counts', data)
        self.assertIn('alerts', data)

    def test_dashboard_sales_endpoint(self):
        """Test sales dashboard endpoint."""
        response = self.client.get('/api/analytics/dashboard/sales/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('summary', data)

    def test_dashboard_inventory_endpoint(self):
        """Test inventory dashboard endpoint."""
        response = self.client.get('/api/analytics/dashboard/inventory/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('summary', data)

    def test_dashboard_financial_endpoint(self):
        """Test financial dashboard endpoint."""
        response = self.client.get('/api/analytics/dashboard/financial/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('performance', data)

    def test_dashboard_hr_endpoint(self):
        """Test HR dashboard endpoint."""
        response = self.client.get('/api/analytics/dashboard/hr/')
        self.assertEqual(response.status_code, 200)

    def test_report_cost_center_endpoint(self):
        """Test cost center report endpoint."""
        response = self.client.get('/api/analytics/reports/cost-center/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)

    def test_report_cash_flow_endpoint(self):
        """Test cash flow report endpoint."""
        response = self.client.get('/api/analytics/reports/cash-flow/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)

    def test_report_profitability_endpoint(self):
        """Test profitability report endpoint."""
        response = self.client.get('/api/analytics/reports/profitability/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)

    def test_report_kpi_endpoint(self):
        """Test KPI report endpoint."""
        response = self.client.get('/api/analytics/reports/kpi/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)

    def test_report_inventory_endpoint(self):
        """Test inventory report endpoint."""
        response = self.client.get('/api/analytics/reports/inventory/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)

    def test_report_sales_endpoint(self):
        """Test sales report endpoint."""
        response = self.client.get('/api/analytics/reports/sales/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)

    def test_report_comprehensive_endpoint(self):
        """Test comprehensive report endpoint."""
        response = self.client.get('/api/analytics/reports/comprehensive/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('report_type', data)
        self.assertIn('sections', data)

    def test_date_filtering(self):
        """Test that date query params are accepted."""
        today = date.today()
        start = today - timedelta(days=60)
        response = self.client.get(
            f'/api/analytics/cost-centers/?start_date={start}&end_date={today}'
        )
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertEqual(data['period']['start_date'], str(start))

    def test_csv_export_cost_center(self):
        """Test CSV export for cost center report."""
        response = self.client.get('/api/analytics/reports/cost-center/?export=true&file_type=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_text_export_kpi(self):
        """Test text export for KPI report."""
        response = self.client.get('/api/analytics/reports/kpi/?export=true&file_type=text')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')

    def test_cash_flow_daily(self):
        """Test daily cash flow endpoint."""
        response = self.client.get('/api/analytics/cash-flow/daily/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('daily_cash_flow', data)

    def test_cash_flow_monthly(self):
        """Test monthly cash flow endpoint."""
        response = self.client.get('/api/analytics/cash-flow/monthly/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('monthly_cash_flow', data)

    def test_kpi_product_performance(self):
        """Test product performance KPI endpoint."""
        response = self.client.get('/api/analytics/kpi/product-performance/')
        self.assertEqual(response.status_code, 200)
        data = self._data(response)
        self.assertIn('products', data)
