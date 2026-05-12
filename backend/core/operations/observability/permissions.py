from rest_framework.permissions import BasePermission


class IsObserver(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsAnalyst(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.groups.filter(name='Analyst').exists()


class IsAuditor(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or request.user.groups.filter(name='Auditor').exists()


class IsObservabilityAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser
