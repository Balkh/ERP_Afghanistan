"""
Rate Limiting & Brute-Force Protection Middleware.

In-memory sliding window rate limiter for API endpoints.
Protects login endpoint from brute-force attacks and limits general API requests.

Configuration (in settings.py):
    RATE_LIMITS = {
        "login": {"max_attempts": 5, "window_seconds": 300, "lockout_seconds": 900},
        "api": {"max_requests": 100, "window_seconds": 60},
    }
"""

import time
from collections import defaultdict
from threading import Lock

from django.conf import settings
from django.http import JsonResponse
from rest_framework import status


class _RateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self):
        self._lock = Lock()
        self._attempts: dict = defaultdict(list)
        self._lockouts: dict = {}

    def is_rate_limited(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        """Check if key has exceeded rate limit within the sliding window."""
        now = time.time()
        with self._lock:
            # Clean old entries
            self._attempts[key] = [
                t for t in self._attempts[key] if now - t < window_seconds
            ]
            return len(self._attempts[key]) >= max_attempts

    def record_attempt(self, key: str) -> int:
        """Record an attempt and return current count."""
        now = time.time()
        with self._lock:
            self._attempts[key].append(now)
            return len(self._attempts[key])

    def is_locked_out(self, key: str, lockout_seconds: int) -> bool:
        """Check if key is in lockout period."""
        now = time.time()
        with self._lock:
            lockout_until = self._lockouts.get(key)
            if lockout_until and now < lockout_until:
                return True
            if lockout_until and now >= lockout_until:
                del self._lockouts[key]
            return False

    def trigger_lockout(self, key: str, lockout_seconds: int) -> None:
        """Put key into lockout period."""
        with self._lock:
            self._lockouts[key] = time.time() + lockout_seconds

    def reset(self, key: str) -> None:
        """Reset rate limit for a key (e.g., after successful login)."""
        with self._lock:
            self._attempts.pop(key, None)
            self._lockouts.pop(key, None)

    def cleanup(self, max_age: int = 3600) -> int:
        """Remove stale entries older than max_age seconds. Returns count cleaned."""
        now = time.time()
        cleaned = 0
        with self._lock:
            stale_keys = [
                k for k, v in self._attempts.items()
                if not v or (now - v[-1]) > max_age
            ]
            for k in stale_keys:
                del self._attempts[k]
                cleaned += 1
            stale_lockouts = [
                k for k, v in self._lockouts.items() if now >= v
            ]
            for k in stale_lockouts:
                del self._lockouts[k]
                cleaned += 1
        return cleaned


# Global singleton
_rate_limiter = _RateLimiter()


def get_rate_limiter() -> _RateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


class RateLimitMiddleware:
    """Django middleware that enforces rate limits on API requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self._check_rate_limit(request)
        if response:
            return response
        return self.get_response(request)

    def _check_rate_limit(self, request):
        """Check rate limits and return 429 response if exceeded."""
        rate_limits = getattr(settings, 'RATE_LIMITS', {})
        if not rate_limits:
            return None

        path = request.path
        ip = self._get_client_ip(request)

        # Login endpoint — brute-force protection
        if '/api/auth/login/' in path:
            login_config = rate_limits.get('login', {})
            max_attempts = login_config.get('max_attempts', 5)
            window = login_config.get('window_seconds', 300)
            lockout = login_config.get('lockout_seconds', 900)

            key = f"login:{ip}"

            if _rate_limiter.is_locked_out(key, lockout):
                return JsonResponse({
                    "success": False,
                    "error": {
                        "code": "AUTH_007",
                        "message": "Too many failed attempts. Please try again later."
                    }
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            if _rate_limiter.is_rate_limited(key, max_attempts, window):
                _rate_limiter.trigger_lockout(key, lockout)
                return JsonResponse({
                    "success": False,
                    "error": {
                        "code": "AUTH_007",
                        "message": f"Rate limit exceeded. Locked out for {lockout}s."
                    }
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # General API rate limiting
        api_config = rate_limits.get('api', {})
        if api_config and path.startswith('/api/'):
            max_requests = api_config.get('max_requests', 100)
            window = api_config.get('window_seconds', 60)
            key = f"api:{ip}"

            if _rate_limiter.is_rate_limited(key, max_requests, window):
                return JsonResponse({
                    "success": False,
                    "error": {
                        "code": "API_001",
                        "message": "Rate limit exceeded. Please slow down."
                    }
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            _rate_limiter.record_attempt(key)

        return None

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request, handling proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


def record_failed_login(ip: str) -> None:
    """Record a failed login attempt for rate limiting."""
    key = f"login:{ip}"
    _rate_limiter.record_attempt(key)


def reset_login_limit(ip: str) -> None:
    """Reset login rate limit after successful authentication."""
    key = f"login:{ip}"
    _rate_limiter.reset(key)


def reset_all_limits() -> None:
    """Reset all rate limits. Use only in tests."""
    _rate_limiter._attempts.clear()
    _rate_limiter._lockouts.clear()
