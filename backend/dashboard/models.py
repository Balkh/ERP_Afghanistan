import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel


class DashboardWidgetConfig(TimeStampedUUIDModel):
    """User-specific dashboard widget configuration."""

    WIDGET_TYPE_CHOICES = [
        ('KPI_CARD', _('KPI Card')),
        ('REVENUE_TREND', _('Revenue Trend')),
        ('PROFIT_TREND', _('Profit Trend')),
        ('EXPENSE_BREAKDOWN', _('Expense Breakdown')),
        ('CASH_FLOW_SUMMARY', _('Cash Flow Summary')),
        ('STOCK_VALUE_WAREHOUSE', _('Stock Value by Warehouse')),
        ('LOW_STOCK_ALERTS', _('Low Stock Alerts')),
        ('EXPIRY_RISK', _('Expiry Risk')),
        ('FAST_MOVING_PRODUCTS', _('Fast Moving Products')),
        ('TRIAL_BALANCE_SNAPSHOT', _('Trial Balance Snapshot')),
        ('LEDGER_ACTIVITY', _('Ledger Activity')),
        ('JE_VOLUME', _('Journal Entry Volume')),
        ('COST_CENTER_PERF', _('Cost Center Performance')),
        ('BUDGET_VARIANCE', _('Budget Variance')),
        ('VARIANCE_HEATMAP', _('Variance Heatmap')),
        ('AR_AGING', _('AR Aging')),
        ('AP_AGING', _('AP Aging')),
        ('TAX_LIABILITY', _('Tax Liability')),
        ('PAYROLL_SUMMARY', _('Payroll Summary')),
        ('ASSET_SUMMARY', _('Asset Summary')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_configs',
        verbose_name=_('User')
    )
    widget_type = models.CharField(
        max_length=30,
        choices=WIDGET_TYPE_CHOICES,
        verbose_name=_('Widget Type')
    )
    title = models.CharField(max_length=255, blank=True, verbose_name=_('Title'))
    position = models.IntegerField(default=0, verbose_name=_('Position'))
    size = models.CharField(max_length=20, default='MEDIUM', verbose_name=_('Size'))
    is_visible = models.BooleanField(default=True, verbose_name=_('Is Visible'))
    filter_config = models.JSONField(default=dict, blank=True, verbose_name=_('Filter Config'))

    class Meta:
        verbose_name = _('Dashboard Widget Config')
        verbose_name_plural = _('Dashboard Widget Configs')
        ordering = ['user', 'position']

    def __str__(self):
        return f"{self.user} - {self.widget_type}"


class DashboardAlert(TimeStampedUUIDModel):
    """Active alerts displayed on dashboard."""

    SEVERITY_CHOICES = [
        ('INFO', _('Info')),
        ('WARNING', _('Warning')),
        ('CRITICAL', _('Critical')),
    ]

    CATEGORY_CHOICES = [
        ('FINANCIAL', _('Financial')),
        ('INVENTORY', _('Inventory')),
        ('ACCOUNTING', _('Accounting')),
        ('BUDGET', _('Budget')),
        ('TAX', _('Tax')),
        ('PAYROLL', _('Payroll')),
        ('SYSTEM', _('System')),
    ]

    title = models.CharField(max_length=255, verbose_name=_('Title'))
    message = models.TextField(verbose_name=_('Message'))
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, verbose_name=_('Severity'))
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name=_('Category'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_acknowledged = models.BooleanField(default=False, verbose_name=_('Is Acknowledged'))
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Acknowledged By')
    )
    source_model = models.CharField(max_length=100, blank=True, verbose_name=_('Source Model'))
    source_id = models.CharField(max_length=50, blank=True, verbose_name=_('Source ID'))

    class Meta:
        verbose_name = _('Dashboard Alert')
        verbose_name_plural = _('Dashboard Alerts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', 'is_active']),
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.severity} - {self.title}"