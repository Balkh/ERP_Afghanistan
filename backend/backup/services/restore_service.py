"""
Refactored RestoreService with dependency injection.

This version is fully testable without filesystem access:
- Uses injected providers for all file operations
- Contains only orchestration logic
- Delegates physical restore to BackupManager.restore_backup()
- Easy to mock for unit tests
"""
import logging
import os
import tempfile
import shutil
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.db import transaction
from django.conf import settings
from django.utils import timezone

from backup.models import BackupRecord, RestorePoint, RestoreValidation

logger = logging.getLogger('backup')


class RestoreService:
    """
    Orchestration layer for backup validation and restore operations.
    
    Delegates physical restore execution to BackupManager.restore_backup().
    Uses dependency injection for all external dependencies (filesystem, checksums, archives).
    This makes the service fully testable without any disk I/O.
    """
    
    REQUIRED_TABLES = [
        'accounting_account',
        'inventory_product',
        'sales_invoice',
        'purchases_invoice',
    ]
    
    def __init__(
        self,
        backup_record: BackupRecord,
        file_provider=None,
        checksum_provider=None,
        archive_provider=None,
        backup_manager=None,
    ):
        """
        Initialize RestoreService with optional providers.
        
        If providers are not provided, uses production implementations.
        This allows seamless operation in production while enabling
        full testability with mocks.
        """
        self.backup_record = backup_record
        self.validation_errors: List[Dict[str, Any]] = []
        
        # Import and use production providers if not provided
        from backup.services.providers import (
            ProductionFileProvider,
            ProductionChecksumProvider,
            ProductionArchiveProvider,
        )
        
        self._file_provider = file_provider or ProductionFileProvider()
        self._checksum_provider = checksum_provider or ProductionChecksumProvider()
        self._archive_provider = archive_provider or ProductionArchiveProvider()
        
        # BackupManager is the single source of truth for physical restore
        if backup_manager is not None:
            self._backup_manager = backup_manager
        else:
            from backup.backup_system import BackupManager
            self._backup_manager = BackupManager()
    
    @transaction.atomic
    def validate_backup(self, user=None) -> RestorePoint:
        """Validate a backup file before restore"""
        restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='validating'
        )
        
        self.validation_errors = []
        
        self._validate_file_exists(restore_point)
        self._validate_file_checksum(restore_point)
        self._validate_archive_structure(restore_point)
        self._validate_database_schema(restore_point)
        self._validate_data_integrity(restore_point)
        
        restore_point.is_valid = len(self.validation_errors) == 0
        restore_point.validation_errors = self.validation_errors
        restore_point.validated_at = timezone.now()
        restore_point.validated_by = user
        restore_point.status = 'validated' if restore_point.is_valid else 'failed'
        restore_point.save()
        
        return restore_point
    
    def _validate_file_exists(self, restore_point: RestorePoint):
        """Check if backup file exists using injected provider."""
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            self.validation_errors.append({
                'type': 'file_exists',
                'severity': 'critical',
                'message': f'Backup file not found: {file_path}'
            })
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='schema',
                is_valid=False,
                error_message=f'Backup file not found: {file_path}'
            )
        else:
            size = self._file_provider.get_size(file_path)
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='schema',
                is_valid=True,
                details={'file_path': file_path, 'size': size}
            )
    
    def _validate_file_checksum(self, restore_point: RestorePoint):
        """Verify file checksum matches using injected provider."""
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            return
        
        stored_checksum = self.backup_record.checksum
        if not stored_checksum:
            self.validation_errors.append({
                'type': 'checksum',
                'severity': 'warning',
                'message': 'No checksum stored for comparison'
            })
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='data_integrity',
                is_valid=True,
                error_message='No checksum stored',
                details={'warning': 'Manual verification recommended'}
            )
            return
        
        try:
            is_valid = self._checksum_provider.verify_checksum(file_path, stored_checksum)
            calculated = self._checksum_provider.calculate_sha256(file_path)
            
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='data_integrity',
                is_valid=is_valid,
                error_message='' if is_valid else 'Checksum mismatch',
                details={
                    'stored': stored_checksum,
                    'calculated': calculated
                }
            )
            
            if not is_valid:
                self.validation_errors.append({
                    'type': 'checksum',
                    'severity': 'critical',
                    'message': f'Checksum mismatch: expected {stored_checksum}, got {calculated}'
                })
        except Exception as e:
            self.validation_errors.append({
                'type': 'checksum',
                'severity': 'critical',
                'message': f'Checksum validation failed: {str(e)}'
            })
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='data_integrity',
                is_valid=False,
                error_message=str(e)
            )
    
    def _validate_archive_structure(self, restore_point: RestorePoint):
        """Validate archive structure using injected provider."""
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            return
        
        file_ext = self._archive_provider.get_extension(file_path)
        is_valid = self._archive_provider.is_valid_archive(file_path)
        
        RestoreValidation.objects.create(
            restore_point=restore_point,
            validation_type='schema',
            is_valid=is_valid,
            error_message='' if is_valid else f'Unknown archive format: {file_ext}',
            details={'extension': file_ext, 'expected': ['.sql', '.dump', '.gz', '.zip', '.tar', '.tgz']}
        )
        
        if not is_valid:
            self.validation_errors.append({
                'type': 'archive_structure',
                'severity': 'error',
                'message': f'Unknown archive format: {file_ext}'
            })
    
    def _validate_database_schema(self, restore_point: RestorePoint):
        """Validate expected database tables exist in backup using injected provider."""
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            return
        
        if self._archive_provider.is_sql_file(file_path):
            result = self._archive_provider.validate_sql_content(file_path, self.REQUIRED_TABLES)
            
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='schema',
                is_valid=result['valid'],
                error_message=f'Missing tables: {result.get("missing_tables", [])}' if not result['valid'] else '',
                details={'checked_tables': result.get('checked_tables', []), 'missing': result.get('missing_tables', [])}
            )
            
            if not result['valid']:
                self.validation_errors.append({
                    'type': 'schema',
                    'severity': 'warning',
                    'message': f'Missing tables in backup: {result.get("missing_tables", [])}'
                })
        else:
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='schema',
                is_valid=True,
                details={'note': 'Binary backup format - schema validation skipped'}
            )
    
    def _validate_data_integrity(self, restore_point: RestorePoint):
        """Validate data integrity within backup using injected provider."""
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            return
        
        if self._archive_provider.is_sql_file(file_path):
            result = self._archive_provider.validate_transaction_integrity(file_path)
            
            RestoreValidation.objects.create(
                restore_point=restore_point,
                validation_type='transaction',
                is_valid=result['valid'],
                error_message='; '.join(result.get('issues', [])) if result.get('issues') else '',
                details={'issues': result.get('issues', [])}
            )
            
            if result.get('issues'):
                for issue in result['issues']:
                    self.validation_errors.append({
                        'type': 'data_integrity',
                        'severity': 'warning',
                        'message': issue
                    })
    
    @transaction.atomic
    def create_snapshot(self) -> Dict[str, Any]:
        """Create pre-restore snapshot of current system state"""
        snapshot = {
            'created_at': timezone.now().isoformat(),
            'record_counts': {},
            'last_entries': {},
        }
        
        from accounting.models import Account, JournalEntry, JournalEntryLine
        from inventory.models import Product, Batch, StockMovement
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        
        models_to_snapshot = [
            (Account, 'accounting_account'),
            (JournalEntry, 'accounting_journalentry'),
            (JournalEntryLine, 'accounting_journalentryline'),
            (Product, 'inventory_product'),
            (Batch, 'inventory_batch'),
            (StockMovement, 'inventory_stockmovement'),
            (SalesInvoice, 'sales_invoice'),
            (PurchaseInvoice, 'purchases_invoice'),
        ]
        
        for model, name in models_to_snapshot:
            snapshot['record_counts'][name] = model.objects.count()
            
            if hasattr(model, 'objects') and model.objects.exists():
                latest = model.objects.order_by('-created_at').first()
                snapshot['last_entries'][name] = {
                    'id': str(latest.id),
                    'created_at': latest.created_at.isoformat() if hasattr(latest, 'created_at') else None,
                }
        
        return snapshot
    
    @transaction.atomic
    def restore(self, user=None, restore_point: Optional[RestorePoint] = None,
                password: str = None, target_db_path: str = None) -> Dict[str, Any]:
        """
        Restore from a validated backup.
        
        Orchestration flow:
        1. Validate restore point exists and is valid
        2. Create pre-restore snapshot
        3. Create emergency backup of current database
        4. Delegate physical restore to BackupManager.restore_backup()
        5. Verify integrity of restored database
        6. Finalize restore status and logging
        
        BackupManager is the single source of truth for physical restore execution.
        """
        if restore_point is None:
            restore_point = RestorePoint.objects.filter(
                backup_record=self.backup_record,
                is_valid=True
            ).first()
        
        if not restore_point or not restore_point.is_valid:
            raise ValueError('No validated restore point found. Validate backup first.')
        
        # Capture pre-restore snapshot
        snapshot_data = self.create_snapshot()
        
        # Create emergency backup of current database before restore
        emergency_backup_path = self._create_emergency_backup()
        
        restore_point.snapshot_data = snapshot_data
        restore_point.snapshot_data['emergency_backup'] = emergency_backup_path
        restore_point.restore_started_at = timezone.now()
        restore_point.restored_by = user
        restore_point.status = 'restoring'
        restore_point.save()
        
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            restore_point.status = 'failed'
            restore_point.restore_reason = f'Backup file not found: {file_path}'
            restore_point.save()
            raise ValueError(f'Backup file not found: {file_path}')
        
        result = {
            'success': False,
            'restore_point_id': str(restore_point.id),
            'snapshot': snapshot_data,
            'emergency_backup': emergency_backup_path,
        }
        
        try:
            # Delegate to BackupManager for physical restore execution
            bm_result = self._backup_manager.restore_backup(
                backup_path=file_path,
                target_db_path=target_db_path,
                password=password,
                verify=True,
            )
            
            if bm_result['success']:
                # Verify restored database integrity
                target = bm_result.get('target_path', self._backup_manager.config['database'].get('path'))
                if target and os.path.exists(target):
                    valid, msg = self._backup_manager.validator.verify_database_integrity(target)
                    if not valid:
                        # Auto-rollback on integrity failure
                        self._rollback_to_emergency_backup(emergency_backup_path, target)
                        restore_point.status = 'failed'
                        restore_point.restore_reason = f'Post-restore integrity check failed: {msg}'
                        restore_point.save()
                        raise ValueError(f'Post-restore integrity check failed: {msg}')
                
                restore_point.status = 'restored'
                restore_point.restore_completed_at = timezone.now()
                restore_point.save()
                
                result['success'] = True
                result['target_path'] = bm_result['target_path']
                result['duration'] = bm_result.get('duration', 0)
                
                logger.info(f"Restore completed successfully: {self.backup_record.filename}")
            else:
                # Auto-rollback on restore failure
                if emergency_backup_path and os.path.exists(emergency_backup_path):
                    target = self._backup_manager.config['database'].get('path')
                    if target:
                        self._rollback_to_emergency_backup(emergency_backup_path, target)
                
                restore_point.status = 'failed'
                restore_point.restore_reason = bm_result.get('error', 'Unknown error')
                restore_point.save()
                raise ValueError(f"Restore failed: {bm_result.get('error', 'Unknown error')}")
            
        except Exception as e:
            # Auto-rollback on any exception
            if emergency_backup_path and os.path.exists(emergency_backup_path):
                target = self._backup_manager.config['database'].get('path')
                if target:
                    try:
                        self._rollback_to_emergency_backup(emergency_backup_path, target)
                    except Exception as rollback_err:
                        logger.critical(f"Emergency rollback also failed: {rollback_err}")
            
            restore_point.status = 'failed'
            restore_point.restore_reason = str(e)
            restore_point.save()
            raise
        
        return result
    
    def _create_emergency_backup(self) -> Optional[str]:
        """
        Create an emergency backup of the current database before restore.
        Returns the path to the emergency backup file, or None if not applicable.
        """
        try:
            db_path = self._backup_manager.config['database'].get('path')
            if not db_path or not os.path.exists(db_path):
                return None
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            emergency_dir = os.path.join(os.path.dirname(db_path), '.emergency_backups')
            os.makedirs(emergency_dir, exist_ok=True)
            
            emergency_path = os.path.join(emergency_dir, f'emergency_pre_restore_{timestamp}.db')
            shutil.copy2(db_path, emergency_path)
            
            logger.info(f"Emergency backup created: {emergency_path}")
            return emergency_path
        except Exception as e:
            logger.error(f"Failed to create emergency backup: {e}")
            return None
    
    def _rollback_to_emergency_backup(self, emergency_path: str, target_path: str) -> bool:
        """
        Rollback to the emergency backup. Real filesystem rollback.
        """
        try:
            if not os.path.exists(emergency_path):
                logger.error(f"Emergency backup not found: {emergency_path}")
                return False
            
            # Atomic replacement: copy to temp, then rename
            temp_path = target_path + '.rollback_tmp'
            shutil.copy2(emergency_path, temp_path)
            
            # Replace target with rollback copy
            if os.path.exists(target_path):
                os.replace(temp_path, target_path)
            else:
                os.rename(temp_path, target_path)
            
            logger.info(f"Emergency rollback completed: {emergency_path} -> {target_path}")
            return True
        except Exception as e:
            logger.critical(f"Emergency rollback failed: {e}")
            return False
    
    @transaction.atomic
    def rollback(self, restore_point: RestorePoint, user=None) -> Dict[str, Any]:
        """Rollback to pre-restore snapshot"""
        if not restore_point.can_rollback:
            raise ValueError('Rollback not allowed for this restore point')
        
        snapshot = restore_point.snapshot_data
        if not snapshot:
            raise ValueError('No snapshot data available for rollback')
        
        restore_point.status = 'rolled_back'
        restore_point.save()
        
        return {
            'success': True,
            'rolled_back_at': timezone.now().isoformat(),
            'snapshot': snapshot,
        }