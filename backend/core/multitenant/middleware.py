"""
Tenant Middleware.
Extracts company context from request and sets it in thread-local storage.
Supports multiple methods of company identification:
- HTTP header: X-Company-ID, X-Company-Code
- JWT token claims: company_id, company_code
- URL query parameter: company_id, company_code
- Subdomain: companycode.example.com (optional, configurable)
"""
import logging
from typing import Optional
from django.http import HttpResponseForbidden, JsonResponse

from core.multitenant.context import TenantContext
from core.models import Company

logger = logging.getLogger('erp.security')

HEADER_COMPANY_ID = 'HTTP_X_COMPANY_ID'
HEADER_COMPANY_CODE = 'HTTP_X_COMPANY_CODE'
JWT_CLAIM_COMPANY_ID = 'company_id'
JWT_CLAIM_COMPANY_CODE = 'company_code'


def get_company_from_jwt(request) -> Optional[str]:
    """Extract company_id from JWT token in request."""
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        company_id = getattr(user, JWT_CLAIM_COMPANY_ID, None)
        if company_id:
            return str(company_id)
    return None


def get_company_code_from_jwt(request) -> Optional[str]:
    """Extract company_code from JWT token in request."""
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        company_code = getattr(user, JWT_CLAIM_COMPANY_CODE, None)
        if company_code:
            return str(company_code)
    return None


def get_company_from_header(request, header: str) -> Optional[str]:
    """Extract company identifier from HTTP header."""
    return request.META.get(header)


def get_company_from_query(request, param: str) -> Optional[str]:
    """Extract company identifier from query parameter."""
    return request.query_params.get(param) if hasattr(request, 'query_params') else request.GET.get(param)


def resolve_company(company_id: Optional[str] = None, company_code: Optional[str] = None):
    """
    Resolve company from ID or code.
    Returns Company instance or None.
    """
    from django.core.exceptions import ValidationError

    if company_id:
        try:
            return Company.objects.filter(id=company_id, is_active=True).first()
        except (ValueError, TypeError, ValidationError):
            return None
    if company_code:
        try:
            return Company.objects.filter(code=company_code, is_active=True).first()
        except (ValueError, TypeError, ValidationError):
            return None
    return None


class TenantMiddleware:
    """
    Middleware that extracts company context from each request.
    Sets company context in thread-local storage for the duration of the request.

    Priority order:
    1. X-Company-ID header
    2. X-Company-Code header
    3. JWT token claims
    4. Query parameter (admin override only)
    5. Default company (fallback)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = [
            '/admin/',
            '/api/health/',
        ]

    def __call__(self, request):
        # Skip tenant context for excluded paths
        path = request.path
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return self.get_response(request)

        company_id = None
        company_code = None

        # 1. Check headers (highest priority)
        company_id = get_company_from_header(request, HEADER_COMPANY_ID)
        company_code = get_company_from_header(request, HEADER_COMPANY_CODE)

        # 2. Check JWT claims
        if not company_id:
            company_id = get_company_from_jwt(request)
        if not company_code:
            company_code = get_company_from_jwt(request)

        # 3. Check query params (admin override)
        if not company_id:
            company_id = get_company_from_query(request, 'company_id')
        if not company_code:
            company_code = get_company_from_query(request, 'company_code')

        # Resolve company
        company = resolve_company(company_id, company_code)

        # Set context
        if company:
            TenantContext.set_company_id(str(company.id))
            TenantContext.set_company_code(company.code)
            request.company = company
            request.company_id = str(company.id)
        else:
            # No company context set - allow request to proceed
            # Company-aware queries will return all data (backward compatible)
            request.company = None
            request.company_id = None

        # Set user ID in context
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            TenantContext.set_user_id(str(user.id))

        # Attach request ID if present
        request_id = getattr(request, 'request_id', None)
        if request_id:
            TenantContext.set_request_id(request_id)

        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up thread-local context after request
            TenantContext.clear()


class StrictTenantMiddleware:
    """
    Strict version of TenantMiddleware.
    Requires valid company context for all API requests.
    Returns 403 if company cannot be resolved.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = [
            '/admin/',
            '/api/health/',
        ]

    def __call__(self, request):
        path = request.path
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return self.get_response(request)

        company_id = get_company_from_header(request, HEADER_COMPANY_ID)
        company_code = get_company_from_header(request, HEADER_COMPANY_CODE)

        if not company_id:
            company_id = get_company_from_jwt(request)
        if not company_code:
            company_code = get_company_from_jwt(request)

        company = resolve_company(company_id, company_code)

        if not company:
            return JsonResponse(
                {'error': 'Company context required. Set X-Company-ID or X-Company-Code header.'},
                status=403
            )

        TenantContext.set_company_id(str(company.id))
        TenantContext.set_company_code(company.code)
        request.company = company
        request.company_id = str(company.id)

        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            TenantContext.set_user_id(str(user.id))

        try:
            response = self.get_response(request)
            return response
        finally:
            TenantContext.clear()
