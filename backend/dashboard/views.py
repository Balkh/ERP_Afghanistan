from datetime import date, timedelta
from decimal import Decimal
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum

from dashboard.models import DashboardWidgetConfig, DashboardAlert
from dashboard.serializers import (
    DashboardWidgetConfigSerializer,
    DashboardAlertSerializer,
    KPIOverviewSerializer,
    WidgetDataSerializer
)
from dashboard.services.dashboard_service import DashboardService, DashboardAlertService
from dashboard.services.widget_service import WidgetService
from dashboard.services.drilldown_engine import DrillDownEngine
from security.permissions import RoleBasedPermission


class DashboardWidgetConfigViewSet(viewsets.ModelViewSet):
    """CRUD for widget configurations."""
    queryset = DashboardWidgetConfig.objects.all()
    serializer_class = DashboardWidgetConfigSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'widget_type', 'is_visible']

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_layout(self, request):
        """Get user's dashboard layout."""
        configs = self.get_queryset().filter(is_visible=True).order_by('position')
        return Response(DashboardWidgetConfigSerializer(configs, many=True).data)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder widgets."""
        widget_ids = request.data.get('widget_ids', [])
        for idx, widget_id in enumerate(widget_ids):
            DashboardWidgetConfig.objects.filter(
                id=widget_id, user=request.user
            ).update(position=idx)
        return Response({'status': 'reordered'})


class DashboardAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only alerts."""
    queryset = DashboardAlert.objects.filter(is_active=True)
    serializer_class = DashboardAlertSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['severity', 'category', 'is_acknowledged']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'])
    def acknowledge(self, request):
        """Acknowledge an alert."""
        alert_id = request.data.get('alert_id')
        try:
            alert = DashboardAlert.objects.get(id=alert_id)
            alert.is_acknowledged = True
            alert.acknowledged_by = request.user
            alert.save()
            return Response({'status': 'acknowledged'})
        except DashboardAlert.DoesNotExist:
            return Response({'error': 'Alert not found'}, status=404)

    @action(detail=False, methods=['get'])
    def active_count(self, request):
        """Get active alert counts by severity."""
        counts = DashboardAlert.objects.filter(
            is_active=True, is_acknowledged=False
        ).values('severity').annotate(count=Sum('id'))

        result = {'INFO': 0, 'WARNING': 0, 'CRITICAL': 0}
        for item in counts:
            result[item['severity']] = DashboardAlert.objects.filter(
                is_active=True, is_acknowledged=False, severity=item['severity']
            ).count()

        return Response(result)


class DashboardKPIController(viewsets.ViewSet):
    """Central controller for all KPI data."""

    permission_classes = [RoleBasedPermission]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get all KPI overview cards."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')

        if start_param and end_param:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)

        kpis = DashboardService.get_kpi_summary(start_date, end_date)

        kpis['gross_margin'] = DashboardService.get_gross_margin()
        kpis['dso'] = DashboardService.get_dso()
        kpis['dpo'] = DashboardService.get_dpo()
        kpis['current_ratio'] = DashboardService.get_current_ratio()
        kpis['quick_ratio'] = DashboardService.get_quick_ratio()

        return Response(kpis)

    @action(detail=False, methods=['get'])
    def today_counters(self, request):
        """Get today's transaction counters."""
        return Response(DashboardService.get_today_counters())

    @action(detail=False, methods=['get'])
    def sales_kpis(self, request):
        """Get sales-specific KPIs."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')

        if start_param and end_param:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)

        return Response(DashboardService.get_sales_kpis(start_date, end_date))

    @action(detail=False, methods=['get'])
    def purchase_kpis(self, request):
        """Get purchase-specific KPIs."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')

        if start_param and end_param:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)

        return Response(DashboardService.get_purchase_kpis(start_date, end_date))

    @action(detail=False, methods=['get'])
    def inventory_kpis(self, request):
        """Get inventory-specific KPIs."""
        return Response(DashboardService.get_inventory_kpis())

    @action(detail=False, methods=['get'])
    def budget_variance(self, request):
        """Get budget variance summary."""
        fiscal_year = int(request.query_params.get('year', date.today().year))
        return Response(DashboardService.get_budget_variance_summary(fiscal_year))

    @action(detail=False, methods=['get'])
    def cost_center_perf(self, request):
        """Get cost center performance."""
        return Response(DashboardService.get_cost_center_performance())

    @action(detail=False, methods=['get'])
    def payment_summary(self, request):
        """Get payment summary."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')

        if start_param and end_param:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)

        return Response(DashboardService.get_payment_summary(start_date, end_date))

    @action(detail=False, methods=['get'])
    def payroll_summary(self, request):
        """Get payroll cost summary."""
        year = int(request.query_params.get('year', date.today().year))
        return Response(DashboardService.get_payroll_cost_summary(year))

    @action(detail=False, methods=['get'])
    def asset_summary(self, request):
        """Get asset summary."""
        return Response(DashboardService.get_asset_summary())

    @action(detail=False, methods=['get'])
    def tax_liability(self, request):
        """Get tax liability."""
        return Response(DashboardService.get_tax_liability_summary())


class DashboardWidgetController(viewsets.ViewSet):
    """Controller for individual widget data."""

    permission_classes = [RoleBasedPermission]

    @action(detail=False, methods=['get'])
    def revenue_trend(self, request):
        """Revenue trend widget."""
        months = int(request.query_params.get('months', 12))
        return Response(WidgetService.get_revenue_trend(months))

    @action(detail=False, methods=['get'])
    def profit_trend(self, request):
        """Profit trend widget."""
        months = int(request.query_params.get('months', 12))
        return Response(WidgetService.get_profit_trend(months))

    @action(detail=False, methods=['get'])
    def expense_breakdown(self, request):
        """Expense breakdown widget."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')

        if start_param and end_param:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)

        return Response(WidgetService.get_expense_breakdown(start_date, end_date))

    @action(detail=False, methods=['get'])
    def cash_flow_summary(self, request):
        """Cash flow summary widget."""
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')

        if start_param and end_param:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)

        return Response(WidgetService.get_cash_flow_summary(start_date, end_date))

    @action(detail=False, methods=['get'])
    def stock_value_warehouse(self, request):
        """Stock value by warehouse widget."""
        return Response(WidgetService.get_stock_value_by_warehouse())

    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Low stock alerts widget."""
        limit = int(request.query_params.get('limit', 10))
        return Response(WidgetService.get_low_stock_alerts(limit))

    @action(detail=False, methods=['get'])
    def expiry_risk(self, request):
        """Expiry risk widget."""
        limit = int(request.query_params.get('limit', 10))
        return Response(WidgetService.get_expiry_risk(limit))

    @action(detail=False, methods=['get'])
    def fast_moving_products(self, request):
        """Fast moving products widget."""
        limit = int(request.query_params.get('limit', 10))
        days = int(request.query_params.get('days', 30))
        return Response(WidgetService.get_fast_moving_products(limit, days))

    @action(detail=False, methods=['get'])
    def trial_balance_snapshot(self, request):
        """Trial balance snapshot widget."""
        as_of = request.query_params.get('as_of_date')
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
        return Response(WidgetService.get_trial_balance_snapshot(as_of_date))

    @action(detail=False, methods=['get'])
    def ledger_activity(self, request):
        """Ledger activity heatmap widget."""
        days = int(request.query_params.get('days', 30))
        return Response(WidgetService.get_ledger_activity(days))

    @action(detail=False, methods=['get'])
    def je_volume(self, request):
        """JE volume widget."""
        months = int(request.query_params.get('months', 6))
        return Response(WidgetService.get_je_volume(months))

    @action(detail=False, methods=['get'])
    def cost_center_perf_widget(self, request):
        """Cost center performance widget."""
        return Response(WidgetService.get_cost_center_performance())

    @action(detail=False, methods=['get'])
    def budget_variance_widget(self, request):
        """Budget variance widget."""
        year = int(request.query_params.get('year', date.today().year))
        return Response(WidgetService.get_budget_variance_widget(year))

    @action(detail=False, methods=['get'])
    def ar_aging_widget(self, request):
        """AR aging widget."""
        return Response(WidgetService.get_ar_aging_widget())

    @action(detail=False, methods=['get'])
    def ap_aging_widget(self, request):
        """AP aging widget."""
        return Response(WidgetService.get_ap_aging_widget())


class DrillDownController(viewsets.ViewSet):
    """Controller for drill-down functionality."""

    permission_classes = [RoleBasedPermission]

    @action(detail=False, methods=['get'])
    def revenue(self, request):
        """Drill down revenue to invoices."""
        start_date = date.fromisoformat(request.query_params.get('start_date'))
        end_date = date.fromisoformat(request.query_params.get('end_date'))
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_revenue_to_invoices(start_date, end_date, limit=limit))

    @action(detail=False, methods=['get'])
    def inventory_value(self, request):
        """Drill down inventory value to batches."""
        warehouse_id = request.query_params.get('warehouse_id')
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_inventory_value_to_batches(warehouse_id, limit))

    @action(detail=False, methods=['get'])
    def cash_position(self, request):
        """Drill down cash position to transactions."""
        start_date = date.fromisoformat(request.query_params.get('start_date'))
        end_date = date.fromisoformat(request.query_params.get('end_date'))
        tx_type = request.query_params.get('transaction_type')
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_cash_position_to_transactions(start_date, end_date, tx_type, limit))

    @action(detail=False, methods=['get'])
    def ar(self, request):
        """Drill down AR to invoices."""
        status_filter = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_ar_to_invoices(status_filter, limit))

    @action(detail=False, methods=['get'])
    def ap(self, request):
        """Drill down AP to invoices."""
        status_filter = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_ap_to_invoices(status_filter, limit))

    @action(detail=False, methods=['get'])
    def profit(self, request):
        """Drill down profit to journal entries."""
        start_date = date.fromisoformat(request.query_params.get('start_date'))
        end_date = date.fromisoformat(request.query_params.get('end_date'))
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_profit_to_journal_entries(start_date, end_date, limit))

    @action(detail=False, methods=['get'])
    def budget_variance(self, request):
        """Drill down budget variance to lines."""
        year = int(request.query_params.get('year', date.today().year))

        return Response(DrillDownEngine.drill_budget_variance_to_lines(year))

    @action(detail=False, methods=['get'])
    def cost_center(self, request):
        """Drill down cost center to transactions."""
        cost_center_id = request.query_params.get('cost_center_id')
        start_date = date.fromisoformat(request.query_params.get('start_date'))
        end_date = date.fromisoformat(request.query_params.get('end_date'))
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_cost_center_to_transactions(cost_center_id, start_date, end_date, limit))

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Drill down low stock to batches."""
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_low_stock_to_batches(limit))

    @action(detail=False, methods=['get'])
    def expiry_risk(self, request):
        """Drill down expiry risk to batches."""
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 50))

        return Response(DrillDownEngine.drill_expiry_to_batches(days, limit))