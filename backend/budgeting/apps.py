from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class BudgetingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgeting'
    verbose_name = _('Budget Management')