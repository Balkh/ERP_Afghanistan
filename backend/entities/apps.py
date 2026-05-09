from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class EntitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'entities'
    verbose_name = _('Business Entities')