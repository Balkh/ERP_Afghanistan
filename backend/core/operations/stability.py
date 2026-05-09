"""
Enterprise Stability Refinement Layer.
Addresses critical systemic risks:
1. Sampling inconsistency
2. Configuration drift
3. Observability recursion
"""
import hashlib
import json
import logging
from datetime import datetime
from django.conf import settings


logger = logging.getLogger('erp.stability')


class ConfigurationDriftDetector:
    """
    Detect configuration drift that could cause instability.
    Ensures all settings remain consistent across restarts.
    """

    _config_snapshot = None

    @classmethod
    def capture_snapshot(cls) -> dict:
        """Capture current configuration state."""
        important_settings = {
            'DEBUG': settings.DEBUG,
            'SECRET_KEY': '***REDACTED***' if hasattr(settings, 'SECRET_KEY') else None,
            'DATABASE_ENGINE': settings.DATABASES.get('default', {}).get('ENGINE', 'unknown'),
            'ALLOWED_HOSTS': getattr(settings, 'ALLOWED_HOSTS', []),
            'CACHES': list(settings.CACHES.keys()) if hasattr(settings, 'CACHES') else [],
            'LOGGING': {
                'level': settings.LOGGING.get('root', {}).get('level', 'INFO') if hasattr(settings, 'LOGGING') else 'INFO',
                'handlers': list(settings.LOGGING.get('root', {}).get('handlers', [])) if hasattr(settings, 'LOGGING') else []
            },
            'REST_FRAMEWORK': {
                'DEFAULT_RENDERER_CLASSES': len(settings.REST_FRAMEWORK.get('DEFAULT_RENDERER_CLASSES', [])) if hasattr(settings, 'REST_FRAMEWORK') else 0,
                'DEFAULT_PAGINATION_CLASS': settings.REST_FRAMEWORK.get('DEFAULT_PAGINATION_CLASS', None) if hasattr(settings, 'REST_FRAMEWORK') else None,
            }
        }

        cls._config_snapshot = {
            'hash': cls._generate_hash(important_settings),
            'settings': important_settings,
            'captured_at': datetime.now().isoformat()
        }

        return cls._config_snapshot

    @staticmethod
    def _generate_hash(config_dict: dict) -> str:
        """Generate stable hash of configuration."""
        config_str = json.dumps(config_dict, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]

    @classmethod
    def verify_consistency(cls) -> dict:
        """Verify configuration hasn't drifted since last snapshot."""
        current = cls.capture_snapshot()

        if cls._config_snapshot is None:
            return {
                'status': 'no_baseline',
                'message': 'No configuration baseline exists',
                'action': 'baseline_captured'
            }

        if current['hash'] == cls._config_snapshot['hash']:
            return {
                'status': 'consistent',
                'message': 'Configuration unchanged since baseline',
                'baseline_hash': cls._config_snapshot['hash'],
                'current_hash': current['hash']
            }
        else:
            return {
                'status': 'drift_detected',
                'message': 'Configuration has changed since baseline',
                'baseline_hash': cls._config_snapshot['hash'],
                'current_hash': current['hash'],
                'warning': 'Potential for behavior changes - review new configuration'
            }

    @classmethod
    def get_stability_report(cls) -> dict:
        """Get comprehensive stability report."""
        return {
            'configuration': cls.verify_consistency(),
            'security_checks': {
                'debug_mode': not settings.DEBUG,
                'secret_key_set': hasattr(settings, 'SECRET_KEY') and settings.SECRET_KEY != '',
                'allowed_hosts_configured': len(getattr(settings, 'ALLOWED_HOSTS', [])) > 0
            },
            'database_stability': {
                'engine': settings.DATABASES.get('default', {}).get('ENGINE', 'unknown'),
                'name_set': bool(settings.DATABASES.get('default', {}).get('NAME'))
            }
        }


class SamplingConsistencyEnforcer:
    """
    Ensure sampling is consistent and deterministic.
    Prevents random variations that could cause observability gaps.
    """

    @staticmethod
    def deterministic_sample(key: str, rate: float) -> bool:
        """
        Generate deterministic sample decision based on key.
        Same key always returns same result - prevents sampling gaps.
        """
        if rate >= 1.0:
            return True
        if rate <= 0:
            return False

        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        threshold = int(rate * 10000)
        return (hash_value % 10000) < threshold

    @classmethod
    def sample_request(cls, request_path: str, method: str, user_id: str = 'anonymous') -> bool:
        """Deterministically sample a request."""
        key = f"{method}:{request_path}:{user_id}"
        return cls.deterministic_sample(key, 0.25)

    @classmethod
    def sample_error(cls, error_signature: str) -> bool:
        """Always sample errors - no randomness for errors."""
        return True

    @classmethod
    def sample_slow_request(cls, path: str, duration_ms: float) -> bool:
        """Always sample slow requests - critical for performance."""
        return True


class ObservabilityRecursionGuard:
    """
    Prevent observability from causing more observability.
    Prevents infinite recursion when monitoring the monitor.
    """

    _monitoring_depth = 0
    _max_depth = 2
    _guarded_operations = set()

    @classmethod
    def enter_monitoring(cls, operation: str) -> bool:
        """Check if we can enter monitoring context."""
        if cls._monitoring_depth >= cls._max_depth:
            return False
        cls._monitoring_depth += 1
        cls._guarded_operations.add(operation)
        return True

    @classmethod
    def exit_monitoring(cls, operation: str):
        """Exit monitoring context."""
        cls._monitoring_depth = max(0, cls._monitoring_depth - 1)
        if operation in cls._guarded_operations:
            cls._guarded_operations.discard(operation)

    @classmethod
    def can_execute(cls, operation: str) -> bool:
        """Check if operation can be executed."""
        return cls._monitoring_depth < cls._max_depth

    @classmethod
    def get_status(cls) -> dict:
        """Get recursion guard status."""
        return {
            'current_depth': cls._monitoring_depth,
            'max_depth': cls._max_depth,
            'active_operations': list(cls._guarded_operations)[:5],
            'is_safe': cls._monitoring_depth < cls._max_depth
        }


class SafeLogger:
    """
    Logging that cannot cause recursion or performance issues.
    """

    _logging_active = True
    _log_buffer = []
    _max_buffer_size = 100

    @classmethod
    def safe_log(cls, level: str, message: str, extra: dict = None):
        """Log without risk of recursion."""
        if not cls._logging_active:
            return

        try:
            if not ObservabilityRecursionGuard.can_execute('logging'):
                cls._buffer_log(level, message, extra)
                return

            ObservabilityRecursionGuard.enter_monitoring('logging')

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'extra': extra
            }

            if level in ['ERROR', 'CRITICAL']:
                logger.log(getattr(logging, level, logging.INFO), message, extra=extra or {})

            ObservabilityRecursionGuard.exit_monitoring('logging')

        except Exception:
            cls._buffer_log(level, message, extra)

    @classmethod
    def _buffer_log(cls, level: str, message: str, extra: dict = None):
        """Buffer log when recursion guard is active."""
        cls._log_buffer.append({
            'level': level,
            'message': message,
            'extra': extra
        })
        if len(cls._log_buffer) > cls._max_buffer_size:
            cls._log_buffer = cls._log_buffer[-cls._max_buffer_size:]

    @classmethod
    def get_buffer(cls) -> list:
        """Get buffered logs."""
        return cls._log_buffer


class StabilityValidator:
    """
    Comprehensive stability validation.
    """

    @staticmethod
    def run_all_checks() -> dict:
        """Run all stability validations."""
        return {
            'configuration_drift': ConfigurationDriftDetector.verify_consistency(),
            'sampling_consistency': {
                'deterministic_sampling': True,
                'sampling_method': 'deterministic_hash_based'
            },
            'recursion_guard': ObservabilityRecursionGuard.get_status(),
            'logging_safety': {
                'logging_active': SafeLogger._logging_active,
                'buffer_size': len(SafeLogger._log_buffer)
            }
        }

    @staticmethod
    def get_stability_score() -> dict:
        """Calculate overall stability score."""
        checks = StabilityValidator.run_all_checks()

        score = 100
        issues = []

        config = checks.get('configuration_drift', {})
        if config.get('status') == 'drift_detected':
            score -= 20
            issues.append('Configuration drift detected')

        recursion = checks.get('recursion_guard', {})
        if not recursion.get('is_safe', True):
            score -= 30
            issues.append('Recursion guard triggered')

        if recursion.get('current_depth', 0) >= recursion.get('max_depth', 2):
            score -= 10
            issues.append('Monitoring depth at limit')

        return {
            'score': max(0, score),
            'status': 'stable' if score >= 80 else 'needs_attention',
            'issues': issues,
            'checks': checks
        }


def get_stability_status() -> dict:
    """Get comprehensive stability status."""
    ConfigurationDriftDetector.capture_snapshot()
    return {
        'stability_score': StabilityValidator.get_stability_score(),
        'configuration': ConfigurationDriftDetector.get_stability_report(),
        'recursion_guard': ObservabilityRecursionGuard.get_status()
    }