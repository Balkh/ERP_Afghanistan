"""
Production settings for Pharmacy ERP
Overrides default settings for packaged deployment
"""
import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_DIR = Path(os.path.dirname(sys.executable))
else:
    # Running in development
    BASE_DIR = Path(__file__).resolve().parent.parent

# Production specific settings
DEBUG = False
SECRET_KEY = os.environ.get('PHARMACY_ERP_SECRET_KEY', 'django-insecure-please-change-in-production')
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']  # Restrict in actual production

# Database configuration for production
DATABASE_DIR = BASE_DIR / 'data'
DATABASE_DIR.mkdir(exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_DIR / 'pharmacy_erp.db',
        'ATOMIC_REQUESTS': True,
    }
}

# Logging for production
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
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
            'filename': LOG_DIR / 'pharmacy_erp.log',
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'error.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'error_file'],
        'level': 'INFO',
    },
}

# Static files for production
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
] if (BASE_DIR / 'static').exists() else []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Security settings for production
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'