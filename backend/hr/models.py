"""
HR Models - Employee Management, Department, Positions
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from uuid import uuid4


User = get_user_model()


class Department(models.Model):
    """
    Department/Unit in the organization
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sub_departments'
    )
    manager = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hr_department'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        if self.parent and self.parent == self:
            raise ValidationError('Department cannot be its own parent.')


class Position(models.Model):
    """
    Job position/role within a department
    """
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='positions'
    )
    description = models.TextField(blank=True)
    is_manager = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hr_position'
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'
        unique_together = ['department', 'code']
        ordering = ['title']

    def __str__(self):
        return f"{self.title} - {self.department.name}"


class Employee(models.Model):
    """
    Employee profile - core HR model
    """
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERNSHIP', 'Internship'),
        ('TEMPORARY', 'Temporary'),
    ]
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ON_LEAVE', 'On Leave'),
        ('TERMINATED', 'Terminated'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    # UUID primary key
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    
    # User account (optional - linked to system user)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee'
    )
    
    # Unique employee ID
    employee_number = models.CharField(
        max_length=50,
        unique=True,
        help_text='System-generated or manual employee ID'
    )
    
    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Contact information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Emergency contact
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    
    # Employment details
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='FULL_TIME'
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default='ACTIVE'
    )
    
    # Dates
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    
    # Contract
    contract_start_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    
    # Salary information (basic)
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monthly basic salary'
    )
    
    # Leave balance
    annual_leave_balance = models.PositiveIntegerField(default=20)
    remaining_leave = models.PositiveIntegerField(default=20)
    
    # Photo
    photo = models.ImageField(upload_to='employees/photos/', blank=True, null=True)
    
    # Documents
    id_card_number = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # HR Manager who created this record
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_employees'
    )

    class Meta:
        db_table = 'hr_employee'
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['department', 'employment_status']),
            models.Index(fields=['employee_number']),
            models.Index(fields=['employment_type']),
        ]

    def __str__(self):
        return f"{self.employee_number} - {self.first_name} {self.last_name}"

    def clean(self):
        if self.termination_date and self.termination_date > timezone.now().date():
            raise ValidationError('Termination date cannot be in the future.')
        if self.hire_date and self.hire_date > timezone.now().date():
            raise ValidationError('Hire date cannot be in the future.')
        if self.contract_end_date and self.contract_start_date:
            if self.contract_end_date < self.contract_start_date:
                raise ValidationError('Contract end date must be after start date.')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_employed(self):
        return self.employment_status == 'ACTIVE'

    def get_years_of_service(self):
        """Calculate years of service"""
        if not self.hire_date:
            return 0
        today = timezone.now().date()
        return (today - self.hire_date).days // 365


class Attendance(models.Model):
    """
    Daily attendance tracking
    """
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('ON_TIME', 'On Time'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    
    # Check-in/Check-out times
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ABSENT'
    )
    
    # Work hours
    hours_worked = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        help_text='Total hours worked'
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Late arrival (in minutes)
    late_minutes = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hr_attendance'
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
        ]
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"
    
    @property
    def is_present(self):
        return self.status in ['PRESENT', 'LATE', 'ON_TIME']
    
    @property
    def work_duration(self):
        """Calculate work duration in hours"""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return round(delta.total_seconds() / 3600, 2)
        return 0


class Leave(models.Model):
    """
    Leave request and tracking
    """
    TYPE_CHOICES = [
        ('ANNUAL', 'Annual Leave'),
        ('SICK', 'Sick Leave'),
        ('UNPAID', 'Unpaid Leave'),
        ('MATERNITY', 'Maternity Leave'),
        ('PATERNITY', 'Paternity Leave'),
        ('WORK', 'Work Related'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    # Duration (auto-calculated)
    days_requested = models.PositiveIntegerField()
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hr_leave'
        verbose_name = 'Leave'
        verbose_name_plural = 'Leaves'
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee} - {self.get_leave_type_display()} ({self.get_status_display()})"


class Overtime(models.Model):
    """
    Overtime tracking
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='overtime_records'
    )
    date = models.DateField()
    
    # Duration
    hours = models.DecimalField(max_digits=4, decimal_places=2)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    # Rate (1.0, 1.5, 2.0, etc.)
    rate = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    
    # Calculation
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Calculated overtime amount'
    )
    
    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_overtime'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Work description
    description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hr_overtime'
        verbose_name = 'Overtime'
        verbose_name_plural = 'Overtimes'
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['status', 'date']),
        ]
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.hours}h)"
    
    def calculate_amount(self, hourly_rate=None):
        """Calculate overtime amount"""
        if hourly_rate is None:
            # Use daily rate / 8 as default hourly rate
            hourly_rate = 0  # Will use base salary / 240
        return round(self.hours * self.rate * hourly_rate, 2)