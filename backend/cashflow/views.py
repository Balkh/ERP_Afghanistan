from datetime import date, timedelta
from decimal import Decimal
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from cashflow.models import CashFlowForecast, CashFlowItem, CashFlowScenario
from cashflow.serializers import (
    CashFlowForecastSerializer, CashFlowItemSerializer, CashFlowScenarioSerializer
)
from cashflow.services.forecasting_service import CashFlowForecastingService
from security.permissions import RoleBasedPermission


class CashFlowForecastViewSet(viewsets.ModelViewSet):
    """CRUD for cash flow forecasts."""
    queryset = CashFlowForecast.objects.all()
    serializer_class = CashFlowForecastSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['forecast_type', 'is_active', 'currency']
    ordering = ['-start_date']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get forecast summary."""
        forecast_id = request.query_params.get('forecast_id')
        if not forecast_id:
            return Response({'error': 'forecast_id required'}, status=400)
        
        try:
            forecast = CashFlowForecast.objects.get(id=forecast_id)
        except CashFlowForecast.DoesNotExist:
            return Response({'error': 'Forecast not found'}, status=404)
        
        summary = CashFlowForecastingService.get_forecast_summary(forecast)
        return Response(summary)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate forecast based on historical data."""
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        forecast_type = request.data.get('forecast_type', 'MONTHLY')
        
        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date required'}, status=400)
        
        result = CashFlowForecastingService.generate_forecast(
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
            forecast_type
        )
        return Response(result)


class CashFlowItemViewSet(viewsets.ModelViewSet):
    """CRUD for cash flow items."""
    queryset = CashFlowItem.objects.all()
    serializer_class = CashFlowItemSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['forecast', 'category', 'item_type', 'is_actual']

    @action(detail=True, methods=['post'])
    def mark_actual(self, request, pk=None):
        """Mark item as actual with actual values."""
        item = self.get_object()
        item.is_actual = True
        item.actual_date = date.today()
        item.actual_amount = request.data.get('amount', item.amount)
        item.save()
        return Response(CashFlowItemSerializer(item).data)


class CashFlowScenarioViewSet(viewsets.ModelViewSet):
    """CRUD for cash flow scenarios."""
    queryset = CashFlowScenario.objects.all()
    serializer_class = CashFlowScenarioSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['scenario_type']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def analyze(self, request):
        """Run scenario analysis."""
        scenario_id = request.query_params.get('scenario_id')
        if not scenario_id:
            return Response({'error': 'scenario_id required'}, status=400)
        
        try:
            scenario = CashFlowScenario.objects.get(id=scenario_id)
        except CashFlowScenario.DoesNotExist:
            return Response({'error': 'Scenario not found'}, status=404)
        
        result = CashFlowForecastingService.run_scenario_analysis(scenario)
        return Response(result)

    @action(detail=False, methods=['get'])
    def receivables_forecast(self, request):
        """Get receivables forecast."""
        days = int(request.query_params.get('days', 30))
        result = CashFlowForecastingService.get_receivables_forecast(days)
        return Response(result)

    @action(detail=False, methods=['get'])
    def payables_forecast(self, request):
        """Get payables forecast."""
        days = int(request.query_params.get('days', 30))
        result = CashFlowForecastingService.get_payables_forecast(days)
        return Response(result)