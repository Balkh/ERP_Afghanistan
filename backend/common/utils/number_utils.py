"""
Utility functions for number formatting and calculations.
"""
from decimal import Decimal, ROUND_HALF_UP


def format_currency(value: Decimal, currency: str = 'AFN') -> str:
    """
    Format a decimal value with currency symbol.
    
    Args:
        value: The decimal value to format
        currency: The currency code (AFN or USD)
        
    Returns:
        Formatted currency string
    """
    symbols = {
        'AFN': '؋',
        'USD': '$',
    }
    symbol = symbols.get(currency, currency)
    formatted = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f"{symbol} {formatted:,}"


def calculate_total_price(price: Decimal, quantity: Decimal) -> Decimal:
    """
    Calculate total price from unit price and quantity.
    
    Args:
        price: Unit price
        quantity: Quantity
        
    Returns:
        Total price as Decimal
    """
    return (price * quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_discount(total: Decimal, discount_percent: Decimal) -> Decimal:
    """
    Calculate discount amount from total and discount percentage.
    
    Args:
        total: Total amount before discount
        discount_percent: Discount percentage (0-100)
        
    Returns:
        Discount amount as Decimal
    """
    return (total * discount_percent / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )


def calculate_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """
    Calculate tax amount from base amount and tax rate.
    
    Args:
        amount: Base amount
        tax_rate: Tax rate percentage (0-100)
        
    Returns:
        Tax amount as Decimal
    """
    return (amount * tax_rate / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )