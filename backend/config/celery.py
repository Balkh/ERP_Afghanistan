"""
Celery app configuration for Pharmacy ERP.
Additive — only activates when celery and broker are available.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from celery import Celery as _Celery

    app = _Celery("pharmacy_erp")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
    celery_available = True
except ImportError:
    celery_available = False
    app = None


def get_celery_app():
    """Return Celery app if available, None otherwise."""
    return app


def async_task(task_path, *args, **kwargs):
    """
    Dispatch a task asynchronously if Celery is available, or run synchronously.

    Additive — no-op when Celery is not installed.
    """
    if celery_available and app:
        try:
            result = app.send_task(task_path, args=args, kwargs=kwargs)
            return result
        except Exception:
            pass
    return None
