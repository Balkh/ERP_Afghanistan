"""
Enterprise Currency & Exchange Workflow Tests.
Tests AFN/USD conversions, exchange rate management, rounding, and mixed currency.
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TransactionTestCase

from accounting.models import Currency, ExchangeRate, Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.currency_converter import CurrencyConverter, CurrencyConversionError


class CurrencyModelTest(TransactionTestCase):
    """Test Currency model enterprise operations."""

    def setUp(self):
        pass

    def test_create_afn_currency(self):
        """Create AFN currency - Afghanistan's base currency."""
        afn = Currency.objects.create(
            code='AFN',
            name='Afghan Afghani',
            symbol='؋',
            is_default=True,
            is_active=True
        )
        self.assertEqual(afn.code, 'AFN')
        self.assertTrue(afn.is_default)

    def test_create_usd_currency(self):
        """Create USD currency - common for international trade."""
        usd = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            is_active=True
        )
        self.assertEqual(usd.code, 'USD')
        self.assertTrue(usd.is_active)

    def test_currency_str_representation(self):
        """Currency string shows code and symbol."""
        afn = Currency.objects.create(
            code='AFN', name='Afghani', symbol='؋', is_active=True
        )
        self.assertIn('AFN', str(afn))


class ExchangeRateModelTest(TransactionTestCase):
    """Test ExchangeRate model - critical for AFN/USD workflows."""

    def setUp(self):
        self.afn = Currency.objects.create(
            code='AFN', name='Afghan Afghani', symbol='؋', is_default=True, is_active=True
        )
        self.usd = Currency.objects.create(
            code='USD', name='US Dollar', symbol='$', is_active=True
        )

    def test_create_exchange_rate_usd_to_afn(self):
        """Create exchange rate: 1 USD = 70 AFN (typical market rate)."""
        rate = ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('70.000000'),
            effective_date=date.today(),
            is_active=True
        )
        self.assertEqual(rate.rate, Decimal('70.000000'))

    def test_exchange_rate_reverse_direction(self):
        """Create reverse rate: 1 AFN = 0.0143 USD."""
        rate = ExchangeRate.objects.create(
            from_currency=self.afn,
            to_currency=self.usd,
            rate=Decimal('0.0142857'),
            effective_date=date.today(),
            is_active=True
        )
        self.assertLess(rate.rate, Decimal('1'))

    def test_exchange_rate_with_manual_override(self):
        """Test manual rate override capability - critical for Afghanistan market."""
        rate = ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('72.500000'),
            effective_date=date.today(),
            is_active=True,
            is_manual=True
        )
        self.assertTrue(rate.is_manual)

    def test_historical_exchange_rate(self):
        """Test historical exchange rate retrieval."""
        # Create rate for past date
        past_date = date.today() - timedelta(days=30)
        ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('68.000000'),
            effective_date=past_date,
            is_active=True
        )
        # Create rate for today
        ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('70.000000'),
            effective_date=date.today(),
            is_active=True
        )

        # Should get today's rate when no specific date provided
        rates = ExchangeRate.objects.filter(
            from_currency=self.usd,
            to_currency=self.afn,
            is_active=True
        ).order_by('-effective_date')
        self.assertEqual(rates.first().rate, Decimal('70.000000'))


class CurrencyConverterServiceTest(TransactionTestCase):
    """Test CurrencyConverter service - core conversion logic."""

    def setUp(self):
        self.afn = Currency.objects.create(
            code='AFN', name='Afghan Afghani', symbol='؋', is_default=True, is_active=True
        )
        self.usd = Currency.objects.create(
            code='USD', name='US Dollar', symbol='$', is_active=True
        )
        # Create exchange rate: 1 USD = 70 AFN
        ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('70.000000'),
            effective_date=date.today(),
            is_active=True
        )

    def test_get_base_currency(self):
        """Get base currency - should return AFN."""
        base = CurrencyConverter.get_base_currency()
        self.assertEqual(base.code, 'AFN')

    def test_same_currency_conversion_returns_one(self):
        """Converting same currency returns 1."""
        rate = CurrencyConverter.get_exchange_rate(self.afn, self.afn)
        self.assertEqual(rate, Decimal('1.000000'))

    def test_get_exchange_rate_usd_to_afn(self):
        """Get USD to AFN exchange rate."""
        rate = CurrencyConverter.get_exchange_rate(self.usd, self.afn)
        self.assertEqual(rate, Decimal('70.000000'))

    def test_convert_amount_usd_to_afn(self):
        """Convert USD amount to AFN."""
        result = CurrencyConverter.convert_amount(
            Decimal('100.00'),
            self.usd,
            self.afn
        )
        self.assertEqual(result, Decimal('7000.00'))

    def test_convert_amount_afn_to_usd(self):
        """Convert AFN amount to USD."""
        # Need reverse rate
        ExchangeRate.objects.create(
            from_currency=self.afn,
            to_currency=self.usd,
            rate=Decimal('0.0142857'),
            effective_date=date.today(),
            is_active=True
        )
        result = CurrencyConverter.convert_amount(
            Decimal('7000.00'),
            self.afn,
            self.usd
        )
        self.assertEqual(result, Decimal('100.00'))

    def test_rounding_consistency(self):
        """Test rounding is consistent for financial accuracy."""
        # Convert with various amounts
        result1 = CurrencyConverter.convert_amount(Decimal('1.99'), self.usd, self.afn)
        result2 = CurrencyConverter.convert_amount(Decimal('1.999'), self.usd, self.afn)
        
        # Both should round to same precision (2 decimal places)
        self.assertEqual(result1.as_tuple().exponent, -2)
        self.assertEqual(result2.as_tuple().exponent, -2)


class MixedCurrencyPaymentTest(TransactionTestCase):
    """Test mixed currency payment workflows - critical for Afghanistan."""

    def setUp(self):
        self.cash_afn = Account.objects.create(code='1000', name='Cash AFN', account_type='ASSET', is_active=True)
        self.cash_usd = Account.objects.create(code='1001', name='Cash USD', account_type='ASSET', is_active=True)
        self.ar = Account.objects.create(code='1100', name='Accounts Receivable', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

        self.afn = Currency.objects.get(code='AFN')
        self.usd = Currency.objects.get(code='USD')

        # Rate: 1 USD = 70 AFN
        ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('70.000000'),
            effective_date=date.today(),
            is_active=True
        )

    def test_invoice_in_usd_payment_in_afn(self):
        """Test invoice in USD paid in AFN at conversion rate."""
        # Invoice for $100 USD = 7000 AFN
        lines = [
            {'account_id': str(self.ar.id), 'debit': '7000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '7000'},
        ]
        result = JournalEngine.create_entry('INVOICE', 'INV-USD-001', lines)
        JournalEngine.post_entry(result['entry_id'])

        # Payment in AFN
        lines2 = [
            {'account_id': str(self.cash_afn.id), 'debit': '7000', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '7000'},
        ]
        result2 = JournalEngine.create_entry('RECEIPT', 'RCT-USD-001', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        # Verify AR is zero
        ar_ledger = FinancialReportEngine.get_account_ledger(str(self.ar.id), date.today(), date.today())
        self.assertEqual(ar_ledger['closing_balance'], Decimal('0'))


class HawalaSettlementTest(TransactionTestCase):
    """Test Hawala-style settlement workflows common in Afghanistan."""

    def setUp(self):
        self.cash = Account.objects.create(code='1000', name='Cash', account_type='ASSET', is_active=True)
        self.hawala = Account.objects.create(code='1030', name='Hawala Payable', account_type='LIABILITY', is_active=True)
        self.ar = Account.objects.create(code='1100', name='AR', account_type='ASSET', is_active=True)
        self.sales = Account.objects.create(code='4000', name='Sales', account_type='REVENUE', is_active=True)

    def test_hawala_settlement_journal_entry(self):
        """Test hawala settlement creates proper journal entry."""
        # Invoice
        lines1 = [
            {'account_id': str(self.ar.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.sales.id), 'debit': '0', 'credit': '1000'},
        ]
        result1 = JournalEngine.create_entry('INVOICE', 'INV-HAW-001', lines1)
        JournalEngine.post_entry(result1['entry_id'])

        # Hawala settlement (through hawala agent)
        lines2 = [
            {'account_id': str(self.hawala.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.ar.id), 'debit': '0', 'credit': '1000'},
        ]
        result2 = JournalEngine.create_entry('HAWALA', 'HAW-001', lines2)
        JournalEngine.post_entry(result2['entry_id'])

        # Cash payment to hawala agent
        lines3 = [
            {'account_id': str(self.cash.id), 'debit': '1000', 'credit': '0'},
            {'account_id': str(self.hawala.id), 'debit': '0', 'credit': '1000'},
        ]
        result3 = JournalEngine.create_entry('PAYMENT', 'PAY-HAW-001', lines3)
        JournalEngine.post_entry(result3['entry_id'])

        # Verify all posted
        self.assertTrue(JournalEntry.objects.get(entry_number='INV-HAW-001').is_posted)
        self.assertTrue(JournalEntry.objects.get(entry_number='HAW-001').is_posted)
        self.assertTrue(JournalEntry.objects.get(entry_number='PAY-HAW-001').is_posted)


class CurrencyRoundingTest(TransactionTestCase):
    """Test rounding consistency for financial accuracy."""

    def setUp(self):
        self.afn = Currency.objects.create(
            code='AFN', name='Afghan Afghani', symbol='؋', is_default=True, is_active=True
        )
        self.usd = Currency.objects.create(
            code='USD', name='US Dollar', symbol='$', is_active=True
        )
        # Set rate to 70.25 to test rounding
        ExchangeRate.objects.create(
            from_currency=self.usd,
            to_currency=self.afn,
            rate=Decimal('70.250000'),
            effective_date=date.today(),
            is_active=True
        )

    def test_fractional_amount_rounding(self):
        """Test fractional amounts round correctly."""
        result = CurrencyConverter.convert_amount(Decimal('10.99'), self.usd, self.afn)
        expected = Decimal('772.25')  # 10.99 * 70.25 = 772.2475 -> 772.25
        self.assertEqual(result, expected)

    def test_zero_amount_handling(self):
        """Zero amount converts to zero."""
        result = CurrencyConverter.convert_amount(Decimal('0'), self.usd, self.afn)
        self.assertEqual(result, Decimal('0'))

    def test_large_amount_rounding(self):
        """Test large amounts round correctly."""
        result = CurrencyConverter.convert_amount(Decimal('10000.99'), self.usd, self.afn)
        # 10000.99 * 70.25 = 702569.5975 -> 702569.60
        self.assertEqual(result.as_tuple().exponent, -2)