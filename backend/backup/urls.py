from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BackupRecordViewSet, BackupScheduleViewSet, BackupLogViewSet,
    RestorePointViewSet, BackupHealthViewSet, OffsiteReplicationViewSet,
    RecoveryValidationViewSet, CertificationViewSet,
    FailureInjectionViewSet, SafeRestoreTestingViewSet,
    ControlPlaneViewSet,
)

router = DefaultRouter()
router.register(r'records', BackupRecordViewSet, basename='backup-record')
router.register(r'schedules', BackupScheduleViewSet, basename='backup-schedule')
router.register(r'logs', BackupLogViewSet, basename='backup-log')
router.register(r'restore-points', RestorePointViewSet, basename='restore-point')
router.register(r'health', BackupHealthViewSet, basename='backup-health')
router.register(r'offsite', OffsiteReplicationViewSet, basename='offsite-replication')
router.register(r'recovery', RecoveryValidationViewSet, basename='recovery-validation')
router.register(r'certification', CertificationViewSet, basename='certification')
router.register(r'failure-injection', FailureInjectionViewSet, basename='failure-injection')
router.register(r'safe-restore-test', SafeRestoreTestingViewSet, basename='safe-restore-test')
router.register(r'control-plane', ControlPlaneViewSet, basename='control-plane')

urlpatterns = [
    path('', include(router.urls)),
]