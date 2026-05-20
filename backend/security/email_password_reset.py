"""Email-based password reset service for Pharmacy ERP.

Token-based self-service password reset with:
- Secure token generation and hashing
- Expiration (1 hour default)
- Single-use tokens
- Rate limiting per email/IP
- Security: never reveals whether email exists
"""
import hashlib
import hmac
import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

User = get_user_model()

RESET_TOKEN_EXPIRY_SECONDS = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRY', 3600)
RESET_RATE_LIMIT_WINDOW = 300  # 5 minutes
RESET_RATE_LIMIT_MAX = 3  # max 3 requests per window


class PasswordResetToken:
    """Secure, single-use password reset token manager."""

    @classmethod
    def generate(cls, user) -> str:
        """Generate a secure reset token for a user."""
        timestamp = str(int(time.time()))
        raw = f"{user.id}:{user.email}:{user.password}:{timestamp}:{secrets.token_hex(16)}"
        token = hashlib.sha256(raw.encode()).hexdigest()

        from security.models import PasswordResetToken as TokenModel
        TokenModel.objects.create(
            user=user,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(seconds=RESET_TOKEN_EXPIRY_SECONDS),
        )
        return token

    @classmethod
    def validate(cls, token: str) -> User | None:
        """Validate a reset token and return the user, or None if invalid."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        from security.models import PasswordResetToken as TokenModel
        try:
            token_obj = TokenModel.objects.get(
                token_hash=token_hash,
                used=False,
                expires_at__gt=timezone.now(),
            )
        except TokenModel.DoesNotExist:
            return None

        return token_obj.user

    @classmethod
    def consume(cls, token: str) -> bool:
        """Mark a token as used (single-use enforcement)."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        from security.models import PasswordResetToken as TokenModel
        try:
            token_obj = TokenModel.objects.get(
                token_hash=token_hash,
                used=False,
            )
            token_obj.used = True
            token_obj.save(update_fields=['used', 'used_at'])
            return True
        except TokenModel.DoesNotExist:
            return False


class RateLimiter:
    """Rate limiter for password reset requests."""

    _requests: dict[str, list[float]] = {}

    @classmethod
    def is_allowed(cls, key: str) -> bool:
        """Check if a reset request is allowed for this key."""
        now = time.time()
        if key not in cls._requests:
            cls._requests[key] = []

        cls._requests[key] = [
            t for t in cls._requests[key]
            if now - t < RESET_RATE_LIMIT_WINDOW
        ]

        return len(cls._requests[key]) < RESET_RATE_LIMIT_MAX

    @classmethod
    def record(cls, key: str):
        """Record a reset request."""
        now = time.time()
        if key not in cls._requests:
            cls._requests[key] = []
        cls._requests[key].append(now)

    @classmethod
    def remaining(cls, key: str) -> int:
        """Get remaining allowed requests."""
        now = time.time()
        if key not in cls._requests:
            return RESET_RATE_LIMIT_MAX
        active = [t for t in cls._requests[key] if now - t < RESET_RATE_LIMIT_WINDOW]
        return max(0, RESET_RATE_LIMIT_MAX - len(active))


class EmailPasswordResetService:
    """Email-based self-service password reset."""

    @classmethod
    def request_reset(cls, email: str, ip_address: str = '') -> dict:
        """
        Request a password reset email.

        SECURITY: Always returns success message even if email doesn't exist.
        This prevents email enumeration attacks.
        """
        rate_key = f"reset:{email}:{ip_address}"
        if not RateLimiter.is_allowed(rate_key):
            return {
                "success": False,
                "message": "Too many reset requests. Please try again later.",
                "rate_limited": True,
            }

        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user:
            RateLimiter.record(rate_key)
            token = PasswordResetToken.generate(user)
            cls._send_reset_email(user, token)

        from security.models import AuditLog
        AuditLog.objects.create(
            action='PASSWORD_RESET_REQUEST',
            username=email,
            ip_address=ip_address,
            additional_data={'email': email, 'user_found': user is not None},
        )

        return {
            "success": True,
            "message": "If an account with that email exists, a reset link has been sent.",
        }

    @classmethod
    def confirm_reset(cls, token: str, new_password: str) -> dict:
        """
        Confirm password reset with token and new password.
        """
        from django.contrib.auth.password_validation import validate_password

        user = PasswordResetToken.validate(token)
        if not user:
            return {
                "success": False,
                "message": "Invalid or expired reset token.",
                "error_code": "INVALID_TOKEN",
            }

        try:
            validate_password(new_password, user)
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "error_code": "WEAK_PASSWORD",
            }

        user.set_password(new_password)
        user.save(update_fields=['password'])

        PasswordResetToken.consume(token)

        from security.models import AuditLog
        AuditLog.objects.create(
            action='PASSWORD_RESET_CONFIRM',
            user=user,
            username=user.username,
            additional_data={'action': 'email_password_reset'},
        )

        return {
            "success": True,
            "message": "Password has been reset successfully.",
        }

    @classmethod
    def _send_reset_email(cls, user, token: str):
        """Send password reset email."""
        subject = 'Pharmacy ERP — Password Reset'
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            "You requested a password reset for your Pharmacy ERP account.\n"
            f"Use the following token to reset your password:\n\n"
            f"Token: {token}\n\n"
            "This token expires in 1 hour and can only be used once.\n"
            "If you did not request this, please ignore this email.\n"
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@pharmacy-erp.local')

        try:
            send_mail(subject, message, from_email, [user.email])
        except Exception:
            pass
