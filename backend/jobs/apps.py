"""
Background Jobs App
Safe, lightweight, enterprise-grade async processing.
"""
from django.apps import AppConfig


class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'jobs'
    verbose_name = 'Background Jobs'
    
    def ready(self):
        """Import signals and register jobs"""
        import jobs.signals  # noqa
        import jobs.job_registry  # noqa