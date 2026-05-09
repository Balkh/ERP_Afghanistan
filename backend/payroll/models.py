"""
Payroll Models - Salary Structures, Payroll Cycle, Payroll Records
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from uuid import uuid4
from decimal import Decimal


User = get_user_model()


class SalaryStructure(models.Model):
    """
    Salary structure with allowances and deductions
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Base monthly salary'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_salary_structure'
        verbose_name = 'Salary Structure'
        verbose_name_plural = 'Salary Structures'

    def __str__(self):
        return self.name


class Allowance(models.Model):
    """
    Salary allowances (transport, housing, food, etc.)
    """
    TYPE_CHOICES = [
        ('FIXED', 'Fixed Amount'),
        ('PERCENTAGE', 'Percentage of Basic'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    allowance_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='FIXED')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_taxable = models.BooleanField(default=True, help_text='Include in tax calculation')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'payroll_allowance'
        verbose_name = 'Allowance'
        verbose_name_plural = 'Allowances'

    def __str__(self):
        return f"{self.name} ({self.amount})"


class Deduction(models.Model):
    """
    Salary deductions (tax, insurance, etc.)
    """
    TYPE_CHOICES = [
        ('FIXED', 'Fixed Amount'),
        ('PERCENTAGE', 'Percentage of Basic'),
    ]
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    deduction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='FIXED')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_taxable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'payroll_deduction'
        verbose_name = 'Deduction'
        verbose_name_plural = 'Deductions'

    def __str__(self):
        return f"{self.name} ({self.amount})"


class EmployeeSalary(models.Model):
    """
    Employee-specific salary configuration
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    employee = models.OneToOneField(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='salary_config'
    )
    salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Allowances
    allowances = models.ManyToManyField(
        Allowance,
        through='EmployeeAllowance',
        blank=True
    )
    
    # Deductions
    deductions = models.ManyToManyField(
        Deduction,
        through='EmployeeDeduction',
        blank=True
    )
    
    # Tax info
    tax_number = models.CharField(max_length=50, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_employee_salary'
        verbose_name = 'Employee Salary'
        verbose_name_plural = 'Employee Salaries'

    def __str__(self):
        return f"{self.employee} - {self.basic_salary}"


class EmployeeAllowance(models.Model):
    """Through model for employee-specific allowances"""
    employee_salary = models.ForeignKey(EmployeeSalary, on_delete=models.CASCADE)
    allowance = models.ForeignKey(Allowance, on_delete=models.CASCADE)
    custom_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ['employee_salary', 'allowance']


class EmployeeDeduction(models.Model):
    """Through model for employee-specific deductions"""
    employee_salary = models.ForeignKey(EmployeeSalary, on_delete=models.CASCADE)
    deduction = models.ForeignKey(Deduction, on_delete=models.CASCADE)
    custom_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ['employee_salary', 'deduction']


class PayrollCycle(models.Model):
    """
    Payroll period/month
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('GENERATING', 'Generating'),
        ('GENERATED', 'Generated'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    period_month = models.PositiveIntegerField()  # 1-12
    period_year = models.PositiveIntegerField()
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Totals
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payrolls'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Accounting integration
    accounting_entry_id = models.UUIDField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_cycle'
        verbose_name = 'Payroll Cycle'
        verbose_name_plural = 'Payroll Cycles'
        unique_together = ['period_month', 'period_year']
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class PayrollRecord(models.Model):
    """
    Individual employee payroll record
    """
    STATUS_CHOICES = [
        ('CALCULATED', 'Calculated'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    payroll_cycle = models.ForeignKey(
        PayrollCycle,
        on_delete=models.CASCADE,
        related_name='records'
    )
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_records'
    )
    
    # Salary components
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Overtime
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CALCULATED')
    
    # Payment info
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payroll_record'
        verbose_name = 'Payroll Record'
        verbose_name_plural = 'Payroll Records'
        unique_together = ['payroll_cycle', 'employee']
        indexes = [
            models.Index(fields=['payroll_cycle', 'status']),
            models.Index(fields=['employee', 'payroll_cycle']),
        ]

    def __str__(self):
        return f"{self.payroll_cycle} - {self.employee}"

    @property
    def calculated_correctly(self):
        """Verify salary calculation"""
        calculated_gross = self.basic_salary + self.total_allowances + self.overtime_amount
        calculated_net = calculated_gross - self.total_deductions
        
        return (calculated_gross == self.gross_salary and 
                calculated_net == self.net_salary)