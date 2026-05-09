"""
Payroll Reporting Services
"""
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

User = get_user_model()


class PayrollReportService:
    """Payroll reporting"""
    
    @staticmethod
    def get_payroll_summary(period_year=None):
        """Get yearly payroll summary"""
        from payroll.models import PayrollCycle
        
        queryset = PayrollCycle.objects.filter(status__in=['APPROVED', 'PAID'])
        
        if period_year:
            queryset = queryset.filter(period_year=period_year)
        
        cycles = queryset.values(
            'period_month', 'period_year', 'status',
            'total_gross', 'total_deductions', 'total_net'
        )
        
        summary = {
            'total_gross': sum(c['total_gross'] or 0 for c in cycles),
            'total_deductions': sum(c['total_deductions'] or 0 for c in cycles),
            'total_net': sum(c['total_net'] or 0 for c in cycles),
            'cycles': list(cycles)
        }
        
        return summary
    
    @staticmethod
    def get_monthly_payroll(month, year):
        """Get detailed monthly payroll"""
        from payroll.models import PayrollCycle, PayrollRecord
        
        try:
            cycle = PayrollCycle.objects.get(period_month=month, period_year=year)
        except PayrollCycle.DoesNotExist:
            return None
        
        records = PayrollRecord.objects.filter(
            payroll_cycle=cycle
        ).select_related('employee__department')
        
        return {
            'cycle': {
                'id': str(cycle.id),
                'name': cycle.name,
                'status': cycle.status,
                'total_gross': float(cycle.total_gross or 0),
                'total_deductions': float(cycle.total_deductions or 0),
                'total_net': float(cycle.total_net or 0)
            },
            'employees': list(records.values(
                'employee__employee_number',
                'employee__first_name',
                'employee__last_name',
                'employee__department__name',
                'basic_salary',
                'total_allowances',
                'total_deductions',
                'gross_salary',
                'net_salary',
                'overtime_hours',
                'overtime_amount'
            ))
        }
    
    @staticmethod
    def get_department_payroll_cost(start_date, end_date):
        """Get payroll cost by department"""
        from payroll.models import PayrollRecord
        from hr.models import Employee
        
        records = PayrollRecord.objects.filter(
            payroll_cycle__start_date__gte=start_date,
            payroll_cycle__end_date__lte=end_date,
            payroll_cycle__status__in=['APPROVED', 'PAID']
        ).select_related('employee__department')
        
        by_department = {}
        
        for record in records:
            dept_name = record.employee.department.name
            if dept_name not in by_department:
                by_department[dept_name] = {
                    'employee_count': 0,
                    'total_gross': 0,
                    'total_deductions': 0,
                    'total_net': 0
                }
            
            by_department[dept_name]['employee_count'] += 1
            by_department[dept_name]['total_gross'] += float(record.gross_salary or 0)
            by_department[dept_name]['total_deductions'] += float(record.total_deductions or 0)
            by_department[dept_name]['total_net'] += float(record.net_salary or 0)
        
        return by_department
    
    @staticmethod
    def get_employee_payment_history(employee_id):
        """Get payment history for an employee"""
        from payroll.models import PayrollRecord
        
        records = PayrollRecord.objects.filter(
            employee_id=employee_id,
            payroll_cycle__status__in=['APPROVED', 'PAID']
        ).order_by('-payroll_cycle__period_year', '-payroll_cycle__period_month')
        
        return list(records.values(
            'payroll_cycle__period_month',
            'payroll_cycle__period_year',
            'basic_salary',
            'total_allowances',
            'total_deductions',
            'gross_salary',
            'net_salary',
            'status',
            'paid_at'
        ))
    
    @staticmethod
    def get_payroll_trend(months=12):
        """Get payroll trend for last N months"""
        from payroll.models import PayrollCycle
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        start_date = date(today.year - 1, today.month, 1) if months == 12 else today
        
        cycles = PayrollCycle.objects.filter(
            status__in=['APPROVED', 'PAID'],
            period_year__gte=start_date.year
        ).order_by('period_year', 'period_month')
        
        trend = []
        for cycle in cycles:
            trend.append({
                'month': cycle.period_month,
                'year': cycle.period_year,
                'total_gross': float(cycle.total_gross or 0),
                'total_deductions': float(cycle.total_deductions or 0),
                'total_net': float(cycle.total_net or 0),
                'employee_count': cycle.records.filter(status='CALCULATED').count()
            })
        
        return trend
    
    @staticmethod
    def export_payroll_excel(cycle_id):
        """Prepare data for Excel export (future-ready)"""
        from payroll.models import PayrollCycle, PayrollRecord
        
        try:
            cycle = PayrollCycle.objects.get(id=cycle_id)
        except PayrollCycle.DoesNotExist:
            return None
        
        records = PayrollRecord.objects.filter(
            payroll_cycle=cycle
        ).select_related('employee__department')
        
        rows = []
        for record in records:
            rows.append({
                'Employee Number': record.employee.employee_number,
                'Name': f"{record.employee.first_name} {record.employee.last_name}",
                'Department': record.employee.department.name,
                'Basic Salary': float(record.basic_salary or 0),
                'Allowances': float(record.total_allowances or 0),
                'Overtime': float(record.overtime_amount or 0),
                'Gross': float(record.gross_salary or 0),
                'Deductions': float(record.total_deductions or 0),
                'Net': float(record.net_salary or 0),
                'Status': record.status
            })
        
        return {
            'title': f"Payroll - {cycle.name}",
            'headers': list(rows[0].keys()) if rows else [],
            'rows': rows,
            'totals': {
                'Basic Salary': sum(r['Basic Salary'] for r in rows),
                'Allowances': sum(r['Allowances'] for r in rows),
                'Gross': sum(r['Gross'] for r in rows),
                'Deductions': sum(r['Deductions'] for r in rows),
                'Net': sum(r['Net'] for r in rows)
            }
        }