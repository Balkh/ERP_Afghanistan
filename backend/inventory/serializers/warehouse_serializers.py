from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from ..models import Warehouse, StockMovement, Product, Batch


class WarehouseSerializer(serializers.ModelSerializer):
    """
    Serializer for the Warehouse model
    """
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'code', 'address', 'contact_person', 'contact_phone', 'is_active', 'is_default']
        read_only_fields = ['id']


class StockMovementSerializer(serializers.ModelSerializer):
    """
    Serializer for the StockMovement model
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_generic_name = serializers.CharField(source='product.generic_name', read_only=True)
    product_brand_name = serializers.CharField(source='product.brand_name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_code = serializers.CharField(source='warehouse.code', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    reference_type_display = serializers.CharField(source='get_reference_type_display', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'product_generic_name', 'product_brand_name',
            'batch', 'batch_number', 'warehouse', 'warehouse_name', 'warehouse_code',
            'movement_type', 'movement_type_display', 'reference_type', 'reference_type_display',
            'reference_id', 'quantity', 'unit_cost', 'total_cost', 'notes', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'quantity': {'required': True},
            'warehouse': {'required': True},
            'product': {'required': True},
            'movement_type': {'required': True},
            'reference_type': {'required': True},
        }

    def validate_quantity(self, value):
        """
        Quantity cannot be zero
        """
        if value == 0:
            raise serializers.ValidationError(_('Quantity cannot be zero.'))
        return value

    def validate(self, data):
        """
        Additional validation for stock movement data
        """
        movement_type = data.get('movement_type')
        quantity = data.get('quantity')
        
        # For IN movements, quantity should be positive
        if movement_type == 'IN' and quantity is not None and quantity < 0:
            raise serializers.ValidationError(_('Stock IN quantity must be positive.'))
        
        # For OUT movements, quantity should be negative
        if movement_type == 'OUT' and quantity is not None and quantity > 0:
            raise serializers.ValidationError(_('Stock OUT quantity must be negative.'))
        
        # If batch is provided, verify it belongs to the product
        batch = data.get('batch')
        product = data.get('product')
        if batch and product and batch.product_id != product.id:
            raise serializers.ValidationError(_('Batch does not belong to the specified product.'))
        
        # Calculate total cost if unit cost and quantity are provided
        unit_cost = data.get('unit_cost')
        if unit_cost is not None and quantity is not None:
            data['total_cost'] = abs(quantity) * unit_cost
        
        return data