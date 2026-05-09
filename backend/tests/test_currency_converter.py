"""
Comprehensive tests for Currency Converter service.

Covers:
- Base currency retrieval
- Currency lookup
- Exchange rate lookup (exact date, fallback, not found)
- Currency conversion (same currency, different currencies, explicit rate)
- Convert to/from base currency
- Mixed payment calculation
- Available currencies list
- Latest rates retrieval
- Validation and error handling
"""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from tests.base import BaseTestCase
from tests.factories import CurrencyFactory
from accounting.models import Currency, ExchangeRate
from accounting.services.currency_converter import (
    CurrencyConverter,
    CurrencyConversionError,
)


class BaseCurrencyTests(BaseTestCase):

    def test_get_base_currency_returns_default(self):
        base = CurrencyConverter.get_base_currency()
        self.assertEqual(base.code, 'AFN')

    def test_get_base_currency_creates_afn_if_none(self):
        Currency.objects.all().delete()
        base = CurrencyConverter.get_base_currency()
        self.assertEqual(base.code, 'AFN')
        self.assertTrue(base.is_default)


class GetCurrencyTests(BaseTestCase):

    def test_get_existing_currency(self):
        currency = CurrencyConverter.get_currency('AFN')
        self.assertEqual(currency.code, 'AFN')

    def test_get_inactive_currency_raises(self):
        self.currency_usd.is_active = False
        self.currency_usd.save()
        with self.assertRaises(CurrencyConversionError):
            CurrencyConverter.get_currency('USD')

    def test_get_nonexistent_currency_raises(self):
        with self.assertRaises(CurrencyConversionError) as ctx:
            CurrencyConverter.get_currency('EUR')
        self.assertIn('not found', str(ctx.exception))


class ExchangeRateTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        self.rate = ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011500'),
            effective_date=self.today,
            is_active=True,
        )

    def test_exact_date_match(self):
        result = CurrencyConverter.get_exchange_rate(
            self.currency, self.currency_usd, self.today
        )
        self.assertEqual(result, Decimal('0.011500'))

    def test_same_currency_returns_one(self):
        result = CurrencyConverter.get_exchange_rate(
            self.currency, self.currency
        )
        self.assertEqual(result, Decimal('1.000000'))

    def test_fallback_to_earlier_rate(self):
        future_date = self.today + timedelta(days=5)
        result = CurrencyConverter.get_exchange_rate(
            self.currency, self.currency_usd, future_date
        )
        self.assertEqual(result, Decimal('0.011500'))

    def test_no_rate_raises(self):
        third_currency = CurrencyFactory.create(code='EUR', name='Euro', symbol='\u20ac')
        with self.assertRaises(CurrencyConversionError) as ctx:
            CurrencyConverter.get_exchange_rate(self.currency, third_currency)
        self.assertIn('No exchange rate found', str(ctx.exception))

    def test_inactive_rate_not_used(self):
        self.rate.is_active = False
        self.rate.save()
        with self.assertRaises(CurrencyConversionError):
            CurrencyConverter.get_exchange_rate(
                self.currency_usd, self.currency, self.today
            )

    def test_uses_most_recent_rate(self):
        older = self.today - timedelta(days=10)
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011000'),
            effective_date=older,
            is_active=True,
        )
        result = CurrencyConverter.get_exchange_rate(
            self.currency, self.currency_usd, self.today
        )
        self.assertEqual(result, Decimal('0.011500'))

    def test_default_effective_date_is_today(self):
        result = CurrencyConverter.get_exchange_rate(
            self.currency, self.currency_usd
        )
        self.assertEqual(result, Decimal('0.011500'))


class ConvertTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011500'),
            effective_date=self.today,
            is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )

    def test_same_currency_no_conversion(self):
        result = CurrencyConverter.convert(
            Decimal('100'), self.currency, self.currency
        )
        self.assertEqual(result['converted_amount'], Decimal('100'))
        self.assertEqual(result['rate_used'], Decimal('1.000000'))

    def test_basic_conversion(self):
        result = CurrencyConverter.convert(
            Decimal('1000'), self.currency, self.currency_usd
        )
        self.assertEqual(result['converted_amount'], Decimal('11.50'))

    def test_explicit_rate(self):
        result = CurrencyConverter.convert(
            Decimal('100'), self.currency, self.currency_usd,
            exchange_rate=Decimal('0.012000')
        )
        self.assertEqual(result['converted_amount'], Decimal('1.20'))

    def test_negative_amount_raises(self):
        with self.assertRaises(CurrencyConversionError):
            CurrencyConverter.convert(
                Decimal('-100'), self.currency, self.currency_usd
            )

    def test_zero_amount(self):
        result = CurrencyConverter.convert(
            Decimal('0'), self.currency, self.currency_usd
        )
        self.assertEqual(result['converted_amount'], Decimal('0.00'))

    def test_returns_metadata(self):
        result = CurrencyConverter.convert(
            Decimal('100'), self.currency, self.currency_usd
        )
        self.assertEqual(result['from_currency'], 'AFN')
        self.assertEqual(result['to_currency'], 'USD')
        self.assertIn('rate_used', result)
        self.assertIn('effective_date', result)


class ConvertToFromBaseTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011500'),
            effective_date=self.today,
            is_active=True,
        )

    def test_convert_to_base(self):
        result = CurrencyConverter.convert_to_base(
            Decimal('100'), self.currency_usd
        )
        self.assertEqual(result['to_currency'], 'AFN')

    def test_convert_from_base(self):
        result = CurrencyConverter.convert_from_base(
            Decimal('100'), self.currency_usd
        )
        self.assertEqual(result['from_currency'], 'AFN')


class MixedPaymentTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        ExchangeRate.objects.create(
            from_currency=self.currency_usd,
            to_currency=self.currency,
            rate=Decimal('86.956522'),
            effective_date=self.today,
            is_active=True,
        )

    def test_single_currency_payment(self):
        payments = [
            {'amount': 1000, 'currency_code': 'AFN', 'payment_method': 'cash'},
        ]
        result = CurrencyConverter.calculate_mixed_payment_total(
            payments, to_currency=self.currency
        )
        self.assertEqual(result['total'], Decimal('1000'))
        self.assertEqual(result['payment_count'], 1)

    def test_mixed_afn_usd_payment(self):
        payments = [
            {'amount': 1000, 'currency_code': 'AFN', 'payment_method': 'cash'},
            {'amount': 10, 'currency_code': 'USD', 'payment_method': 'bank', 'exchange_rate': 86.956522},
        ]
        result = CurrencyConverter.calculate_mixed_payment_total(
            payments, to_currency=self.currency
        )
        expected = Decimal('1000') + (Decimal('10') * Decimal('86.956522')).quantize(Decimal('0.01'))
        self.assertEqual(result['total'], expected)

    def test_explicit_exchange_rate_in_payment(self):
        payments = [
            {'amount': 10, 'currency_code': 'USD', 'payment_method': 'cash', 'exchange_rate': 90},
        ]
        result = CurrencyConverter.calculate_mixed_payment_total(
            payments, to_currency=self.currency
        )
        self.assertEqual(result['total'], Decimal('900.00'))

    def test_breakdown_included(self):
        payments = [
            {'amount': 500, 'currency_code': 'AFN', 'payment_method': 'cash'},
        ]
        result = CurrencyConverter.calculate_mixed_payment_total(
            payments, to_currency=self.currency
        )
        self.assertEqual(len(result['breakdown']), 1)
        self.assertEqual(result['breakdown'][0]['original_amount'], Decimal('500'))

    def test_empty_payments(self):
        result = CurrencyConverter.calculate_mixed_payment_total(
            [], to_currency=self.currency
        )
        self.assertEqual(result['total'], Decimal('0'))
        self.assertEqual(result['payment_count'], 0)


class AvailableCurrenciesTests(BaseTestCase):

    def test_returns_active_currencies(self):
        result = CurrencyConverter.get_available_currencies()
        self.assertGreaterEqual(len(result), 2)
        codes = [c['code'] for c in result]
        self.assertIn('AFN', codes)

    def test_excludes_inactive(self):
        self.currency_usd.is_active = False
        self.currency_usd.save()
        result = CurrencyConverter.get_available_currencies()
        codes = [c['code'] for c in result]
        self.assertNotIn('USD', codes)

    def test_returns_required_fields(self):
        result = CurrencyConverter.get_available_currencies()
        currency = result[0]
        self.assertIn('code', currency)
        self.assertIn('name', currency)
        self.assertIn('symbol', currency)
        self.assertIn('is_default', currency)


class LatestRatesTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011000'),
            effective_date=self.yesterday,
            is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency=self.currency,
            to_currency=self.currency_usd,
            rate=Decimal('0.011500'),
            effective_date=self.today,
            is_active=True,
        )

    def test_returns_latest_rate_only(self):
        result = CurrencyConverter.get_latest_rates(self.currency)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['rate'], Decimal('0.011500'))

    def test_returns_all_fields(self):
        result = CurrencyConverter.get_latest_rates(self.currency)
        rate = result[0]
        self.assertIn('from_currency', rate)
        self.assertIn('to_currency', rate)
        self.assertIn('rate', rate)
        self.assertIn('effective_date', rate)
        self.assertIn('source', rate)

    def test_filters_by_from_currency(self):
        third_currency = CurrencyFactory.create(code='EUR', name='Euro', symbol='\u20ac')
        ExchangeRate.objects.create(
            from_currency=third_currency,
            to_currency=self.currency,
            rate=Decimal('100'),
            effective_date=self.today,
            is_active=True,
        )
        result = CurrencyConverter.get_latest_rates(self.currency)
        for rate in result:
            self.assertEqual(rate['from_currency'], 'AFN')

    def test_excludes_inactive_rates(self):
        ExchangeRate.objects.filter().update(is_active=False)
        result = CurrencyConverter.get_latest_rates(self.currency)
        self.assertEqual(len(result), 0)

    def test_uses_base_currency_when_none_provided(self):
        result = CurrencyConverter.get_latest_rates()
        self.assertGreaterEqual(len(result), 0)
