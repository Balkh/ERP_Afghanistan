from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.api.responses import APIResponse
from core.drift_prevention.registry import DriftRegistry
from core.drift_prevention.gate import PreventionGate
from core.drift_prevention.report import HealthReport


class DriftPreventionViewSet(viewsets.ViewSet):
    """API endpoints for monitoring drift prevention system."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        return self.health(request)

    @action(detail=False, methods=['get'])
    def health(self, request):
        report = HealthReport.generate()
        return APIResponse.success(data=report)

    @action(detail=False, methods=['get'])
    def modules(self, request):
        statuses = PreventionGate.all_module_statuses()
        return APIResponse.success(data={'modules': statuses})

    @action(detail=True, methods=['get'])
    def module(self, request, pk=None):
        report = HealthReport.module_report(pk)
        if not report.get('state'):
            return APIResponse.error(
                message=f'Module "{pk}" not found',
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return APIResponse.success(data=report)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        reason = request.data.get('reason', 'Manual block by administrator')
        result = PreventionGate.block_module(pk, reason)
        return APIResponse.success(data=result)

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        cleared_by = request.data.get('cleared_by', 'admin')
        reason = request.data.get('reason', 'Manual unblock by administrator')
        result = PreventionGate.unblock_module(pk, cleared_by, reason)
        if 'error' in result:
            return APIResponse.error(message=result['error'], status_code=status.HTTP_404_NOT_FOUND)
        return APIResponse.success(data=result)

    @action(detail=False, methods=['get'])
    def records(self, request):
        module = request.query_params.get('module')
        limit = int(request.query_params.get('limit', 100))
        records = DriftRegistry.get_recent_records(module=module, limit=limit)
        data = [
            {
                'id': str(r.id),
                'module': r.module,
                'operation': r.operation,
                'classification': r.classification,
                'financial_impact': r.financial_impact,
                'reference': r.reference,
                'engine_success': r.engine_success,
                'gateway_success': r.gateway_success,
                'created_at': str(r.created_at),
            }
            for r in records
        ]
        return APIResponse.success(data={'records': data, 'total': len(data)})

    @action(detail=False, methods=['get'])
    def critical(self, request):
        module = request.query_params.get('module')
        records = DriftRegistry.get_class_c_records(module=module)
        data = [
            {
                'id': str(r.id),
                'module': r.module,
                'operation': r.operation,
                'reference': r.reference,
                'mismatch_detail': r.mismatch_detail,
                'created_at': str(r.created_at),
            }
            for r in records
        ]
        return APIResponse.success(data={'critical_records': data, 'total': len(data)})
