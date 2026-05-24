"""
Tax Engine — lightweight configurable tax bracket system.

All tax brackets are loaded from Django settings (TAX_CONFIG).
No business logic hardcoding. Tax is always optional per transaction.
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Optional
from django.conf import settings


@dataclass
class TaxBracket:
    """A single tax bracket configuration."""
    rate: Decimal
    name: str
    description: str = ""
    is_default: bool = False


class TaxEngineConfig:
    """Loads tax configuration from Django settings."""

    DEFAULT_CONFIG = {
        "brackets": [
            {"rate": "0.00", "name": "No Tax", "description": "Zero tax rate", "is_default": True},
            {"rate": "2.00", "name": "Reduced", "description": "Reduced rate (2%)"},
            {"rate": "5.00", "name": "Standard", "description": "Standard rate (5%)"},
            {"rate": "10.00", "name": "Enhanced", "description": "Enhanced rate (10%)"},
        ]
    }

    @classmethod
    def get_brackets(cls) -> List[TaxBracket]:
        """Load brackets from Django settings or fall back to defaults."""
        config = getattr(settings, 'TAX_CONFIG', cls.DEFAULT_CONFIG)
        brackets_data = config.get('brackets', cls.DEFAULT_CONFIG['brackets'])
        return [
            TaxBracket(
                rate=Decimal(b['rate']),
                name=b['name'],
                description=b.get('description', ''),
                is_default=b.get('is_default', False),
            )
            for b in brackets_data
        ]

    @classmethod
    def get_default_rate(cls) -> Decimal:
        """Get the default tax rate from config."""
        brackets = cls.get_brackets()
        for b in brackets:
            if b.is_default:
                return b.rate
        return Decimal('0.00')


class TaxEngine:
    """
    Lightweight tax calculation engine.

    All rates come from TaxEngineConfig (Django settings).
    Tax is optional — callers decide whether to enable it.
    """

    @staticmethod
    def calculate_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate tax for a given amount and percentage rate."""
        if tax_rate <= Decimal('0') or amount <= Decimal('0'):
            return Decimal('0.00')
        return (amount * tax_rate / Decimal('100')).quantize(Decimal('0.01'))

    @staticmethod
    def calculate_total_with_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
        """Calculate total including tax."""
        return amount + TaxEngine.calculate_tax(amount, tax_rate)

    @staticmethod
    def validate_tax_rate(rate: Decimal) -> Optional[str]:
        """
        Validate a tax rate.
        Returns None if valid, error message string if invalid.
        """
        if rate < Decimal('0'):
            return "Tax rate cannot be negative."
        if rate > Decimal('100'):
            return "Tax rate cannot exceed 100%."
        return None

    @staticmethod
    def get_applicable_brackets(amount: Decimal) -> List[TaxBracket]:
        """
        Get applicable tax brackets for a given amount.
        Simple implementation — returns all brackets.
        Can be extended for income-based bracket logic.
        """
        if amount < Decimal('0'):
            return []
        return TaxEngineConfig.get_brackets()
