from decimal import Decimal
from datetime import date
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.core.exceptions import ValidationError

from fixed_assets.models import AssetCategory, FixedAsset, AssetDepreciation, AssetDisposal
from fixed_assets.serializers import (
    AssetCategorySerializer,
    AssetCategorySimpleSerializer,
    FixedAssetSerializer,
    FixedAssetListSerializer,
    AssetDepreciationSerializer,
    AssetDisposalSerializer,
    AssetDepreciationCreateSerializer,
    AssetDisposalCreateSerializer,
)
from fixed_assets.services.depreciation_service import DepreciationCalculationService
from fixed_assets.services.asset_lifecycle_service import AssetLifecycleService
from fixed_assets.services.asset_accounting_service import AssetAccountingIntegrationService
from security.permissions import RoleBasedPermission


class AssetCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD API for asset categories.
    """
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'default_depreciation_method']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetCategorySimpleSerializer
        return AssetCategorySerializer


class FixedAssetViewSet(viewsets.ModelViewSet):
    """
    CRUD API for fixed assets.
    """
    queryset = FixedAsset.objects.all()
    serializer_class = FixedAssetSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'depreciation_method']
    search_fields = ['asset_code', 'asset_name', 'serial_number', 'location']
    ordering_fields = ['asset_code', 'asset_name', 'purchase_date', 'current_book_value']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_disposed = self.request.query_params.get('include_disposed', 'false')
        if include_disposed != 'true':
            queryset = queryset.exclude(status='DISPOSED')
        return queryset.select_related('category')

    def get_serializer_class(self):
        if self.action == 'list':
            return FixedAssetListSerializer
        return FixedAssetSerializer

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a draft asset."""
        asset = self.get_object()
        try:
            activated_asset = AssetLifecycleService.activate_asset(asset)
            serializer = self.get_serializer(activated_asset)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def depreciate(self, request, pk=None):
        """Run depreciation for an asset."""
        asset = self.get_object()
        period_date = request.data.get('period_date')

        try:
            depreciation = AssetLifecycleService.depreciate_asset(
                asset,
                period_date=date.fromisoformat(period_date) if period_date else None
            )
            serializer = AssetDepreciationSerializer(depreciation)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def dispose(self, request, pk=None):
        """Dispose of an asset."""
        asset = self.get_object()
        serializer = AssetDisposalCreateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                disposal = AssetLifecycleService.dispose_asset(
                    asset,
                    disposal_date=serializer.validated_data['disposal_date'],
                    disposal_method=serializer.validated_data['disposal_method'],
                    proceeds=serializer.validated_data.get('proceeds', Decimal('0.00')),
                    disposal_cost=serializer.validated_data.get('disposal_cost', Decimal('0.00')),
                    buyer_info=serializer.validated_data.get('buyer_info', ''),
                    reference_number=serializer.validated_data.get('reference_number', ''),
                    notes=serializer.validated_data.get('notes', '')
                )
                disposal_serializer = AssetDisposalSerializer(disposal)
                return Response(disposal_serializer.data)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get asset summary."""
        asset = self.get_object()
        summary = AssetLifecycleService.get_asset_summary(asset)
        return Response(summary)

    @action(detail=False, methods=['get'])
    def value_report(self, request):
        """Get asset value report."""
        as_of_date = request.query_params.get('as_of_date')
        report_date = date.fromisoformat(as_of_date) if as_of_date else date.today()

        report = AssetAccountingIntegrationService.calculate_asset_value_report(report_date)
        return Response(report)


class AssetDepreciationViewSet(viewsets.ModelViewSet):
    """
    CRUD API for asset depreciation entries.
    """
    queryset = AssetDepreciation.objects.all()
    serializer_class = AssetDepreciationSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['asset', 'is_posted']
    search_fields = ['asset__asset_code', 'asset__asset_name']
    ordering_fields = ['period_start', 'period_end', 'depreciation_amount']
    ordering = ['-period_end']

    def get_queryset(self):
        return super().get_queryset().select_related('asset', 'asset__category')

    @action(detail=True, methods=['post'])
    def post_depreciation(self, request, pk=None):
        """Post depreciation to accounting."""
        depreciation = self.get_object()

        if depreciation.is_posted:
            return Response(
                {'error': 'Depreciation is already posted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        accounts = AssetAccountingIntegrationService.get_asset_accounts()

        if not all(accounts.values()):
            return Response(
                {'error': 'Required accounts not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entry = AssetAccountingIntegrationService.post_depreciation(
                depreciation,
                accounts['depreciation_expense'],
                accounts['accumulated_depreciation']
            )
            return Response({'entry_number': entry.entry_number, 'status': 'posted'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AssetDisposalViewSet(viewsets.ModelViewSet):
    """
    CRUD API for asset disposals.
    """
    queryset = AssetDisposal.objects.all()
    serializer_class = AssetDisposalSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['asset', 'disposal_method', 'is_posted']
    search_fields = ['asset__asset_code', 'asset__asset_name', 'reference_number']
    ordering_fields = ['disposal_date', 'proceeds', 'gain_loss']
    ordering = ['-disposal_date']

    def get_queryset(self):
        return super().get_queryset().select_related('asset', 'asset__category')

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse a disposal."""
        disposal = self.get_object()
        asset = disposal.asset

        try:
            AssetLifecycleService.reverse_disposal(asset)
            return Response({'status': 'reversed'})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)