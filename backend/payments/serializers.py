from rest_framework import serializers
from payments.models import (
    PaymentMethod,
    PaymentAccount,
    FinancialTransaction,
    TransactionSettlement,
    SettlementTransaction,
)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PaymentAccountSerializer(serializers.ModelSerializer):
    accounting_account_code = serializers.CharField(
        source='accounting_account.code', read_only=True
    )
    accounting_account_name = serializers.CharField(
        source='accounting_account.name', read_only=True
    )

    class Meta:
        model = PaymentAccount
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class FinancialTransactionSerializer(serializers.ModelSerializer):
    payment_method_name = serializers.CharField(
        source='payment_method.name', read_only=True
    )
    source_account_name = serializers.CharField(
        source='source_account.name', read_only=True
    )
    destination_account_name = serializers.CharField(
        source='destination_account.name', read_only=True
    )

    class Meta:
        model = FinancialTransaction
        fields = '__all__'
        read_only_fields = [
            'transaction_number', 'net_amount', 'amount_in_base',
            'created_at', 'updated_at'
        ]


class TransactionSettlementSerializer(serializers.ModelSerializer):
    payment_account_name = serializers.CharField(
        source='payment_account.name', read_only=True
    )

    class Meta:
        model = TransactionSettlement
        fields = '__all__'
        read_only_fields = ['settlement_number', 'created_at', 'updated_at']


class SettlementTransactionSerializer(serializers.ModelSerializer):
    transaction_number = serializers.CharField(
        source='transaction.transaction_number', read_only=True
    )
    transaction_type = serializers.CharField(
        source='transaction.transaction_type', read_only=True
    )
    transaction_date = serializers.DateField(
        source='transaction.transaction_date', read_only=True
    )

    class Meta:
        model = SettlementTransaction
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
