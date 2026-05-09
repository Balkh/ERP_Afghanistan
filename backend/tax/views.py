from decimal import Decimal
from datetime import date
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from tax.models import (
    TaxCategory, TaxRate, TaxJurisdiction, TaxReturn, TaxTransaction
)
from tax.serializers import (
    TaxCategorySerializer, TaxRateSerializer, TaxJurisdictionSerializer,
    TaxReturnSerializer, TaxTransactionSerializer, TaxReturnCreateSerializer
)
from tax.services.tax_calculator import TaxCalculationService
from tax.services.tax_reporting import TaxReportingService
from security.permissions import RoleBasedPermission


class TaxCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for tax categories."""
    queryset = TaxCategory.objects.all()
    serializer_class = TaxCategorySerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_exempt', 'is_active']
    search_fields = ['name', 'code']


class TaxRateViewSet(viewsets.ModelViewSet):
    """CRUD for tax rates."""
    queryset = TaxRate.objects.all()
    serializer_class = TaxRateSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tax_type', 'is_active']
    search_fields = ['name', 'code']
    ordering = ['-effective_from']

    @action(detail=False, methods=['get'])
    def active_for_date(self, request):
        """Get active rate for a specific date."""
        tax_date = request.query_params.get('date')
        tax_type = request.query_params.get('type', 'STANDARD')

        if not tax_date:
            return Response({'error': 'date parameter required'}, status=400)

        rate = TaxCalculationService.get_active_rate_for_date(
            date.fromisoformat(tax_date), tax_type
        )

        if rate:
            return Response(TaxRateSerializer(rate).data)
        return Response({'error': 'No active rate found'}, status=404)


class TaxJurisdictionViewSet(viewsets.ModelViewSet):
    """CRUD for tax jurisdictions."""
    queryset = TaxJurisdiction.objects.all()
    serializer_class = TaxJurisdictionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']


class TaxReturnViewSet(viewsets.ModelViewSet):
    """CRUD for tax returns."""
    queryset = TaxReturn.objects.all()
    serializer_class = TaxReturnSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['reference_number']
    ordering = ['-period_end']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create tax return with optional calculation."""
        serializer = TaxReturnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        calculate_from_journal = data.pop('calculate_from_journal', True)

        if calculate_from_journal:
            tax_return = TaxReportingService.prepare_tax_return(
                period_start=data['period_start'],
                period_end=data['period_end']
            )
        else:
            tax_return = TaxReturn.objects.create(**data)

        return Response(TaxReturnSerializer(tax_return).data, status=201)

    @action(detail=True, methods=['post'])
    def file(self, request, pk=None):
        """Mark tax return as filed."""
        tax_return = self.get_object()
        tax_return.status = 'FILED'
        tax_return.filing_date = date.today()
        tax_return.reference_number = request.data.get('reference_number', '')
        tax_return.save()
        return Response(TaxReturnSerializer(tax_return).data)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Mark tax return as paid."""
        tax_return = self.get_object()

        if tax_return.status != 'FILED':
            return Response(
                {'error': 'Tax return must be filed before payment.'},
                status=400
            )

        tax_return.status = 'PAID'
        tax_return.payment_date = date.today()
        tax_return.save()
        return Response(TaxReturnSerializer(tax_return).data)

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        """Validate tax return."""
        tax_return = self.get_object()
        issues = TaxReportingService.validate_return(tax_return)
        return Response({'valid': len(issues) == 0, 'issues': issues})

    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        """Get outstanding tax returns."""
        returns = TaxReportingService.get_outstanding_returns()
        serializer = self.get_serializer(returns, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def liability_report(self, request):
        """Get tax liability report."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date required'},
                status=400
            )

        report = TaxReportingService.get_tax_liability_report(
            date.fromisoformat(start_date),
            date.fromisoformat(end_date)
        )
        return Response(report)


class TaxTransactionViewSet(viewsets.ModelViewSet):
    """CRUD for tax transactions."""
    queryset = TaxTransaction.objects.all()
    serializer_class = TaxTransactionSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'tax_return', 'is_reversed']
    ordering = ['-transaction_date']

    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reverse a tax transaction."""
        tx = self.get_object()

        if tx.is_reversed:
            return Response({'error': 'Already reversed'}, status=400)

        tx.is_reversed = True
        tx.save()

        TaxTransaction.objects.create(
            tax_return=tx.tax_return,
            transaction_type=tx.transaction_type,
            reference_id=tx.reference_id,
            base_amount=-tx.base_amount,
            tax_amount=-tx.tax_amount,
            tax_rate=tx.tax_rate,
            transaction_date=date.today(),
            is_reversed=True
        )

        return Response({'status': 'reversed'})