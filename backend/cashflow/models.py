import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedUUIDModel
from accounting.models import Account, Currency


class CashFlowForecast(TimeStampedUUIDModel):
    """Cash flow forecast with projections."""

    FORECAST_TYPE_CHOICES = [
        ('DAILY', _('Daily')),
        ('WEEKLY', _('Weekly')),
        ('MONTHLY', _('Monthly')),
    ]

    name = models.CharField(max_length=100, verbose_name=_('Forecast Name'))
    forecast_type = models.CharField(
        max_length=20,
        choices=FORECAST_TYPE_CHOICES,
        default='MONTHLY',
        verbose_name=_('Forecast Type')
    )
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        verbose_name=_('Currency')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Cash Flow Forecast')
        verbose_name_plural = _('Cash Flow Forecasts')
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class CashFlowItem(TimeStampedUUIDModel):
    """Individual cash flow projection item."""

    CATEGORY_CHOICES = [
        ('SALES_RECEIPT', _('Sales Receipt')),
        ('ACCOUNTS_RECEIVABLE', _('Accounts Receivable')),
        ('OTHER_INCOME', _('Other Income')),
        ('INVENTORY_PAYMENT', _('Inventory Payment')),
        ('ACCOUNTS_PAYABLE', _('Accounts Payable')),
        ('PAYROLL', _('Payroll')),
        ('OPERATING_EXPENSE', _('Operating Expense')),
        ('CAPITAL_EXPENDITURE', _('Capital Expenditure')),
        ('TAX_PAYMENT', _('Tax Payment')),
        ('LOAN_PAYMENT', _('Loan Payment')),
        ('OTHER_EXPENSE', _('Other Expense')),
    ]

    TYPE_CHOICES = [
        ('INFLOW', _('Inflow')),
        ('OUTFLOW', _('Outflow')),
    ]

    forecast = models.ForeignKey(
        CashFlowForecast,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Forecast')
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, verbose_name=_('Category'))
    item_type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name=_('Type'))
    description = models.CharField(max_length=255, verbose_name=_('Description'))
    expected_date = models.DateField(verbose_name=_('Expected Date'))
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_('Amount'))
    probability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        verbose_name=_('Probability %')
    )
    is_actual = models.BooleanField(default=False, verbose_name=_('Is Actual'))
    actual_date = models.DateField(null=True, blank=True, verbose_name=_('Actual Date'))
    actual_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Actual Amount')
    )
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Cash Flow Item')
        verbose_name_plural = _('Cash Flow Items')
        ordering = ['expected_date']
        indexes = [
            models.Index(fields=['expected_date']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.category} - {self.amount} ({self.expected_date})"

    @property
    def weighted_amount(self) -> Decimal:
        return self.amount * self.probability / 100


class CashFlowScenario(TimeStampedUUIDModel):
    """Scenario for what-if analysis."""

    SCENARIO_TYPE_CHOICES = [
        ('OPTIMISTIC', _('Optimistic')),
        ('REALISTIC', _('Realistic')),
        ('PESSIMISTIC', _('Pessimistic')),
        ('CUSTOM', _('Custom')),
    ]

    name = models.CharField(max_length=100, verbose_name=_('Scenario Name'))
    scenario_type = models.CharField(max_length=20, choices=SCENARIO_TYPE_CHOICES, verbose_name=_('Type'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name=_('Currency'))
    sales_growth_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), verbose_name=_('Sales Growth Rate %'))
    collection_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'), verbose_name=_('Collection Rate %'))
    payment_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'), verbose_name=_('Payment Rate %'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        verbose_name = _('Cash Flow Scenario')
        verbose_name_plural = _('Cash Flow Scenarios')

    def __str__(self):
        return f"{self.name} - {self.scenario_type}"