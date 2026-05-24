from rest_framework import serializers
from core.models.invoice_template import InvoiceTemplate
from core.models.system import Company
from core.models.audit import SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = ['id', 'key', 'value', 'description', 'is_sensitive']
        read_only_fields = ['id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_sensitive:
            data['value'] = '***'
        return data


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'code', 'address', 'phone', 'email',
            'tax_number', 'registration_number', 'is_active', 'default_currency',
            'secondary_currency', 'logo', 'invoice_prefix', 'invoice_footer',
        ]
        read_only_fields = ['id']


class InvoiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = ['id', 'company', 'name', 'is_active', 'config', 'logo_override']
        read_only_fields = ['id', 'company']
