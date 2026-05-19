"""
Django AppConfig for events module.
Auto-registers event bus handlers on startup.
"""
from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.events"
    verbose_name = "Enterprise Event Bus"

    def ready(self):
        from core.events.handlers import register_all_handlers
        register_all_handlers()
