"""
Money/Currency utilities for the ERP system.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


def to_decimal(value, precision: int = 2) -> Decimal:
    """Convert value to Decimal with specified precision."""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)


def round_money(amount: Decimal, precision: int = 2) -> Decimal:
    """Round money amount to specified precision."""
    return amount.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)


def format_currency(amount: Decimal, symbol: str = '', decimal_places: int = 2) -> str:
    """Format amount as currency string."""
    formatted = f"{round_money(amount, decimal_places):,.{decimal_places}f}"
    return f"{symbol} {formatted}" if symbol else formatted


def zero_if_none(value: Optional[Decimal]) -> Decimal:
    """Return Decimal('0') if value is None."""
    if value is None:
        return Decimal('0')
    return value


def add_money(*amounts) -> Decimal:
    """Add multiple money amounts together."""
    result = Decimal('0')
    for amount in amounts:
        result += zero_if_none(amount)
    return round_money(result)


def subtract_money(amount1: Decimal, amount2: Decimal) -> Decimal:
    """Subtract two money amounts."""
    return round_money(zero_if_none(amount1) - zero_if_none(amount2))


def multiply_money(amount: Decimal, multiplier: Decimal) -> Decimal:
    """Multiply money amount by a factor."""
    return round_money(zero_if_none(amount) * zero_if_none(multiplier))


def divide_money(amount: Decimal, divisor: Decimal) -> Decimal:
    """Divide money amount by a divisor."""
    if divisor == 0:
        return Decimal('0')
    return round_money(zero_if_none(amount) / zero_if_none(divisor))


def percentage_of(amount: Decimal, total: Decimal) -> Decimal:
    """Calculate percentage: (amount / total) * 100."""
    if total == 0:
        return Decimal('0')
    return round_money((zero_if_none(amount) / zero_if_none(total)) * 100)


def apply_percentage(amount: Decimal, percent: Decimal) -> Decimal:
    """Apply percentage to amount."""
    return round_money(zero_if_none(amount) * (zero_if_none(percent) / Decimal('100')))