"""
Analytics API Views.
Provides read-only endpoints for cost centers, cash flow, profitability, KPIs, dashboards, and reports.

All responses follow standardized format:
{
  "success": true/false,
  "data": {...},
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "company_id": "uuid"
  }
}
SECURITY NOTE: All endpoints require authentication for data access.
Public access is intentionally limited to prevent business data leakage.
"""
from datetime import date, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse

from core.api.responses import APIResponse
from core.api.errors import create_error_response, ErrorCode, get_status_for_error
from core.multitenant.context import TenantContext

from analytics.services.costing import CostCenter, CostAggregator
from analytics.services.cashflow import CashFlowStatementGenerator
from analytics.services.profitability import (
    ProductProfitabilityAnalyzer,
    CustomerProfitabilityAnalyzer,
    SupplierProfitabilityAnalyzer,
    WarehouseProfitabilityAnalyzer,
)
from analytics.services.kpi import KPICalculator
from analytics.services.dashboard import DashboardAggregator
from analytics.services.reports import ReportGenerator


def parse_dates(request):
    """Extract start_date and end_date from request query params."""
    end_str = request.query_params.get('end_date')
    start_str = request.query_params.get('start_date')

    try:
        end_date = date.fromisoformat(end_str) if end_str else date.today()
    except ValueError:
        end_date = date.today()

    try:
        start_date_val = date.fromisoformat(start_str) if start_str else end_date - timedelta(days=30)
    except ValueError:
        start_date_val = end_date - timedelta(days=30)

    return start_date_val, end_date


def get_company_id():
    """Get current company ID from context."""
    return TenantContext.get_company_id()


class AnalyticsViewSet(viewsets.ViewSet):
    """
    Read-only analytics API.
    All endpoints return computed data from existing transactional records.

    SECURITY: All endpoints require authentication to protect business data.
    Company context is enforced to ensure tenant isolation.

    All responses use standardized format with company context.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='cost-centers')
    def cost_centers(self, request):
        """Get all cost centers with expense summaries."""
        try:
            start_date, end_date = parse_dates(request)
            data = CostAggregator.get_all_cost_centers_summary(start_date, end_date)
            return Response(APIResponse.success(
                data={'cost_centers': data, 'period': {'start_date': str(start_date), 'end_date': str(end_date)}},
                company_id=get_company_id()
            ))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='cost-centers/(?P<code>[^/.]+)')
    def cost_center_detail(self, request, code=None):
        """Get detailed expenses for a specific cost center."""
        try:
            start_date, end_date = parse_dates(request)
            data = CostAggregator.get_cost_center_expenses(code, start_date, end_date)
            if 'error' in data:
                return Response(
                    create_error_response(ErrorCode.FIN_003, data['error']),
                    status=404
                )
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='cost-centers/trend/(?P<code>[^/.]+)')
    def cost_center_trend(self, request, code=None):
        """Get monthly cost trend for a cost center."""
        try:
            months = int(request.query_params.get('months', 12))
            data = CostAggregator.get_monthly_cost_trend(code, months)
            return Response(APIResponse.success(
                data={'cost_center': code, 'trend': data},
                company_id=get_company_id()
            ))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='cash-flow')
    def cash_flow(self, request):
        """Generate cash flow statement."""
        try:
            start_date, end_date = parse_dates(request)
            comparison = request.query_params.get('comparison', 'false') == 'true'
            data = CashFlowStatementGenerator.generate_statement(start_date, end_date, comparison)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='cash-flow/daily')
    def cash_flow_daily(self, request):
        """Get daily cash flow aggregation."""
        try:
            start_date, end_date = parse_dates(request)
            data = CashFlowStatementGenerator.get_daily_cash_flow(start_date, end_date)
            return Response(APIResponse.success(data={'daily_cash_flow': data}, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='cash-flow/monthly')
    def cash_flow_monthly(self, request):
        """Get monthly cash flow aggregation."""
        try:
            start_date, end_date = parse_dates(request)
            data = CashFlowStatementGenerator.get_monthly_cash_flow(start_date, end_date)
            return Response(APIResponse.success(data={'monthly_cash_flow': data}, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='cash-position')
    def cash_position(self, request):
        """Get current cash position."""
        try:
            as_of_str = request.query_params.get('as_of_date')
            as_of_date = date.fromisoformat(as_of_str) if as_of_str else date.today()
            data = CashFlowStatementGenerator.get_cash_position(as_of_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='profitability/products')
    def profitability_products(self, request):
        """Get top products by profitability."""
        try:
            start_date, end_date = parse_dates(request)
            limit = int(request.query_params.get('limit', 10))
            sort_by = request.query_params.get('sort_by', 'gross_profit')
            data = ProductProfitabilityAnalyzer.get_top_products(limit, start_date, end_date, sort_by)
            return Response(APIResponse.success(
                data={'products': data},
                company_id=get_company_id()
            ))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='profitability/products/(?P<product_id>[^/.]+)')
    def profitability_product_detail(self, request, product_id=None):
        """Get detailed profitability for a product."""
        try:
            start_date, end_date = parse_dates(request)
            data = ProductProfitabilityAnalyzer.analyze_product(product_id, start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.INV_003, str(e)),
                status=get_status_for_error(ErrorCode.INV_003)
            )

    @action(detail=False, methods=['get'], url_path='profitability/customers')
    def profitability_customers(self, request):
        """Get top customers by revenue."""
        try:
            start_date, end_date = parse_dates(request)
            limit = int(request.query_params.get('limit', 10))
            data = CustomerProfitabilityAnalyzer.get_top_customers(limit, start_date, end_date)
            return Response(APIResponse.success(data={'customers': data}, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='profitability/customers/(?P<customer_id>[^/.]+)')
    def profitability_customer_detail(self, request, customer_id=None):
        """Get detailed profitability for a customer."""
        try:
            start_date, end_date = parse_dates(request)
            data = CustomerProfitabilityAnalyzer.analyze_customer(customer_id, start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SAL_001, str(e)),
                status=get_status_for_error(ErrorCode.SAL_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi')
    def kpis(self, request):
        """Get all KPIs summary."""
        try:
            start_date, end_date = parse_dates(request)
            data = KPICalculator.get_all_kpis_summary(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/gross-margin')
    def kpi_gross_margin(self, request):
        """Get gross margin KPI."""
        try:
            start_date, end_date = parse_dates(request)
            data = KPICalculator.get_gross_margin(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/net-margin')
    def kpi_net_margin(self, request):
        """Get net margin KPI."""
        try:
            start_date, end_date = parse_dates(request)
            data = KPICalculator.get_net_margin(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/inventory-turnover')
    def kpi_inventory_turnover(self, request):
        """Get inventory turnover KPI."""
        try:
            start_date, end_date = parse_dates(request)
            data = KPICalculator.get_inventory_turnover(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/cash-conversion-cycle')
    def kpi_cash_conversion_cycle(self, request):
        """Get cash conversion cycle KPI."""
        try:
            start_date, end_date = parse_dates(request)
            data = KPICalculator.get_cash_conversion_cycle(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/sales-velocity')
    def kpi_sales_velocity(self, request):
        """Get sales velocity KPI."""
        try:
            days = int(request.query_params.get('days', 30))
            data = KPICalculator.get_sales_velocity(days)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/expiry-risk')
    def kpi_expiry_risk(self, request):
        """Get batch expiry risk KPI."""
        try:
            days = int(request.query_params.get('days', 90))
            data = KPICalculator.get_batch_expiry_risk(days)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='kpi/product-performance')
    def kpi_product_performance(self, request):
        """Get product performance ranking."""
        try:
            limit = int(request.query_params.get('limit', 10))
            days = int(request.query_params.get('days', 30))
            data = KPICalculator.get_product_performance(limit, days)
            return Response(APIResponse.success(data={'products': data}, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='profitability/suppliers/(?P<supplier_id>[^/.]+)')
    def profitability_supplier_detail(self, request, supplier_id=None):
        """Get detailed cost efficiency for a supplier."""
        try:
            start_date, end_date = parse_dates(request)
            data = SupplierProfitabilityAnalyzer.analyze_supplier(supplier_id, start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='profitability/warehouses/(?P<warehouse_id>[^/.]+)')
    def profitability_warehouse_detail(self, request, warehouse_id=None):
        """Get detailed profitability for a warehouse."""
        try:
            start_date, end_date = parse_dates(request)
            data = WarehouseProfitabilityAnalyzer.analyze_warehouse(warehouse_id, start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='dashboard/executive')
    def dashboard_executive(self, request):
        """Get executive summary dashboard."""
        try:
            as_of_str = request.query_params.get('as_of_date')
            as_of_date = date.fromisoformat(as_of_str) if as_of_str else date.today()
            data = DashboardAggregator.get_executive_summary(as_of_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='dashboard/sales')
    def dashboard_sales(self, request):
        """Get sales dashboard."""
        try:
            start_date, end_date = parse_dates(request)
            data = DashboardAggregator.get_sales_dashboard(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='dashboard/inventory')
    def dashboard_inventory(self, request):
        """Get inventory dashboard."""
        try:
            as_of_str = request.query_params.get('as_of_date')
            as_of_date = date.fromisoformat(as_of_str) if as_of_str else date.today()
            data = DashboardAggregator.get_inventory_dashboard(as_of_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='dashboard/financial')
    def dashboard_financial(self, request):
        """Get financial dashboard."""
        try:
            start_date, end_date = parse_dates(request)
            data = DashboardAggregator.get_financial_dashboard(start_date, end_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='dashboard/hr')
    def dashboard_hr(self, request):
        """Get HR dashboard."""
        try:
            as_of_str = request.query_params.get('as_of_date')
            as_of_date = date.fromisoformat(as_of_str) if as_of_str else date.today()
            data = DashboardAggregator.get_hr_dashboard(as_of_date)
            return Response(APIResponse.success(data=data, company_id=get_company_id()))
        except Exception as e:
            return Response(
                create_error_response(ErrorCode.SYS_001, str(e)),
                status=get_status_for_error(ErrorCode.SYS_001)
            )

    @action(detail=False, methods=['get'], url_path='reports/cost-center')
    def report_cost_center(self, request):
        """Generate cost center report."""
        start_date, end_date = parse_dates(request)
        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'csv': 'csv', 'text': 'text'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_cost_center_report(start_date, end_date, report_fmt)

            if file_type == 'csv':
                return HttpResponse(data, content_type='text/csv')
            elif file_type == 'text':
                return HttpResponse(data, content_type='text/plain')

        data = ReportGenerator.generate_cost_center_report(start_date, end_date, 'dict')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reports/cash-flow')
    def report_cash_flow(self, request):
        """Generate cash flow report."""
        start_date, end_date = parse_dates(request)
        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'text': 'text'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_cash_flow_report(start_date, end_date, report_fmt)

            if file_type == 'text':
                return HttpResponse(data, content_type='text/plain')

        data = ReportGenerator.generate_cash_flow_report(start_date, end_date, 'dict')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reports/profitability')
    def report_profitability(self, request):
        """Generate profitability report."""
        start_date, end_date = parse_dates(request)
        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'csv': 'csv'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_profitability_report(start_date, end_date, report_fmt)

            if file_type == 'csv':
                return HttpResponse(data, content_type='text/csv')

        data = ReportGenerator.generate_profitability_report(start_date, end_date, 'dict')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reports/kpi')
    def report_kpi(self, request):
        """Generate KPI report."""
        start_date, end_date = parse_dates(request)
        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'text': 'text'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_kpi_report(start_date, end_date, report_fmt)

            if file_type == 'text':
                return HttpResponse(data, content_type='text/plain')

        data = ReportGenerator.generate_kpi_report(start_date, end_date, 'dict')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reports/inventory')
    def report_inventory(self, request):
        """Generate inventory report."""
        as_of_str = request.query_params.get('as_of_date')
        try:
            as_of_date = date.fromisoformat(as_of_str) if as_of_str else date.today()
        except ValueError:
            as_of_date = date.today()

        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'csv': 'csv'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_inventory_report(as_of_date, report_fmt)

            if file_type == 'csv':
                return HttpResponse(data, content_type='text/csv')

        data = ReportGenerator.generate_inventory_report(as_of_date, 'dict')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reports/sales')
    def report_sales(self, request):
        """Generate sales report."""
        start_date, end_date = parse_dates(request)
        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'csv': 'csv'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_sales_report(start_date, end_date, report_fmt)

            if file_type == 'csv':
                return HttpResponse(data, content_type='text/csv')

        data = ReportGenerator.generate_sales_report(start_date, end_date, 'dict')
        return Response(data)

    @action(detail=False, methods=['get'], url_path='reports/comprehensive')
    def report_comprehensive(self, request):
        """Generate comprehensive analytics report."""
        start_date, end_date = parse_dates(request)
        file_type = request.query_params.get('file_type', 'json')
        export = request.query_params.get('export', 'false') == 'true'

        if export:
            type_map = {'csv': 'csv', 'text': 'text'}
            report_fmt = type_map.get(file_type, 'dict')
            data = ReportGenerator.generate_comprehensive_report(start_date, end_date, report_fmt)

            if file_type == 'csv':
                return HttpResponse(data, content_type='text/csv')
            elif file_type == 'text':
                return HttpResponse(data, content_type='text/plain')

        data = ReportGenerator.generate_comprehensive_report(start_date, end_date, 'dict')
        return Response(data)
