import time
import json
from typing import Optional, Any, Dict
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from audit.models import AuditTrail, AuditRetentionPolicy

User = get_user_model()


class AuditService:
    """Service for managing audit logs."""

    @staticmethod
    def log(
        user,
        action: str,
        app_label: str,
        model_name: str,
        object_id: Optional[str] = None,
        object_repr: str = '',
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: str = '',
        request_method: str = '',
        request_path: str = '',
        is_error: bool = False,
        error_message: str = '',
    ):
        """Create an audit log entry."""
        changes = {}
        if old_values and new_values:
            for key in set(list(old_values.keys()) + list(new_values.keys())):
                old_val = old_values.get(key)
                new_val = new_values.get(key)
                if old_val != new_val:
                    changes[key] = {'old': old_val, 'new': new_val}

        # Validate user is a real User instance, not a mock
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if user is not None and not isinstance(user, User):
            user = None

        username = user.username if user else 'anonymous'

        AuditTrail.objects.create(
            user=user,
            username=username,
            action=action,
            app_label=app_label,
            model_name=model_name,
            object_id=str(object_id) if object_id else '',
            object_repr=object_repr[:500] if object_repr else '',
            changes=changes,
            old_values=old_values or {},
            new_values=new_values or {},
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            request_method=request_method,
            request_path=request_path[:500] if request_path else '',
            is_error=is_error,
            error_message=error_message[:1000] if error_message else '',
        )

    @staticmethod
    def log_model_change(
        user,
        action: str,
        instance: models.Model,
        old_instance: Optional[models.Model] = None,
        **kwargs
    ):
        """Log changes to a model instance."""
        app_label = instance._meta.app_label
        model_name = instance._meta.model_name

        old_values = {}
        new_values = {}

        if action in ['UPDATE', 'DELETE'] and old_instance:
            for field in instance._meta.fields:
                old_values[field.name] = getattr(old_instance, field.name, None)

        if action in ['CREATE', 'UPDATE']:
            for field in instance._meta.fields:
                new_values[field.name] = getattr(instance, field.name, None)

        AuditService.log(
            user=user,
            action=action,
            app_label=app_label,
            model_name=model_name,
            object_id=str(instance.pk) if instance.pk else None,
            object_repr=str(instance)[:500],
            old_values=old_values,
            new_values=new_values,
            **kwargs
        )

    @staticmethod
    def log_request(
        user,
        action: str,
        request,
        app_label: str = '',
        model_name: str = '',
        object_id: Optional[str] = None,
        object_repr: str = '',
        **kwargs
    ):
        """Log an HTTP request."""
        ip_address = AuditService._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        method = request.method
        path = request.path

        AuditService.log(
            user=user,
            action=action,
            app_label=app_label,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=method,
            request_path=path,
            **kwargs
        )

    @staticmethod
    def _get_client_ip(request) -> Optional[str]:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def cleanup_old_logs():
        """Delete logs older than retention period."""
        deleted_count = 0
        policies = AuditRetentionPolicy.objects.filter(is_active=True)

        if not policies.exists():
            default_days = 365
            cutoff = timezone.now() - timezone.timedelta(days=default_days)
            deleted_count, _ = AuditTrail.objects.filter(created_at__lt=cutoff).delete()
            return deleted_count

        for policy in policies:
            cutoff = timezone.now() - timezone.timedelta(days=policy.retention_days)
            queryset = AuditTrail.objects.filter(created_at__lt=cutoff)

            if policy.app_labels:
                queryset = queryset.filter(app_label__in=policy.app_labels)
            if policy.action_types:
                queryset = queryset.filter(action__in=policy.action_types)

            deleted_count += queryset.delete()[0]

        return deleted_count

    @staticmethod
    def get_user_activity(user, days: int = 30) -> Dict:
        """Get activity summary for a user."""
        from django.utils import timezone
        from datetime import timedelta

        since = timezone.now() - timedelta(days=days)

        logs = AuditTrail.objects.filter(user=user, created_at__gte=since)
        
        return {
            'total_actions': logs.count(),
            'by_action': dict(logs.values_list('action').annotate(models.Count('id'))),
            'by_app': dict(logs.values_list('app_label').annotate(models.Count('id'))),
            'recent': list(logs.order_by('-created_at')[:10].values(
                'action', 'model_name', 'object_repr', 'created_at'
            ))
        }


class AuditMiddleware:
    """Middleware to automatically log requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        user = getattr(request, 'user', None)
        is_authenticated = user and hasattr(user, 'is_authenticated') and user.is_authenticated

        response = self.get_response(request)

        execution_time = int((time.time() - start_time) * 1000)

        if is_authenticated and hasattr(request, '_audit_logged'):
            return response

        if request.path.startswith('/api/') and is_authenticated:
            action = 'VIEW'
            if request.method in ['POST', 'PUT', 'PATCH']:
                action = 'UPDATE'
            if request.method == 'DELETE':
                action = 'DELETE'

            AuditService.log_request(
                user=user,
                action=action,
                request=request,
                execution_time_ms=execution_time,
                is_error=response.status_code >= 400
            )

        return response