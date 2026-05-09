"""Workflows app configuration."""
from django.apps import AppConfig


class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workflows'
    verbose_name = 'Workflow Management'
    
    def ready(self):
        """Import signals when app is ready"""
        import workflows.signals  # noqa