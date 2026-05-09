"""
Company-Scoped QuerySet and Manager.
Automatically filters all queries by the current company context.
Usage:
    class MyModel(CompanyScopedMixin, TimeStampedUUIDModel):
        objects = CompanyScopedManager()
"""
from django.db import models
from django.db.models import Q


class CompanyScopedQuerySet(models.QuerySet):
    """
    QuerySet that automatically filters by company context.
    When TenantContext has a company_id set, all queries are scoped to that company.
    When no context is set (backward compatible), returns all data.
    """

    def _company_filter(self):
        """Build company filter based on current context."""
        from core.multitenant.context import TenantContext
        company_id = TenantContext.get_company_id()
        if company_id:
            return Q(company_id=company_id)
        return Q()

    def scoped(self):
        """
        Return queryset filtered by current company context.
        If no context is set, returns all records (backward compatible).
        """
        return self.filter(self._company_filter())

    def for_company(self, company_id: str):
        """Return queryset filtered by specific company."""
        return self.filter(company_id=company_id)

    def for_all_companies(self):
        """Return queryset for all companies (use with caution)."""
        return self.all()


class CompanyScopedManager(models.Manager):
    """
    Manager that uses CompanyScopedQuerySet.
    All queries are automatically company-scoped.
    """

    def get_queryset(self):
        return CompanyScopedQuerySet(self.model, using=self._db)

    def scoped(self):
        """Return company-scoped queryset."""
        return self.get_queryset().scoped()

    def for_company(self, company_id: str):
        """Return queryset for specific company."""
        return self.get_queryset().for_company(company_id)

    def for_all_companies(self):
        """Return queryset for all companies."""
        return self.get_queryset().for_all_companies()


class CompanyScopedMixin(models.Model):
    """
    Abstract mixin that adds company ForeignKey to a model.
    Use this on models that need company-level data isolation.

    Example:
        class SalesInvoice(CompanyScopedMixin, TimeStampedUUIDModel):
            objects = CompanyScopedManager()
            # ... other fields
    """
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.PROTECT,
        related_name='%(class)s_set',
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Company',
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['company']),
        ]

    def save(self, *args, **kwargs):
        """Auto-assign company from context if not set."""
        from core.multitenant.context import TenantContext
        if not self.company_id:
            company_id = TenantContext.get_company_id()
            if company_id:
                self.company_id = company_id
        super().save(*args, **kwargs)


class CompanyScopedModel(CompanyScopedMixin):
    """
    Full company-scoped model with CompanyScopedManager.
    Inherits both the company field and the scoped manager.

    Example:
        class Product(CompanyScopedModel):
            name = models.CharField(max_length=255)
            # Product.objects.scoped() returns only current company's products
    """

    objects = CompanyScopedManager()

    class Meta(CompanyScopedMixin.Meta):
        abstract = True
