"""
Production configuration for executable deployment
Handles paths, database, and settings for packaged application
"""
import os
import sys
from pathlib import Path


def get_base_path():
    """
    Get the base path for the application
    Works in both development and PyInstaller packaged mode
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        base_path = os.path.dirname(sys.executable)
    else:
        # Running in development
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path


def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for dev and PyInstaller
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)


def get_data_path():
    """
    Get the application data directory
    In production, this will be in %%APPDATA%%\\PharmacyERP or similar
    """
    if getattr(sys, 'frozen', False):
        # Use AppData directory for user data in production
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_path = os.path.join(appdata, 'PharmacyERP', 'data')
    else:
        # Use project directory in development
        data_path = os.path.join(get_base_path(), 'data')
    
    # Create directory if it doesn't exist
    os.makedirs(data_path, exist_ok=True)
    return data_path


def get_database_path():
    """
    Get the database file path
    Uses production-safe path handling
    """
    data_path = get_data_path()
    db_filename = os.environ.get('PHARMACY_ERP_DB', 'pharmacy_erp.db')
    return os.path.join(data_path, db_filename)


def get_log_path():
    """
    Get the log directory path
    """
    if getattr(sys, 'frozen', False):
        # Use AppData directory for logs in production
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        log_path = os.path.join(appdata, 'PharmacyERP', 'logs')
    else:
        # Use project directory in development
        log_path = os.path.join(get_base_path(), 'logs')
    
    os.makedirs(log_path, exist_ok=True)
    return log_path


def get_config_path():
    """
    Get the configuration directory path
    """
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        config_path = os.path.join(appdata, 'PharmacyERP', 'config')
    else:
        config_path = os.path.join(get_base_path(), 'config')
    
    os.makedirs(config_path, exist_ok=True)
    return config_path


def get_backup_path():
    """
    Get the backup directory path
    """
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        backup_path = os.path.join(appdata, 'PharmacyERP', 'backups')
    else:
        backup_path = os.path.join(get_base_path(), 'backups')
    
    os.makedirs(backup_path, exist_ok=True)
    return backup_path


# Django production settings override
def get_django_settings():
    """
    Return Django settings for production deployment
    """
    base_path = get_base_path()
    data_path = get_data_path()
    log_path = get_log_path()
    config_path = get_config_path()
    
    settings = {
        'DATABASE_PATH': get_database_path(),
        'DEBUG': os.environ.get('PHARMACY_ERP_DEBUG', 'False').lower() == 'true',
        'SECRET_KEY': os.environ.get(
            'PHARMACY_ERP_SECRET_KEY',
            'django-insecure-please-change-in-production'
        ),
        'ALLOWED_HOSTS': os.environ.get('PHARMACY_ERP_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','),
        'LOGGING': {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                    'style': '{',
                },
            },
            'handlers': {
                'file': {
                    'level': 'INFO',
                    'class': 'logging.FileHandler',
                    'filename': os.path.join(log_path, 'django.log'),
                    'formatter': 'verbose',
                },
            },
            'root': {
                'handlers': ['file'],
                'level': 'INFO',
            },
        },
    }
    
    return settings