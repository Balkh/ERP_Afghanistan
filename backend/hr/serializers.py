"""
HR Serializers
"""
from rest_framework import serializers
from .models import Employee, Department, Position


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department"""
    sub_departments_count = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description',
            'parent', 'manager', 'manager_name',
            'is_active', 'created_at', 'updated_at',
            'sub_departments_count', 'employee_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_sub_departments_count(self, obj):
        return obj.sub_departments.filter(is_active=True).count()
    
    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True, employment_status='ACTIVE').count()
    
    def get_manager_name(self, obj):
        return str(obj.manager) if obj.manager else None


class PositionSerializer(serializers.ModelSerializer):
    """Serializer for Position"""
    department_name = serializers.CharField(source='department.name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = [
            'id', 'title', 'code', 'department', 'department_name',
            'description', 'is_manager', 'is_active',
            'created_at', 'updated_at', 'employee_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_employee_count(self, obj):
        return obj.employees.filter(is_active=True, employment_status='ACTIVE').count()


class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer for Employee"""
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    years_of_service = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_number', 'user',
            'first_name', 'last_name', 'full_name', 'father_name',
            'gender', 'date_of_birth',
            'email', 'phone', 'mobile', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation',
            'department', 'department_name',
            'position', 'position_title',
            'employment_type', 'employment_status',
            'hire_date', 'termination_date',
            'contract_start_date', 'contract_end_date',
            'basic_salary', 'annual_leave_balance', 'remaining_leave',
            'photo', 'id_card_number', 'tax_id',
            'is_active', 'created_at', 'updated_at',
            'years_of_service'
        ]
        read_only_fields = [
            'id', 'employee_number', 'created_at', 'updated_at',
            'years_of_service'
        ]
    
    def create(self, validated_data):
        # Generate employee number if not provided
        if not validated_data.get('employee_number'):
            validated_data['employee_number'] = EmployeeService._generate_employee_number()
        return super().create(validated_data)


class EmployeeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Employee"""
    class Meta:
        model = Employee
        fields = [
            'employee_number', 'user',
            'first_name', 'last_name', 'father_name',
            'gender', 'date_of_birth',
            'email', 'phone', 'mobile', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation',
            'department', 'position',
            'employment_type', 'employment_status',
            'hire_date', 'termination_date',
            'contract_start_date', 'contract_end_date',
            'basic_salary',
            'photo', 'id_card_number', 'tax_id',
        ]


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for lists"""
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_number', 'full_name',
            'department_name', 'position_title',
            'employment_type', 'employment_status',
            'hire_date', 'is_active'
        ]


# Import service for employee number generation
from hr.services import EmployeeService