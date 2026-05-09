from rest_framework import serializers
from purchases.models import Supplier, SupplierPayment


class SupplierSerializer(serializers.ModelSerializer):
    available_credit = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_over_credit_limit = serializers.BooleanField(read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'contact_person', 'email', 'phone',
            'address', 'city', 'country', 'tax_number', 'credit_limit',
            'balance', 'payment_terms_days', 'notes', 'is_active',
            'available_credit', 'is_over_credit_limit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
            'phone': {'required': True},
        }

    def validate_code(self, value):
        """Ensure supplier code is unique."""
        instance = self.instance
        if Supplier.objects.filter(code=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError('Supplier with this code already exists.')
        return value

    def validate_credit_limit(self, value):
        """Ensure credit limit is non-negative."""
        if value < 0:
            raise serializers.ValidationError('Credit limit cannot be negative.')
        return value


class SupplierPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = SupplierPayment
        fields = [
            'id', 'supplier', 'supplier_name', 'invoice', 'invoice_number',
            'amount', 'payment_date', 'payment_method', 'reference_number',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'supplier': {'required': True},
            'amount': {'required': True},
            'payment_date': {'required': True},
            'payment_method': {'required': True},
        }

    def validate_amount(self, value):
        """Ensure payment amount is positive."""
        if value <= 0:
            raise serializers.ValidationError('Payment amount must be positive.')
        return value
