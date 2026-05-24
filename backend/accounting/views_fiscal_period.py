"""Fiscal Period API views — CRUD, closing, reopening, and readiness checks."""
import logging

from django.core.exceptions import ValidationError
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounting.models import FiscalPeriod, FiscalPeriodCloseLog
from accounting.serializers import (
    FiscalPeriodSerializer,
    FiscalPeriodCloseLogSerializer,
    PeriodClosingReadinessSerializer,
    PeriodCloseRequestSerializer,
    PeriodReopenRequestSerializer,
)
from accounting.services.period_closing import PeriodClosingService
from core.api.responses import APIResponse

logger = logging.getLogger('erp.fiscal_period_views')


class FiscalPeriodViewSet(viewsets.ModelViewSet):
    """ViewSet for fiscal period management."""
    serializer_class = FiscalPeriodSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-start_date']

    def get_queryset(self):
        return FiscalPeriod.objects.all().prefetch_related('close_logs')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return APIResponse.success(
            data=serializer.data,
            message='Fiscal period created successfully.',
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.can_modify():
            return APIResponse.error(
                message=f'Cannot modify period {instance.code} — status is {instance.status}.',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return APIResponse.success(
            data=serializer.data,
            message='Fiscal period updated successfully.',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.can_modify():
            return APIResponse.error(
                message=f'Cannot delete period {instance.code} — status is {instance.status}.',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if instance.journalentry_set.exists():
            return APIResponse.error(
                message='Cannot delete period with journal entries.',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        self.perform_destroy(instance)
        return APIResponse.success(message='Fiscal period deleted.')

    @action(detail=True, methods=['get'])
    def readiness(self, request, pk=None):
        """Check if a period is ready for closing."""
        period = self.get_object()
        readiness = PeriodClosingService.check_readiness(period)
        return APIResponse.success(data=readiness.to_dict())

    @action(detail=True, methods=['post'])
    def soft_close(self, request, pk=None):
        """Soft-close a period."""
        period = self.get_object()
        serializer = PeriodCloseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PeriodClosingService.soft_close(
                period=period,
                user=request.user,
                reason=serializer.validated_data['reason'],
            )
            return APIResponse.success(data=result, message='Period soft-closed.')
        except ValidationError as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a period."""
        period = self.get_object()
        serializer = PeriodCloseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PeriodClosingService.close_period(
                period=period,
                user=request.user,
                reason=serializer.validated_data['reason'],
                force=serializer.validated_data.get('force', False),
            )
            return APIResponse.success(data=result, message='Period closed.')
        except ValidationError as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock a period."""
        period = self.get_object()
        serializer = PeriodCloseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PeriodClosingService.lock_period(
                period=period,
                user=request.user,
                reason=serializer.validated_data['reason'],
            )
            return APIResponse.success(data=result, message='Period locked.')
        except ValidationError as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Reopen a closed/locked period."""
        period = self.get_object()
        serializer = PeriodReopenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = PeriodClosingService.reopen_period(
                period=period,
                user=request.user,
                reason=serializer.validated_data['reason'],
            )
            return APIResponse.success(data=result, message='Period reopened.')
        except ValidationError as e:
            return APIResponse.error(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def close_logs(self, request, pk=None):
        """Get close/reopen logs for a period."""
        period = self.get_object()
        logs = period.close_logs.all().order_by('-created_at')
        serializer = FiscalPeriodCloseLogSerializer(logs, many=True)
        return APIResponse.success(data=serializer.data)

    @action(detail=False, methods=['get'])
    def current_open(self, request):
        """Get the current open period for today."""
        from django.utils import timezone
        from accounting.models import get_open_period_for_date

        today = timezone.now().date()
        period = get_open_period_for_date(today)

        if period:
            return APIResponse.success(data=FiscalPeriodSerializer(period).data)
        return APIResponse.error(
            message='No open period found for today.',
            status_code=status.HTTP_404_NOT_FOUND,
        )

    @action(detail=True, methods=['get'])
    def export_closing_summary_pdf(self, request, pk=None):
        """Export period closing summary as PDF."""
        from core.pdf_generator import generate_period_closing_summary_pdf, pdf_response
        from accounting.services.period_closing import PeriodClosingService

        period = self.get_object()
        readiness = PeriodClosingService.check_readiness(period)
        pdf_bytes = generate_period_closing_summary_pdf(
            period, readiness.to_dict(), generated_by=str(request.user)
        )
        return pdf_response(pdf_bytes, f'period_closing_{period.code}.pdf')


class FiscalPeriodCloseLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for fiscal period close logs."""
    serializer_class = FiscalPeriodCloseLogSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']

    def get_queryset(self):
        return FiscalPeriodCloseLog.objects.all().select_related('period', 'performed_by')
