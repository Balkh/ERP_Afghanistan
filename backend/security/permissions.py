from rest_framework import permissions
from django.contrib.auth.models import Permission
import logging

logger = logging.getLogger(__name__)


class RoleBasedPermission(permissions.BasePermission):
    """
    Custom permission class that checks user roles and permissions.
    Supports explicit permission codes on views and automatic inference.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.warning("Unauthenticated access attempt to %s", view)
            return False

        if request.user.is_superuser:
            return True

        required_permission = self.get_required_permission(view, request)
        if not required_permission:
            return True

        return self.user_has_permission(request.user, required_permission)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

    def get_required_permission(self, view, request=None):
        if hasattr(view, 'required_permission'):
            return view.required_permission

        if hasattr(view, 'required_permissions'):
            return view.required_permissions

        return self.infer_permission_from_view(view, request)

    def infer_permission_from_view(self, view, request=None):
        model_class = getattr(view, 'queryset', None)
        if model_class and hasattr(model_class, 'model'):
            model_name = model_class.model.__name__.lower()
        else:
            model_name = 'unknown'

        action = 'read'
        if hasattr(view, 'action'):
            action = view.action
        elif request and request.method.lower() in ['post', 'put', 'patch']:
            action = 'write'
        elif request and request.method.lower() == 'delete':
            action = 'delete'

        return f"{model_name}_{action}"

    def user_has_permission(self, user, permission):
        if isinstance(permission, list):
            return all(self.user_has_permission(user, perm) for perm in permission)

        try:
            user_roles = getattr(user, 'user_roles', None)
            if user_roles:
                roles = user_roles.filter(role__is_active=True)
                for user_role in roles:
                    if user_role.is_expired:
                        continue
                    role_permissions = user_role.role.role_permissions.filter(
                        permission__is_active=True
                    )
                    if role_permissions.filter(permission__codename=permission).exists():
                        return True
        except Exception as e:
            logger.warning("Error checking permissions for user %s: %s", user.id, e)

        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` attribute.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Instance must have an attribute named `owner`.
        return obj.owner == request.user


class LicenseRequiredPermission(permissions.BasePermission):
    """
    Permission that requires a valid license
    """
    
    def has_permission(self, request, view):
        # First check authentication
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Then check license validity through existing license middleware
        # The license middleware should have already validated the license
        # and set request.license or similar
        return hasattr(request, 'license_valid') and request.license_valid