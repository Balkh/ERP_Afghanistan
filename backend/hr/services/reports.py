"""
HR Reporting Services
"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

User = get_user_model()


class EmployeeReportService:
    """Employee reporting"""
    
    @staticmethod
    def get_employee_summary():
        """Get overall employee summary"""
        from hr.models import Employee
        
        total = Employee.objects.count()
        active = Employee.objects.filter(employment_status='ACTIVE', is_active=True).count()
        inactive = Employee.objects.filter(employment_status='INACTIVE').count()
        terminated = Employee.objects.filter(employment_status='TERMINATED').count()
        on_leave = Employee.objects.filter(employment_status='ON_LEAVE').count()
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'terminated': terminated,
            'on_leave': on_leave
        }
    
    @staticmethod
    def get_department_summary():
        """Get employee count by department"""
        from hr.models import Employee, Department
        
        departments = Department.objects.filter(is_active=True).annotate(
            employee_count=Count('employees', filter=Q(employees__is_active=True))
        ).values('id', 'name', 'code', 'employee_count')
        
        return list(departments)
    
    @staticmethod
    def get_employee_list(filters=None):
        """Get filtered employee list"""
        from hr.models import Employee
        
        queryset = Employee.objects.select_related('department', 'position')
        
        if filters:
            if filters.get('department'):
                queryset = queryset.filter(department_id=filters['department'])
            if filters.get('status'):
                queryset = queryset.filter(employment_status=filters['status'])
            if filters.get('employment_type'):
                queryset = queryset.filter(employment_type=filters['employment_type'])
            if filters.get('active_only'):
                queryset = queryset.filter(is_active=True, employment_status='ACTIVE')
        
        return list(queryset.values(
            'id', 'employee_number', 'first_name', 'last_name',
            'department__name', 'position__title',
            'employment_type', 'employment_status', 'hire_date'
        ))
    
    @staticmethod
    def get_years_of_service_distribution():
        """Get distribution of employees by years of service"""
        from hr.models import Employee
        
        employees = Employee.objects.filter(
            is_active=True
        ).values('hire_date')
        
        distribution = {'0-1': 0, '1-3': 0, '3-5': 0, '5-10': 0, '10+': 0}
        
        today = timezone.now().date()
        
        for emp in employees:
            if not emp['hire_date']:
                continue
            years = (today - emp['hire_date']).days // 365
            
            if years < 1:
                distribution['0-1'] += 1
            elif years < 3:
                distribution['1-3'] += 1
            elif years < 5:
                distribution['3-5'] += 1
            elif years < 10:
                distribution['5-10'] += 1
            else:
                distribution['10+'] += 1
        
        return distribution


class AttendanceReportService:
    """Attendance reporting"""
    
    @staticmethod
    def get_attendance_summary(start_date, end_date):
        """Get attendance summary for period"""
        from hr.models import Attendance
        
        records = Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        return {
            'total_days': (end_date - start_date).days + 1,
            'present': records.filter(status='PRESENT').count(),
            'absent': records.filter(status='ABSENT').count(),
            'late': records.filter(status='LATE').count(),
            'on_time': records.filter(status='ON_TIME').count()
        }
    
    @staticmethod
    def get_employee_attendance(employee_id, start_date, end_date):
        """Get attendance for specific employee"""
        from hr.models import Attendance
        
        records = Attendance.objects.filter(
            employee_id=employee_id,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')
        
        return list(records.values('date', 'status', 'check_in', 'check_out', 'hours_worked'))
    
    @staticmethod
    def get_late_arrivals(start_date, end_date, threshold_minutes=30):
        """Get employees with late arrivals"""
        from hr.models import Attendance
        
        return list(Attendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            late_minutes__gte=threshold_minutes
        ).values('employee__first_name', 'employee__last_name', 'date', 'late_minutes'))


class LeaveReportService:
    """Leave reporting"""
    
    @staticmethod
    def get_leave_summary(start_date, end_date):
        """Get leave summary for period"""
        from hr.models import Leave
        
        records = Leave.objects.filter(
            start_date__gte=start_date,
            end_date__lte=end_date
        )
        
        return {
            'total': records.count(),
            'pending': records.filter(status='PENDING').count(),
            'approved': records.filter(status='APPROVED').count(),
            'rejected': records.filter(status='REJECTED').count(),
            'cancelled': records.filter(status='CANCELLED').count()
        }
    
    @staticmethod
    def get_leave_by_type(start_date, end_date):
        """Get leave count by type"""
        from hr.models import Leave
        
        records = Leave.objects.filter(
            start_date__gte=start_date,
            end_date__lte=end_date,
            status='APPROVED'
        )
        
        by_type = {}
        for leave_type, _ in Leave.TYPE_CHOICES:
            count = records.filter(leave_type=leave_type).count()
            if count > 0:
                by_type[leave_type] = count
        
        return by_type


class OvertimeReportService:
    """Overtime reporting"""
    
    @staticmethod
    def get_overtime_summary(start_date, end_date):
        """Get overtime summary"""
        from hr.models import Overtime
        
        records = Overtime.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        return {
            'total_records': records.count(),
            'total_hours': sum(r.hours for r in records if r.hours),
            'pending': records.filter(status='PENDING').count(),
            'approved': records.filter(status='APPROVED').count(),
            'rejected': records.filter(status='REJECTED').count()
        }
    
    @staticmethod
    def get_top_overtime_employees(start_date, end_date, limit=10):
        """Get employees with most overtime"""
        from hr.models import Overtime
        from django.db.models import Sum
        
        return list(Overtime.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            status='APPROVED'
        ).values(
            'employee__first_name', 'employee__last_name'
        ).annotate(
            total_hours=Sum('hours')
        ).order_by('-total_hours')[:limit])