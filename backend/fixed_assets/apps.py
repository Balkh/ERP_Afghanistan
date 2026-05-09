from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class FixedAssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fixed_assets'
    verbose_name = _('Fixed Assets')