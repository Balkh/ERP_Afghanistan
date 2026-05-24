from decimal import Decimal
from rest_framework import serializers
from purchases.models import PurchaseInvoice, PurchaseItem


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'invoice', 'product', 'product_name',
            'batch_number', 'expiry_date', 'quantity',
            'unit_price', 'discount', 'tax', 'total',
            'received_quantity', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total', 'created_at', 'updated_at']
        extra_kwargs = {
            'product': {'required': True},
            'batch_number': {'required': True},
            'expiry_date': {'required': True},
            'quantity': {'required': True},
            'unit_price': {'required': True},
        }

    def validate_quantity(self, value):
        """Ensure quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError('Quantity must be positive.')
        return value

    def validate_unit_price(self, value):
        """Ensure unit price is non-negative."""
        if value < 0:
            raise serializers.ValidationError('Unit price cannot be negative.')
        return value

    def validate(self, data):
        """Validate and calculate total."""
        quantity = data.get('quantity', getattr(self.instance, 'quantity', 0))
        unit_price = data.get('unit_price', getattr(self.instance, 'unit_price', 0))
        discount = data.get('discount', getattr(self.instance, 'discount', Decimal('0.00')))
        tax = data.get('tax', getattr(self.instance, 'tax', Decimal('0.00')))

        data['total'] = (quantity * unit_price) - discount + tax

        if data['total'] < 0:
            raise serializers.ValidationError('Total cannot be negative.')

        return data


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    remaining_balance = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    writable_items = PurchaseItemSerializer(many=True, required=False, write_only=True)
    tax_rate_display = serializers.SerializerMethodField()
    workflow_status = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    can_post = serializers.SerializerMethodField()
    
    def get_workflow_status(self, obj):
        from workflows.services import WorkflowService
        status = WorkflowService.get_workflow_status('PURCHASE_INVOICE', obj.id)
        return status
    
    def get_can_submit(self, obj):
        status = self.get_workflow_status(obj)
        return status.get('can_submit', False) if status else False
    
    def get_can_approve(self, obj):
        status = self.get_workflow_status(obj)
        return status.get('can_approve', False) if status else False
    
    def get_can_post(self, obj):
        status = self.get_workflow_status(obj)
        return status.get('can_post', False) if status else False

    def get_tax_rate_display(self, obj):
        return f"{obj.tax_rate}%" if obj.tax_enabled else "Disabled"

    class Meta:
        model = PurchaseInvoice
        fields = [
            'id', 'invoice_number', 'supplier', 'supplier_name',
            'order_date', 'invoice_date', 'due_date',
            'subtotal', 'discount', 'tax', 'tax_enabled', 'tax_rate',
            'tax_rate_display', 'total_amount',
            'paid_amount', 'remaining_balance',
            'status', 'payment_status',
            'workflow_status', 'can_submit', 'can_approve', 'can_post',
            'items', 'writable_items',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subtotal', 'tax', 'total_amount', 'paid_amount',
            'remaining_balance', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'invoice_number': {'required': True},
            'supplier': {'required': True},
            'order_date': {'required': True},
            'invoice_date': {'required': True},
            'due_date': {'required': True},
            'tax_enabled': {'required': False},
            'tax_rate': {'required': False},
        }

    def create(self, validated_data):
        """Create invoice with line items."""
        items_data = validated_data.pop('writable_items', [])
        invoice = PurchaseInvoice.objects.create(**validated_data)

        for item_data in items_data:
            item_data.pop('invoice', None)
            PurchaseItem.objects.create(invoice=invoice, **item_data)

        invoice.calculate_totals()
        invoice.save()
        return invoice

    def update(self, instance, validated_data):
        """Update invoice with line items."""
        items_data = validated_data.pop('writable_items', None)
        instance = super().update(instance, validated_data)

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                item_data.pop('invoice', None)
                PurchaseItem.objects.create(invoice=instance, **item_data)

        instance.calculate_totals()
        instance.save()
        return instance

    def validate_discount(self, value):
        """Ensure discount is non-negative."""
        if value < 0:
            raise serializers.ValidationError('Discount cannot be negative.')
        return value

    def validate_tax(self, value):
        """Ensure tax is non-negative."""
        if value < 0:
            raise serializers.ValidationError('Tax cannot be negative.')
        return value
