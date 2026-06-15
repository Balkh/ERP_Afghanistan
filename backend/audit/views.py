from rest_framework import serializers, viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count

from audit.models import AuditTrail, AuditRetentionPolicy
from audit.services.audit_service import AuditService
from security.permissions import RoleBasedPermission


class AuditTrailSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditTrail
        fields = [
            'id', 'user', 'user_username', 'action', 'action_display',
            'app_label', 'model_name', 'object_id', 'object_repr',
            'changes', 'old_values', 'new_values', 'ip_address',
            'user_agent', 'request_method', 'request_path',
            'is_error', 'error_message', 'execution_time_ms',
            'created_at'
        ]
        read_only_fields = fields


class AuditTrailViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view of audit trail."""
    queryset = AuditTrail.objects.all()
    serializer_class = AuditTrailSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'action', 'app_label', 'model_name', 'is_error']
    search_fields = ['username', 'object_repr', 'request_path']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get audit summary statistics."""
        summary = {
            'total_logs': AuditTrail.objects.count(),
            'by_action': dict(
                AuditTrail.objects.values('action').annotate(count=Count('id')).values_list('action', 'count')
            ),
            'by_app': dict(
                AuditTrail.objects.values('app_label').annotate(count=Count('id')).values_list('app_label', 'count')
            ),
            'errors': AuditTrail.objects.filter(is_error=True).count(),
        }
        return Response(summary)

    @action(detail=False, methods=['post'])
    def cleanup(self, request):
        """Run cleanup of old logs."""
        deleted = AuditService.cleanup_old_logs()
        return Response({'deleted': deleted})

    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """Get activity for a specific user."""
        user_id = request.query_params.get('user_id')
        days = int(request.query_params.get('days', 30))
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        
        activity = AuditService.get_user_activity(user, days)
        return Response(activity)


class AuditRetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditRetentionPolicy
        fields = [
            'id', 'name', 'app_labels', 'action_types',
            'retention_days', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditRetentionPolicyViewSet(viewsets.ModelViewSet):
    """CRUD for audit retention policies."""
    queryset = AuditRetentionPolicy.objects.all()
    serializer_class = AuditRetentionPolicySerializer
    permission_classes = [RoleBasedPermission]