"""
HR URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'departments', views.DepartmentViewSet)
router.register(r'positions', views.PositionViewSet)
router.register(r'employees', views.EmployeeViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('update-status/', views.update_employee_status, name='update-employee-status'),
    path('department-tree/', views.department_tree, name='department-tree'),
    path('active-employees/', views.active_employees, name='active-employees'),
    # Reports
    path('reports/employee-summary/', views.employee_summary_report, name='employee-summary-report'),
    path('reports/department-summary/', views.department_summary_report, name='department-summary-report'),
    path('reports/attendance-summary/', views.attendance_summary_report, name='attendance-summary-report'),
    path('reports/leave-summary/', views.leave_summary_report, name='leave-summary-report'),
    path('reports/overtime-summary/', views.overtime_summary_report, name='overtime-summary-report'),
]