import jwt
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication, exceptions
from .models import Role, Permission


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT Authentication backend for Django REST Framework
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            # Extract token from "Bearer <token>" format
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            raise exceptions.AuthenticationFailed('Invalid authorization header format')

        if not token:
            return None

        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        """
        Validate JWT token and return user
        """
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

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User is inactive')

        # Attach roles and permissions to user for RBAC
        user.roles = self.get_user_roles(user)
        user.permissions = self.get_user_permissions(user)

        return (user, token)

    def get_user_roles(self, user):
        """Get roles for user"""
        # This would be implemented with a UserProfile model linking to Role
        # For now, returning empty list as placeholder
        return []

    def get_user_permissions(self, user):
        """Get permissions for user"""
        # This would aggregate permissions from user's roles
        # For now, returning empty list as placeholder
        return []


def generate_jwt_token(user):
    """
    Generate JWT access token for user.
    Expires in 24 hours.
    """
    payload = {
        'user_id': user.id,
        'email': user.email,
        'token_type': 'access',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def generate_refresh_token(user):
    """
    Generate JWT refresh token for user.
    Expires in 7 days.
    """
    payload = {
        'user_id': user.id,
        'token_type': 'refresh',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def verify_jwt_token(token, expected_type=None):
    """
    Verify and decode JWT token.
    Optionally check token_type claim.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
        if expected_type and payload.get('token_type') != expected_type:
            raise exceptions.AuthenticationFailed('Invalid token type')
        return payload
    except jwt.ExpiredSignatureError:
        raise exceptions.AuthenticationFailed('Token has expired')
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed('Invalid token')