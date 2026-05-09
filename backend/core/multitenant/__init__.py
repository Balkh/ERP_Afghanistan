"""
Multi-Tenant Architecture for Pharmacy ERP.
Provides company-scoped data isolation, context management, and security integration.

Usage:
    from core.multitenant import TenantContext, CompanyScopedModel, TenantMiddleware
"""
from core.multitenant.context import TenantContext
from core.multitenant.middleware import TenantMiddleware, StrictTenantMiddleware
from core.multitenant.models import (
    CompanyScopedMixin,
    CompanyScopedModel,
    CompanyScopedQuerySet,
    CompanyScopedManager,
)
from core.models.multitenant import (
    UserCompanyMapping,
    CompanyPermissionService,
)

__all__ = [
    'TenantContext',
    'TenantMiddleware',
    'StrictTenantMiddleware',
    'CompanyScopedMixin',
    'CompanyScopedModel',
    'CompanyScopedQuerySet',
    'CompanyScopedManager',
    'UserCompanyMapping',
    'CompanyPermissionService',
]
