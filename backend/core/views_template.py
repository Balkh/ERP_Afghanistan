from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.models.invoice_template import InvoiceTemplate
from core.serializers import InvoiceTemplateSerializer
from core.multitenant.views import CompanyScopedViewSetMixin

class InvoiceTemplateViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    API for managing dynamic invoice templates.
    """
    queryset = InvoiceTemplate.objects.all()
    serializer_class = InvoiceTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Auto-assign company from context
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        serializer.save(company_id=company_id)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the currently active template for the company."""
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        
        # If no company context, try to get any active template or return default
        if company_id:
            template = InvoiceTemplate.objects.filter(company_id=company_id, is_active=True).first()
        else:
            template = InvoiceTemplate.objects.filter(is_active=True).first()
            
        if not template:
            # Return default config if no template exists
            return Response({
                'id': None,
                'name': 'Default',
                'is_active': True,
                'config': {
                    'layout': 'compact',
                    'show_logo': True,
                    'show_qr': True,
                    'currency': 'AFN',
                }
            })
        serializer = self.get_serializer(template)
        return Response(serializer.data)
