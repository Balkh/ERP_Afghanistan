"""
Payroll URL Configuration
"""
from datetime import date
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'cycles', views.PayrollCycleViewSet)
router.register(r'records', views.PayrollRecordViewSet)
router.register(r'allowances', views.AllowanceViewSet)
router.register(r'deductions', views.DeductionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', views.generate_payroll, name='generate-payroll'),
    path('approve/', views.approve_payroll, name='approve-payroll'),
    path('summary/', views.payroll_summary, name='payroll-summary'),
    # Reports
    path('reports/yearly-summary/', views.payroll_yearly_summary, name='payroll-yearly-summary'),
    path('reports/monthly-detail/', views.payroll_monthly_detail, name='payroll-monthly-detail'),
    path('reports/department-cost/', views.payroll_department_cost, name='payroll-department-cost'),
    path('reports/employee-history/', views.payroll_employee_history, name='payroll-employee-history'),
    path('reports/trend/', views.payroll_trend, name='payroll-trend'),
]