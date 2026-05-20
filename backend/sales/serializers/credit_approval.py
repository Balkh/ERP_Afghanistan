"""Serializers for credit approval requests."""
from rest_framework import serializers
from sales.models import CreditApprovalRequest


class CreditApprovalRequestSerializer(serializers.ModelSerializer):
    """Serializer for credit approval requests."""

    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    requested_by_username = serializers.CharField(source='requested_by.username', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)

    class Meta:
        model = CreditApprovalRequest
        fields = [
            'id', 'invoice', 'invoice_number',
            'customer', 'customer_name', 'customer_code',
            'requested_amount', 'current_balance', 'credit_limit',
            'status', 'requested_by', 'requested_by_username',
            'approved_by', 'approved_by_username', 'approved_at',
            'approval_reason', 'rejection_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
