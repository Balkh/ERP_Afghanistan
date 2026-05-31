"""
HR Tests - Unit, Integration, and Business Logic
"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from hr.models import Employee, Department, Position
from hr.services import EmployeeService, DepartmentService, PositionService

User = get_user_model()


class DepartmentModelTests(TestCase):
    """Unit tests for Department model"""
    
    def setUp(self):
        self.parent_dept = Department.objects.create(
            name='Parent Department',
            code='PARENT'
        )
    
    def test_create_department(self):
        """Test department creation"""
        dept = Department.objects.create(
            name='IT Department',
            code='IT',
            parent=self.parent_dept
        )
        self.assertEqual(dept.name, 'IT Department')
        self.assertEqual(dept.code, 'IT')
        self.assertTrue(dept.is_active)
    
    def test_department_str(self):
        """Test department string representation"""
        dept = Department.objects.create(
            name='HR Department',
            code='HR'
        )
        self.assertEqual(str(dept), 'HR Department (HR)')


class PositionModelTests(TestCase):
    """Unit tests for Position model"""
    
    def setUp(self):
        self.department = Department.objects.create(
            name='IT Department',
            code='IT'
        )
    
    def test_create_position(self):
        """Test position creation"""
        position = Position.objects.create(
            title='Software Developer',
            code='DEV',
            department=self.department,
            is_manager=False
        )
        self.assertEqual(position.title, 'Software Developer')
        self.assertFalse(position.is_manager)
    
    def test_position_str(self):
        """Test position string representation"""
        position = Position.objects.create(
            title='Manager',
            code='MGR',
            department=self.department
        )
        self.assertEqual(str(position), 'Manager - IT Department')


class EmployeeModelTests(TestCase):
    """Unit tests for Employee model"""
    
    def setUp(self):
        self.department = Department.objects.create(
            name='IT Department',
            code='IT'
        )
        self.position = Position.objects.create(
            title='Developer',
            code='DEV',
            department=self.department
        )
    
    def test_create_employee(self):
        """Test employee creation"""
        employee = Employee.objects.create(
            employee_number='EMP-TEST-001',
            first_name='John',
            last_name='Doe',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        self.assertEqual(employee.first_name, 'John')
        self.assertEqual(employee.full_name, 'John Doe')
        self.assertEqual(employee.employment_status, 'ACTIVE')
    
    def test_employee_str(self):
        """Test employee string representation"""
        employee = Employee.objects.create(
            employee_number='EMP-TEST-002',
            first_name='Jane',
            last_name='Smith',
            gender='FEMALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        self.assertIn('EMP-TEST-002', str(employee))
    
    def test_years_of_service(self):
        """Test years of service calculation"""
        employee = Employee.objects.create(
            employee_number='EMP-TEST-003',
            first_name='Test',
            last_name='User',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date() - timedelta(days=400)
        )
        self.assertEqual(employee.get_years_of_service(), 1)


class DepartmentServiceTests(TestCase):
    """Tests for DepartmentService"""
    
    def test_create_department(self):
        """Test department creation via service"""
        dept = DepartmentService.create_department(
            name='Finance',
            code='FIN'
        )
        self.assertEqual(dept.name, 'Finance')
        self.assertEqual(dept.code, 'FIN')
    
    def test_duplicate_code_fails(self):
        """Test duplicate department code raises error"""
        DepartmentService.create_department(name='A', code='DUP')
        with self.assertRaises(Exception):
            DepartmentService.create_department(name='B', code='DUP')


class PositionServiceTests(TestCase):
    """Tests for PositionService"""
    
    def setUp(self):
        self.department = Department.objects.create(
            name='IT',
            code='IT'
        )
    
    def test_create_position(self):
        """Test position creation via service"""
        position = PositionService.create_position(
            title='Developer',
            code='DEV',
            department=self.department
        )
        self.assertEqual(position.title, 'Developer')


class EmployeeServiceTests(TestCase):
    """Tests for EmployeeService"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.department = Department.objects.create(
            name='HR',
            code='HR'
        )
        self.position = Position.objects.create(
            title='Manager',
            code='MGR',
            department=self.department
        )
    
    def test_create_employee(self):
        """Test employee creation via service"""
        employee = EmployeeService.create_employee(
            first_name='John',
            last_name='Doe',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date(),
            created_by=self.user
        )
        self.assertEqual(employee.first_name, 'John')
        self.assertTrue(employee.employee_number.startswith('EMP-'))
    
    def test_update_employee_status(self):
        """Test employee status update"""
        employee = Employee.objects.create(
            employee_number='EMP-STATUS-001',
            first_name='Test',
            last_name='User',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        
        updated = EmployeeService.update_employee_status(
            employee_id=employee.id,
            new_status='TERMINATED',
            updated_by=self.user
        )
        
        self.assertEqual(updated.employment_status, 'TERMINATED')
        self.assertIsNotNone(updated.termination_date)
    
    def test_get_active_employees(self):
        """Test getting active employees"""
        # Create active employee
        emp1 = Employee.objects.create(
            employee_number='EMP-ACTIVE-SVC-1',
            first_name='Active',
            last_name='User',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date(),
            employment_status='ACTIVE'
        )
        
        # Create inactive employee
        emp2 = Employee.objects.create(
            employee_number='EMP-INACTIVE-SVC-1',
            first_name='Inactive',
            last_name='User',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date(),
            employment_status='INACTIVE'
        )
        
        active = EmployeeService.get_active_employees()
        # Should be 1 because one is ACTIVE
        self.assertEqual(active.count(), 1)


class EmployeeAPITests(APITestCase):
    """Integration tests for HR API"""
    
    def setUp(self):
        self.user = User.objects.create_superuser(username='apiuser', password='api123')
        self.department = Department.objects.create(
            name='API Dept',
            code='APID'
        )
        self.position = Position.objects.create(
            title='API Pos',
            code='APIP',
            department=self.department
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_department_api(self):
        """Test department creation via API"""
        response = self.client.post('/api/hr/departments/', {
            'name': 'New Department',
            'code': 'NEW',
            'description': 'Test description'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_list_employees_api(self):
        """Test employee list via API"""
        Employee.objects.create(
            employee_number='EMP-API-1',
            first_name='API',
            last_name='User',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        
        response = self.client.get('/api/hr/employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_update_employee_status_api(self):
        """Test update employee status via API"""
        employee = Employee.objects.create(
            employee_number='EMP-STATUS-API',
            first_name='Status',
            last_name='Test',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        
        response = self.client.post('/api/hr/update-status/', {
            'employee_id': str(employee.id),
            'status': 'SUSPENDED'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['employment_status'], 'SUSPENDED')
    
    def test_search_employees_api(self):
        """Test employee search via API"""
        Employee.objects.create(
            employee_number='EMP-SEARCH',
            first_name='Search',
            last_name='Test',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        
        response = self.client.get('/api/hr/employees/?search=Search')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_filter_by_department_api(self):
        """Test filter employees by department"""
        Employee.objects.create(
            employee_number='EMP-FILTER',
            first_name='Filter',
            last_name='Test',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        
        response = self.client.get(f'/api/hr/employees/?department={self.department.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_active_employees_endpoint(self):
        """Test active employees endpoint"""
        Employee.objects.create(
            employee_number='EMP-ACTIVE-TEST',
            first_name='Active',
            last_name='Test',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date()
        )
        
        response = self.client.get('/api/hr/active-employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EdgeCaseTests(TestCase):
    """Edge case tests"""
    
    def setUp(self):
        self.department = Department.objects.create(
            name='Edge',
            code='EDGE'
        )
        self.position = Position.objects.create(
            title='Edge Pos',
            code='EDGEP',
            department=self.department
        )
    
    def test_termination_date_future_fails(self):
        """Test termination date in future raises validation error"""
        employee = Employee(
            employee_number='EMP-FUTURE',
            first_name='Test',
            last_name='Future',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date(),
            termination_date=timezone.now().date() + timedelta(days=30)
        )
        
        with self.assertRaises(ValidationError):
            employee.clean()
    
    def test_hire_date_future_fails(self):
        """Test hire date in future raises validation error"""
        employee = Employee(
            employee_number='EMP-HIRE',
            first_name='Test',
            last_name='Hire',
            gender='MALE',
            department=self.department,
            position=self.position,
            hire_date=timezone.now().date() + timedelta(days=30)
        )
        
        with self.assertRaises(ValidationError):
            employee.clean()
    
    def test_position_department_mismatch_fails(self):
        """Test creating employee with position in different department fails"""
        other_dept = Department.objects.create(name='Other', code='OTH')
        other_pos = Position.objects.create(
            title='Other Pos',
            code='OTHP',
            department=other_dept
        )
        
        with self.assertRaises(ValidationError):
            EmployeeService.create_employee(
                first_name='Test',
                last_name='Mismatch',
                gender='MALE',
                department=self.department,
                position=other_pos,
                hire_date=timezone.now().date()
            )