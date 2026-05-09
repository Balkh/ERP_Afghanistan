from rest_framework import serializers
from entities.models import Entity, EntityAccount, InterCompanyTransaction


class EntitySerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_entity_type_display', read_only=True)
    base_currency_code = serializers.CharField(source='base_currency.code', read_only=True)

    class Meta:
        model = Entity
        fields = [
            'id', 'name', 'code', 'entity_type', 'type_display',
            'is_active', 'is_default', 'address', 'phone', 'email',
            'base_currency', 'base_currency_code', 'tax_number',
            'license_number', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EntityAccountSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    entity_name = serializers.CharField(source='entity.name', read_only=True)

    class Meta:
        model = EntityAccount
        fields = [
            'id', 'entity', 'entity_name', 'account', 'account_code',
            'account_name', 'account_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InterCompanyTransactionSerializer(serializers.ModelSerializer):
    from_entity_name = serializers.CharField(source='from_entity.name', read_only=True)
    to_entity_name = serializers.CharField(source='to_entity.name', read_only=True)
    type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    currency_code = serializers.CharField(source='currency.code', read_only=True)

    class Meta:
        model = InterCompanyTransaction
        fields = [
            'id', 'from_entity', 'from_entity_name', 'to_entity', 'to_entity_name',
            'transaction_type', 'type_display', 'amount', 'currency',
            'currency_code', 'reference_number', 'transaction_date',
            'description', 'is_reconciled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_reconciled', 'created_at', 'updated_at']