"""
API Response Mixins for standardized response format.

Usage:
    class MyViewSet(StandardizedResponseMixin, viewsets.ModelViewSet):
        pass
"""
from rest_framework.response import Response
from rest_framework import status
from core.api.responses import APIResponse
from core.api.errors import create_error_response, ErrorCode, get_status_for_error
from core.multitenant.context import TenantContext


def get_company_id():
    """Get current company ID from context."""
    return TenantContext.get_company_id()


class StandardizedResponseMixin:
    """
    Mixin that standardizes all ViewSet responses.
    
    Wraps list/retrieve/create/update/destroy responses in APIResponse format.
    Handles pagination for list actions.
    """
    
    def list(self, request, *args, **kwargs):
        """List with standardized pagination."""
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginator = self.paginator
            
            return Response(APIResponse.paginated(
                data=serializer.data,
                company_id=get_company_id(),
                page=paginator.page.number,
                page_size=paginator.page_size,
                total=paginator.count,
                total_pages=paginator.page.paginator.num_pages
            ))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(APIResponse.success(
            data=serializer.data,
            company_id=get_company_id()
        ))
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve single object with standardized format."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(APIResponse.success(
            data=serializer.data,
            company_id=get_company_id()
        ))
    
    def create(self, request, *args, **kwargs):
        """Create with standardized format."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            APIResponse.success(data=serializer.data, company_id=get_company_id()),
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update with standardized format."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(APIResponse.success(
            data=serializer.data,
            company_id=get_company_id()
        ))
    
    def destroy(self, request, *args, **kwargs):
        """Destroy with standardized format."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            APIResponse.success(data={'deleted': True, 'id': str(kwargs.get('pk'))}, company_id=get_company_id()),
            status=status.HTTP_204_NO_CONTENT
        )


class StandardizedErrorMixin:
    """
    Mixin that adds standardized error handling to ViewSets.
    """
    
    def handle_exception(self, exc):
        """Override to provide standardized error format."""
        response = super().handle_exception(exc)
        
        if hasattr(response, 'data'):
            if 'detail' in response.data:
                error_code = ErrorCode.PER_001 if 'permission' in str(response.data.get('detail', '')).lower() else ErrorCode.VAL_001
                response.data = create_error_response(
                    error_code,
                    str(response.data.get('detail', 'Unknown error'))
                )
        
        return response