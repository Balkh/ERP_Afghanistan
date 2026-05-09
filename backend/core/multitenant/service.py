"""
Company Service - Utilities for multi-company operations.
Provides helpers for filtering, context resolution, and company-aware queries.
"""
from typing import Optional, List, Any
from django.db import models, Q
from django.db.models import QuerySet


class CompanyService:
    """
    Service class for company-scoped operations.
    """
    
    @staticmethod
    def get_current_company_id() -> Optional[str]:
        """Get current company ID from context."""
        from core.multitenant.context import TenantContext
        return TenantContext.get_company_id()
    
    @staticmethod
    def get_current_company():
        """Get current company object from context."""
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        if not company_id:
            return None
        from core.models import Company
        return Company.objects.filter(id=company_id, is_active=True).first()
    
    @staticmethod
    def filter_by_company(queryset: QuerySet, company_field: str = 'company_id') -> QuerySet:
        """
        Filter queryset by current company context.
        
        Args:
            queryset: The queryset to filter
            company_field: The field name to use for filtering (default: 'company_id')
        
        Returns:
            Filtered queryset or original if no company context and user is superuser
        """
        company_id = TenantContext.get_company_id()
        
        if not company_id:
            # Check if user is superuser - allow all
            # This is handled at view level, not here
            return queryset
        
        return queryset.filter(**{company_field: company_id})
    
    @staticmethod
    def create_company_isolation_filter(
        queryset: QuerySet,
        company_id: Optional[str] = None,
        company_field: str = 'company_id'
    ) -> QuerySet:
        """
        Create Django Q filter for company isolation.
        
        Args:
            queryset: The queryset to filter
            company_id: Optional specific company ID (uses context if not provided)
            company_field: The field name to use
        
        Returns:
            Filtered queryset
        """
        from core.multitenant.context import TenantContext
        
        if company_id is None:
            company_id = TenantContext.get_company_id()
        
        if not company_id:
            # No company context - check model
            if hasattr(queryset.model, 'company'):
                # Model has company field but no context
                # Return empty queryset to prevent data leakage
                return queryset.none()
        
        return queryset.filter(**{company_field: company_id})
    
    @staticmethod
    def get_user_companies(user) -> List[Any]:
        """
        Get all companies a user has access to.
        
        Args:
            user: Django user object
        
        Returns:
            List of Company objects
        """
        from core.models import Company
        from core.models.multitenant import UserCompanyMapping
        
        if not user or not user.is_authenticated:
            return []
        
        if user.is_superuser:
            return list(Company.objects.filter(is_active=True))
        
        mappings = UserCompanyMapping.objects.filter(
            user=user,
            is_active=True
        ).select_related('company')
        
        return [m.company for m in mappings]
    
    @staticmethod
    def set_company_context(company_id: Optional[str] = None, company_code: Optional[str] = None):
        """
        Set company context for current thread.
        
        Args:
            company_id: Company UUID
            company_code: Company code
        """
        from core.multitenant.context import TenantContext
        from core.multitenant.middleware import resolve_company
        
        if company_id or company_code:
            company = resolve_company(company_id, company_code)
            if company:
                TenantContext.set_company_id(str(company.id))
                TenantContext.set_company_code(company.code)
            else:
                TenantContext.clear()
        else:
            TenantContext.clear()
    
    @staticmethod
    def clear_context():
        """Clear company context."""
        from core.multitenant.context import TenantContext
        TenantContext.clear()
    
    @staticmethod
    def is_company_isolated() -> bool:
        """Check if company isolation is active."""
        from core.multitenant.context import TenantContext
        return TenantContext.get_company_id() is not None


class CompanyQueryHelper:
    """
    Helper for building company-aware queries.
    """
    
    @staticmethod
    def build_company_filter(company_id: str, field_name: str = 'company_id') -> Q:
        """Build Q object for company filter."""
        return Q(**{field_name: company_id})
    
    @staticmethod
    def build_exclude_filter(company_id: str, field_name: str = 'company_id') -> Q:
        """Build Q object to exclude a company."""
        return ~Q(**{field_name: company_id})
    
    @staticmethod
    def build_multi_company_filter(company_ids: List[str], field_name: str = 'company_id') -> Q:
        """Build Q object for multiple companies."""
        return Q(**{f'{field_name}__in': company_ids})
    
    @staticmethod
    def has_company_field(model_or_instance) -> bool:
        """Check if model/instance has a company field."""
        if hasattr(model_or_instance, '_meta'):
            return hasattr(model_or_instance._meta.model, 'company')
        return hasattr(model_or_instance, 'company')