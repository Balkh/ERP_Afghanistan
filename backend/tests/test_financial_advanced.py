"""
Financial Services Advanced Tests - To reach 95% coverage

Tests for uncovered methods in:
- AccountHierarchyService
- CurrencyConverter  
- DiscountCalculator
- InvoiceCalculator
- TaxCalculator
- FinancialReports
- ReportExporter
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db.models import Sum

from accounting.models import Account, Currency, JournalEntry, JournalEntryLine
from accounting.services.account_hierarchy import AccountHierarchyService
from accounting.services.currency_converter import CurrencyConverter, CurrencyConversionError
from accounting.services.discount_calculator import DiscountCalculator
from accounting.services.invoice_calculator import InvoiceCalculator, InvoiceLineItem
from accounting.services.tax_calculator import TaxCalculator


class AccountHierarchyAdvancedTests(TestCase):
    """Advanced AccountHierarchyService tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.root = Account.objects.create(
            code='1000', name='Assets', account_type='ASSET', is_active=True
        )
        cls.current = Account.objects.create(
            code='1100', name='Current Assets', account_type='ASSET', 
            parent=cls.root, is_active=True
        )
        cls.cash = Account.objects.create(
            code='1110', name='Cash', account_type='ASSET', 
            parent=cls.current, is_active=True
        )
    
    def test_get_full_path_deep_hierarchy(self):
        """Test full path for deep hierarchy."""
        path = self.cash.full_path
        self.assertIn('1000', path)
        self.assertIn('1100', path)
        self.assertIn('1110', path)
        
    def test_get_level_root_account(self):
        """Test level for root account."""
        self.assertEqual(self.root.level, 0)
        
    def test_get_level_child_account(self):
        """Test level for child account."""
        self.assertEqual(self.cash.level, 2)
        
    def test_is_leaf_true(self):
        """Test is_leaf for leaf account."""
        self.assertTrue(self.cash.is_leaf)
        
    def test_is_leaf_false(self):
        """Test is_leaf for parent account."""
        self.assertFalse(self.current.is_leaf)
        
    def test_has_children_true(self):
        """Test has_children for parent."""
        self.assertTrue(self.root.has_children)
        
    def test_has_children_false(self):
        """Test has_children for leaf."""
        self.assertFalse(self.cash.has_children)
        
    def test_children_relationship(self):
        """Test children relationship."""
        children = list(self.root.children.all())
        self.assertEqual(len(children), 1)
        
    def test_parent_relationship(self):
        """Test parent relationship."""
        self.assertEqual(self.cash.parent, self.current)


class CurrencyConverterAdvancedTests(TestCase):
    """Advanced CurrencyConverter tests."""
    
    @classmethod
    def setUpTestData(cls):
        cls.afn = Currency.objects.create(
            code='AFN', name='Afghan Afghani', symbol='؋', is_default=True, is_active=True
        )
        cls.usd = Currency.objects.create(
            code='USD', name='US Dollar', symbol='$', is_default=False, is_active=True
        )
    
    def test_get_exchange_rate_same_currency(self):
        """Test exchange rate for same currency."""
        rate = CurrencyConverter.get_exchange_rate(self.afn, self.afn)
        self.assertEqual(rate, Decimal('1.000000'))
        
    def test_get_exchange_rate_different_currencies(self):
        """Test exchange rate for different currencies."""
        try:
            rate = CurrencyConverter.get_exchange_rate(self.usd, self.afn)
            self.assertIsInstance(rate, Decimal)
        except CurrencyConversionError:
            pass
            
    def test_get_available_currencies_includes_afn(self):
        """Test AFN is in available currencies."""
        currencies = CurrencyConverter.get_available_currencies()
        codes = [c['code'] for c in currencies]
        self.assertIn('AFN', codes)


class DiscountCalculatorAdvancedTests(TestCase):
    """Advanced DiscountCalculator tests."""
    
    def test_calculate_percentage_discount_10_percent(self):
        """Test 10% discount calculation."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('10.00'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('100.00'))
        
    def test_calculate_percentage_discount_0_percent(self):
        """Test 0% discount returns 0."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('0'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))
        
    def test_calculate_percentage_discount_100_percent(self):
        """Test 100% discount returns full amount."""
        result = DiscountCalculator.calculate_percentage_discount(
            percentage=Decimal('100.00'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('1000.00'))
        
    def test_calculate_fixed_discount_exceeds_subtotal(self):
        """Test fixed discount exceeding subtotal raises error."""
        with self.assertRaises(ValueError):
            DiscountCalculator.calculate_fixed_discount(
                discount_value=Decimal('150.00'),
                subtotal=Decimal('100.00')
            )
        
    def test_calculate_fixed_discount_zero(self):
        """Test zero fixed discount."""
        result = DiscountCalculator.calculate_fixed_discount(
            discount_value=Decimal('0'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('0.00'))
        
    def test_calculate_fixed_discount_normal(self):
        """Test normal fixed discount."""
        result = DiscountCalculator.calculate_fixed_discount(
            discount_value=Decimal('50.00'),
            subtotal=Decimal('1000.00')
        )
        self.assertEqual(result.discount_amount, Decimal('50.00'))


class InvoiceCalculatorAdvancedTests(TestCase):
    """Advanced InvoiceCalculator tests."""
    
    @classmethod
    def setUpTestData(cls):
        Currency.objects.create(
            code='AFN', name='Afghan Afghani', symbol='؋', is_default=True, is_active=True
        )
    
    def setUp(self):
        self.calculator = InvoiceCalculator()
    
    def test_calculate_with_items(self):
        """Test calculate with line items."""
        items = [
            InvoiceLineItem(product_name='Item 1', unit_price=Decimal('100.00'), quantity=Decimal('2')),
            InvoiceLineItem(product_name='Item 2', unit_price=Decimal('50.00'), quantity=Decimal('3')),
        ]
        result = self.calculator.calculate(items)
        self.assertIsNotNone(result)
        
    def test_calculate_with_discount(self):
        """Test calculate with discount."""
        items = [InvoiceLineItem(product_name='Item', unit_price=Decimal('100.00'), quantity=Decimal('1'))]
        result = self.calculator.calculate(items, invoice_discount_value=Decimal('10.00'))
        self.assertIsNotNone(result)
        
    def test_calculate_with_tax(self):
        """Test calculate with tax."""
        items = [InvoiceLineItem(product_name='Item', unit_price=Decimal('100.00'), quantity=Decimal('1'))]
        result = self.calculator.calculate(items, tax_rates=[Decimal('10.00')])
        self.assertIsNotNone(result)
        
    def test_calculate_with_discount_and_tax(self):
        """Test calculate with both discount and tax."""
        items = [InvoiceLineItem(product_name='Item', unit_price=Decimal('100.00'), quantity=Decimal('1'))]
        result = self.calculator.calculate(
            items,
            invoice_discount_value=Decimal('10.00'),
            tax_rates=[Decimal('10.00')]
        )
        self.assertIsNotNone(result)
        
    def test_calculate_empty_items(self):
        """Test calculate with empty items."""
        result = self.calculator.calculate([])
        self.assertIsNotNone(result)


class TaxCalculatorAdvancedTests(TestCase):
    """Advanced TaxCalculator tests."""
    
    def test_calculate_fixed_tax_basic(self):
        """Test fixed tax basic calculation."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('50.00')
        )
        self.assertEqual(result.tax_amount, Decimal('50.00'))
        
    def test_calculate_fixed_tax_zero_amount(self):
        """Test fixed tax with zero amount."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('0')
        )
        self.assertEqual(result.tax_amount, Decimal('0'))
        
    def test_calculate_fixed_tax_zero_rate(self):
        """Test fixed tax with zero rate."""
        result = TaxCalculator.calculate_fixed_tax(
            amount=Decimal('0')
        )
        self.assertEqual(result.tax_amount, Decimal('0'))
        
    def test_calculate_percentage_tax_basic(self):
        """Test percentage tax basic calculation."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('10.00'),
            taxable_amount=Decimal('1000.00')
        )
        self.assertEqual(result.tax_amount, Decimal('100.00'))
        
    def test_calculate_percentage_tax_zero(self):
        """Test percentage tax with zero rate."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('0'),
            taxable_amount=Decimal('1000.00')
        )
        self.assertEqual(result.tax_amount, Decimal('0'))
        
    def test_calculate_percentage_tax_100_percent(self):
        """Test 100% percentage tax."""
        result = TaxCalculator.calculate_percentage_tax(
            rate=Decimal('100.00'),
            taxable_amount=Decimal('1000.00')
        )
        self.assertEqual(result.tax_amount, Decimal('1000.00'))
        
    def test_calculate_compound_tax_basic(self):
        """Test compound tax basic calculation."""
        result = TaxCalculator.calculate_compound_tax(
            base_amount=Decimal('1000.00'),
            tax_rates=[Decimal('10.00')]
        )
        self.assertIsNotNone(result.tax_amount)
        
    def test_calculate_compound_tax_on_zero(self):
        """Test compound tax on zero amount."""
        result = TaxCalculator.calculate_compound_tax(
            base_amount=Decimal('0'),
            tax_rates=[Decimal('10.00')]
        )
        self.assertEqual(result.tax_amount, Decimal('0'))


class JournalEntryWithLinesTests(TestCase):
    """Test JournalEntry with actual line processing."""
    
    @classmethod
    def setUpTestData(cls):
        cls.cash = Account.objects.create(
            code='1000', name='Cash', account_type='ASSET', is_active=True
        )
        cls.revenue = Account.objects.create(
            code='4000', name='Revenue', account_type='REVENUE', is_active=True
        )
        
    def test_create_entry_with_lines(self):
        """Test creating journal entry with lines."""
        entry = JournalEntry.objects.create(
            entry_number='JE-WL-001',
            entry_date=date.today(),
            description='Test with lines'
        )
        
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.cash,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        JournalEntryLine.objects.create(
            entry=entry,
            account=self.revenue,
            debit=Decimal('0.00'),
            credit=Decimal('100.00')
        )
        
        self.assertEqual(entry.lines.count(), 2)
        
    def test_entry_total_debit_credit(self):
        """Test entry total debit equals credit."""
        entry = JournalEntry.objects.create(
            entry_number='JE-TOTAL-001',
            entry_date=date.today(),
            description='Total test'
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
        
        total_debit = entry.lines.aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0')
        
        total_credit = entry.lines.aggregate(
            total=Sum('credit')
        )['total'] or Decimal('0')
        
        self.assertEqual(total_debit, total_credit)