"""
TOTP (Time-based One-Time Password) Service for 2FA.
Uses pyotp library for TOTP generation and verification.
"""

import base64
import pyotp
import qrcode
import io
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from .models import TOTPDevice


class TOTPService:
    """Handles TOTP secret generation, QR code creation, and code verification."""

    @staticmethod
    def generate_secret(user: User) -> dict:
        """
        Generate a new TOTP secret for a user.
        Returns: {"secret": str, "provisioning_uri": str, "qr_code_base64": str}
        """
        # Remove existing unconfirmed device
        try:
            existing = TOTPDevice.objects.get(user=user, is_confirmed=False)
            existing.delete()
        except TOTPDevice.DoesNotExist:
            pass

        secret = pyotp.random_base32()
        issuer = getattr(settings, 'TOTP_ISSUER', 'Pharmacy ERP')
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email or user.username,
            issuer_name=issuer
        )

        # Generate QR code as base64 PNG
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Save device (unconfirmed until user verifies)
        TOTPDevice.objects.update_or_create(
            user=user,
            defaults={
                "secret": secret,
                "is_confirmed": False,
                "failed_attempts": 0,
                "locked_until": None,
            }
        )

        return {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code_base64": qr_base64,
        }

    @staticmethod
    def verify_code(user: User, code: str) -> bool:
        """
        Verify a TOTP code. Returns True if valid.
        Handles lockout and failure tracking.
        """
        try:
            device = TOTPDevice.objects.get(user=user)
        except TOTPDevice.DoesNotExist:
            return False

        if device.is_locked:
            return False

        totp = pyotp.TOTP(device.secret)
        if totp.verify(code, valid_window=1):
            device.reset_failures()
            device.last_used_at = timezone.now()
            if not device.is_confirmed:
                device.is_confirmed = True
            device.save(update_fields=['last_used_at', 'is_confirmed', 'failed_attempts', 'locked_until'])
            return True

        device.record_failure()
        return False

    @staticmethod
    def disable(user: User) -> bool:
        """Disable TOTP for a user."""
        try:
            device = TOTPDevice.objects.get(user=user)
            device.delete()
            return True
        except TOTPDevice.DoesNotExist:
            return False

    @staticmethod
    def is_enabled(user: User) -> bool:
        """Check if TOTP is enabled and confirmed for a user."""
        try:
            device = TOTPDevice.objects.get(user=user)
            return device.is_confirmed
        except TOTPDevice.DoesNotExist:
            return False

    @staticmethod
    def requires_2fa(user: User) -> bool:
        """Check if user's role requires 2FA."""
        from .models import UserRole
        now = timezone.now()
        user_roles = UserRole.objects.filter(
            user=user,
            role__is_active=True,
        ).exclude(
            expires_at__lt=now
        ).select_related('role')
        return any(ur.role.require_2fa for ur in user_roles)
