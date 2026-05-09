"""
Payroll API Views - Thin API layer, business logic in services
"""
from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from calendar import monthrange

from .models import (
    PayrollCycle, PayrollRecord, SalaryStructure,
    Allowance, Deduction, EmployeeSalary
)
from .serializers import (
    PayrollCycleSerializer, PayrollRecordSerializer,
    SalaryStructureSerializer, AllowanceSerializer,
    DeductionSerializer, EmployeeSalarySerializer
)
from .services import PayrollService, SalaryCalculationService

User = get_user_model()


class PayrollCycleViewSet(viewsets.ModelViewSet):
    """API for Payroll Cycle CRUD"""
    queryset = PayrollCycle.objects.all()
    serializer_class = PayrollCycleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PayrollCycle.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by('-period_year', '-period_month')
    
    @staticmethod
    def create(request):
        """Create payroll cycle"""
        period_month = request.data.get('period_month')
        period_year = request.data.get('period_year')
        
        if not period_month or not period_year:
            return Response(
                {'error': 'period_month and period_year required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate dates
        start_date = date(int(period_year), int(period_month), 1)
        last_day = monthrange(int(period_year), int(period_month))[1]
        end_date = date(int(period_year), int(period_month), last_day)
        
        name = f"Payroll {period_month}/{period_year}"
        
        try:
            cycle = PayrollService.create_payroll_cycle(
                name=name,
                period_month=int(period_month),
                period_year=int(period_year),
                start_date=start_date,
                end_date=end_date
            )
            serializer = PayrollCycleSerializer(cycle)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PayrollRecordViewSet(viewsets.ModelViewSet):
    """API for Payroll Record CRUD"""
    queryset = PayrollRecord.objects.all()
    serializer_class = PayrollRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PayrollRecord.objects.all()
        cycle_id = self.request.query_params.get('cycle')
        employee_id = self.request.query_params.get('employee')
        if cycle_id:
            queryset = queryset.filter(payroll_cycle_id=cycle_id)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset.select_related('payroll_cycle', 'employee')


class AllowanceViewSet(viewsets.ModelViewSet):
    """API for Allowance CRUD"""
    queryset = Allowance.objects.all()
    serializer_class = AllowanceSerializer
    permission_classes = [IsAuthenticated]


class DeductionViewSet(viewsets.ModelViewSet):
    """API for Deduction CRUD"""
    queryset = Deduction.objects.all()
    serializer_class = DeductionSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_payroll(request):
    """Generate payroll for a cycle"""
    cycle_id = request.data.get('cycle_id')
    
    if not cycle_id:
        return Response(
            {'error': 'cycle_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from payroll.models import PayrollCycle
        cycle = PayrollCycle.objects.get(id=cycle_id)
        
        records = PayrollService.generate_payroll(cycle)
        
        serializer = PayrollRecordSerializer(records, many=True)
        return Response({
            'cycle': PayrollCycleSerializer(cycle).data,
            'records': serializer.data,
            'count': len(records)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_payroll(request):
    """Approve payroll cycle"""
    cycle_id = request.data.get('cycle_id')
    
    if not cycle_id:
        return Response(
            {'error': 'cycle_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from payroll.models import PayrollCycle
        cycle = PayrollCycle.objects.get(id=cycle_id)
        
        cycle = PayrollService.approve_payroll(cycle, request.user)
        
        return Response(PayrollCycleSerializer(cycle).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_summary(request):
    """Get payroll summary"""
    cycles = PayrollCycle.objects.all()[:12]  # Last 12 months
    
    summary = []
    for cycle in cycles:
        summary.append({
            'id': str(cycle.id),
            'name': cycle.name,
            'period_month': cycle.period_month,
            'period_year': cycle.period_year,
            'status': cycle.status,
            'total_gross': float(cycle.total_gross),
            'total_deductions': float(cycle.total_deductions),
            'total_net': float(cycle.total_net),
            'approved_at': cycle.approved_at.isoformat() if cycle.approved_at else None
        })
    
    return Response(summary)


# ==================== REPORTS ====================

from payroll.services.reports import PayrollReportService


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_yearly_summary(request):
    """Get yearly payroll summary"""
    year = request.query_params.get('year')
    if year:
        year = int(year)
    else:
        year = timezone.now().year
    
    summary = PayrollReportService.get_payroll_summary(year)
    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_monthly_detail(request):
    """Get monthly payroll detail"""
    month = int(request.query_params.get('month', timezone.now().month))
    year = int(request.query_params.get('year', timezone.now().year))
    
    detail = PayrollReportService.get_monthly_payroll(month, year)
    if not detail:
        return Response({'error': 'Payroll not found'}, status=404)
    
    return Response(detail)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_department_cost(request):
    """Get payroll cost by department"""
    start = request.query_params.get('start_date')
    end = request.query_params.get('end_date')
    
    if not start or not end:
        today = timezone.now().date()
        start = today.replace(day=1)
        end = today
    else:
        start = timezone.datetime.strptime(start, '%Y-%m-%d').date()
        end = timezone.datetime.strptime(end, '%Y-%m-%d').date()
    
    cost = PayrollReportService.get_department_payroll_cost(start, end)
    return Response(cost)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_employee_history(request):
    """Get employee payment history"""
    employee_id = request.query_params.get('employee_id')
    if not employee_id:
        return Response({'error': 'employee_id required'}, status=400)
    
    history = PayrollReportService.get_employee_payment_history(employee_id)
    return Response(history)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_trend(request):
    """Get payroll trend"""
    months = int(request.query_params.get('months', 12))
    trend = PayrollReportService.get_payroll_trend(months)
    return Response(trend)