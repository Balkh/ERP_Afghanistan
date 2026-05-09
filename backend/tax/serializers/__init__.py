from rest_framework import serializers
from tax.models import (
    TaxCategory, TaxRate, TaxJurisdiction, TaxReturn, TaxTransaction
)


class TaxCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxCategory
        fields = [
            'id', 'name', 'code', 'description', 'default_rate',
            'is_exempt', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxRateSerializer(serializers.ModelSerializer):
    tax_type_display = serializers.CharField(source='get_tax_type_display', read_only=True)

    class Meta:
        model = TaxRate
        fields = [
            'id', 'name', 'code', 'rate_percentage', 'tax_type', 'tax_type_display',
            'effective_from', 'effective_to', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxJurisdictionSerializer(serializers.ModelSerializer):
    rate_code = serializers.CharField(source='tax_rate.code', read_only=True)

    class Meta:
        model = TaxJurisdiction
        fields = ['id', 'name', 'code', 'tax_rate', 'rate_code', 'is_active']


class TaxReturnSerializer(serializers.ModelSerializer):
    period_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TaxReturn
        fields = [
            'id', 'period_start', 'period_end', 'period_display',
            'status', 'status_display', 'gross_sales', 'exempt_sales',
            'taxable_sales', 'output_tax', 'input_tax', 'net_tax',
            'filing_date', 'payment_date', 'reference_number', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'net_tax', 'created_at', 'updated_at']


class TaxTransactionSerializer(serializers.ModelSerializer):
    tax_rate_code = serializers.CharField(source='tax_rate.code', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = TaxTransaction
        fields = [
            'id', 'tax_return', 'transaction_type', 'transaction_type_display',
            'reference_id', 'base_amount', 'tax_amount', 'tax_rate', 'tax_rate_code',
            'transaction_date', 'is_reversed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxReturnCreateSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    calculate_from_journal = serializers.BooleanField(default=True)