"""
Payroll Tests - Unit, Integration, and Business Logic
"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from payroll.models import (
    PayrollCycle, PayrollRecord, SalaryStructure,
    Allowance, Deduction, EmployeeSalary
)
from payroll.services import PayrollService, SalaryCalculationService
from payroll.services.accounting import PayrollAccountingService
from hr.models import Employee, Department, Position

User = get_user_model()


class SalaryCalculationTests(TestCase):
    """Tests for salary calculations"""
    
    def test_calculate_gross_salary(self):
        """Test gross salary calculation"""
        base = Decimal('10000')
        allowances = Decimal('2000')
        overtime = Decimal('10')
        
        gross = SalaryCalculationService.calculate_gross_salary(
            base, allowances, overtime
        )
        
        # 10000 + 2000 + (10 * daily_rate * 1.5)
        self.assertGreater(gross, base)
    
    def test_calculate_net_salary(self):
        """Test net salary calculation"""
        gross = Decimal('15000')
        deductions = Decimal('2000')
        
        net = SalaryCalculationService.calculate_net_salary(gross, deductions)
        self.assertEqual(net, Decimal('13000'))
    
    def test_calculate_tax(self):
        """Test tax calculation"""
        gross = Decimal('10000')
        
        tax = SalaryCalculationService.calculate_tax(gross, 10)
        self.assertEqual(tax, Decimal('1000'))


class PayrollCycleTests(TestCase):
    """Tests for PayrollCycle model"""
    
    def test_create_cycle(self):
        """Test payroll cycle creation"""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        
        cycle = PayrollCycle.objects.create(
            name='January 2024',
            period_month=1,
            period_year=2024,
            start_date=start,
            end_date=end
        )
        
        self.assertEqual(cycle.name, 'January 2024')
        self.assertEqual(cycle.status, 'DRAFT')


class PayrollServiceTests(TestCase):
    """Tests for PayrollService"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='payroll_user', password='test123')
        
        # Create department and position
        self.department = Department.objects.create(name='Payroll Dept', code='PAY')
        self.position = Position.objects.create(title='Developer', code='DEV', department=self.department)
        
        # Create employee
        self.employee = Employee.objects.create(
            employee_number='EMP-PAY-001',
            first_name='Test',
            last_name='Employee',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date(),
            basic_salary=Decimal('10000')
        )
    
    def test_create_payroll_cycle(self):
        """Test create payroll cycle"""
        cycle = PayrollService.create_payroll_cycle(
            name='Test Cycle',
            period_month=6,
            period_year=2024,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30)
        )
        
        self.assertEqual(cycle.period_month, 6)
        self.assertEqual(cycle.status, 'DRAFT')
    
    def test_duplicate_cycle_fails(self):
        """Test duplicate payroll cycle fails"""
        PayrollService.create_payroll_cycle(
            name='Duplicate Test',
            period_month=7,
            period_year=2024,
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 31)
        )
        
        # Try to create another for same month
        with self.assertRaises(Exception):
            PayrollService.create_payroll_cycle(
                name='Duplicate Test 2',
                period_month=7,
                period_year=2024,
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 31)
            )


class AllowanceDeductionTests(TestCase):
    """Tests for Allowance and Deduction models"""
    
    def test_create_allowance(self):
        """Test allowance creation"""
        allowance = Allowance.objects.create(
            name='Transport',
            code='TRANSPORT',
            allowance_type='FIXED',
            amount=Decimal('5000')
        )
        
        self.assertEqual(allowance.name, 'Transport')
    
    def test_create_deduction(self):
        """Test deduction creation"""
        deduction = Deduction.objects.create(
            name='Health Insurance',
            code='HEALTH',
            deduction_type='FIXED',
            amount=Decimal('1000')
        )
        
        self.assertEqual(deduction.name, 'Health Insurance')


class PayrollAPITests(APITestCase):
    """Integration tests for Payroll API"""
    
    def setUp(self):
        self.user = User.objects.create_superuser(username='api_payroll', password='api123')
        self.client.force_authenticate(user=self.user)
        
        # Create department and position
        self.department = Department.objects.create(name='API Dept', code='APID')
        self.position = Position.objects.create(title='API Pos', code='APIP', department=self.department)
    
    def test_create_cycle_api(self):
        """Test create payroll cycle via API"""
        response = self.client.post('/api/payroll/cycles/', {
            'name': 'Test Payroll',
            'period_month': 12,
            'period_year': 2024,
            'start_date': '2024-12-01',
            'end_date': '2024-12-31'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_payroll_summary_api(self):
        """Test payroll summary endpoint"""
        # Create a cycle
        PayrollCycle.objects.create(
            name='Summary Test',
            period_month=8,
            period_year=2024,
            start_date=date(2024, 8, 1),
            end_date=date(2024, 8, 31),
            status='DRAFT',
            total_gross=Decimal('100000'),
            total_deductions=Decimal('20000'),
            total_net=Decimal('80000')
        )
        
        response = self.client.get('/api/payroll/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PayrollAccountingTests(TestCase):
    """Tests for Payroll Accounting Integration"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='acc_user', password='test123')
        
        # Create department and position
        self.department = Department.objects.create(name='Acc Dept', code='ACCD')
        self.position = Position.objects.create(title='Acc Pos', code='ACCP', department=self.department)
        
        # Create employee
        self.employee = Employee.objects.create(
            employee_number='EMP-ACC-001',
            first_name='Accounting',
            last_name='Test',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date(),
            basic_salary=Decimal('10000')
        )
    
    def test_validate_accounts_missing(self):
        """Test validation when accounts are missing"""
        # Create cycle
        cycle = PayrollCycle.objects.create(
            name='Acc Test Cycle',
            period_month=11,
            period_year=2024,
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 30),
            status='APPROVED',
            total_gross=Decimal('10000'),
            total_deductions=Decimal('1000'),
            total_net=Decimal('9000')
        )
        
        # Should fail due to missing accounts
        with self.assertRaises(Exception):
            PayrollAccountingService.create_payroll_journal_entry(cycle, self.user)
    
    def test_create_journal_requires_approved(self):
        """Test journal entry requires approved payroll"""
        cycle = PayrollCycle.objects.create(
            name='Draft Cycle',
            period_month=12,
            period_year=2024,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            status='DRAFT'  # Not approved
        )
        
        with self.assertRaises(Exception):
            PayrollAccountingService.create_payroll_journal_entry(cycle, self.user)