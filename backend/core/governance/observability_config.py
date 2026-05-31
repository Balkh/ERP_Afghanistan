"""
Observability Configuration & Sampling Controller.

Controls observability verbosity based on environment profile.
Provides adaptive sampling to prevent observability from blocking business operations.
"""
import os
import random
from django.conf import settings


OBSERVABILITY_VERSION = "1.0.0"

# Sampling rates by environment profile
_SAMPLING_RATES = {
    "development": 1.0,      # 100% sampling — full visibility
    "qa": 0.5,               # 50% sampling — reduced overhead
    "staging": 0.25,         # 25% sampling — minimal
    "production": 0.1,       # 10% sampling — only critical paths
}

# Slow request thresholds by environment (ms)
_SLOW_THRESHOLDS = {
    "development": {"warning": 500, "critical": 1500},
    "qa": {"warning": 800, "critical": 2000},
    "staging": {"warning": 1000, "critical": 3000},
    "production": {"warning": 2000, "critical": 5000},
}


def get_environment_profile() -> str:
    """Detect current environment profile."""
    env = os.environ.get("ENV", "").lower()
    debug = getattr(settings, "DEBUG", True)

    if env == "production":
        return "production"
    if env == "staging":
        return "staging"
    if env == "qa" or env == "testing":
        return "qa"
    if debug or env == "development" or not env:
        return "development"
    return "production"


def get_sampling_rate(path: str = "") -> float:
    """Get sampling rate for current environment, adjusted by path."""
    profile = get_environment_profile()
    rate = _SAMPLING_RATES.get(profile, 0.1)

    # Always sample health/licensing/ops endpoints at full rate
    always_sample_prefixes = ["/api/health", "/api/licensing", "/api/ops"]
    for prefix in always_sample_prefixes:
        if path.startswith(prefix):
            return 1.0

    # Always sample slow requests
    return rate


def should_sample(path: str = "") -> bool:
    """Determine if a request should be sampled for observability."""
    rate = get_sampling_rate(path)
    return random.random() < rate


def get_slow_thresholds() -> dict:
    """Get slow request thresholds for current environment."""
    profile = get_environment_profile()
    return _SLOW_THRESHOLDS.get(profile, {"warning": 2000, "critical": 5000})


def is_observability_blocking() -> bool:
    """Check if observability should block business operations."""
    profile = get_environment_profile()
    # Only block in development mode
    return profile == "development"


def get_logger_name(path: str) -> str:
    """Determine logger name based on request path."""
    if "/api/accounting/" in path or "/api/financial" in path:
        return "erp.financial"
    if "/api/inventory/" in path:
        return "erp.inventory"
    if "/api/auth/" in path or "/api/security/" in path:
        return "erp.security"
    return "erp.api"
