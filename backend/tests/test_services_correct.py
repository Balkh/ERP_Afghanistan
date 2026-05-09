"""
Service Tests with Correct Method Names
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from accounting.services.report_exporter import ReportExporter
from accounting.services.invoice_calculator import InvoiceCalculator
from accounting.services.tax_calculator import TaxCalculator
from accounting.services.discount_calculator import DiscountCalculator
from accounting.services.currency_converter import CurrencyConverter


class JournalEngineMethodTests(TestCase):
    """Test actual journal engine methods."""
    
    def test_generate_entry_number_exists(self):
        """Test generate_entry_number exists."""
        self.assertTrue(hasattr(JournalEngine, 'generate_entry_number'))
        
    def test_validate_lines_exists(self):
        """Test validate_lines exists."""
        self.assertTrue(hasattr(JournalEngine, 'validate_lines'))
        
    def test_create_entry_exists(self):
        """Test create_entry exists."""
        self.assertTrue(hasattr(JournalEngine, 'create_entry'))
        
    def test_post_entry_exists(self):
        """Test post_entry exists."""
        self.assertTrue(hasattr(JournalEngine, 'post_entry'))
        
    def test_unpost_entry_exists(self):
        """Test unpost_entry exists."""
        self.assertTrue(hasattr(JournalEngine, 'unpost_entry'))
        
    def test_reverse_entry_exists(self):
        """Test reverse_entry exists."""
        self.assertTrue(hasattr(JournalEngine, 'reverse_entry'))
        
    def test_get_account_ledger_exists(self):
        """Test get_account_ledger exists."""
        self.assertTrue(hasattr(JournalEngine, 'get_account_ledger'))


class InvoiceCalculatorMethodTests(TestCase):
    """Test actual invoice calculator methods."""
    
    def test_calculate_exists(self):
        """Test calculate method exists."""
        self.assertTrue(hasattr(InvoiceCalculator, 'calculate'))
        
    def test_calculate_simple_exists(self):
        """Test calculate_simple method exists."""
        self.assertTrue(hasattr(InvoiceCalculator, 'calculate_simple'))
        
    def test_calculate_mixed_payment_invoice_exists(self):
        """Test calculate_mixed_payment_invoice exists."""
        self.assertTrue(hasattr(InvoiceCalculator, 'calculate_mixed_payment_invoice'))
        
    def test_calculate_simple_basic(self):
        """Test calculate_simple basic."""
        result = InvoiceCalculator.calculate_simple(
            subtotal=Decimal('1000.00'),
            tax_rate=Decimal('0.10'),
            discount_rate=Decimal('0.05')
        )
        self.assertIsInstance(result, dict)
        self.assertIn('total', result)


class TaxCalculatorMethodTests(TestCase):
    """Test actual tax calculator methods."""
    
    def test_calculate_percentage_tax_exists(self):
        """Test calculate_percentage_tax exists."""
        self.assertTrue(hasattr(TaxCalculator, 'calculate_percentage_tax'))
        
    def test_calculate_fixed_tax_exists(self):
        """Test calculate_fixed_tax exists."""
        self.assertTrue(hasattr(TaxCalculator, 'calculate_fixed_tax'))
        
    def test_calculate_item_level_taxes_exists(self):
        """Test calculate_item_level_taxes exists."""
        self.assertTrue(hasattr(TaxCalculator, 'calculate_item_level_taxes'))
        
    def test_calculate_compound_tax_exists(self):
        """Test calculate_compound_tax exists."""
        self.assertTrue(hasattr(TaxCalculator, 'calculate_compound_tax'))
        
    def test_calculate_multi_tax_exists(self):
        """Test calculate_multi_tax exists."""
        self.assertTrue(hasattr(TaxCalculator, 'calculate_multi_tax'))
        
    def test_calculate_afghanistan_business_tax_exists(self):
        """Test calculate_afghanistan_business_tax exists."""
        self.assertTrue(hasattr(TaxCalculator, 'calculate_afghanistan_business_tax'))
        
    def test_calculate_percentage_tax_basic(self):
        """Test percentage tax calculation."""
        result = TaxCalculator.calculate_percentage_tax(
            amount=Decimal('1000.00'),
            rate=Decimal('0.10')
        )
        self.assertEqual(result, Decimal('100.00'))


class DiscountCalculatorMethodTests(TestCase):
    """Test actual discount calculator methods."""
    
    def test_calculate_fixed_discount_exists(self):
        """Test calculate_fixed_discount exists."""
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_fixed_discount'))
        
    def test_calculate_percentage_discount_exists(self):
        """Test calculate_percentage_discount exists."""
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_percentage_discount'))
        
    def test_calculate_tiered_discount_exists(self):
        """Test calculate_tiered_discount exists."""
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_tiered_discount'))
        
    def test_calculate_item_level_discounts_exists(self):
        """Test calculate_item_level_discounts exists."""
        self.assertTrue(hasattr(DiscountCalculator, 'calculate_item_level_discounts'))
        
    def test_calculate_percentage_discount_basic(self):
        """Test percentage discount basic."""
        result = DiscountCalculator.calculate_percentage_discount(
            subtotal=Decimal('1000.00'),
            percentage=Decimal('10')
        )
        self.assertIsInstance(result, dict)


class CurrencyConverterMethodTests(TestCase):
    """Test actual currency converter methods."""
    
    def test_get_base_currency_exists(self):
        """Test get_base_currency exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'get_base_currency'))
        
    def test_convert_exists(self):
        """Test convert exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'convert'))
        
    def test_convert_to_base_exists(self):
        """Test convert_to_base exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'convert_to_base'))
        
    def test_convert_from_base_exists(self):
        """Test convert_from_base exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'convert_from_base'))
        
    def test_calculate_mixed_payment_total_exists(self):
        """Test calculate_mixed_payment_total exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'calculate_mixed_payment_total'))
        
    def test_get_available_currencies_exists(self):
        """Test get_available_currencies exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'get_available_currencies'))
        
    def test_get_latest_rates_exists(self):
        """Test get_latest_rates exists."""
        self.assertTrue(hasattr(CurrencyConverter, 'get_latest_rates'))


class ReportExporterMethodTests(TestCase):
    """Test actual report exporter methods."""
    
    def test_export_trial_balance_csv_exists(self):
        """Test _export_trial_balance_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_trial_balance_csv'))
        
    def test_export_profit_loss_csv_exists(self):
        """Test _export_profit_loss_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_profit_loss_csv'))
        
    def test_export_balance_sheet_csv_exists(self):
        """Test _export_balance_sheet_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_balance_sheet_csv'))
        
    def test_export_ledger_csv_exists(self):
        """Test _export_ledger_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_ledger_csv'))
        
    def test_export_cash_flow_csv_exists(self):
        """Test _export_cash_flow_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_cash_flow_csv'))
        
    def test_export_ar_aging_csv_exists(self):
        """Test _export_ar_aging_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_ar_aging_csv'))
        
    def test_export_ap_aging_csv_exists(self):
        """Test _export_ap_aging_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_ap_aging_csv'))
        
    def test_export_generic_csv_exists(self):
        """Test _export_generic_csv exists."""
        self.assertTrue(hasattr(ReportExporter, '_export_generic_csv'))