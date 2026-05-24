from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReturnsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'returns'
    verbose_name = _('Returns Management')

    def ready(self):
        import returns.signals  # noqa: F401 — register signal handlers