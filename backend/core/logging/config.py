"""
Logging configuration loader for Pharmacy ERP.
Environment-aware settings for development and production.
"""
import os


def is_production() -> bool:
    """Check if running in production environment."""
    return os.environ.get('DJANGO_ENV', 'development').lower() in ('production', 'prod')


def is_development() -> bool:
    """Check if running in development environment."""
    return not is_production()


def get_log_level() -> str:
    """Get log level based on environment."""
    if is_production():
        return os.environ.get('LOG_LEVEL', 'INFO')
    return os.environ.get('LOG_LEVEL', 'DEBUG')


def get_log_dir() -> str:
    """Get log directory path."""
    return os.environ.get('LOG_DIR', 'logs')


def logging_config() -> dict:
    """
    Generate Django-compatible logging configuration dictionary.
    """
    log_dir = get_log_dir()

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': 'core.logging.formatters.JSONFormatter',
            },
            'human': {
                '()': 'core.logging.formatters.HumanFormatter',
            },
            'verbose': {
                'format': '%(asctime)s %(levelname)s %(name)s %(module)s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG' if is_development() else 'WARNING',
                'class': 'logging.StreamHandler',
                'formatter': 'human' if is_development() else 'json',
            },
            'erp_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'erp.log'),
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
                'formatter': 'json' if is_production() else 'verbose',
            },
            'audit_file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'audit.log'),
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 10,
                'formatter': 'json',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'error.log'),
                'maxBytes': 10 * 1024 * 1024,
                'backupCount': 5,
                'formatter': 'json',
            },
        },
        'loggers': {
            'erp': {
                'handlers': ['console', 'erp_file'],
                'level': get_log_level(),
                'propagate': False,
            },
            'erp.audit': {
                'handlers': ['console', 'audit_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'erp.error': {
                'handlers': ['console', 'error_file'],
                'level': 'ERROR',
                'propagate': False,
            },
            'erp.financial': {
                'handlers': ['console', 'erp_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'erp.inventory': {
                'handlers': ['console', 'erp_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'erp.security': {
                'handlers': ['console', 'audit_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'erp.performance': {
                'handlers': ['console', 'erp_file'],
                'level': 'WARNING' if is_production() else 'DEBUG',
                'propagate': False,
            },
            'django': {
                'handlers': ['console', 'erp_file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['error_file'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }

    return config
