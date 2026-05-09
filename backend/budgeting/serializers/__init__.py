from rest_framework import serializers
from budgeting.models import Budget, BudgetLine


class BudgetLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance_percentage = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = BudgetLine
        fields = [
            'id', 'budget', 'account', 'account_code', 'account_name',
            'period', 'budgeted_amount', 'actual_amount',
            'variance', 'variance_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'actual_amount', 'variance', 'variance_percentage',
                           'created_at', 'updated_at']


class BudgetSerializer(serializers.ModelSerializer):
    lines = BudgetLineSerializer(many=True, read_only=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    variance_percentage = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'fiscal_year', 'period_type', 'status',
            'total_budgeted', 'total_actual', 'variance', 'variance_percentage',
            'notes', 'approved_by', 'approved_date',
            'lines', 'line_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_actual', 'variance', 'variance_percentage',
                           'created_at', 'updated_at']

    def get_line_count(self, obj):
        return obj.lines.count()


class BudgetListSerializer(serializers.ModelSerializer):
    variance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'fiscal_year', 'period_type', 'status',
            'total_budgeted', 'total_actual', 'variance',
            'created_at'
        ]


class BudgetLineCreateSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    period = serializers.CharField()
    budgeted_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


class BudgetUpdateActualsSerializer(serializers.Serializer):
    period = serializers.CharField(required=False)