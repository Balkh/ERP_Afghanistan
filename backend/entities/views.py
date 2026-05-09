from datetime import date
from decimal import Decimal
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from entities.models import Entity, EntityAccount, InterCompanyTransaction
from entities.serializers import (
    EntitySerializer, EntityAccountSerializer, InterCompanyTransactionSerializer
)
from entities.services.entity_service import EntityService
from entities.services.consolidated_reporting import ConsolidatedReportingService
from security.permissions import RoleBasedPermission


class EntityViewSet(viewsets.ModelViewSet):
    """CRUD for business entities."""
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['entity_type', 'is_active', 'is_default']
    search_fields = ['name', 'code']

    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get default entity."""
        entity = EntityService.get_default_entity()
        if entity:
            return Response(EntitySerializer(entity).data)
        return Response({'error': 'No default entity'}, status=404)

    @action(detail=False, methods=['get'])
    def consolidated_balance_sheet(self, request):
        """Get consolidated balance sheet."""
        as_of = request.query_params.get('as_of_date')
        if not as_of:
            return Response({'error': 'as_of_date required'}, status=400)
        report = ConsolidatedReportingService.get_consolidated_balance_sheet(
            date.fromisoformat(as_of)
        )
        return Response(report)

    @action(detail=False, methods=['get'])
    def consolidated_cash_flow(self, request):
        """Get consolidated cash flow."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response({'error': 'start_date and end_date required'}, status=400)
        report = ConsolidatedReportingService.get_consolidated_cash_flow(
            date.fromisoformat(start), date.fromisoformat(end)
        )
        return Response(report)

    @action(detail=False, methods=['get'])
    def performance_summary(self, request):
        """Get entity performance summary."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response({'error': 'start_date and end_date required'}, status=400)
        summary = ConsolidatedReportingService.get_entity_performance_summary(
            date.fromisoformat(start), date.fromisoformat(end)
        )
        return Response(summary)


class EntityAccountViewSet(viewsets.ModelViewSet):
    """CRUD for entity accounts."""
    queryset = EntityAccount.objects.all()
    serializer_class = EntityAccountSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entity', 'is_active']


class InterCompanyTransactionViewSet(viewsets.ModelViewSet):
    """CRUD for inter-company transactions."""
    queryset = InterCompanyTransaction.objects.all()
    serializer_class = InterCompanyTransactionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['from_entity', 'to_entity', 'transaction_type', 'is_reconciled']
    ordering = ['-transaction_date']

    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Reconcile transaction."""
        tx = self.get_object()
        tx = EntityService.reconcile_transaction(tx)
        return Response(InterCompanyTransactionSerializer(tx).data)