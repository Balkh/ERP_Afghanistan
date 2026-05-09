from django_filters.rest_framework import DjangoFilterBackend

class CustomFilterBackend(DjangoFilterBackend):
    """Custom backend that uses request.GET instead of request.query_params."""
    
    def get_filterset_kwargs(self, request, queryset, view):
        return {
            'data': getattr(request, 'query_params', request.GET),
            'queryset': queryset,
            'request': request,
        }
