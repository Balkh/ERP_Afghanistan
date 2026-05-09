from rest_framework import serializers
from core.models.invoice_template import InvoiceTemplate

class InvoiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = ['id', 'company', 'name', 'is_active', 'config', 'logo_override']
        read_only_fields = ['id', 'company']
