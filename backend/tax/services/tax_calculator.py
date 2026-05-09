from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db import models
from django.db.models import Sum

from tax.models import TaxRate, TaxCategory


class TaxCalculationService:
    """
    Service for tax calculations using configured tax rates.
    Integrates with existing invoice tax calculator.
    """

    @staticmethod
    def get_active_rate_for_date(
        tax_date: date,
        tax_type: str = 'STANDARD'
    ) -> Optional[TaxRate]:
        """
        Get the active tax rate for a specific date.

        Args:
            tax_date: Date to check
            tax_type: Type of tax (STANDARD, REDUCED, etc.)

        Returns:
            Active TaxRate or None
        """
        rates = TaxRate.objects.filter(
            tax_type=tax_type,
            is_active=True,
            effective_from__lte=tax_date
        ).filter(
            models.Q(effective_to__isnull=True) |
            models.Q(effective_to__gte=tax_date)
        )

        return rates.first()

    @staticmethod
    def calculate_tax(
        amount: Decimal,
        tax_date: date,
        tax_type: str = 'STANDARD'
    ) -> dict:
        """
        Calculate tax for an amount using configured rates.

        Args:
            amount: Base amount
            tax_date: Date of transaction
            tax_type: Type of tax

        Returns:
            Dictionary with tax details
        """
        rate = TaxCalculationService.get_active_rate_for_date(tax_date, tax_type)

        if not rate:
            return {
                'rate': Decimal('0.00'),
                'rate_code': None,
                'tax_amount': Decimal('0.00'),
                'total_amount': amount,
                'tax_type': 'NONE'
            }

        if rate.tax_type in ['EXEMPT', 'ZERO']:
            return {
                'rate': Decimal('0.00'),
                'rate_code': rate.code,
                'tax_amount': Decimal('0.00'),
                'total_amount': amount,
                'tax_type': rate.tax_type
            }

        tax_amount = (amount * rate.rate_percentage / Decimal('100')).quantize(
            Decimal('0.01')
        )

        return {
            'rate': rate.rate_percentage,
            'rate_code': rate.code,
            'tax_amount': tax_amount,
            'total_amount': amount + tax_amount,
            'tax_type': rate.tax_type
        }

    @staticmethod
    def get_category_rate(category: TaxCategory) -> Decimal:
        """
        Get effective tax rate for a category.

        Args:
            category: TaxCategory instance

        Returns:
            Effective tax rate percentage
        """
        if category.is_exempt:
            return Decimal('0.00')

        return category.default_rate

    @staticmethod
    def validate_tax_configuration() -> List[str]:
        """
        Validate tax configuration.
        Returns list of warnings/errors.
        """
        issues = []

        active_rates = TaxRate.objects.filter(is_active=True)
        if not active_rates.exists():
            issues.append('No active tax rates configured.')

        active_categories = TaxCategory.objects.filter(is_active=True)
        if not active_categories.exists():
            issues.append('No active tax categories configured.')

        for rate in active_rates:
            if rate.effective_to and rate.effective_to < date.today():
                issues.append(f"Tax rate {rate.code} has expired.")

        return issues