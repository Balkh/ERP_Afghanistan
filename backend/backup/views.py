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


class BackupRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """View set for viewing backup records"""
    queryset = BackupRecord.objects.all()
    serializer_class = BackupRecordSerializer
    permission_classes = [AllowAny]
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
        """Restore from a backup record"""
        backup_record = self.get_object()
        
        serializer = RestoreBackupSerializer(data=request.data)
        if not serializer.is_valid():
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
                )
                
                return Response({
                    'success': True,
                    'message': 'Backup restored successfully',
                    'target_path': result['target_path'],
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
    permission_classes = [AllowAny]
    ordering = ['-created_at']


class BackupLogViewSet(viewsets.ReadOnlyModelViewSet):
    """View set for viewing backup logs"""
    queryset = BackupLog.objects.all()
    serializer_class = BackupLogSerializer
    permission_classes = [AllowAny]
    ordering = ['-timestamp']


class RestorePointViewSet(viewsets.ReadOnlyModelViewSet):
    """View set for viewing restore points"""
    queryset = RestorePoint.objects.all()
    serializer_class = RestorePointSerializer
    permission_classes = [AllowAny]
    ordering = ['-created_at']
    
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
        """Restore from a validated backup"""
        restore_point = self.get_object()
        
        if not restore_point.is_valid:
            return Response({
                'success': False,
                'error': 'Backup not validated'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        restore_service = RestoreService(restore_point.backup_record)
        
        try:
            result = restore_service.restore(user=request.user, restore_point=restore_point)
            return Response(result)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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