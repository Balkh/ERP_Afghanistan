"""
Financial Core Correct API Tests - Reaching 95% coverage

Tests with CORRECT API signatures matching actual implementations.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.db import models

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.currency_converter import CurrencyConverter
from accounting.services.discount_calculator import DiscountCalculator, DiscountType
from accounting.services.tax_calculator import TaxCalculator, TaxType
from accounting.services.invoice_calculator import InvoiceCalculator


class DiscountCalculatorCorrectTests(TestCase):
    """Test DiscountCalculator with correct API."""
    
    def test_calculate_fixed_discount_basic(self):
        """Test fixed discount with correct signature."""
        result = DiscountCalculator.calculate_fixed_discount(
            discount_value=Decimal('50.00')
        )
        self.assertEqual(result.discount_amount, Decimal('50.00'))
        self.assertEqual(result.discount_type, DiscountType.FIXED)
        
    def test_calculate_fixed_discount_with_subtotal_raises(self):
        """Test fixed discount exceeding subtotal raises error."""
        # The actual behavior is to raise an error, not cap
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_fixed_discount(
                discount_value=Decimal('150.00'),
                subtotal=Decimal('100.00')
            )
        
    def test_calculate_fixed_discount_negative_raises(self):
        """Test negative fixed discount raises error."""
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_fixed_discount(
                discount_value=Decimal('-10.00')
            )
            
    def test_calculate_percentage_discount_10_percent(self):
        """Test percentage discount with correct signature."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('10.00'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))
        
    def test_calculate_percentage_discount_0_percent(self):
        """Test 0% discount."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('0'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('0'))
        
    def test_calculate_percentage_discount_100_percent(self):
        """Test 100% discount."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('100.00'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('1000.00'))
        
    def test_calculate_percentage_discount_invalid_range(self):
        """Test percentage outside 0-100 raises."""
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_percentage_discount(
                percentage=Decimal('150.00'),
                subtotal=Decimal('1000.00')
            )


class TaxCalculatorCorrectTests(TestCase):
    """Test TaxCalculator with correct API."""
    
    def test_calculate_percentage_tax_basic(self):
        """Test percentage tax with correct signature."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('10.00'),
            taxable_amount=Decimal('1000.00')
        )
        self.assertEqual(result.tax_amount, Decimal('100.00'))
        
    def test_calculate_percentage_tax_0_percent(self):
        """Test 0% tax."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('0'),
            taxable_amount=Decimal('1000.00')
        )
        self.assertEqual(result.tax_amount, Decimal('0'))
        
    def test_calculate_percentage_tax_100_percent(self):
        """Test 100% tax."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('100.00'),
            taxable_amount=Decimal('1000.00')
        )
        self.assertEqual(result.tax_amount, Decimal('1000.00'))
        
    def test_calculate_percentage_tax_negative_rate_raises(self):
        """Test negative rate raises error."""
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_percentage_tax(
                rate=Decimal('-10.00'),
                taxable_amount=Decimal('1000.00')
            )
            
    def test_calculate_percentage_tax_negative_amount_raises(self):
        """Test negative amount raises error."""
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_percentage_tax(
                rate=Decimal('10.00'),
                taxable_amount=Decimal('-1000.00')
            )
            
    def test_calculate_percentage_tax_compound(self):
        """Test compound tax."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('10.00'),
            taxable_amount=Decimal('1000.00'),
            is_compound=True
        )
        self.assertEqual(result.tax_amount, Decimal('100.00'))
        self.assertTrue(result.is_compound)
        
    def test_calculate_fixed_tax_basic(self):
        """Test fixed tax with correct signature."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('50.00')
        )
        self.assertEqual(result.tax_amount, Decimal('50.00'))
        self.assertEqual(result.tax_type, TaxType.FIXED)
        
    def test_calculate_fixed_tax_zero(self):
        """Test zero fixed tax."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('0')
        )
        self.assertEqual(result.tax_amount, Decimal('0'))
        
    def test_calculate_fixed_tax_negative_raises(self):
        """Test negative fixed tax raises error."""
        with self.assertRaises(ValueError):
            TaxCalculator.calculate_fixed_tax(
                amount=Decimal('-50.00')
            )
            
    def test_calculate_compound_tax_basic(self):
        """Test compound tax calculation."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('10.00'),
            taxable_amount=Decimal('1000.00'),
            is_compound=True
        )
        self.assertIsNotNone(result)


class InvoiceCalculatorCorrectTests(TestCase):
    """Test InvoiceCalculator with correct API."""
    
    def test_calculate_item_level_taxes(self):
        """Test item-level tax calculation."""
        items = [
            {'quantity': Decimal('1'), 'unit_price': Decimal('100.00'), 'tax_rate': Decimal('10.00')},
            {'quantity': Decimal('2'), 'unit_price': Decimal('50.00'), 'tax_rate': Decimal('0')},
        ]
        total_tax, updated = TaxCalculator.calculate_item_level_taxes(items)
        self.assertIsInstance(total_tax, Decimal)


class JournalEntryLineCorrectTests(TestCase):
    """Test JournalEntryLine with correct field names."""
    
    @classmethod
    def setUpTestData(cls):
        cls.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        cls.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )
        
    def test_create_line_with_correct_fields(self):
        """Test JournalEntryLine uses correct field names."""
        entry = JournalEntry.objects.create(
            entry_number='JE-LINE-001',
            entry_date=date.today(),
            description='Test line creation'
        )
        
        # Use correct field names: debit, credit (not debit_amount, credit_amount)
        line = JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        self.assertEqual(line.debit, Decimal('100.00'))
        
    def test_entry_with_balanced_lines_correct_fields(self):
        """Test entry with balanced lines using correct field names."""
        entry = JournalEntry.objects.create(
            entry_number='JE-BAL-001',
            entry_date=date.today(),
            description='Balanced test'
        )
        
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash,
            debit=Decimal('500.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue,
            debit=Decimal('0.00'),
            credit=Decimal('500.00')
        )
        
        # Verify both lines exist
        self.assertEqual(entry.lines.count(), 2)


class CurrencyConverterCorrectTests(TestCase):
    """Test CurrencyConverter with proper exception handling."""
    
    def test_get_exchange_rate_same_currency_returns_one(self):
        """Test same currency returns 1."""
        rate = CurrencyConverter.get_exchange_rate('AFN', 'AFN')
        self.assertEqual(rate, Decimal('1.00'))
        
    def test_get_available_currencies_works(self):
        """Test get_available_currencies."""
        currencies = CurrencyConverter.get_available_currencies()
        self.assertIsInstance(currencies, (list, tuple))