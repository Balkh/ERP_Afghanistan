from rest_framework import serializers
from cost_centers.models import CostCenter, CostAllocation, CostAllocationLine, CostTransaction


class CostCenterSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_cost_center_type_display', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = CostCenter
        fields = [
            'id', 'name', 'code', 'cost_center_type', 'type_display',
            'department', 'parent', 'parent_name', 'default_account',
            'budget', 'is_active', 'description', 'manager',
            'children_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_children_count(self, obj):
        return obj.children.count()


class CostCenterListSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_cost_center_type_display', read_only=True)

    class Meta:
        model = CostCenter
        fields = ['id', 'name', 'code', 'cost_center_type', 'type_display', 'budget', 'is_active']


class CostAllocationLineSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(source='target_cost_center.name', read_only=True)
    target_code = serializers.CharField(source='target_cost_center.code', read_only=True)

    class Meta:
        model = CostAllocationLine
        fields = ['id', 'target_cost_center', 'target_name', 'target_code', 'percentage']


class CostAllocationSerializer(serializers.ModelSerializer):
    lines = CostAllocationLineSerializer(many=True, read_only=True)
    method_display = serializers.CharField(source='get_allocation_method_display', read_only=True)

    class Meta:
        model = CostAllocation
        fields = [
            'id', 'name', 'source_cost_center', 'allocation_method', 'method_display',
            'is_active', 'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CostTransactionSerializer(serializers.ModelSerializer):
    cost_center_code = serializers.CharField(source='cost_center.code', read_only=True)
    cost_center_name = serializers.CharField(source='cost_center.name', read_only=True)

    class Meta:
        model = CostTransaction
        fields = [
            'id', 'cost_center', 'cost_center_code', 'cost_center_name',
            'journal_entry_line', 'amount', 'transaction_date', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CostAllocationLineCreateSerializer(serializers.Serializer):
    target_cost_center_id = serializers.UUIDField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)