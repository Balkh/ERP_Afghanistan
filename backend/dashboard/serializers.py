from rest_framework import serializers
from dashboard.models import DashboardWidgetConfig, DashboardAlert


class DashboardWidgetConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidgetConfig
        fields = [
            'id', 'user', 'widget_type', 'title', 'position',
            'size', 'is_visible', 'filter_config',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardAlertSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.username', read_only=True)

    class Meta:
        model = DashboardAlert
        fields = [
            'id', 'title', 'message', 'severity', 'severity_display',
            'category', 'category_display', 'is_active', 'is_acknowledged',
            'acknowledged_by', 'acknowledged_by_name', 'source_model',
            'source_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class KPIOverviewSerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    gross_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    cogs = serializers.DecimalField(max_digits=15, decimal_places=2)
    inventory_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    cash_position = serializers.DecimalField(max_digits=15, decimal_places=2)
    accounts_receivable = serializers.DecimalField(max_digits=15, decimal_places=2)
    accounts_payable = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_liabilities = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_equity = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()
    gross_margin = serializers.DecimalField(max_digits=10, decimal_places=2)
    dso = serializers.IntegerField()
    dpo = serializers.IntegerField()
    current_ratio = serializers.DecimalField(max_digits=10, decimal_places=2)
    quick_ratio = serializers.DecimalField(max_digits=10, decimal_places=2)


class WidgetDataSerializer(serializers.Serializer):
    widget_type = serializers.CharField()
    data = serializers.JSONField()