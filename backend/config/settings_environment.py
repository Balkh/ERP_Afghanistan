"""
Environment-specific settings profiles.

Extends config/settings.py with environment-appropriate overrides.
Import conditionally based on ENV environment variable.

Usage in manage.py or wsgi.py:
    from config.settings_environment import get_environment_settings
    # merge into settings
"""
import os


ENVIRONMENT_PROFILES_VERSION = "1.0.0"


ENVIRONMENT_PROFILES = {
    "development": {
        "label": "Development",
        "DEBUG": True,
        "observability_sampling_rate": 1.0,
        "observability_blocking": True,
        "slow_request_warning_ms": 500,
        "slow_request_critical_ms": 1500,
        "SECURE_SSL_REDIRECT": False,
        "SESSION_COOKIE_SECURE": False,
        "CSRF_COOKIE_SECURE": False,
        "license_bypass": True,
        "telemetry_enabled": True,
        "rate_limiting_enabled": True,
    },
    "qa": {
        "label": "Quality Assurance",
        "DEBUG": True,
        "observability_sampling_rate": 0.5,
        "observability_blocking": False,
        "slow_request_warning_ms": 800,
        "slow_request_critical_ms": 2000,
        "SECURE_SSL_REDIRECT": False,
        "SESSION_COOKIE_SECURE": False,
        "CSRF_COOKIE_SECURE": False,
        "license_bypass": False,
        "telemetry_enabled": True,
        "rate_limiting_enabled": True,
    },
    "staging": {
        "label": "Staging",
        "DEBUG": False,
        "observability_sampling_rate": 0.25,
        "observability_blocking": False,
        "slow_request_warning_ms": 1000,
        "slow_request_critical_ms": 3000,
        "SECURE_SSL_REDIRECT": True,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "license_bypass": False,
        "telemetry_enabled": True,
        "rate_limiting_enabled": True,
    },
    "production": {
        "label": "Production",
        "DEBUG": False,
        "observability_sampling_rate": 0.1,
        "observability_blocking": False,
        "slow_request_warning_ms": 2000,
        "slow_request_critical_ms": 5000,
        "SECURE_SSL_REDIRECT": True,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "license_bypass": False,
        "telemetry_enabled": False,
        "rate_limiting_enabled": True,
    },
}

_DEFAULT_PROFILE = "development"


def detect_environment() -> str:
    """Detect current environment from ENV variable."""
    env = os.environ.get("ENV", "").lower().strip()
    if env in ENVIRONMENT_PROFILES:
        return env
    # Fallback: DEBUG mode detection
    from django.conf import settings
    if getattr(settings, "DEBUG", True):
        return "development"
    return "production"


def get_profile(name: str = "") -> dict:
    """Get environment profile settings."""
    if not name:
        name = detect_environment()
    profile = ENVIRONMENT_PROFILES.get(name, ENVIRONMENT_PROFILES[_DEFAULT_PROFILE])
    return dict(profile)


def apply_environment_overrides(settings_module) -> None:
    """Apply environment-specific overrides to a Django settings module."""
    profile = get_profile()
    for key, value in profile.items():
        if hasattr(settings_module, key):
            setattr(settings_module, key, value)
