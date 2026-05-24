"""
Payroll Services - Business Logic

All payroll calculation logic must be here.
Keep APIs thin - business logic in services.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from calendar import monthrange
import uuid
import logging

logger = logging.getLogger('erp.payroll')

User = get_user_model()


class PayrollService:
    """Service for Payroll operations"""
    
    @staticmethod
    @transaction.atomic
    def create_payroll_cycle(name, period_month, period_year, start_date, end_date):
        """
        Create a new payroll cycle
        
        Args:
            name: Cycle name
            period_month: Month (1-12)
            period_year: Year
            start_date: Period start
            end_date: Period end
            
        Returns:
            PayrollCycle instance
        """
        # Check for existing cycle
        if PayrollCycle.objects.filter(period_month=period_month, period_year=period_year).exists():
            raise ValidationError(f'Payroll cycle for {period_month}/{period_year} already exists.')
        
        cycle = PayrollCycle.objects.create(
            name=name,
            period_month=period_month,
            period_year=period_year,
            start_date=start_date,
            end_date=end_date,
            status='DRAFT'
        )
        
        return cycle
    
    @staticmethod
    @transaction.atomic
    def generate_payroll(cycle):
        """
        Generate payroll for all active employees
        
        Args:
            cycle: PayrollCycle instance
            
        Returns:
            List of PayrollRecord instances
        """
        from payroll.models import PayrollRecord, EmployeeSalary
        from hr.models import Employee
        
        if cycle.status != 'DRAFT':
            raise ValidationError('Can only generate payroll for DRAFT cycles.')
        
        cycle.status = 'GENERATING'
        cycle.save()
        
        records = []
        
        # Get active employees
        active_employees = Employee.objects.filter(
            employment_status='ACTIVE',
            is_active=True
        ).select_related('department', 'position')
        
        for employee in active_employees:
            try:
                record = PayrollService._generate_employee_payroll(employee, cycle)
                records.append(record)
            except ValidationError as e:
                logger.warning("Payroll generation skipped for %s: %s", employee, e)
            except Exception as e:
                logger.error("Payroll generation failed for %s: %s", employee, e)
        
        # Calculate totals
        total_gross = sum(r.gross_salary for r in records)
        total_deductions = sum(r.total_deductions for r in records)
        total_net = sum(r.net_salary for r in records)
        
        cycle.total_gross = total_gross
        cycle.total_deductions = total_deductions
        cycle.total_net = total_net
        cycle.status = 'GENERATED'
        cycle.save()
        
        return records
    
    @staticmethod
    def _generate_employee_payroll(employee, cycle):
        """Generate payroll for single employee"""
        from payroll.models import PayrollRecord, EmployeeSalary, EmployeeAllowance, EmployeeDeduction
        
        # Get basic salary
        try:
            emp_salary = EmployeeSalary.objects.get(employee=employee)
            basic_salary = emp_salary.basic_salary
        except EmployeeSalary.DoesNotExist:
            basic_salary = employee.basic_salary or Decimal('0')
        
        if not basic_salary:
            raise ValidationError(f'No salary configured for {employee}')
        
        # Calculate allowances
        total_allowances = Decimal('0')
        overtime_amount = Decimal('0')
        
        # Add overtime if any
        try:
            from hr.models import Overtime
            overtime = Overtime.objects.filter(
                employee=employee,
                date__gte=cycle.start_date,
                date__lte=cycle.end_date,
                status='APPROVED'
            )
            overtime_hours = sum(o.hours for o in overtime)
            overtime_amount = overtime_hours * basic_salary / Decimal('240')  # Daily rate
        except Exception as e:
            logger.warning("Overtime calculation failed for %s: %s", employee, e)
            overtime_hours = Decimal('0')
        
        # Calculate deductions
        total_deductions = Decimal('0')
        
        # Tax calculation (simplified - 10%)
        tax = basic_salary * Decimal('0.10')
        total_deductions += tax
        
        # Gross salary
        gross_salary = basic_salary + total_allowances + overtime_amount
        
        # Net salary
        net_salary = gross_salary - total_deductions
        
        # Create record
        record = PayrollRecord.objects.create(
            payroll_cycle=cycle,
            employee=employee,
            basic_salary=basic_salary,
            total_allowances=total_allowances,
            total_deductions=total_deductions,
            gross_salary=gross_salary,
            net_salary=net_salary,
            overtime_hours=overtime_hours,
            overtime_amount=overtime_amount,
            status='CALCULATED'
        )
        
        return record
    
    @staticmethod
    @transaction.atomic
    def approve_payroll(cycle, user):
        """Approve payroll cycle"""
        if cycle.status != 'GENERATED':
            raise ValidationError('Can only approve GENERATED cycles.')
        
        cycle.status = 'APPROVED'
        cycle.approved_by = user
        cycle.approved_at = timezone.now()
        cycle.save()
        
        return cycle
    
    @staticmethod
    @transaction.atomic
    def mark_as_paid(record):
        """Mark payroll record as paid"""
        if record.status == 'PAID':
            raise ValidationError('Record already marked as paid.')
        
        record.status = 'PAID'
        record.paid_at = timezone.now()
        record.save()
        
        return record
    
    @staticmethod
    def calculate_month_days(month, year):
        """Get working days in a month"""
        _, num_days = monthrange(year, month)
        # Exclude Fridays (assuming Friday is weekend)
        # This is simplified - adjust based on actual work week
        working_days = num_days - (num_days // 7) * 1  # Simple approximation
        return working_days


class SalaryCalculationService:
    """Service for salary calculations"""
    
    @staticmethod
    def calculate_gross_salary(base, allowances, overtime_hours=0, overtime_rate=1.5):
        """
        Calculate gross salary
        
        Args:
            base: Base salary
            allowances: Total allowances
            overtime_hours: Overtime hours
            overtime_rate: Overtime multiplier
            
        Returns:
            Gross salary
        """
        daily_rate = base / Decimal('30')
        overtime_pay = overtime_hours * daily_rate * Decimal(str(overtime_rate))
        
        return base + allowances + overtime_pay
    
    @staticmethod
    def calculate_net_salary(gross, deductions):
        """
        Calculate net salary
        
        Args:
            gross: Gross salary
            deductions: Total deductions
            
        Returns:
            Net salary
        """
        return gross - deductions
    
    @staticmethod
    def calculate_tax(gross, percentage=10):
        """
        Calculate tax
        
        Args:
            gross: Gross salary
            percentage: Tax percentage
            
        Returns:
            Tax amount
        """
        return gross * Decimal(str(percentage)) / Decimal('100')
    
    @staticmethod
    def calculate_overtime_pay(hours, daily_rate, rate=1.5):
        """
        Calculate overtime pay
        
        Args:
            hours: Overtime hours
            daily_rate: Daily rate
            rate: Overtime multiplier
            
        Returns:
            Overtime pay amount
        """
        hourly_rate = daily_rate / Decimal('8')
        return hours * hourly_rate * Decimal(str(rate))


# Import models at bottom to avoid circular imports
from payroll.models import (
    PayrollCycle, PayrollRecord, EmployeeSalary,
    Allowance, Deduction
)