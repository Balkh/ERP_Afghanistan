import jwt
import uuid
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import authentication, exceptions
from .models import Role, Permission, UserRole


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT Authentication backend for Django REST Framework.
    Validates Bearer tokens, attaches roles/permissions to user.
    """

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid authorization header format')

        if not token:
            return None

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')

        # Check token blacklist
        if _is_token_blacklisted(payload.get('jti')):
            raise exceptions.AuthenticationFailed('Token has been revoked')

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User is inactive')

        # Attach roles and permissions to user for RBAC
        user.roles = self.get_user_roles(user)
        user.permissions = self.get_user_permissions(user)
        user.tenant_id = payload.get('tenant_id')
        user.ui_scopes = payload.get('ui_scopes', {})

        return (user, token)

    @staticmethod
    def get_user_roles(user):
        """Get active role names for user from UserRole model."""
        try:
            now = timezone.now()
            user_roles = UserRole.objects.filter(
                user=user,
                role__is_active=True,
            ).exclude(
                expires_at__lt=now
            ).select_related('role')
            return [ur.role.name for ur in user_roles]
        except Exception:
            return []

    @staticmethod
    def get_user_permissions(user):
        """Aggregate all permission codenames from user's active roles."""
        try:
            now = timezone.now()
            perms = Permission.objects.filter(
                permission_roles__role__role_users__user=user,
                permission_roles__role__is_active=True,
                permission_roles__role__role_users__expires_at__gt=now,
                is_active=True,
            ).distinct()
            return [p.codename for p in perms]
        except Exception:
            return []


def generate_jwt_token(user, tenant_id=None, ui_scopes=None):
    """
    Generate JWT access token for user.
    Expires in 24 hours. Includes jti for revocation.
    """
    payload = {
        'user_id': user.id,
        'email': user.email,
        'username': user.username,
        'token_type': 'access',
        'jti': str(uuid.uuid4()),
        'iat': timezone.now(),
        'exp': timezone.now() + datetime.timedelta(hours=24),
    }
    if tenant_id:
        payload['tenant_id'] = tenant_id
    if ui_scopes:
        payload['ui_scopes'] = ui_scopes
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user):
    """
    Generate JWT refresh token for user.
    Expires in 7 days. Includes jti for revocation.
    """
    payload = {
        'user_id': user.id,
        'token_type': 'refresh',
        'jti': str(uuid.uuid4()),
        'iat': timezone.now(),
        'exp': timezone.now() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def verify_jwt_token(token, expected_type=None):
    """Verify and decode JWT token. Optionally check token_type claim."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        if expected_type and payload.get('token_type') != expected_type:
            raise exceptions.AuthenticationFailed('Invalid token type')
        if _is_token_blacklisted(payload.get('jti')):
            raise exceptions.AuthenticationFailed('Token has been revoked')
        return payload
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed('Invalid token')


# ── Token Blacklist (database-backed, survives restarts) ──
# The in-memory set is retained as a fast-path cache for the current process.
# The database store is the source of truth.

_token_blacklist: set = set()
_blacklist_check_counter: int = 0


def blacklist_token(jti: str, exp: datetime.datetime = None) -> None:
    """Add a token's jti to the blacklist (persistent + in-memory cache)."""
    _token_blacklist.add(jti)
    try:
        from .models import RevokedToken
        RevokedToken.revoke(jti=jti, expires_at=exp)
    except Exception:
        pass  # Graceful degradation — in-memory cache still works


def _cleanup_token_blacklist() -> None:
    """Remove expired entries from the in-memory blacklist cache.
    
    Reloads the in-memory set from the DB to drop expired tokens.
    Called probabilistically from _is_token_blacklisted to avoid
    unbounded memory growth during long-running sessions.
    """
    from django.utils import timezone
    now = timezone.now()
    try:
        from .models import RevokedToken
        active = set(
            RevokedToken.objects.filter(
                expires_at__gt=now
            ).values_list('jti', flat=True)
        )
        _token_blacklist.clear()
        _token_blacklist.update(active)
    except Exception:
        pass


def _is_token_blacklisted(jti: str) -> bool:
    """Check if a token's jti is blacklisted (cache first, then DB)."""
    global _blacklist_check_counter
    _blacklist_check_counter += 1
    if _blacklist_check_counter >= 100:
        _blacklist_check_counter = 0
        _cleanup_token_blacklist()
    if jti in _token_blacklist:
        return True
    try:
        from .models import RevokedToken
        return RevokedToken.is_revoked(jti)
    except Exception:
        return False