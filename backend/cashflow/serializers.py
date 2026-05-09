from rest_framework import serializers
from cashflow.models import CashFlowForecast, CashFlowItem, CashFlowScenario


class CashFlowItemSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    weighted_amount = serializers.DecimalField(
        source='weighted_amount', max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = CashFlowItem
        fields = [
            'id', 'category', 'category_display', 'item_type', 'type_display',
            'description', 'expected_date', 'amount', 'probability',
            'weighted_amount', 'is_actual', 'actual_date', 'actual_amount',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CashFlowForecastSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_forecast_type_display', read_only=True)
    items = CashFlowItemSerializer(many=True, read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)

    class Meta:
        model = CashFlowForecast
        fields = [
            'id', 'name', 'forecast_type', 'type_display',
            'start_date', 'end_date', 'currency', 'currency_code',
            'is_active', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CashFlowScenarioSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_scenario_type_display', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)

    class Meta:
        model = CashFlowScenario
        fields = [
            'id', 'name', 'scenario_type', 'type_display',
            'start_date', 'end_date', 'currency', 'currency_code',
            'sales_growth_rate', 'collection_rate', 'payment_rate',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']