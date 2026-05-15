"""
DEPRECATED — Multi-Company Architecture Service.
Use ``core.multitenant`` instead.

This module will be removed in a future release.
All functionality is duplicated in:
  - core.multitenant.context.TenantContext  (replaces CompanyContext)
  - core.multitenant.service                (replaces CompanyService)
  - core.multitenant.middleware             (replaces MultiCompanyMiddleware)
  - core.multitenant.models.CompanyScopedMixin  (replaces CompanyRequiredMixin)

IMPORTANT: Entity and Company are different concepts.
Entity = operational location (branch, pharmacy, warehouse)
Company = legal/organizational tenant boundary
This file incorrectly conflated them — fix applied.
"""
import warnings
warnings.warn(
    "entities.services.company_service is deprecated. Use core.multitenant instead.",
    DeprecationWarning,
    stacklevel=2,
)

import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from core.models.system import Company


class CompanyContext:
    """
    Thread-local context for company isolation.
    Sets the current company for all database queries.
    """
    
    _current_company_id = None
    
    @classmethod
    def set_company(cls, company_id: Optional[str]):
        """Set current company ID."""
        cls._current_company_id = company_id
    
    @classmethod
    def get_company(cls) -> Optional[str]:
        """Get current company ID."""
        return cls._current_company_id
    
    @classmethod
    def clear(cls):
        """Clear current company."""
        cls._current_company_id = None


class CompanyService:
    """
    Multi-Company Service - manages company-scoped data access.
    
    Key principles:
    - All transaction data MUST be scoped by company
    - No cross-company data leakage allowed
    - Company context is set via middleware
    """

    @staticmethod
    def get_current_company() -> Optional[str]:
        """Get current company from context."""
        return CompanyContext.get_company()

    @staticmethod
    def set_current_company(company_id: str):
        """Set current company in context."""
        CompanyContext.set_company(company_id)

    @staticmethod
    def clear_company():
        """Clear company context."""
        CompanyContext.clear()

    @staticmethod
    def filter_by_company(queryset, company_field: str = 'entity_id'):
        """
        Filter queryset by current company.
        
        Args:
            queryset: Django queryset to filter
            company_field: Name of company field in model
            
        Returns:
            Filtered queryset
        """
        company_id = CompanyContext.get_company()
        
        if company_id is None:
            return queryset
        
        if company_field not in [f.name for f in queryset.model._meta.get_fields()]:
            return queryset
            
        return queryset.filter(**{company_field: company_id})

    @staticmethod
    def validate_company_access(user, company_id: str) -> bool:
        """
        Validate user has access to company.
        
        Args:
            user: User instance
            company_id: Company ID to validate
            
        Returns:
            True if user has access
        """
        if user.is_superuser:
            return True
            
        try:
            company = Company.objects.get(id=company_id)
            return True
        except Company.DoesNotExist:
            return False

    @staticmethod
    def get_user_companies(user) -> List[str]:
        """
        Get list of company IDs user has access to.
        
        Args:
            user: User instance
            
        Returns:
            List of company IDs
        """
        if user.is_superuser:
            return list(Company.objects.filter(is_active=True).values_list('id', flat=True))
        
        return list(Company.objects.filter(is_active=True).values_list('id', flat=True))

    @staticmethod
    def create_company_isolation_filter(
        model_class,
        company_field: str = 'entity_id'
    ) -> models.Q:
        """
        Create Django Q filter for company isolation.
        
        Args:
            model_class: Model class to create filter for
            company_field: Field name for company
            
        Returns:
            Q object for filtering
        """
        company_id = CompanyContext.get_company()
        
        if company_id is None:
            return models.Q()
        
        return models.Q(**{company_field: company_id})


class CompanyRequiredMixin:
    """
    Mixin for views that require company context.
    """
    
    def get_queryset(self):
        """Filter queryset by current company."""
        queryset = super().get_queryset()
        
        company_id = CompanyContext.get_company()
        
        if company_id and hasattr(queryset.model, 'entity_id'):
            return queryset.filter(entity_id=company_id)
        
        return queryset


def company_required(view_func):
    """
    Decorator to require company context for views.
    """
    def wrapper(request, *args, **kwargs):
        company_id = CompanyContext.get_company()
        
        if not company_id:
            raise PermissionDenied("Company context required")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


class MultiCompanyMiddleware:
    """
    Middleware to set company context from request.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        company_id = None
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            company_id = getattr(request, 'company_id', None)
            
            if not company_id and hasattr(request, 'session'):
                company_id = request.session.get('company_id')
        
        CompanyContext.set_company(company_id)
        
        response = self.get_response(request)
        
        CompanyContext.clear()
        
        return response