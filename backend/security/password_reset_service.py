"""
Password Reset Service — admin-initiated password reset for offline desktop app.
Admins reset user passwords from User Management, generating a temporary password.
Users must change it on next login.
"""

import secrets
from django.contrib.auth.models import User
from django.utils import timezone
from .models import AuditLog


class PasswordResetService:
    """Handles admin-initiated password reset for offline desktop ERP."""

    @classmethod
    def admin_reset(cls, admin_user: User, target_user: User) -> dict:
        """
        Admin resets a user's password. Generates a secure temporary password.
        The user must change it on next login.
        Returns: {"success": bool, "message": str, "temporary_password": str}
        """
        if not admin_user.is_superuser:
            return {"success": False, "message": "Only admins can reset passwords."}

        # Generate secure temporary password (12 chars)
        temp_password = secrets.token_urlsafe(12)

        target_user.set_password(temp_password)
        target_user.save(update_fields=['password'])

        AuditLog.objects.create(
            action='UPDATE',
            user=admin_user,
            username=admin_user.username,
            additional_data={
                'action': 'admin_password_reset',
                'target_user': target_user.username,
            },
        )

        return {
            "success": True,
            "message": f"Password reset for {target_user.username}. Temporary password generated.",
            "temporary_password": temp_password,
        }

    @classmethod
    def force_change_password(cls, user: User, new_password: str) -> dict:
        """
        User changes their own password (required after admin reset or periodic expiry).
        Returns: {"success": bool, "message": str}
        """
        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new_password, user)
        except Exception as e:
            return {"success": False, "message": str(e)}

        user.set_password(new_password)
        user.save(update_fields=['password'])

        AuditLog.objects.create(
            action='UPDATE',
            user=user,
            username=user.username,
            additional_data={'action': 'password_change'},
        )

        return {"success": True, "message": "Password changed successfully."}
