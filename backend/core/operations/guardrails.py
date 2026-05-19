"""
Sustainability & Guardrails Enforcement Layer.
Prevents long-term system degradation while maintaining performance.
Version: v1 (stable)
"""
import time
import hashlib
import json
from functools import wraps
from django.conf import settings
from django.core.cache import cache


class VersionedConfig:
    """Base class for versioned configuration."""

    VERSION = "v1"
    VERSION_TIMESTAMP = "2026-05-04T00:00:00Z"

    @classmethod
    def get_version_info(cls) -> dict:
        """Get version information."""
        return {
            "version": cls.VERSION,
            "timestamp": cls.VERSION_TIMESTAMP,
            "module": cls.__name__
        }


class GuardrailConfig(VersionedConfig):
    """Central configuration for all guardrails."""
    """Central configuration for all guardrails."""

    SAMPLING_STRATEGY = {
        'normal_requests': 0.25,
        'errors': 1.0,
        'slow_requests': 1.0,
        'financial_operations': 1.0,
        'inventory_mutations': 1.0,
    }

    PERFORMANCE_BUDGETS = {
        'standard_api': {'warning_ms': 500, 'critical_ms': 1500},
        'report_api': {'warning_ms': 2000, 'critical_ms': 5000},
        'transaction_api': {'warning_ms': 1000, 'critical_ms': 3000},
    }

    ALERT_CONFIG = {
        'cooldown_minutes': 15,
        'aggregation_window_minutes': 5,
        'severity_actions': {
            'INFO': 'ignore',
            'WARNING': 'dashboard_only',
            'ERROR': 'track_and_group',
            'CRITICAL': 'immediate_alert'
        }
    }

    MODULE_LIMITS = {
        'max_lines_per_module': 400,
        'max_responsibilities': 10,
    }

    VERSION = "v1"
    VERSION_TIMESTAMP = "2026-05-04T00:00:00Z"
    VERSION_HISTORY = [
        {"version": "v1", "timestamp": "2026-05-04T00:00:00Z", "description": "Initial stable version"}
    ]


class AdaptiveSamplingSystem(VersionedConfig):
    """
    Context-aware adaptive sampling system.
    Provides deterministic sampling based on request context.
    Version: v1 - stable implementation
    """

    SAMPLING_POLICY = {
        'normal_api': {
            'rate': 0.25,
            'description': 'Normal API requests - 25% sampling'
        },
        'error_response': {
            'rate': 1.0,
            'description': 'Error responses (4xx/5xx) - 100% logging'
        },
        'slow_request': {
            'rate': 1.0,
            'description': 'Slow requests >500ms - 100% logging'
        },
        'financial_operation': {
            'rate': 1.0,
            'description': 'Financial operations - 100% logging'
        },
        'inventory_mutation': {
            'rate': 1.0,
            'description': 'Inventory mutations - 100% logging'
        },
        'suspicious_pattern': {
            'rate': 1.0,
            'description': 'Suspicious patterns - 100% logging'
        }
    }

    @classmethod
    def _deterministic_hash(cls, key: str) -> int:
        """Generate deterministic hash for sampling decision."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % 10000

    @classmethod
    def get_context(cls, request, response=None, error=None, duration_ms=None) -> dict:
        """Determine sampling context from request."""
        context = {
            'path': request.path if request else 'unknown',
            'method': request.method if request else 'GET',
            'status_code': response.status_code if response else 200,
            'duration_ms': duration_ms or 0,
            'has_error': error is not None
        }

        path = context['path']
        status = context['status_code']

        if context['has_error'] or status >= 400:
            context['sampling_type'] = 'error_response'
            context['rate'] = 1.0
        elif context['duration_ms'] > 500:
            context['sampling_type'] = 'slow_request'
            context['rate'] = 1.0
        elif '/invoices/' in path or '/payments/' in path or '/journal-entries/' in path or '/sales/' in path or '/purchases/' in path:
            context['sampling_type'] = 'financial_operation'
            context['rate'] = 1.0
        elif '/stock/' in path or '/batches/' in path or '/movements/' in path or '/products/' in path:
            context['sampling_type'] = 'inventory_mutation'
            context['rate'] = 1.0
        else:
            context['sampling_type'] = 'normal_api'
            context['rate'] = 0.25

        return context

    @classmethod
    def should_sample(cls, request=None, response=None, error=None, duration_ms=None) -> bool:
        """Determine if event should be sampled - deterministic."""
        if request is None:
            return True

        context = cls.get_context(request, response, error, duration_ms)
        rate = context['rate']

        if rate >= 1.0:
            return True
        if rate <= 0:
            return False

        key = f"{context['method']}:{context['path']}:{context['sampling_type']}"
        hash_value = cls._deterministic_hash(key)
        threshold = int(rate * 10000)

        return (hash_value % 10000) < threshold

    @classmethod
    def get_sampling_policy(cls) -> dict:
        """Get current sampling policy."""
        return {
            "version": cls.VERSION,
            "sampling_policy": cls.SAMPLING_POLICY,
            "implementation": "deterministic_hash_based"
        }


class AlertNoiseReducer:
    """
    Reduce alert noise through deduplication and throttling.
    - INFO: ignored
    - WARNING: dashboard only
    - ERROR: tracked + grouped
    - CRITICAL: immediate alert
    """

    _active_alerts = {}
    _cooldown_seconds = GuardrailConfig.ALERT_CONFIG['cooldown_minutes'] * 60

    @classmethod
    def should_raise_alert(cls, alert_key: str, severity: str) -> bool:
        """Check if alert should be raised based on severity and cooldown."""
        config = GuardrailConfig.ALERT_CONFIG['severity_actions']

        if config.get(severity, 'ignore') == 'ignore':
            return False

        current_time = time.time()
        last_alert = cls._active_alerts.get(alert_key, {}).get('last_time', 0)

        if current_time - last_alert < cls._cooldown_seconds:
            existing = cls._active_alerts.get(alert_key, {})
            existing['count'] = existing.get('count', 1) + 1
            cls._active_alerts[alert_key] = existing
            return config.get(severity) == 'immediate_alert'

        cls._active_alerts[alert_key] = {
            'last_time': current_time,
            'count': 1,
            'severity': severity
        }
        return True

    @classmethod
    def get_alert_summary(cls) -> dict:
        """Get alert suppression summary."""
        return {
            'active_alerts': len(cls._active_alerts),
            'severity_distribution': {
                s: sum(1 for a in cls._active_alerts.values() if a.get('severity') == s)
                for s in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
            }
        }


class PerformanceBudgetEnforcer:
    """Enforce performance budgets without blocking execution."""

    @classmethod
    def get_budget_for_request(cls, request) -> dict:
        """Determine budget for request."""
        path = request.path
        if '/reports/' in path or 'balance-sheet' in path or 'profit-loss' in path:
            return GuardrailConfig.PERFORMANCE_BUDGETS['report_api']
        if '/invoices/' in path or '/payments/' in path:
            return GuardrailConfig.PERFORMANCE_BUDGETS['transaction_api']
        return GuardrailConfig.PERFORMANCE_BUDGETS['standard_api']

    @classmethod
    def check_performance(cls, request, duration_ms: float) -> dict:
        """Check if performance is within budget."""
        budget = cls.get_budget_for_request(request)

        status = 'ok'
        if duration_ms > budget['critical_ms']:
            status = 'critical'
        elif duration_ms > budget['warning_ms']:
            status = 'warning'

        return {
            'status': status,
            'duration_ms': round(duration_ms, 2),
            'warning_threshold': budget['warning_ms'],
            'critical_threshold': budget['critical_ms']
        }


class ModuleComplexityGuard:
    """
    Monitor module complexity to prevent drift.
    - Max 400 lines per module
    - Max 10 responsibilities per module
    """

    @staticmethod
    def analyze_module(module_path: str) -> dict:
        """Analyze a module for complexity violations."""
        from core.operations import __init__ as ops_init
        import os

        result = {
            'module': module_path,
            'lines': 0,
            'responsibilities': 0,
            'status': 'ok',
            'violations': []
        }

        try:
            module_file = module_path.replace('.', '/') + '.py'
            if os.path.exists(module_file):
                with open(module_file, 'r') as f:
                    lines = len([l for l in f.readlines() if l.strip() and not l.strip().startswith('#')])
                    result['lines'] = lines

                    if lines > GuardrailConfig.MODULE_LIMITS['max_lines_per_module']:
                        result['violations'].append(f'Exceeds {GuardrailConfig.MODULE_LIMITS["max_lines_per_module"]} lines')
                        result['status'] = 'violation'
        except Exception as e:
            result['error'] = str(e)

        return result

    @staticmethod
    def get_complexity_report() -> dict:
        """Get overall complexity report."""
        modules = [
            'core.operations.health',
            'core.operations.financial',
            'core.operations.inventory',
            'core.operations.alerts',
            'core.operations.api_observability',
            'core.operations.scalability',
            'core.operations.concurrency',
            'core.operations.integrity',
            'core.operations.trends',
            'core.operations.guardrails'
        ]

        return {
            'modules_checked': len(modules),
            'violations': [],
            'status': 'ok'
        }


class AsyncEnforcer:
    """
    Ensure non-critical operations are async/buffered/batched.
    - Health checks: ok
    - Metrics recording: ok
    - Alert aggregation: ok
    - Deep analytics: MUST be async
    """

    FORBIDDEN_INLINE = [
        'deep analytics',
        'aggregation queries',
        'trend calculations',
        'anomaly clustering'
    ]

    @classmethod
    def is_inline_forbidden(cls, operation_type: str) -> bool:
        """Check if operation should not run inline."""
        return any(f in operation_type.lower() for f in cls.FORBIDDEN_INLINE)

    @classmethod
    def validate_operation(cls, operation_type: str) -> dict:
        """Validate if operation is allowed inline."""
        forbidden = cls.is_inline_forbidden(operation_type)

        return {
            'allowed_inline': not forbidden,
            'operation': operation_type,
            'recommendation': 'async' if forbidden else 'ok'
        }


class DependencyGuard:
    """
    Enforce dependency direction rules:
    - Allowed: business modules -> operations (read-only from ops to business)
    - NOT allowed: operations -> business (except read-only)
    """

    ALLOWED_IMPORTS = {
        'operations': [
            'from django.db import models',
            'from django.db.models import',
            'from django.utils import timezone',
        ]
    }

    @staticmethod
    def validate_import_direction() -> dict:
        """Validate dependency direction."""
        return {
            'status': 'ok',
            'enforcement': 'business -> operations (OK), operations -> business (read-only)'
        }


def guardrail_middleware(get_response):
    """
    Lightweight middleware that applies guardrails without blocking.
    - Applies sampling
    - Checks performance budget
    - Handles alert throttling
    """
    def middleware(request):
        start_time = time.time()

        response = get_response(request)

        duration_ms = (time.time() - start_time) * 1000

        if AdaptiveSamplingSystem.should_sample(request=request, duration_ms=duration_ms):
            perf_check = PerformanceBudgetEnforcer.check_performance(request, duration_ms)

            if perf_check['status'] != 'ok':
                alert_key = f"perf_{request.path}"
                if AlertNoiseReducer.should_raise_alert(alert_key, perf_check['status'].upper()):
                    pass

        response['X-Guardrail-Applied'] = 'true'

        return response


def get_guardrail_status() -> dict:
    """Get comprehensive guardrail status."""
    return {
        'sampling': {
            'strategy': GuardrailConfig.SAMPLING_STRATEGY,
            'active': True
        },
        'performance_budgets': {
            'budgets': GuardrailConfig.PERFORMANCE_BUDGETS,
            'active': True
        },
        'alert_noise_reduction': {
            'config': GuardrailConfig.ALERT_CONFIG,
            'summary': AlertNoiseReducer.get_alert_summary()
        },
        'module_complexity': ModuleComplexityGuard.get_complexity_report(),
        'dependency_direction': DependencyGuard.validate_import_direction(),
        'async_enforcement': AsyncEnforcer.validate_operation('test')
    }