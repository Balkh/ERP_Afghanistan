"""Security app URL configuration - authentication endpoints."""
import jwt
import datetime
from django.conf import settings
from django.urls import path
from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

User = get_user_model()


def generate_jwt_token(user):
    """Generate JWT token for user."""
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Username and password required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        if user is not None:
            token = generate_jwt_token(user)
            user_roles = list(user.user_roles.values_list('role__name', flat=True))
            response_data = {
                'token': token,
                'user_id': str(user.id),
                'username': user.username,
                'roles': user_roles,
            }
            
            # Create audit log
            try:
                from security.models import AuditLog as SecurityAuditLog
                SecurityAuditLog.objects.create(
                    user=user,
                    username=user.username,
                    action='LOGIN',
                    model_name='User',
                    object_id=str(user.id),
                    object_repr=user.username,
                    additional_data={'username': username},
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
            except Exception:
                pass
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        # Failed login audit
        try:
            from security.models import AuditLog as SecurityAuditLog
            SecurityAuditLog.objects.create(
                user=None,
                username=username or '',
                action='LOGIN_FAILED',
                model_name='User',
                object_repr=username or '',
                additional_data={'username': username},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required', 'code': 'AUTH_003'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Create audit log
        try:
            from security.models import AuditLog as SecurityAuditLog
            SecurityAuditLog.objects.create(
                user=request.user,
                username=request.user.username,
                action='LOGOUT',
                model_name='User',
                object_id=str(request.user.id),
                object_repr=request.user.username,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return Response({'success': True, 'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_authenticated or request.user.is_anonymous:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        user = request.user
        user_roles = []
        user_permissions = []
        try:
            for ur in user.user_roles.select_related('role').all():
                user_roles.append(ur.role.name)
                for perm in ur.role.role_permissions.all():
                    if perm.permission.codename not in user_permissions:
                        user_permissions.append(perm.permission.codename)
        except Exception:
            pass
        return Response({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'roles': user_roles,
            'permissions': user_permissions,
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response({'error': 'Both old and new passwords are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(new_password)
        request.user.save()
        
        # Create audit log
        try:
            from security.models import AuditLog as SecurityAuditLog
            SecurityAuditLog.objects.create(
                user=request.user,
                username=request.user.username,
                action='UPDATE',
                model_name='User',
                object_id=str(request.user.id),
                object_repr=request.user.username,
                additional_data={'action': 'password_change'},
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass
        
        return Response({'success': True, 'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


from security.views import (
    notifications_list, notifications_mark_read, notifications_unread_count,
    users_list, users_detail, roles_list, roles_detail, permissions_list
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('notifications/', notifications_list, name='notifications-list'),
    path('notifications/read/', notifications_mark_read, name='notifications-mark-read'),
    path('notifications/unread-count/', notifications_unread_count, name='notifications-unread-count'),
    path('users/', users_list, name='users-list'),
    path('users/<uuid:user_id>/', users_detail, name='users-detail'),
    path('roles/', roles_list, name='roles-list'),
    path('roles/<int:role_id>/', roles_detail, name='roles-detail'),
    path('permissions/', permissions_list, name='permissions-list'),
]
