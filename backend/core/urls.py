from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.views_template import InvoiceTemplateViewSet
from core.serializers import CompanySerializer, SystemConfigSerializer
from core import import_views
from core.drift_prevention.views import DriftPreventionViewSet
from core.models.system import Company
from core.models.audit import SystemConfig


class CompanyViewSet(viewsets.ModelViewSet):
    """CRUD API for Company profile — SINGLE SOURCE OF TRUTH for business config."""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get the active company (SSOT for all business configuration)."""
        company = Company.objects.active()
        if not company:
            return Response({'error': 'No active company found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get or create the default company."""
        company = Company.objects.active()
        if not company:
            company = Company.objects.create(
                name='Default Company',
                code='DEFAULT',
                is_active=True,
            )
        serializer = self.get_serializer(company)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get business configuration from active company (SSOT endpoint).

        Returns all business config fields that consumers need:
        - company identity (name, code, address, phone, email)
        - tax info (tax_number, registration_number)
        - currency (default_currency, secondary_currency)
        - invoice settings (invoice_prefix, invoice_footer)
        """
        company = Company.objects.active()
        if not company:
            return Response({'error': 'No active company found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'company_name': company.name,
            'company_code': company.code,
            'address': company.address,
            'phone': company.phone,
            'email': company.email,
            'tax_number': company.tax_number,
            'registration_number': company.registration_number,
            'default_currency': company.default_currency,
            'secondary_currency': company.secondary_currency,
            'invoice_prefix': company.invoice_prefix,
            'invoice_footer': company.invoice_footer,
            'has_logo': bool(company.logo),
        })


class SystemConfigViewSet(viewsets.ModelViewSet):
    """CRUD API for SystemConfig key-value settings."""
    queryset = SystemConfig.objects.all()
    serializer_class = SystemConfigSerializer

    @action(detail=False, methods=['get'])
    def by_keys(self, request):
        """Get multiple config values by key query params: ?keys=theme&keys=language."""
        keys = request.query_params.getlist('keys')
        if not keys:
            return Response({'error': 'No keys provided'}, status=status.HTTP_400_BAD_REQUEST)
        configs = SystemConfig.objects.filter(key__in=keys)
        result = {c.key: c.value for c in configs}
        for key in keys:
            if key not in result:
                result[key] = None
        return Response(result)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update/create configs. Body: {"theme": "dark", "language": "en"}."""
        data = request.data
        updated = {}
        for key, value in data.items():
            obj, created = SystemConfig.objects.update_or_create(
                key=key, defaults={'value': str(value)}
            )
            updated[key] = value
        return Response(updated)


router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'invoice-templates', InvoiceTemplateViewSet, basename='invoice-template')
router.register(r'drift-prevention', DriftPreventionViewSet, basename='drift-prevention')
router.register(r'system-config', SystemConfigViewSet, basename='system-config')

urlpatterns = [
    path('', include(router.urls)),
    path('import/<str:entity_type>/dry-run/', import_views.import_dry_run, name='import_dry_run'),
    path('import/<str:entity_type>/execute/', import_views.import_execute, name='import_execute'),
]
