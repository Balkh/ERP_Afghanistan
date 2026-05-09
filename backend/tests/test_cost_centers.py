"""
Tests for Cost Centers module.
"""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
import uuid as uuid_module

from accounting.models import Currency, Account
from cost_centers.models import CostCenter, CostAllocation, CostAllocationLine, CostTransaction
from cost_centers.services.cost_allocation_service import CostAllocationService
from cost_centers.services.cost_reporting_service import CostReportingService


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


class CostCenterModelTests(TestCase):
    """Tests for CostCenter model."""

    def test_create_cost_center(self):
        """Test creating a cost center."""
        cc = CostCenter.objects.create(
            name='IT Department',
            code='IT',
            cost_center_type='DEPARTMENT',
            budget=Decimal('500000.00')
        )
        self.assertEqual(cc.name, 'IT Department')
        self.assertEqual(cc.code, 'IT')

    def test_cost_center_str(self):
        """Test string representation."""
        cc = CostCenter.objects.create(
            name='Sales',
            code='SALES',
            is_active=True
        )
        self.assertIn('SALES', str(cc))

    def test_parent_validation(self):
        """Test validation rejects self-parent."""
        cc = CostCenter.objects.create(
            name='Test',
            code='TEST',
            is_active=True
        )
        cc.parent = cc
        with self.assertRaises(ValidationError):
            cc.full_clean()


class CostAllocationModelTests(TestCase):
    """Tests for CostAllocation model."""

    def setUp(self):
        TestHelper.get_currency()
        self.source = CostCenter.objects.create(
            name='Source',
            code='SRC',
            cost_center_type='DEPARTMENT'
        )
        self.target1 = CostCenter.objects.create(
            name='Target1',
            code='T1',
            cost_center_type='PROJECT'
        )
        self.target2 = CostCenter.objects.create(
            name='Target2',
            code='T2',
            cost_center_type='PROJECT'
        )

    def test_create_allocation(self):
        """Test creating allocation."""
        alloc = CostAllocation.objects.create(
            name='Test Allocation',
            source_cost_center=self.source,
            allocation_method='PERCENTAGE'
        )
        self.assertEqual(alloc.name, 'Test Allocation')

    def test_allocation_lines(self):
        """Test adding allocation lines."""
        alloc = CostAllocation.objects.create(
            name='Test',
            source_cost_center=self.source,
            allocation_method='PERCENTAGE'
        )
        CostAllocationLine.objects.create(
            allocation=alloc,
            target_cost_center=self.target1,
            percentage=Decimal('60.00')
        )
        CostAllocationLine.objects.create(
            allocation=alloc,
            target_cost_center=self.target2,
            percentage=Decimal('40.00')
        )
        self.assertEqual(alloc.lines.count(), 2)


class CostAllocationServiceTests(TestCase):
    """Tests for CostAllocationService."""

    def setUp(self):
        TestHelper.get_currency()
        self.source = CostCenter.objects.create(
            name='HQ',
            code='HQ',
            cost_center_type='DEPARTMENT'
        )
        self.dept1 = CostCenter.objects.create(
            name='Dept 1',
            code='D1',
            cost_center_type='DEPARTMENT'
        )
        self.dept2 = CostCenter.objects.create(
            name='Dept 2',
            code='D2',
            cost_center_type='DEPARTMENT'
        )
        self.allocation = CostAllocation.objects.create(
            name='Test',
            source_cost_center=self.source,
            allocation_method='PERCENTAGE',
            is_active=True
        )
        CostAllocationLine.objects.create(
            allocation=self.allocation,
            target_cost_center=self.dept1,
            percentage=Decimal('70.00')
        )
        CostAllocationLine.objects.create(
            allocation=self.allocation,
            target_cost_center=self.dept2,
            percentage=Decimal('30.00')
        )

    def test_allocate_by_percentage(self):
        """Test percentage allocation."""
        result = CostAllocationService.calculate_allocation(
            Decimal('10000.00'),
            self.allocation
        )
        self.assertEqual(result[self.dept1], Decimal('7000.00'))
        self.assertEqual(result[self.dept2], Decimal('3000.00'))

    def test_validate_allocation_invalid(self):
        """Test validation catches invalid percentages."""
        alloc = CostAllocation.objects.create(
            name='Invalid',
            source_cost_center=self.source,
            allocation_method='PERCENTAGE'
        )
        CostAllocationLine.objects.create(
            allocation=alloc,
            target_cost_center=self.dept1,
            percentage=Decimal('50.00')
        )
        issues = CostAllocationService.validate_allocation(alloc)
        self.assertIn('Percentages sum to', issues[0])

    def test_validate_allocation_valid(self):
        """Test validation passes for valid allocation."""
        issues = CostAllocationService.validate_allocation(self.allocation)
        self.assertEqual(issues, [])


class CostReportingServiceTests(TestCase):
    """Tests for CostReportingService."""

    def setUp(self):
        TestHelper.get_currency()
        self.cc = CostCenter.objects.create(
            name='Test Center',
            code='TC',
            cost_center_type='DEPARTMENT',
            budget=Decimal('100000.00'),
            is_active=True
        )

    def test_get_cost_center_summary(self):
        """Test getting cost center summary."""
        summary = CostReportingService.get_cost_center_summary(self.cc)
        self.assertEqual(summary['budget'], Decimal('100000.00'))
        self.assertEqual(summary['total_spent'], Decimal('0.00'))

    def test_get_budget_variance_report(self):
        """Test budget variance report."""
        report = CostReportingService.get_budget_variance_report()
        self.assertIsInstance(report, list)

    def test_get_all_centers_summary(self):
        """Test getting all centers summary."""
        summaries = CostReportingService.get_all_centers_summary()
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]['budget'], Decimal('100000.00'))


class CostTransactionModelTests(TestCase):
    """Tests for CostTransaction model."""

    def setUp(self):
        TestHelper.get_currency()
        self.cc = CostCenter.objects.create(
            name='Test',
            code='T',
            cost_center_type='DEPARTMENT'
        )
        self.account = Account.objects.create(
            code='6000',
            name='Test Expense',
            account_type='EXPENSE',
            is_active=True
        )

    def test_create_cost_transaction(self):
        """Test creating cost transaction."""
        from accounting.models import JournalEntry, JournalEntryLine
        entry = JournalEntry.objects.create(
            entry_number='JE-001',
            entry_date=date(2025, 1, 15),
            entry_type='ADJUSTMENT',
            description='Test'
        )
        line = JournalEntryLine.objects.create(
            entry=entry,
            account=self.account,
            debit=Decimal('5000.00'),
            credit=Decimal('0.00')
        )
        tx = CostTransaction.objects.create(
            cost_center=self.cc,
            journal_entry_line=line,
            amount=Decimal('5000.00'),
            transaction_date=date(2025, 1, 15)
        )
        self.assertEqual(tx.amount, Decimal('5000.00'))