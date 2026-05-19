from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from .models import BackupRecord, BackupSchedule, BackupLog, RestorePoint, RestoreValidation
from .serializers import (
    BackupRecordSerializer,
    BackupScheduleSerializer,
    BackupLogSerializer,
    CreateBackupSerializer,
    RestoreBackupSerializer,
    RestorePointSerializer,
)
from backup.backup_system import BackupManager
from backup.services.restore_service import RestoreService
from backup.services.restore_lock import RestoreLock
from backup.services.health_monitor import BackupHealthMonitor
from backup.services.offsite_replication import OffsiteReplicator, OffsiteReplicationConfig
from backup.services.recovery_validator import AccountingRecoveryValidator, InventoryRecoveryValidator
from backup.services.certification_report import RecoveryCertificationReport
from backup.services.corruption_scanner import CorruptionScanner
from backup.services.failure_injection import FailureInjectionTester
from backup.services.restore_testing import SafeRestoreTester
from backup.services.control_plane import BackupControlPlane
from security.permissions import RoleBasedPermission

# ============================================================================
# ARCHITECTURE LOCK — DO NOT MODIFY WITHOUT REVIEW
# ============================================================================
# GUARDRAIL 1: SSOT IS FINAL AUTHORITY
#   All UI status reads MUST use ControlPlaneViewSet (SSOT endpoint).
#   Secondary status endpoints (BackupHealthViewSet, CertificationViewSet)
#   are for API consumers only — NEVER wire them to UI.
#
# GUARDRAIL 2: RESTORE IS SINGLE-LOCK EXECUTION
#   All restore endpoints MUST acquire RestoreLock via lock.acquire().
#   NEVER use lock.is_locked check alone (TOCTOU race condition).
#   ALWAYS release lock in finally block.
#
# GUARDRAIL 3: EMAIL IS QUEUED, NEVER DIRECTLY COUPLED
#   Email failures MUST queue for retry — never block backup/restore.
#   OffsiteReplicationViewSet is isolated from restore flow.
#
# GUARDRAIL 4: NO DUPLICATE STATE SOURCES
#   Do not add new status computation endpoints that overlap with SSOT.
#   All system state derivation happens in BackupControlPlane.get_status().
#
# GUARDRAIL 5: ALL FAILURES ARE ISOLATED
#   Each service call in control plane is wrapped in try/except.
#   Failure in one service MUST NOT cascade to others.
# ============================================================================


class BackupRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """View set for viewing backup records"""
    queryset = BackupRecord.objects.all()
    serializer_class = BackupRecordSerializer
    permission_classes = [RoleBasedPermission]
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get backup statistics"""
        backup_manager = BackupManager()
        stats = backup_manager.get_backup_stats()
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def create_backup(self, request):
        """Create a new backup"""
        serializer = CreateBackupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create backup record
        backup_record = BackupRecord.objects.create(
            status='in_progress',
            backup_type='manual',
            created_by=request.user,
            started_at=timezone.now(),
            description=serializer.validated_data.get('description', 'Manual backup'),
        )
        
        try:
            # Perform backup
            backup_manager = BackupManager()
            result = backup_manager.create_backup(
                include_files=serializer.validated_data.get('include_files', []),
                description=serializer.validated_data.get('description', 'Manual backup'),
            )
            
            if result['success']:
                # Update backup record
                metadata = result['metadata']
                backup_record.status = 'completed'
                backup_record.filename = metadata['filename']
                backup_record.file_path = result['backup_path']
                backup_record.file_size_bytes = metadata['size_bytes']
                backup_record.checksum = metadata['checksum']
                backup_record.encrypted = metadata.get('encrypted', False)
                backup_record.compressed = metadata.get('compressed', False)
                backup_record.completed_at = timezone.now()
                backup_record.duration_seconds = metadata.get('duration', 0)
                backup_record.save()
                
                # Log the event
                BackupLog.objects.create(
                    level='INFO',
                    event='backup_completed',
                    message=f"Backup completed: {metadata['filename']}",
                    backup_record=backup_record,
                    user=request.user,
                    details={'size_mb': metadata['size_mb']},
                )
                
                return Response({
                    'success': True,
                    'backup_record': BackupRecordSerializer(backup_record).data,
                    'metadata': metadata,
                })
            else:
                # Update backup record with failure
                backup_record.status = 'failed'
                backup_record.completed_at = timezone.now()
                backup_record.save()
                
                BackupLog.objects.create(
                    level='ERROR',
                    event='backup_failed',
                    message=f"Backup failed: {result.get('error', 'Unknown error')}",
                    backup_record=backup_record,
                    user=request.user,
                )
                
                return Response({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            backup_record.status = 'failed'
            backup_record.completed_at = timezone.now()
            backup_record.save()
            
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a backup record"""
        backup_record = self.get_object()
        
        from backup.backup_system import BackupValidator
        validator = BackupValidator()
        
        # Verify file exists and is valid
        valid, msg = validator.verify_backup_archive(backup_record.file_path)
        
        if valid:
            backup_record.status = 'verified'
            backup_record.verified_at = timezone.now()
            backup_record.verified_by = request.user
            backup_record.verification_result = msg
            backup_record.save()
            
            BackupLog.objects.create(
                level='INFO',
                event='backup_verified',
                message=f"Backup verified: {backup_record.filename}",
                backup_record=backup_record,
                user=request.user,
            )
            
            return Response({
                'success': True,
                'message': msg,
            })
        else:
            backup_record.verification_result = msg
            backup_record.save()
            
            return Response({
                'success': False,
                'message': msg,
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore from a backup record with lock safety.

        NOTE: This is a direct restore path. For full validation + emergency backup,
        use RestorePointViewSet.restore instead (validate → restore flow).
        """
        backup_record = self.get_object()

        lock = RestoreLock()
        if not lock.acquire(timeout=10):
            return Response({
                'success': False,
                'error': 'Another restore is already in progress or lock acquisition timed out',
            }, status=status.HTTP_409_CONFLICT)

        serializer = RestoreBackupSerializer(data=request.data)
        if not serializer.is_valid():
            lock.release()
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            backup_manager = BackupManager()
            result = backup_manager.restore_backup(
                backup_path=backup_record.file_path,
                target_db_path=serializer.validated_data.get('target_db_path'),
                password=serializer.validated_data.get('password'),
                verify=serializer.validated_data.get('verify', True),
            )

            if result['success']:
                backup_record.status = 'restored'
                backup_record.restored_at = timezone.now()
                backup_record.restored_by = request.user
                backup_record.restore_target_path = result['target_path']
                backup_record.save()

                BackupLog.objects.create(
                    level='INFO',
                    event='restore_completed',
                    message=f"Backup restored: {backup_record.filename}",
                    backup_record=backup_record,
                    user=request.user,
                    details={'duration': result.get('duration', 0)},
                )

                return Response({
                    'success': True,
                    'message': 'Backup restored successfully',
                    'target_path': result['target_path'],
                    'duration': result.get('duration', 0),
                })
            else:
                BackupLog.objects.create(
                    level='ERROR',
                    event='restore_failed',
                    message=f"Restore failed: {result.get('error', 'Unknown')}",
                    backup_record=backup_record,
                    user=request.user,
                )
                return Response({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            BackupLog.objects.create(
                level='ERROR',
                event='restore_failed',
                message=f"Restore exception: {str(e)}",
                backup_record=backup_record,
                user=request.user,
            )
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            lock.release()
    
    @action(detail=True, methods=['delete'])
    def delete_backup(self, request, pk=None):
        """Delete a backup record and file"""
        backup_record = self.get_object()
        
        backup_manager = BackupManager()
        deleted = backup_manager.delete_backup(backup_record.file_path)
        
        if deleted:
            backup_record.status = 'deleted'
            backup_record.save()
            
            BackupLog.objects.create(
                level='INFO',
                event='backup_deleted',
                message=f"Backup deleted: {backup_record.filename}",
                backup_record=backup_record,
                user=request.user,
            )
            
            return Response({'success': True})
        else:
            return Response({
                'success': False,
                'error': 'Failed to delete backup file',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BackupScheduleViewSet(viewsets.ModelViewSet):
    """View set for managing backup schedules"""
    queryset = BackupSchedule.objects.all()
    serializer_class = BackupScheduleSerializer
    permission_classes = [RoleBasedPermission]


class BackupLogViewSet(viewsets.ReadOnlyModelViewSet):
    """View set for viewing backup logs"""
    queryset = BackupLog.objects.all()
    serializer_class = BackupLogSerializer
    permission_classes = [RoleBasedPermission]
    ordering = ['-timestamp']

    @action(detail=False, methods=['get'])
    def operational_summary(self, request):
        """Get structured operational log summary (bounded, no streaming)."""
        recent = self.queryset.order_by('-timestamp')[:50]
        logs = []
        for log in recent:
            logs.append({
                'timestamp': log.timestamp.isoformat() if log.timestamp else '',
                'level': log.level,
                'event': log.event,
                'message': log.message,
                'user': log.user.username if log.user else 'system',
            })

        event_counts = {}
        for log in self.queryset.values_list('event', flat=True).order_by('event'):
            event_counts[log] = event_counts.get(log, 0) + 1

        return Response({
            'recent': logs,
            'event_counts': event_counts,
            'total': self.queryset.count(),
        })


class RestorePointViewSet(viewsets.ReadOnlyModelViewSet):
    """View set for viewing restore points"""
    queryset = RestorePoint.objects.all()
    serializer_class = RestorePointSerializer
    permission_classes = [RoleBasedPermission]
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate a backup before restore"""
        restore_point = self.get_object()
        
        if restore_point.status != 'pending':
            return Response({
                'success': False,
                'error': f'Cannot validate: status is {restore_point.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        restore_service = RestoreService(restore_point.backup_record)
        restore_point = restore_service.validate_backup(user=request.user)
        
        return Response({
            'success': restore_point.is_valid,
            'restore_point': RestorePointSerializer(restore_point).data,
            'validation_errors': restore_point.validation_errors,
        })
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore from a validated backup using unified restore flow."""
        restore_point = self.get_object()

        if not restore_point.is_valid:
            return Response({
                'success': False,
                'error': 'Backup not validated'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Hard mutex — acquire lock atomically (not just check)
        lock = RestoreLock()
        if not lock.acquire(timeout=10):
            return Response({
                'success': False,
                'error': 'Another restore is already in progress or lock acquisition timed out'
            }, status=status.HTTP_409_CONFLICT)

        restore_service = RestoreService(restore_point.backup_record)

        try:
            result = restore_service.restore(
                user=request.user,
                restore_point=restore_point,
                password=request.data.get('password'),
                target_db_path=request.data.get('target_db_path'),
            )
            return Response(result)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            lock.release()
    
    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """Rollback to pre-restore snapshot"""
        restore_point = self.get_object()
        
        if not restore_point.can_rollback:
            return Response({
                'success': False,
                'error': 'Rollback not allowed for this restore point'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if restore_point.status != 'restored':
            return Response({
                'success': False,
                'error': 'Can only rollback restored backups'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        restore_service = RestoreService(restore_point.backup_record)
        
        try:
            result = restore_service.rollback(restore_point, user=request.user)
            return Response(result)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def can_restore(self, request):
        """Check which backups can be restored"""
        valid_restore_points = RestorePoint.objects.filter(
            is_valid=True,
            status__in=['validated', 'restored']
        ).select_related('backup_record')
        
        return Response({
            'count': valid_restore_points.count(),
            'restore_points': RestorePointSerializer(valid_restore_points, many=True).data,
        })


class BackupHealthViewSet(viewsets.ViewSet):
    """View set for backup health monitoring."""
    permission_classes = [RoleBasedPermission]
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get comprehensive backup health status."""
        monitor = BackupHealthMonitor()
        health = monitor.check_health()
        return Response(health)
    
    @action(detail=False, methods=['get'])
    def startup_warning(self, request):
        """Get startup warning if any."""
        monitor = BackupHealthMonitor()
        warning = monitor.get_startup_warning()
        return Response({
            'warning': warning,
            'has_warning': warning is not None,
        })
    
    @action(detail=False, methods=['post'])
    def dry_run_validate(self, request):
        """Validate a backup file without restoring."""
        backup_path = request.data.get('backup_path')
        if not backup_path:
            return Response({
                'success': False,
                'error': 'backup_path is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        monitor = BackupHealthMonitor()
        result = monitor.dry_run_validate(backup_path)
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def revalidate_checksums(self, request):
        """Revalidate checksums for all stored backups."""
        monitor = BackupHealthMonitor()
        result = monitor.revalidate_all_checksums()
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def lock_status(self, request):
        """Check if a restore lock is active."""
        lock = RestoreLock()
        return Response({
            'is_locked': lock.is_locked,
            'lock_file': str(lock.lock_file),
        })




class RecoveryValidationViewSet(viewsets.ViewSet):
    """View set for post-restore recovery validation."""
    permission_classes = [RoleBasedPermission]
    
    @action(detail=False, methods=['get'])
    def accounting(self, request):
        """Validate accounting consistency after restore."""
        validator = AccountingRecoveryValidator()
        result = validator.validate()
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """Validate inventory consistency after restore."""
        validator = InventoryRecoveryValidator()
        result = validator.validate()
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def full(self, request):
        """Run full recovery validation (accounting + inventory)."""
        acc_validator = AccountingRecoveryValidator()
        inv_validator = InventoryRecoveryValidator()
        
        acc_result = acc_validator.validate()
        inv_result = inv_validator.validate()
        
        all_valid = acc_result['valid'] and inv_result['valid']
        all_errors = acc_result.get('errors', []) + inv_result.get('errors', [])
        all_warnings = acc_result.get('warnings', []) + inv_result.get('warnings', [])
        all_checks = acc_result.get('checks', []) + inv_result.get('checks', [])
        
        return Response({
            'valid': all_valid,
            'checks': all_checks,
            'errors': all_errors,
            'warnings': all_warnings,
            'accounting': acc_result,
            'inventory': inv_result,
        })


class CertificationViewSet(viewsets.ViewSet):
    """View set for recovery certification reporting."""
    permission_classes = [RoleBasedPermission]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a recovery certification report."""
        acc_validator = AccountingRecoveryValidator()
        inv_validator = InventoryRecoveryValidator()
        
        acc_result = acc_validator.validate()
        inv_result = inv_validator.validate()
        
        report = RecoveryCertificationReport(
            accounting_results=acc_result,
            inventory_results=inv_result,
            restore_duration_seconds=request.data.get('restore_duration', 0),
            validation_duration_seconds=request.data.get('validation_duration', 0),
            backup_checksum_valid=request.data.get('backup_checksum_valid', True),
            rollback_tested=request.data.get('rollback_tested', False),
        )
        
        certification = report.generate()
        return Response(certification)
    
    @action(detail=False, methods=['get'])
    def quick_status(self, request):
        """Quick recovery status without full certification."""
        scanner = CorruptionScanner()
        scan_result = scanner.scan()
        
        return Response({
            'valid': scan_result['valid'],
            'scans_run': len(scan_result.get('scans', [])),
            'errors': scan_result.get('errors', []),
            'warnings': scan_result.get('warnings', []),
        })


class FailureInjectionViewSet(viewsets.ViewSet):
    """View set for safe failure injection testing."""
    permission_classes = [RoleBasedPermission]
    
    @action(detail=False, methods=['post'])
    def run_all(self, request):
        """Run all failure injection scenarios."""
        tester = FailureInjectionTester()
        results = tester.run_all()
        return Response(results)
    
    @action(detail=False, methods=['post'])
    def run_scenario(self, request):
        """Run a specific failure injection scenario."""
        scenario = request.data.get('scenario')
        if not scenario:
            return Response({
                'success': False,
                'error': 'scenario is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tester = FailureInjectionTester()
        method_name = f'test_{scenario}'
        method = getattr(tester, method_name, None)
        if method is None:
            return Response({
                'success': False,
                'error': f'Unknown scenario: {scenario}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = method()
        return Response(result)


class SafeRestoreTestingViewSet(viewsets.ViewSet):
    """View set for safe automated restore testing."""
    permission_classes = [RoleBasedPermission]
    
    @action(detail=False, methods=['post'])
    def run_test(self, request):
        """Run a safe restore test in isolated environment."""
        tester = SafeRestoreTester()
        result = tester.run_test()
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Check if restore testing is available."""
        tester = SafeRestoreTester()
        backup_path = tester._resolve_backup_path()
        return Response({
            'available': backup_path is not None,
            'reason': 'Backup file found' if backup_path else 'No backup file available for testing',
            'backup_path': backup_path,
        })


class ControlPlaneViewSet(viewsets.ViewSet):
    """Unified control plane — Single Source of Operational Truth (SSOT).

    All UI components MUST read from this endpoint for system state.
    No independent state computation by UI components.
    """
    permission_classes = [RoleBasedPermission]

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get unified system status (SSOT)."""
        plane = BackupControlPlane()
        status = plane.get_status()
        return Response(status.to_dict())

    @action(detail=False, methods=['get'])
    def restore_readiness(self, request):
        """Get restore readiness assessment."""
        plane = BackupControlPlane()
        return Response(plane.get_restore_readiness())

    @action(detail=False, methods=['get'])
    def backup_readiness(self, request):
        """Get backup creation readiness assessment."""
        plane = BackupControlPlane()
        return Response(plane.get_backup_readiness())


class OffsiteReplicationViewSet(viewsets.ViewSet):
    """View set for offsite backup replication."""
    permission_classes = [RoleBasedPermission]

    @action(detail=False, methods=['get'])
    def config(self, request):
        """Get offsite replication config."""
        config = OffsiteReplicationConfig()
        cfg = config.load()
        if cfg.get('smtp_password'):
            cfg['smtp_password'] = '***'
        return Response(cfg)

    @action(detail=False, methods=['post'])
    def save_config(self, request):
        """Save offsite replication config with validation."""
        config = OffsiteReplicationConfig()
        current = config.load()

        new_config = request.data.copy()
        if new_config.get('smtp_password') == '***':
            new_config['smtp_password'] = current.get('smtp_password', '')

        if new_config.get('enabled', False):
            required = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email']
            missing = [f for f in required if not new_config.get(f)]
            if missing:
                return Response({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing)}',
                }, status=status.HTTP_400_BAD_REQUEST)

        config.save(new_config)
        return Response({'success': True, 'message': 'Configuration saved'})

    @action(detail=False, methods=['post'])
    def test_email(self, request):
        """Send a test email to verify SMTP configuration."""
        config = OffsiteReplicationConfig()
        cfg = config.load()

        test_recipient = request.data.get('recipient', cfg.get('from_email', ''))
        if not test_recipient:
            return Response({
                'success': False,
                'error': 'No recipient specified for test email',
            }, status=status.HTTP_400_BAD_REQUEST)

        if not cfg.get('smtp_host'):
            return Response({
                'success': False,
                'error': 'SMTP not configured — save configuration first',
            }, status=status.HTTP_400_BAD_REQUEST)

        from datetime import datetime
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        try:
            msg = MIMEMultipart()
            msg['From'] = cfg['from_email']
            msg['To'] = test_recipient
            msg['Subject'] = 'Pharmacy ERP — SMTP Test'

            body = (
                f"Pharmacy ERP SMTP Test\n"
                f"======================\n\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"If you received this email, your SMTP configuration is working correctly."
            )
            msg.attach(MIMEText(body, 'plain'))

            if cfg.get('smtp_use_tls', True):
                server = smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port'])
                server.starttls()
            else:
                server = smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port'])

            if cfg.get('smtp_user') and cfg.get('smtp_password'):
                server.login(cfg['smtp_user'], cfg['smtp_password'])

            server.sendmail(cfg['from_email'], [test_recipient], msg.as_string())
            server.quit()

            return Response({
                'success': True,
                'message': f'Test email sent to {test_recipient}',
            })
        except smtplib.SMTPAuthenticationError:
            return Response({
                'success': False,
                'error': 'SMTP authentication failed — check username and password',
                'error_category': 'auth_failure',
            }, status=status.HTTP_400_BAD_REQUEST)
        except smtplib.SMTPConnectError:
            return Response({
                'success': False,
                'error': 'Cannot connect to SMTP server — check host and port',
                'error_category': 'network_failure',
            }, status=status.HTTP_400_BAD_REQUEST)
        except smtplib.SMTPException as e:
            return Response({
                'success': False,
                'error': f'SMTP error: {str(e)}',
                'error_category': 'smtp_misconfiguration',
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'error_category': 'timeout',
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def send_backup(self, request):
        """Send a backup to offsite recipients."""
        backup_record_id = request.data.get('backup_record_id')
        if not backup_record_id:
            return Response({
                'success': False,
                'error': 'backup_record_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            backup_record = BackupRecord.objects.get(id=backup_record_id)
        except BackupRecord.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Backup record not found'
            }, status=status.HTTP_404_NOT_FOUND)

        replicator = OffsiteReplicator()
        result = replicator.send_backup(
            backup_record.file_path,
            description=backup_record.description,
        )
        return Response(result)

    @action(detail=False, methods=['post'])
    def process_retry_queue(self, request):
        """Process pending offsite retry queue."""
        replicator = OffsiteReplicator()
        result = replicator.process_retry_queue()
        return Response(result)

    @action(detail=False, methods=['get'])
    def retry_queue_status(self, request):
        """Get retry queue status with delivery history."""
        from backup.services.offsite_replication import RetryQueue
        from pathlib import Path
        import os

        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        retry_dir = Path(appdata) / 'PharmacyERP' / 'config' / 'offsite_retry'
        queue = RetryQueue(retry_dir)

        pending = queue.get_pending()

        all_entries = []
        for queue_file in retry_dir.glob('retry_*.json'):
            try:
                import json
                with open(queue_file, 'r') as f:
                    entry = json.load(f)
                entry['_queue_file'] = str(queue_file)
                all_entries.append(entry)
            except Exception:
                pass

        all_entries.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return Response({
            'pending_count': len(pending),
            'total_entries': len(all_entries),
            'pending': pending[:10],
            'history': all_entries[:20],
        })

    @action(detail=False, methods=['post'])
    def retry_single(self, request):
        """Retry a single failed email delivery."""
        queue_file = request.data.get('queue_file')
        if not queue_file:
            return Response({
                'success': False,
                'error': 'queue_file path is required',
            }, status=status.HTTP_400_BAD_REQUEST)

        from pathlib import Path
        import json
        import os

        try:
            with open(queue_file, 'r') as f:
                entry = json.load(f)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Cannot read retry entry: {str(e)}',
            }, status=status.HTTP_400_BAD_REQUEST)

        backup_path = entry.get('backup_path')
        if not backup_path or not os.path.exists(backup_path):
            return Response({
                'success': False,
                'error': 'Backup file no longer exists',
            }, status=status.HTTP_400_BAD_REQUEST)

        replicator = OffsiteReplicator()
        from backup.services.offsite_replication import RetryQueue
        queue = RetryQueue(Path(queue_file).parent)
        try:
            replicator._send_email(
                backup_path,
                entry.get('recipients', []),
                entry.get('metadata', {}).get('description', ''),
            )
            queue.mark_sent(queue_file)
            return Response({'success': True, 'message': 'Email sent successfully'})
        except Exception as e:
            queue.mark_failed(queue_file, str(e))
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)