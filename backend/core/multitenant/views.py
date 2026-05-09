"""
Company-Scoped ViewSet Mixin.
Automatically filters querysets by current company context.
"""
from rest_framework import viewsets
from core.multitenant.context import TenantContext


class CompanyScopedViewSetMixin:
    """
    Mixin for ViewSets that should be scoped by company.
    Automatically filters the queryset based on TenantContext.
    
    Usage:
        class ProductViewSet(CompanyScopedViewSetMixin, ModelViewSet):
            ...
    """
    
    def get_queryset(self):
        """Get company-scoped queryset."""
        queryset = super().get_queryset()
        
        # Check if model has company field
        if not hasattr(queryset.model, 'company'):
            return queryset
        
        # Get company from context
        company_id = TenantContext.get_company_id()
        
        # If no company context, allow all (backward compatible)
        if not company_id:
            # For superusers, allow all
            if hasattr(self.request, 'user') and self.request.user.is_superuser:
                return queryset
            # For non-superusers, scope to user's default company
            return queryset.none()  # Empty by default
        
        return queryset.filter(company_id=company_id)
    
    def perform_create(self, serializer):
        """Auto-set company on create."""
        if hasattr(serializer.Meta.model, 'company'):
            company_id = TenantContext.get_company_id()
            if company_id:
                serializer.save(company_id=company_id)
            else:
                serializer.save()
        else:
            serializer.save()
    
    def perform_update(self, serializer):
        """Prevent changing company on update."""
        if hasattr(serializer.Meta.model, 'company'):
            # Keep existing company, don't allow changes
            if serializer.instance.company_id:
                serializer.save(company=serializer.instance.company)
            else:
                company_id = TenantContext.get_company_id()
                if company_id:
                    from core.models import Company
                    company = Company.objects.filter(id=company_id).first()
                    if company:
                        serializer.save(company=company)
                    else:
                        serializer.save()
                else:
                    serializer.save()
        else:
            serializer.save()


class CompanyScopedFilter:
    """
    Filter class for DRF to apply company filter.
    Use this in filter_backends.
    """
    
    def filter_queryset(self, request, queryset, view):
        """Apply company filter to queryset."""
        # Check if model has company field
        if not hasattr(queryset.model, 'company'):
            return queryset
        
        # Get company from context
        company_id = TenantContext.get_company_id()
        
        # If no company context
        if not company_id:
            # For superusers, allow all
            if hasattr(request, 'user') and request.user.is_superuser:
                return queryset
            # For non-superusers, scope to user's default company
            return queryset.none()
        
        return queryset.filter(company_id=company_id)


class CompanyContextMixin:
    """
    Mixin that resolves company from request and sets context.
    Use this on API views that need company context.
    """
    
    def initialize_request(self, request, *args, **kwargs):
        """Initialize request and set company context."""
        # Call parent first
        rv = super().initialize_request(request, *args, **kwargs)
        
        # Resolve company from request
        self._set_company_context(request)
        
        return rv
    
    def _set_company_context(self, request):
        """Set company context from request."""
        from core.multitenant.middleware import resolve_company
        
        # Try to get company from query params
        company_id = request.query_params.get('company_id')
        company_code = request.query_params.get('company_code')
        
        # If not in params, try header
        if not company_id:
            company_id = request.headers.get('X-Company-ID')
        if not company_code:
            company_code = request.headers.get('X-Company-Code')
        
        # If not set, try to get from user's default company
        if not company_id and not company_code:
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    from core.models.multitenant import UserCompanyMapping
                    mapping = UserCompanyMapping.objects.filter(
                        user=request.user,
                        is_default=True
                    ).first()
                    if mapping:
                        company_id = str(mapping.company_id)
                except Exception:
                    pass
        
        # Resolve and set context
        if company_id or company_code:
            company = resolve_company(company_id, company_code)
            if company:
                TenantContext.set_company_id(str(company.id))
                TenantContext.set_company_code(company.code)
    
    def finalize_response(self, request, response, *args, **kwargs):
        """Clear context after response."""
        response = super().finalize_response(request, response, *args, **kwargs)
        
        # Don't clear context here - it may be needed by other views
        # Context should be cleared by middleware at end of request
        return response