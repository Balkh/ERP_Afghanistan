from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Optional
from django.db.models import Q
from accounting.models import Currency, ExchangeRate


class CurrencyConversionError(Exception):
    """Custom exception for currency conversion errors."""
    pass


class CurrencyConverter:
    """
    Handles currency conversion with exchange rate support.
    Supports AFN, USD, and other currencies with historical rates.
    """

    @staticmethod
    def get_base_currency() -> Currency:
        """Get the system base (default) currency."""
        base_currency = Currency.objects.filter(is_default=True).first()
        if not base_currency:
            # Default to AFN if no default is set
            base_currency = Currency.objects.filter(code='AFN').first()
            if not base_currency:
                base_currency = Currency.objects.create(
                    code='AFN',
                    name='Afghan Afghani',
                    symbol='؋',
                    is_default=True,
                    is_active=True
                )
        return base_currency

    @staticmethod
    def get_currency(code: str) -> Currency:
        """Get currency by ISO code."""
        currency = Currency.objects.filter(code=code, is_active=True).first()
        if not currency:
            raise CurrencyConversionError(f'Currency {code} not found.')
        return currency

    @staticmethod
    def get_exchange_rate(
        from_currency: Currency,
        to_currency: Currency,
        effective_date: Optional[date] = None
    ) -> Decimal:
        """
        Get exchange rate between two currencies.
        
        Args:
            from_currency: Source currency
            to_currency: Target currency
            effective_date: Date for the rate (defaults to today)
            
        Returns:
            Exchange rate as Decimal
        """
        if from_currency == to_currency:
            return Decimal('1.000000')
        
        if effective_date is None:
            effective_date = date.today()
        
        # Try to find exact date match first
        rate_obj = ExchangeRate.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            effective_date=effective_date,
            is_active=True
        ).first()
        
        # If no exact match, find the most recent rate before the date
        if not rate_obj:
            rate_obj = ExchangeRate.objects.filter(
                from_currency=from_currency,
                to_currency=to_currency,
                effective_date__lte=effective_date,
                is_active=True
            ).order_by('-effective_date').first()
        
        if not rate_obj:
            raise CurrencyConversionError(
                f'No exchange rate found for {from_currency.code} to {to_currency.code} '
                f'as of {effective_date}'
            )
        
        return rate_obj.rate

    @staticmethod
    def convert(
        amount: Decimal,
        from_currency: Currency,
        to_currency: Currency,
        effective_date: Optional[date] = None,
        exchange_rate: Optional[Decimal] = None
    ) -> dict:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            effective_date: Date for the rate
            exchange_rate: Optional explicit rate to use
            
        Returns:
            Dict with converted_amount, rate_used, and metadata
        """
        if amount < 0:
            raise CurrencyConversionError('Amount cannot be negative.')
        
        if from_currency == to_currency:
            return {
                'original_amount': amount,
                'converted_amount': amount,
                'from_currency': from_currency.code,
                'to_currency': to_currency.code,
                'rate_used': Decimal('1.000000'),
                'effective_date': effective_date or date.today(),
            }
        
        if exchange_rate is None:
            exchange_rate = CurrencyConverter.get_exchange_rate(
                from_currency, to_currency, effective_date
            )
        
        converted_amount = (amount * exchange_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return {
            'original_amount': amount,
            'converted_amount': converted_amount,
            'from_currency': from_currency.code,
            'to_currency': to_currency.code,
            'rate_used': exchange_rate,
            'effective_date': effective_date or date.today(),
        }

    @staticmethod
    def convert_to_base(
        amount: Decimal,
        from_currency: Currency,
        effective_date: Optional[date] = None,
        exchange_rate: Optional[Decimal] = None
    ) -> dict:
        """
        Convert amount to base currency.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            effective_date: Date for the rate
            exchange_rate: Optional explicit rate
            
        Returns:
            Dict with conversion results
        """
        base_currency = CurrencyConverter.get_base_currency()
        return CurrencyConverter.convert(
            amount, from_currency, base_currency, effective_date, exchange_rate
        )

    @staticmethod
    def convert_from_base(
        amount: Decimal,
        to_currency: Currency,
        effective_date: Optional[date] = None,
        exchange_rate: Optional[Decimal] = None
    ) -> dict:
        """
        Convert amount from base currency to target currency.
        
        Args:
            amount: Amount in base currency
            to_currency: Target currency
            effective_date: Date for the rate
            exchange_rate: Optional explicit rate
            
        Returns:
            Dict with conversion results
        """
        base_currency = CurrencyConverter.get_base_currency()
        return CurrencyConverter.convert(
            amount, base_currency, to_currency, effective_date, exchange_rate
        )

    @staticmethod
    def calculate_mixed_payment_total(
        payments: list[dict],
        to_currency: Optional[Currency] = None,
        effective_date: Optional[date] = None
    ) -> dict:
        """
        Calculate total from mixed currency payments.
        
        Args:
            payments: List of dicts with keys:
                      - amount
                      - currency_code
                      - exchange_rate (optional)
                      - payment_method
            to_currency: Target currency for total (defaults to base)
            effective_date: Date for rates
            
        Returns:
            Dict with total in target currency and per-currency breakdown
        """
        if to_currency is None:
            to_currency = CurrencyConverter.get_base_currency()
        
        total_in_target = Decimal('0')
        breakdown = []
        
        for payment in payments:
            amount = Decimal(str(payment['amount']))
            currency = CurrencyConverter.get_currency(payment['currency_code'])
            
            conversion = CurrencyConverter.convert(
                amount,
                currency,
                to_currency,
                effective_date,
                Decimal(str(payment['exchange_rate'])) if 'exchange_rate' in payment else None
            )
            
            total_in_target += conversion['converted_amount']
            
            breakdown.append({
                'payment_method': payment.get('payment_method', 'unknown'),
                'original_amount': amount,
                'original_currency': currency.code,
                'converted_amount': conversion['converted_amount'],
                'target_currency': to_currency.code,
                'rate_used': conversion['rate_used'],
            })
        
        return {
            'total': total_in_target,
            'target_currency': to_currency.code,
            'breakdown': breakdown,
            'payment_count': len(payments),
        }

    @staticmethod
    def get_available_currencies() -> list[dict]:
        """Get list of all active currencies."""
        currencies = Currency.objects.filter(is_active=True)
        return [
            {
                'code': c.code,
                'name': c.name,
                'symbol': c.symbol,
                'is_default': c.is_default,
            }
            for c in currencies
        ]

    @staticmethod
    def get_latest_rates(
        from_currency: Optional[Currency] = None,
        to_currency: Optional[Currency] = None
    ) -> list[dict]:
        """Get latest exchange rates."""
        if from_currency is None:
            from_currency = CurrencyConverter.get_base_currency()
        
        rates = ExchangeRate.objects.filter(
            from_currency=from_currency,
            is_active=True
        ).order_by('-effective_date')
        
        # Get unique pairs (latest only)
        seen = set()
        latest_rates = []
        for rate in rates:
            key = (rate.from_currency_id, rate.to_currency_id)
            if key not in seen:
                seen.add(key)
                latest_rates.append({
                    'from_currency': rate.from_currency.code,
                    'to_currency': rate.to_currency.code,
                    'rate': rate.rate,
                    'effective_date': rate.effective_date,
                    'source': rate.source,
                })
        
        return latest_rates
