"""
HR Services - Business Logic Layer

All HR business logic must stay here.
Keep APIs thin - business logic in services.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from uuid import UUID
import uuid

User = get_user_model()


class EmployeeService:
    """Service for Employee operations"""
    
    @staticmethod
    @transaction.atomic
    def create_employee(
        first_name,
        last_name,
        gender,
        department,
        position,
        hire_date,
        employment_type='FULL_TIME',
        user=None,
        basic_salary=None,
        created_by=None,
        **kwargs
    ):
        """
        Create a new employee
        
        Args:
            first_name, last_name, gender (required)
            department, position (required FK)
            hire_date (required)
            employment_type, user, basic_salary, created_by (optional)
            **kwargs: additional fields
            
        Returns:
            Employee instance
        """
        # Generate unique employee number
        employee_number = kwargs.get('employee_number') or EmployeeService._generate_employee_number()
        
        # Validate department and position match
        if department.id != position.department_id:
            raise ValidationError('Position must belong to the selected department.')
        
        employee = Employee.objects.create(
            employee_number=employee_number,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            department=department,
            position=position,
            hire_date=hire_date,
            employment_type=employment_type,
            user=user,
            basic_salary=basic_salary,
            created_by=created_by,
            **kwargs
        )
        
        return employee
    
    @staticmethod
    def _generate_employee_number():
        """Generate unique employee number"""
        # Format: EMP-YYYYMMDD-XXXX
        today = timezone.now().date()
        prefix = f"EMP-{today.strftime('%Y%m%d')}"
        
        # Find last employee with this prefix
        last = Employee.objects.filter(
            employee_number__startswith=prefix
        ).order_by('-employee_number').first()
        
        if last:
            try:
                # Extract sequence number
                seq = int(last.employee_number.split('-')[-1])
                new_seq = seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1
        
        return f"{prefix}-{new_seq:04d}"
    
    @staticmethod
    @transaction.atomic
    def update_employee_status(employee_id, new_status, updated_by=None):
        """
        Update employee employment status
        
        Args:
            employee_id: Employee ID or instance
            new_status: New status (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, SUSPENDED)
            updated_by: User making the change
        """
        if isinstance(employee_id, (UUID, str)):
            employee = Employee.objects.get(id=employee_id)
        else:
            employee = employee_id
        
        VALID_STATUSES = ['ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED', 'SUSPENDED']
        if new_status not in VALID_STATUSES:
            raise ValidationError(f'Invalid status. Must be one of: {VALID_STATUSES}')
        
        old_status = employee.employment_status
        employee.employment_status = new_status
        
        # Handle termination
        if new_status == 'TERMINATED' and not employee.termination_date:
            employee.termination_date = timezone.now().date()
        
        # Handle reactivation
        if new_status == 'ACTIVE' and old_status == 'TERMINATED':
            employee.termination_date = None
        
        employee.save()
        
        return employee
    
    @staticmethod
    def get_active_employees():
        """Get all active employees"""
        return Employee.objects.filter(
            employment_status='ACTIVE',
            is_active=True
        ).select_related('department', 'position')
    
    @staticmethod
    def search_employees(query):
        """Search employees by name, number, or department"""
        from django.db.models import Q
        return Employee.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(employee_number__icontains=query) |
            Q(department__name__icontains=query)
        ).select_related('department', 'position')


class DepartmentService:
    """Service for Department operations"""
    
    @staticmethod
    @transaction.atomic
    def create_department(
        name,
        code,
        parent=None,
        manager=None,
        description='',
        created_by=None
    ):
        """Create a new department"""
        # Check code uniqueness
        if Department.objects.filter(code=code).exists():
            raise ValidationError(f'Department code "{code}" already exists.')
        
        department = Department.objects.create(
            name=name,
            code=code.upper(),
            parent=parent,
            manager=manager,
            description=description,
        )
        
        return department
    
    @staticmethod
    def get_active_departments():
        """Get all active departments"""
        return Department.objects.filter(is_active=True)
    
    @staticmethod
    def get_department_tree():
        """Get department tree structure"""
        # Get top-level departments (no parent)
        roots = Department.objects.filter(
            parent__isnull=True,
            is_active=True
        ).select_related('manager')
        
        def add_children(dept):
            children = Department.objects.filter(
                parent=dept,
                is_active=True
            ).select_related('manager')
            return {
                'id': str(dept.id),
                'name': dept.name,
                'code': dept.code,
                'manager': str(dept.manager) if dept.manager else None,
                'children': [add_children(c) for c in children]
            }
        
        return [add_children(r) for r in roots]


class PositionService:
    """Service for Position operations"""
    
    @staticmethod
    @transaction.atomic
    def create_position(
        title,
        code,
        department,
        description='',
        is_manager=False
    ):
        """Create a new position"""
        if Position.objects.filter(department=department, code=code).exists():
            raise ValidationError(f'Position code "{code}" already exists in this department.')
        
        position = Position.objects.create(
            title=title,
            code=code.upper(),
            department=department,
            description=description,
            is_manager=is_manager
        )
        
        return position
    
    @staticmethod
    def get_active_positions(department=None):
        """Get all active positions, optionally filtered by department"""
        queryset = Position.objects.filter(is_active=True)
        if department:
            queryset = queryset.filter(department=department)
        return queryset.select_related('department')


# Import models at bottom to avoid circular imports
from hr.models import Employee, Department, Position