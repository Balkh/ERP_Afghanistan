"""
Cash Flow Engine Tests
"""

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.db import transaction

from cashflow.services.cashflow_engine import (
    CashFlowEngine, CashFlowCategory
)


class CashFlowCategoryTests(TestCase):
    """Test cash flow category constants."""

    def test_operating_categories_defined(self):
        """Test operating activity categories."""
        self.assertEqual(CashFlowCategory.CASH_RECEIPT_CUSTOMERS, 'CASH_RECEIPT_CUSTOMERS')
        self.assertEqual(CashFlowCategory.CASH_PAYMENT_SUPPLIERS, 'CASH_PAYMENT_SUPPLIERS')
        self.assertEqual(CashFlowCategory.CASH_PAYMENT_EMPLOYEES, 'CASH_PAYMENT_EMPLOYEES')
        self.assertEqual(CashFlowCategory.TAX_PAID, 'TAX_PAID')

    def test_investing_categories_defined(self):
        """Test investing activity categories."""
        self.assertEqual(CashFlowCategory.PURCHASE_FIXED_ASSETS, 'PURCHASE_FIXED_ASSETS')
        self.assertEqual(CashFlowCategory.SALE_FIXED_ASSETS, 'SALE_FIXED_ASSETS')
        self.assertEqual(CashFlowCategory.INVESTMENT_PURCHASE, 'INVESTMENT_PURCHASE')

    def test_financing_categories_defined(self):
        """Test financing activity categories."""
        self.assertEqual(CashFlowCategory.EQUITY_INJECTION, 'EQUITY_INJECTION')
        self.assertEqual(CashFlowCategory.DIVIDEND_PAID, 'DIVIDEND_PAID')
        self.assertEqual(CashFlowCategory.LOAN_RECEIVED, 'LOAN_RECEIVED')
        self.assertEqual(CashFlowCategory.LOAN_REPAYMENT, 'LOAN_REPAYMENT')


class CashFlowEngineTests(TestCase):
    """Test Cash Flow Engine functionality."""

    def test_engine_exists(self):
        """Test CashFlowEngine is accessible."""
        from cashflow.services.cashflow_engine import CashFlowEngine
        self.assertTrue(hasattr(CashFlowEngine, 'get_cash_flow_statement'))

    def test_classify_transaction_method_exists(self):
        """Test transaction classification method exists."""
        self.assertTrue(hasattr(CashFlowEngine, 'classify_transaction'))

    def test_classify_cash_receipt(self):
        """Test classification of cash receipt transaction."""
        result = CashFlowEngine.classify_transaction(
            '1010', '1200', Decimal('1000.00')
        )
        
        self.assertIsNotNone(result['inflow_category'])
        self.assertIsNone(result['outflow_category'])

    def test_classify_cash_payment(self):
        """Test classification of cash payment transaction."""
        result = CashFlowEngine.classify_transaction(
            '2100', '1010', Decimal('500.00')
        )
        
        self.assertIsNone(result['inflow_category'])
        self.assertIsNotNone(result['outflow_category'])

    def test_get_cash_flow_statement_method_exists(self):
        """Test statement generation method exists."""
        self.assertTrue(hasattr(CashFlowEngine, 'get_cash_flow_statement'))

    def test_get_cash_position_method_exists(self):
        """Test cash position method exists."""
        self.assertTrue(hasattr(CashFlowEngine, 'get_cash_position'))

    def test_get_cash_forecast_lightweight_method_exists(self):
        """Test lightweight forecast method exists."""
        self.assertTrue(hasattr(CashFlowEngine, 'get_cash_forecast_lightweight'))

    def test_get_daily_cash_flow_method_exists(self):
        """Test daily cash flow method exists."""
        self.assertTrue(hasattr(CashFlowEngine, 'get_daily_cash_flow'))


class CashFlowStatementTests(TestCase):
    """Test cash flow statement generation."""

    def test_get_cash_flow_statement_returns_dict(self):
        """Test statement returns proper structure."""
        result = CashFlowEngine.get_cash_flow_statement(
            date(2024, 1, 1),
            date(2024, 12, 31)
        )
        
        self.assertIn('period', result)
        self.assertIn('operating', result)
        self.assertIn('investing', result)
        self.assertIn('financing', result)
        self.assertIn('net_change', result)
        self.assertIn('opening_cash', result)
        self.assertIn('closing_cash', result)

    def test_cash_flow_statement_calculates_totals(self):
        """Test statement calculates totals."""
        result = CashFlowEngine.get_cash_flow_statement(
            date(2024, 1, 1),
            date(2024, 12, 31)
        )
        
        self.assertIsInstance(result['operating']['total'], Decimal)
        self.assertIsInstance(result['investing']['total'], Decimal)
        self.assertIsInstance(result['financing']['total'], Decimal)


class CashPositionTests(TestCase):
    """Test cash position tracking."""

    def test_get_cash_position_returns_structure(self):
        """Test cash position returns proper structure."""
        result = CashFlowEngine.get_cash_position()
        
        self.assertIn('total_cash', result)
        self.assertIn('accounts', result)
        self.assertIsInstance(result['total_cash'], Decimal)


class CashForecastLightweightTests(TestCase):
    """Test lightweight cash forecasting."""

    def test_forecast_returns_structure(self):
        """Test lightweight forecast returns proper structure."""
        result = CashFlowEngine.get_cash_forecast_lightweight(30)
        
        self.assertIn('current_cash', result)
        self.assertIn('expected_receipts', result)
        self.assertIn('expected_payments', result)
        self.assertIn('projected_cash_min', result)
        self.assertIn('forecast_days', result)

    def test_forecast_calculates_projected_cash(self):
        """Test forecast calculates projected cash."""
        result = CashFlowEngine.get_cash_forecast_lightweight(30)
        
        expected = result['current_cash'] + result['expected_receipts'] - result['expected_payments']
        
        self.assertEqual(result['projected_cash_min'], expected)


class DailyCashFlowTests(TestCase):
    """Test daily cash flow tracking."""

    def test_get_daily_cash_flow_returns_list(self):
        """Test daily cash flow returns list."""
        result = CashFlowEngine.get_daily_cash_flow(
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        
        self.assertIsInstance(result, list)

    def test_daily_cash_flow_has_required_fields(self):
        """Test daily entries have required fields."""
        result = CashFlowEngine.get_daily_cash_flow(
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        
        if len(result) > 0:
            entry = result[0]
            self.assertIn('date', entry)
            self.assertIn('receipts', entry)
            self.assertIn('payments', entry)
            self.assertIn('net', entry)


class CashFlowSummaryTests(TestCase):
    """Test cash flow summary by category."""

    def test_get_summary_by_category_method_exists(self):
        """Test summary method exists."""
        self.assertTrue(hasattr(CashFlowEngine, 'get_cash_flow_summary_by_category'))

    def test_summary_returns_structure(self):
        """Test summary returns proper structure."""
        result = CashFlowEngine.get_cash_flow_summary_by_category(
            date(2024, 1, 1),
            date(2024, 12, 31)
        )
        
        self.assertIn('receipts_by_method', result)
        self.assertIn('payments_by_method', result)
        self.assertIn('total_receipts', result)
        self.assertIn('total_payments', result)