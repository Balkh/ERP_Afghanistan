from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from ..models import Batch, Product


class BatchSerializer(serializers.ModelSerializer):
    """
    Serializer for the Batch model
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_generic_name = serializers.CharField(source='product.generic_name', read_only=True)
    product_brand_name = serializers.CharField(source='product.brand_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    profit_margin = serializers.FloatField(read_only=True)

    class Meta:
        model = Batch
        fields = [
            'id', 'product', 'product_name', 'product_generic_name', 'product_brand_name',
            'batch_number', 'manufacturing_date', 'expiry_date', 'purchase_price', 
            'sale_price', 'quantity', 'remaining_quantity', 'location', 'is_active',
            'is_expired', 'days_until_expiry', 'is_expiring_soon', 'profit_margin'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'batch_number': {'required': True},
            'manufacturing_date': {'required': True},
            'expiry_date': {'required': True},
            'purchase_price': {'required': True},
            'sale_price': {'required': True},
            'quantity': {'required': True},
        }

    def validate_batch_number(self, value):
        """
        Check that the batch number is unique (if being updated, exclude current instance)
        """
        if self.instance:
            # Update case: exclude current instance
            if Batch.objects.exclude(id=self.instance.id).filter(batch_number=value).exists():
                raise serializers.ValidationError("A batch with this number already exists.")
        else:
            # Create case
            if Batch.objects.filter(batch_number=value).exists():
                raise serializers.ValidationError("A batch with this number already exists.")
        return value

    def validate(self, data):
        """
        Additional validation for batch data
        """
        # Ensure manufacturing date is not in the future
        manufacturing_date = data.get('manufacturing_date')
        if manufacturing_date and manufacturing_date > serializers.DateTimeField().to_representation(serializers.DateTimeField()).__class__():
            from django.utils import timezone
            if manufacturing_date > timezone.now().date():
                raise serializers.ValidationError(_('Manufacturing date cannot be in the future.'))
        
        # Ensure expiry date is after manufacturing date
        manufacturing_date = data.get('manufacturing_date')
        expiry_date = data.get('expiry_date')
        if manufacturing_date and expiry_date and expiry_date <= manufacturing_date:
            raise serializers.ValidationError(_('Expiry date must be after manufacturing date.'))
        
        # Ensure remaining quantity does not exceed total quantity
        quantity = data.get('quantity')
        remaining_quantity = data.get('remaining_quantity', quantity)  # Default to quantity if not provided
        if quantity is not None and remaining_quantity is not None and remaining_quantity > quantity:
            raise serializers.ValidationError(_('Remaining quantity cannot exceed total quantity.'))
        
        return data