"""
Unified API Response Format.
Standardized response structure for all backend endpoints.
"""
import uuid
from datetime import datetime
from typing import Any, Optional, List
from django.utils import timezone


class APIResponse:
    """
    Standardized API response builder.
    
    Success Response:
    {
        "success": true,
        "message": "Optional message",
        "data": {},
        "meta": {
            "request_id": "uuid",
            "timestamp": "ISO8601",
            "company_id": "uuid or null"
        }
    }
    
    Error Response:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable",
            "details": {}
        },
        "meta": {
            "request_id": "uuid",
            "timestamp": "ISO8601"
        }
    }
    """

    def __init__(self):
        self.request_id = str(uuid.uuid4())
        self.timestamp = timezone.now().isoformat()

    @staticmethod
    def success(
        data: Any = None,
        message: str = "",
        company_id: str = None
    ) -> dict:
        """Build success response."""
        return {
            "success": True,
            "message": message,
            "data": data,
            "meta": {
                "request_id": str(uuid.uuid4()),
                "timestamp": timezone.now().isoformat(),
                "company_id": company_id
            }
        }

    @staticmethod
    def error(
        code: str,
        message: str,
        details: dict = None,
        status_code: int = 400
    ) -> dict:
        """Build error response."""
        return {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {}
            },
            "meta": {
                "request_id": str(uuid.uuid4()),
                "timestamp": timezone.now().isoformat()
            }
        }

    @staticmethod
    def paginated(
        data: List[Any],
        page: int = 1,
        page_size: int = 20,
        total: int = 0,
        company_id: str = None
    ) -> dict:
        """Build paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        return {
            "success": True,
            "data": data,
            "meta": {
                "request_id": str(uuid.uuid4()),
                "timestamp": timezone.now().isoformat(),
                "company_id": company_id,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        }


class StandardResponseMixin:
    """
    Mixin for DRF views to provide standardized responses.
    """
    
    def response_success(self, data=None, message="", status_code=200):
        """Return standardized success response."""
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        
        response = APIResponse.success(data, message, company_id)
        return response, status_code

    def response_error(self, code, message, details=None, status_code=400):
        """Return standardized error response."""
        response = APIResponse.error(code, message, details)
        return response, status_code

    def response_paginated(self, queryset, page=1, page_size=20):
        """Return standardized paginated response."""
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        
        total = queryset.count()
        items = queryset[(page-1)*page_size:page*page_size]
        
        return APIResponse.paginated(
            data=items,
            page=page,
            page_size=page_size,
            total=total,
            company_id=company_id
        )