from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BackupRecordViewSet, BackupScheduleViewSet, BackupLogViewSet, RestorePointViewSet

router = DefaultRouter()
router.register(r'records', BackupRecordViewSet, basename='backup-record')
router.register(r'schedules', BackupScheduleViewSet, basename='backup-schedule')
router.register(r'logs', BackupLogViewSet, basename='backup-log')
router.register(r'restore-points', RestorePointViewSet, basename='restore-point')

urlpatterns = [
    path('', include(router.urls)),
]