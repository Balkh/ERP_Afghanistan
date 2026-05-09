"""
Custom Pagination for API responses.
Standardized pagination format for all list endpoints.
"""
from rest_framework.pagination import PageNumberPagination as DRFPageNumberPagination
from rest_framework.response import Response
from core.api.responses import APIResponse


class StandardizedPagination(DRFPageNumberPagination):
    """
    Custom pagination that returns standardized response format.
    
    Standard response:
    {
        "success": true,
        "data": [...],
        "meta": {
            "request_id": "...",
            "timestamp": "...",
            "company_id": "...",
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": true,
                "has_previous": false
            }
        }
    }
    """
    
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        
        return Response({
            "success": True,
            "data": data,
            "meta": {
                "request_id": "",
                "timestamp": "",
                "company_id": company_id,
                "pagination": {
                    "page": self.page.number,
                    "page_size": self.page.paginator.per_page,
                    "total": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "has_next": self.page.has_next(),
                    "has_previous": self.page.has_previous()
                }
            }
        })


class CountOnlyPagination:
    """
    Simple pagination that just returns count.
    Useful for dashboard statistics.
    """
    
    def paginate_queryset(self, queryset, request, view=None):
        self.count = queryset.count()
        return queryset
    
    def get_paginated_response(self, data):
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        
        return Response({
            "success": True,
            "data": data,
            "meta": {
                "request_id": "",
                "timestamp": "",
                "company_id": company_id,
                "count": self.count
            }
        })


def paginate(queryset, page=1, page_size=20, serializer_class=None):
    """
    Manual pagination helper for function-based views.
    
    Returns standardized paginated response.
    """
    from core.multitenant.context import TenantContext
    from core.api.responses import APIResponse
    from django.core.serializers import serialize
    
    total = queryset.count()
    items = queryset[(page-1)*page_size:page*page_size]
    company_id = TenantContext.get_company_id()
    
    return APIResponse.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        company_id=company_id
    )