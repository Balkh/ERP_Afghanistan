"""Jobs app URLs"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    BackgroundJobViewSet,
    JobStatusView,
    JobActionView,
    JobStatsView,
    ScheduledTaskViewSet,
    RunScheduledTasksView
)

router = DefaultRouter()
router.register(r'jobs', BackgroundJobViewSet, basename='background-job')
router.register(r'scheduled', ScheduledTaskViewSet, basename='scheduled-task')

urlpatterns = [
    path('job/<int:job_id>/', JobStatusView.as_view(), name='job-status'),
    path('job/<int:job_id>/action/', JobActionView.as_view(), name='job-action'),
    path('stats/', JobStatsView.as_view(), name='job-stats'),
    path('run-scheduled/', RunScheduledTasksView.as_view(), name='run-scheduled'),
] + router.urls