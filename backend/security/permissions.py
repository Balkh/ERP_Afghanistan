from rest_framework import permissions
from django.contrib.auth.models import Permission
import logging

logger = logging.getLogger(__name__)


class RoleBasedPermission(permissions.BasePermission):
    """
    Custom permission class that checks user roles and permissions
    """
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access the view
        """
        # Allow unauthenticated users only if explicitly allowed
        if not request.user or not request.user.is_authenticated:
            logger.warning(f"User not authenticated: {request.user}")
            return False
            
        # Superusers have all permissions
        if request.user.is_superuser:
            return True

        # Check if user has the required permission for this view
        required_permission = self.get_required_permission(view)
        if not required_permission:
            # If no specific permission required, allow authenticated users
            return True
            
        # Check if user has the required permission
        return self.user_has_permission(request.user, required_permission)
            
        # Check if user has the required permission for this view
        required_permission = self.get_required_permission(view)
        if not required_permission:
            # If no specific permission required, allow authenticated users
            return True
            
        # Check if user has the required permission
        return self.user_has_permission(request.user, required_permission)
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access the object
        """
        # For object-level permissions, we'll check the same as view permissions
        # but could be extended for object-specific checks
        return self.has_permission(request, view)
    
    def get_required_permission(self, view):
        """
        Extract required permission from view
        """
        # Check if view has a required_permission attribute
        if hasattr(view, 'required_permission'):
            return view.required_permission
            
        # Check if view has required_permissions attribute (list)
        if hasattr(view, 'required_permissions'):
            return view.required_permissions
            
        # Try to infer from view name and action
        return self.infer_permission_from_view(view)
    
    def infer_permission_from_view(self, view):
        """
        Infer permission from view class name and action
        """
        # This is a simplified implementation - in practice, you might want
        # to use a more sophisticated mapping or require explicit declaration
        model_class = getattr(view, 'queryset', None)
        if model_class and hasattr(model_class, 'model'):
            model_name = model_class.model.__name__.lower()
        else:
            model_name = 'unknown'
            
        # Determine action based on view method or class
        action = 'read'  # default
        if hasattr(view, 'action'):
            action = view.action
        elif request.method.lower() in ['post', 'put', 'patch']:
            action = 'write'
        elif request.method.lower() == 'delete':
            action = 'delete'
            
        # Construct permission codename
        return f"{model_name}_{action}"
    
    def user_has_permission(self, user, permission):
        """
        Check if user has the specified permission
        """
        if isinstance(permission, list):
            # User needs ALL permissions in the list
            return all(self.user_has_permission(user, perm) for perm in permission)
            
        # Check direct user permissions (if we extended User model)
        # Check role-based permissions
        try:
            user_roles = getattr(user, 'user_roles', None)
            if user_roles:
                roles = user_roles.filter(role__is_active=True)
                for user_role in roles:
                    if user_role.is_expired:
                        continue
                    # Check if role has this permission
                    role_permissions = user_role.role.role_permissions.filter(
                        permission__is_active=True
                    )
                    if role_permissions.filter(permission__codename=permission).exists():
                        return True
        except Exception as e:
            logger.warning(f"Error checking permissions for user {user.id}: {e}")
            
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