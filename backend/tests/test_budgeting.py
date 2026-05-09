"""
Tests for Budget Management module.

Covers:
- Budget model
- BudgetLine model
- BudgetCalculator service
- BudgetReportingService
"""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError

from accounting.models import Account, Currency
from budgeting.models import Budget, BudgetLine
from budgeting.services.budget_calculator import BudgetCalculator
from budgeting.services.budget_reporting import BudgetReportingService


class TestHelper:
    """Helper for test data."""

    @staticmethod
    def get_currency():
        currency, _ = Currency.objects.get_or_create(
            code='AFN',
            defaults={
                'name': 'Afghan Afghani',
                'symbol': '؋',
                'is_default': True,
                'is_active': True
            }
        )
        return currency


class BudgetModelTests(TestCase):
    """Tests for Budget model."""

    def test_create_budget(self):
        """Test creating a budget."""
        budget = Budget.objects.create(
            name='Annual Budget 2025',
            fiscal_year=2025,
            period_type='ANNUAL',
            status='DRAFT',
            total_budgeted=Decimal('1000000.00')
        )
        self.assertEqual(budget.name, 'Annual Budget 2025')
        self.assertEqual(budget.fiscal_year, 2025)
        self.assertEqual(budget.status, 'DRAFT')

    def test_budget_str(self):
        """Test budget string representation."""
        budget = Budget.objects.create(
            name='Test Budget',
            fiscal_year=2025,
            status='DRAFT'
        )
        self.assertEqual(str(budget), 'Test Budget (2025)')

    def test_budget_variance(self):
        """Test budget variance calculation."""
        budget = Budget.objects.create(
            name='Test',
            fiscal_year=2025,
            total_budgeted=Decimal('100000.00'),
            total_actual=Decimal('75000.00')
        )
        self.assertEqual(budget.variance, Decimal('25000.00'))

    def test_budget_variance_percentage(self):
        """Test budget variance percentage."""
        budget = Budget.objects.create(
            name='Test',
            fiscal_year=2025,
            total_budgeted=Decimal('100000.00'),
            total_actual=Decimal('80000.00')
        )
        self.assertEqual(budget.variance_percentage, Decimal('20.00'))

    def test_invalid_fiscal_year(self):
        """Test validation rejects invalid fiscal year."""
        with self.assertRaises(ValidationError):
            budget = Budget(
                name='Test',
                fiscal_year=1999,
                status='DRAFT'
            )
            budget.full_clean()


class BudgetLineModelTests(TestCase):
    """Tests for BudgetLine model."""

    def setUp(self):
        TestHelper.get_currency()
        self.account = Account.objects.create(
            code='5000',
            name='Test Expense',
            account_type='EXPENSE',
            account_category='OPERATING_EXPENSE',
            is_active=True
        )
        self.budget = Budget.objects.create(
            name='Test Budget',
            fiscal_year=2025,
            status='DRAFT'
        )

    def test_create_budget_line(self):
        """Test creating a budget line."""
        line = BudgetLine.objects.create(
            budget=self.budget,
            account=self.account,
            period='2025',
            budgeted_amount=Decimal('50000.00')
        )
        self.assertEqual(line.budgeted_amount, Decimal('50000.00'))
        self.assertEqual(line.period, '2025')

    def test_budget_line_str(self):
        """Test budget line string representation."""
        line = BudgetLine.objects.create(
            budget=self.budget,
            account=self.account,
            period='2025',
            budgeted_amount=Decimal('10000.00')
        )
        self.assertIn('5000', str(line))
        self.assertIn('2025', str(line))

    def test_line_variance(self):
        """Test budget line variance."""
        line = BudgetLine.objects.create(
            budget=self.budget,
            account=self.account,
            period='2025',
            budgeted_amount=Decimal('10000.00'),
            actual_amount=Decimal('8000.00')
        )
        self.assertEqual(line.variance, Decimal('2000.00'))

    def test_line_variance_percentage(self):
        """Test budget line variance percentage."""
        line = BudgetLine.objects.create(
            budget=self.budget,
            account=self.account,
            period='2025',
            budgeted_amount=Decimal('10000.00'),
            actual_amount=Decimal('12000.00')
        )
        self.assertEqual(line.variance_percentage, Decimal('-20.00'))


class BudgetCalculatorTests(TestCase):
    """Tests for BudgetCalculator service."""

    def setUp(self):
        TestHelper.get_currency()
        self.expense_account = Account.objects.create(
            code='5100',
            name='Rent Expense',
            account_type='EXPENSE',
            account_category='OPERATING_EXPENSE',
            is_active=True
        )

    def test_parse_period_monthly(self):
        """Test parsing monthly period."""
        start, end = BudgetCalculator.parse_period('2025-01')
        self.assertEqual(start, date(2025, 1, 1))
        self.assertEqual(end, date(2025, 1, 31))

    def test_parse_period_quarterly(self):
        """Test parsing quarterly period."""
        start, end = BudgetCalculator.parse_period('2025-Q1')
        self.assertEqual(start, date(2025, 1, 1))
        self.assertEqual(end, date(2025, 3, 31))

    def test_parse_period_annual(self):
        """Test parsing annual period."""
        start, end = BudgetCalculator.parse_period('2025')
        self.assertEqual(start, date(2025, 1, 1))
        self.assertEqual(end, date(2025, 12, 31))

    def test_parse_period_invalid(self):
        """Test parsing invalid period returns None."""
        start, end = BudgetCalculator.parse_period('invalid')
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_validate_budget_line_valid(self):
        """Test validation with valid data."""
        errors = BudgetCalculator.validate_budget_line(
            Decimal('10000.00'),
            self.expense_account
        )
        self.assertEqual(errors, [])

    def test_validate_budget_line_negative_amount(self):
        """Test validation rejects negative amount."""
        errors = BudgetCalculator.validate_budget_line(
            Decimal('-1000.00'),
            self.expense_account
        )
        self.assertIn('Budgeted amount cannot be negative.', errors)

    def test_validate_budget_line_inactive_account(self):
        """Test validation rejects inactive account."""
        inactive = Account.objects.create(
            code='5200',
            name='Inactive',
            account_type='EXPENSE',
            is_active=False
        )
        errors = BudgetCalculator.validate_budget_line(
            Decimal('10000.00'),
            inactive
        )
        self.assertIn('Cannot budget for inactive account.', errors)

    def test_get_periods_for_year_monthly(self):
        """Test getting monthly periods."""
        periods = BudgetCalculator.get_periods_for_year(2025, 'MONTHLY')
        self.assertEqual(len(periods), 12)
        self.assertEqual(periods[0], '2025-01')
        self.assertEqual(periods[11], '2025-12')

    def test_get_periods_for_year_quarterly(self):
        """Test getting quarterly periods."""
        periods = BudgetCalculator.get_periods_for_year(2025, 'QUARTERLY')
        self.assertEqual(len(periods), 4)
        self.assertIn('2025-Q1', periods)
        self.assertIn('2025-Q4', periods)


class BudgetReportingServiceTests(TestCase):
    """Tests for BudgetReportingService."""

    def setUp(self):
        TestHelper.get_currency()
        self.expense = Account.objects.create(
            code='6000',
            name='Operating Expenses',
            account_type='EXPENSE',
            account_category='OPERATING_EXPENSE',
            is_active=True
        )
        self.budget = Budget.objects.create(
            name='2025 Budget',
            fiscal_year=2025,
            period_type='ANNUAL',
            status='APPROVED',
            total_budgeted=Decimal('120000.00')
        )

    def test_get_budget_summary(self):
        """Test getting budget summary."""
        BudgetLine.objects.create(
            budget=self.budget,
            account=self.expense,
            period='2025',
            budgeted_amount=Decimal('120000.00'),
            actual_amount=Decimal('100000.00')
        )

        summary = BudgetReportingService.get_budget_summary(self.budget)

        self.assertEqual(summary['fiscal_year'], 2025)
        self.assertEqual(summary['total_budgeted'], Decimal('120000.00'))
        self.assertEqual(summary['total_actual'], Decimal('100000.00'))
        self.assertEqual(summary['variance'], Decimal('20000.00'))
        self.assertEqual(summary['status'], 'APPROVED')

    def test_get_variance_report(self):
        """Test getting variance report."""
        BudgetLine.objects.create(
            budget=self.budget,
            account=self.expense,
            period='2025',
            budgeted_amount=Decimal('50000.00'),
            actual_amount=Decimal('60000.00')
        )

        report = BudgetReportingService.get_budget_variance_report(self.budget)

        self.assertEqual(report['total_budgeted'], Decimal('50000.00'))
        self.assertEqual(report['total_actual'], Decimal('60000.00'))
        self.assertEqual(report['over_budget_count'], 1)
        self.assertEqual(report['under_budget_count'], 0)

    def test_variance_report_with_period_filter(self):
        """Test variance report with period filter."""
        BudgetLine.objects.create(
            budget=self.budget,
            account=self.expense,
            period='2025',
            budgeted_amount=Decimal('50000.00'),
            actual_amount=Decimal('40000.00')
        )
        BudgetLine.objects.create(
            budget=self.budget,
            account=self.expense,
            period='2024',
            budgeted_amount=Decimal('50000.00'),
            actual_amount=Decimal('60000.00')
        )

        report = BudgetReportingService.get_budget_variance_report(
            self.budget,
            period='2025'
        )

        self.assertEqual(report['total_budgeted'], Decimal('50000.00'))
        self.assertEqual(len(report['lines']), 1)


class BudgetLineUpdateTests(TestCase):
    """Tests for budget line actual amount updates."""

    def setUp(self):
        TestHelper.get_currency()
        self.account = Account.objects.create(
            code='7000',
            name='Test Account',
            account_type='EXPENSE',
            is_active=True
        )
        self.budget = Budget.objects.create(
            name='Test',
            fiscal_year=2025,
            status='APPROVED'
        )

    def test_update_budget_totals(self):
        """Test updating budget totals from lines."""
        BudgetLine.objects.create(
            budget=self.budget,
            account=self.account,
            period='2025',
            budgeted_amount=Decimal('10000.00'),
            actual_amount=Decimal('8000.00')
        )
        BudgetLine.objects.create(
            budget=self.budget,
            account=self.account,
            period='2025-01',
            budgeted_amount=Decimal('5000.00'),
            actual_amount=Decimal('6000.00')
        )

        budget = BudgetCalculator.update_budget_totals(self.budget)

        self.assertEqual(budget.total_budgeted, Decimal('15000.00'))
        self.assertEqual(budget.total_actual, Decimal('14000.00'))
        self.assertEqual(budget.variance, Decimal('1000.00'))