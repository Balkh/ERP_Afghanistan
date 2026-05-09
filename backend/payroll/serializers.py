"""
Payroll Serializers
"""
from rest_framework import serializers
from .models import (
    PayrollCycle, PayrollRecord, SalaryStructure,
    Allowance, Deduction, EmployeeSalary
)


class AllowanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allowance
        fields = '__all__'


class DeductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deduction
        fields = '__all__'


class SalaryStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryStructure
        fields = '__all__'


class EmployeeSalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    
    class Meta:
        model = EmployeeSalary
        fields = '__all__'


class PayrollRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    
    class Meta:
        model = PayrollRecord
        fields = '__all__'


class PayrollCycleSerializer(serializers.ModelSerializer):
    records_count = serializers.SerializerMethodField()
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PayrollCycle
        fields = [
            'id', 'name', 'period_month', 'period_year',
            'start_date', 'end_date', 'status',
            'total_gross', 'total_deductions', 'total_net',
            'approved_by', 'approved_at',
            'created_at', 'updated_at',
            'records_count', 'employee_count'
        ]
    
    def get_records_count(self, obj):
        return obj.records.count()
    
    def get_employee_count(self, obj):
        return obj.records.filter(status='CALCULATED').count()