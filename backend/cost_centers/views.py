from decimal import Decimal
from datetime import date
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from cost_centers.models import CostCenter, CostAllocation, CostAllocationLine, CostTransaction
from cost_centers.serializers import (
    CostCenterSerializer, CostCenterListSerializer,
    CostAllocationSerializer, CostTransactionSerializer,
    CostAllocationLineCreateSerializer
)
from cost_centers.services.cost_allocation_service import CostAllocationService
from cost_centers.services.cost_reporting_service import CostReportingService
from security.permissions import RoleBasedPermission


class CostCenterViewSet(viewsets.ModelViewSet):
    """CRUD for cost centers."""
    queryset = CostCenter.objects.all()
    serializer_class = CostCenterSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['cost_center_type', 'is_active', 'department']
    search_fields = ['name', 'code', 'description']
    ordering = ['code']

    def get_serializer_class(self):
        if self.action == 'list':
            return CostCenterListSerializer
        return CostCenterSerializer

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary for all cost centers."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        if start and end:
            results = CostReportingService.get_all_centers_summary(
                date.fromisoformat(start), date.fromisoformat(end)
            )
        else:
            results = CostReportingService.get_all_centers_summary()

        return Response(results)

    @action(detail=True, methods=['get'])
    def detail_summary(self, request, pk=None):
        """Get detailed summary for a cost center."""
        cost_center = self.get_object()
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        if start and end:
            summary = CostReportingService.get_cost_center_summary(
                cost_center,
                date.fromisoformat(start),
                date.fromisoformat(end)
            )
        else:
            summary = CostReportingService.get_cost_center_summary(cost_center)

        return Response(summary)

    @action(detail=False, methods=['get'])
    def budget_variance(self, request):
        """Get budget variance report."""
        report = CostReportingService.get_budget_variance_report()
        return Response(report)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get cost by type report."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        if not start or not end:
            return Response({'error': 'start_date and end_date required'}, status=400)

        report = CostReportingService.get_cost_by_type_report(
            date.fromisoformat(start),
            date.fromisoformat(end)
        )
        return Response(report)

    @action(detail=False, methods=['get'])
    def top_centers(self, request):
        """Get top cost centers."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 10))

        if not start or not end:
            return Response({'error': 'start_date and end_date required'}, status=400)

        top = CostReportingService.get_top_cost_centers(
            date.fromisoformat(start),
            date.fromisoformat(end),
            limit
        )
        return Response(top)


class CostAllocationViewSet(viewsets.ModelViewSet):
    """CRUD for cost allocations."""
    queryset = CostAllocation.objects.all()
    serializer_class = CostAllocationSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['source_cost_center', 'is_active', 'allocation_method']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create allocation with lines."""
        data = request.data
        lines_data = data.pop('lines', [])

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        allocation = serializer.save()

        for line_data in lines_data:
            cc_id = line_data.get('target_cost_center_id')
            try:
                cc = CostCenter.objects.get(id=cc_id)
                CostAllocationLine.objects.create(
                    allocation=allocation,
                    target_cost_center=cc,
                    percentage=line_data.get('percentage', Decimal('0.00'))
                )
            except CostCenter.DoesNotExist:
                pass

        return Response(CostAllocationSerializer(allocation).data, status=201)

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        """Validate allocation."""
        allocation = self.get_object()
        issues = CostAllocationService.validate_allocation(allocation)
        return Response({'valid': len(issues) == 0, 'issues': issues})


class CostTransactionViewSet(viewsets.ModelViewSet):
    """CRUD for cost transactions."""
    queryset = CostTransaction.objects.all()
    serializer_class = CostTransactionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cost_center', 'transaction_date']
    ordering = ['-transaction_date']

    def get_queryset(self):
        return super().get_queryset().select_related('cost_center')