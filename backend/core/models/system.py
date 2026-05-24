from django.db import models
from core.models.base import BaseModel


class CompanyManager(models.Manager):
    """Custom manager for Company model — enforces SSOT access pattern."""

    def active(self):
        """Return the active company. MUST be used instead of .filter().first().

        Usage:
            company = Company.objects.active()
        """
        return self.filter(is_active=True).first()


class Company(BaseModel):
    """Company model — SINGLE SOURCE OF TRUTH for all business configuration.

    ALL systems MUST access company config via: Company.objects.active()
    NEVER read from: SystemConfig, JSON files, installer config, or hardcoded values.
    """

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    tax_number = models.CharField(max_length=50, blank=True, default='')
    registration_number = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)
    default_currency = models.CharField(max_length=3, default='AFN')
    secondary_currency = models.CharField(max_length=3, default='USD')
    logo = models.ImageField(upload_to='company/logos/', blank=True, null=True)
    invoice_prefix = models.CharField(max_length=10, default='INV', blank=True)
    invoice_footer = models.TextField(blank=True, default='', help_text='Footer text on all invoices/receipts')

    objects = CompanyManager()

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']

    def __str__(self):
        return self.name


class Currency(BaseModel):
    """Currency model for multi-currency support."""
    
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, default=1.0)
    is_base = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Currency'
        verbose_name_plural = 'Currencies'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"