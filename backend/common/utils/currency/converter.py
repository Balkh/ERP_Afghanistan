"""
Currency Utilities
Provides functions for handling different currencies, particularly AFN and USD.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union, Dict
from enum import Enum

class Currency(Enum):
    """Supported currencies."""
    AFN = "AFN"  # Afghan Afghani
    USD = "USD"  # US Dollar

# Exchange rates (these should ideally come from a configuration or API)
# For now, using a fixed rate for demonstration
DEFAULT_EXCHANGE_RATES: Dict[str, Dict[str, float]] = {
    Currency.AFN.value: {
        Currency.USD.value: 0.012,  # 1 AFN = 0.012 USD
        Currency.AFN.value: 1.0
    },
    Currency.USD.value: {
        Currency.AFN.value: 83.33,  # 1 USD = 83.33 AFN
        Currency.USD.value: 1.0
    }
}

def convert_currency(amount: Union[float, int, Decimal], 
                    from_currency: Union[str, Currency], 
                    to_currency: Union[str, Currency],
                    exchange_rates: Dict[str, Dict[str, float]] = None) -> Decimal:
    """
    Convert an amount from one currency to another.
    
    Args:
        amount: The amount to convert
        from_currency: Source currency (AFN or USD)
        to_currency: Target currency (AFN or USD)
        exchange_rates: Optional custom exchange rates dictionary
        
    Returns:
        Converted amount as Decimal (rounded to 2 decimal places)
    """
    # Convert enums to strings if needed
    if isinstance(from_currency, Currency):
        from_currency = from_currency.value
    if isinstance(to_currency, Currency):
        to_currency = to_currency.value
    
    # Use provided rates or default
    rates = exchange_rates if exchange_rates is not None else DEFAULT_EXCHANGE_RATES
    
    # Validate currencies
    if from_currency not in rates:
        raise ValueError(f"Unsupported source currency: {from_currency}")
    if to_currency not in rates[from_currency]:
        raise ValueError(f"Unsupported target currency: {to_currency}")
    
    # Convert amount to Decimal for precise calculations
    amount_decimal = Decimal(str(amount))
    
    # Get exchange rate
    rate = Decimal(str(rates[from_currency][to_currency]))
    
    # Perform conversion
    converted = amount_decimal * rate
    
    # Round to 2 decimal places (standard for currency)
    return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def format_currency(amount: Union[float, int, Decimal], 
                   currency: Union[str, Currency],
                   locale: str = 'fa_IR') -> str:
    """
    Format an amount as a currency string.
    
    Args:
        amount: The amount to format
        currency: Currency code (AFN or USD)
        locale: Locale for formatting (default: fa_IR for Persian)
        
    Returns:
        Formatted currency string
    """
    # Convert enum to string if needed
    if isinstance(currency, Currency):
        currency = currency.value
    
    # Convert amount to Decimal
    amount_decimal = Decimal(str(amount))
    
    # Define currency symbols
    symbols = {
        Currency.AFN.value: "؋",  # Afghan Afghani symbol
        Currency.USD.value: "$",   # US Dollar symbol
    }
    
    # Get symbol (default to currency code if not found)
    symbol = symbols.get(currency, currency)
    
    # Format based on locale
    if locale.startswith('fa'):  # Persian/Farsi
        # In Persian, typically: amount + symbol (e.g., "1000 ₯")
        # Using Unicode for Afghani symbol: U+060B
        afani_symbol = "\u060B" if currency == Currency.AFN.value else symbol
        # Format with commas for thousands
        formatted_amount = "{:,}".format(amount_decimal.normalize())
        return f"{formatted_amount} {afani_symbol}"
    else:  # Default to Western format
        # In Western formats, typically: symbol + amount (e.g., "$1000.00")
        formatted_amount = "{:,.2f}".format(amount_decimal)
        return f"{symbol}{formatted_amount}"


def get_currency_symbol(currency: Union[str, Currency]) -> str:
    """
    Get the symbol for a currency.
    
    Args:
        currency: Currency code (AFN or USD)
        
    Returns:
        Currency symbol string
    """
    # Convert enum to string if needed
    if isinstance(currency, Currency):
        currency = currency.value
    
    symbols = {
        Currency.AFN.value: "\u060B",  # Afghan Afghani symbol (U+060B)
        Currency.USD.value: "$",       # US Dollar symbol
    }
    
    return symbols.get(currency, currency)


def get_currency_name(currency: Union[str, Currency]) -> str:
    """
    Get the full name of a currency.
    
    Args:
        currency: Currency code (AFN or USD)
        
    Returns:
        Currency name string
    """
    # Convert enum to string if needed
    if isinstance(currency, Currency):
        currency = currency.value
    
    names = {
        Currency.AFN.value: "افغانی",  # Afghan Afghani in Persian
        Currency.USD.value: "دلار آمریکا",  # US Dollar in Persian
    }
    
    return names.get(currency, currency)


def is_valid_currency(currency: str) -> bool:
    """
    Check if a currency code is valid.
    
    Args:
        currency: Currency code to check
        
    Returns:
        True if valid, False otherwise
    """
    return currency in [c.value for c in Currency]


def get_supported_currencies() -> list:
    """
    Get a list of supported currency codes.
    
    Returns:
        List of supported currency codes
    """
    return [c.value for c in Currency]