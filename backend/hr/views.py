"""
HR API Views - Thin API layer, business logic in services
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Employee, Department, Position
from core.multitenant.views import CreatedByMixin
from .serializers import (
    EmployeeSerializer, EmployeeCreateSerializer, EmployeeListSerializer,
    DepartmentSerializer, PositionSerializer
)
from .services import EmployeeService, DepartmentService, PositionService
from security.permissions import RoleBasedPermission

User = get_user_model()


class DepartmentViewSet(viewsets.ModelViewSet):
    """API for Department CRUD"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [RoleBasedPermission]
    
    def get_queryset(self):
        queryset = Department.objects.all()
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True)
        return queryset.select_related('parent', 'manager')
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete - set is_active=False"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PositionViewSet(viewsets.ModelViewSet):
    """API for Position CRUD"""
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [RoleBasedPermission]
    
    def get_queryset(self):
        queryset = Position.objects.all()
        department_id = self.request.query_params.get('department')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset.select_related('department')
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmployeeViewSet(CreatedByMixin, viewsets.ModelViewSet):
    """API for Employee CRUD"""
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [RoleBasedPermission]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        if self.action == 'create':
            return EmployeeCreateSerializer
        return EmployeeSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        emp_status = self.request.query_params.get('status')
        if emp_status:
            queryset = queryset.filter(employment_status=emp_status)
        
        # Filter by department
        dept_id = self.request.query_params.get('department')
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        
        # Filter by active only
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(is_active=True, employment_status='ACTIVE')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = EmployeeService.search_employees(search)
        
        return queryset.select_related('department', 'position')
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def update_employee_status(request):
    """Update employee status"""
    employee_id = request.data.get('employee_id')
    new_status = request.data.get('status')
    
    if not employee_id or not new_status:
        return Response(
            {'error': 'employee_id and status are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        employee = EmployeeService.update_employee_status(
            employee_id=employee_id,
            new_status=new_status,
            updated_by=request.user
        )
        serializer = EmployeeSerializer(employee)
        return Response(serializer.data)
    except Employee.DoesNotExist:
        return Response(
            {'error': 'Employee not found.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def department_tree(request):
    """Get department tree structure"""
    tree = DepartmentService.get_department_tree()
    return Response(tree)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def active_employees(request):
    """Get all active employees"""
    employees = EmployeeService.get_active_employees()
    serializer = EmployeeListSerializer(employees, many=True)
    return Response(serializer.data)


# ==================== REPORTS ====================

from hr.services.reports import (
    EmployeeReportService, AttendanceReportService,
    LeaveReportService, OvertimeReportService
)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def employee_summary_report(request):
    """Employee summary report"""
    summary = EmployeeReportService.get_employee_summary()
    return Response(summary)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def department_summary_report(request):
    """Department summary report"""
    summary = EmployeeReportService.get_department_summary()
    return Response(summary)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def attendance_summary_report(request):
    """Attendance summary report"""
    start = request.query_params.get('start_date')
    end = request.query_params.get('end_date')
    
    if not start or not end:
        today = timezone.now().date()
        start = today.replace(day=1)
        end = today
    else:
        start = timezone.datetime.strptime(start, '%Y-%m-%d').date()
        end = timezone.datetime.strptime(end, '%Y-%m-%d').date()
    
    summary = AttendanceReportService.get_attendance_summary(start, end)
    return Response(summary)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def leave_summary_report(request):
    """Leave summary report"""
    start = request.query_params.get('start_date')
    end = request.query_params.get('end_date')
    
    if not start or not end:
        today = timezone.now().date()
        start = today.replace(day=1)
        end = today
    else:
        start = timezone.datetime.strptime(start, '%Y-%m-%d').date()
        end = timezone.datetime.strptime(end, '%Y-%m-%d').date()
    
    summary = LeaveReportService.get_leave_summary(start, end)
    by_type = LeaveReportService.get_leave_by_type(start, end)
    
    return Response({
        'summary': summary,
        'by_type': by_type
    })


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def overtime_summary_report(request):
    """Overtime summary report"""
    start = request.query_params.get('start_date')
    end = request.query_params.get('end_date')
    
    if not start or not end:
        today = timezone.now().date()
        start = today.replace(day=1)
        end = today
    else:
        start = timezone.datetime.strptime(start, '%Y-%m-%d').date()
        end = timezone.datetime.strptime(end, '%Y-%m-%d').date()
    
    summary = OvertimeReportService.get_overtime_summary(start, end)
    top_employees = OvertimeReportService.get_top_overtime_employees(start, end)
    
    return Response({
        'summary': summary,
        'top_employees': top_employees
    })