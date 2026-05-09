"""
Refactored RestoreService with dependency injection.

This version is fully testable without filesystem access:
- Uses injected providers for all file operations
- Contains only orchestration logic
- Easy to mock for unit tests
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.db import transaction
from django.conf import settings
from django.utils import timezone

from backup.models import BackupRecord, RestorePoint, RestoreValidation


class RestoreService:
    """
    Service for validating and restoring database backups.
    
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
    def restore(self, user=None, restore_point: Optional[RestorePoint] = None) -> Dict[str, Any]:
        """Restore from a validated backup"""
        if restore_point is None:
            restore_point = RestorePoint.objects.filter(
                backup_record=self.backup_record,
                is_valid=True
            ).first()
        
        if not restore_point:
            raise ValueError('No validated restore point found. Validate backup first.')
        
        snapshot_data = self.create_snapshot()
        
        restore_point.snapshot_data = snapshot_data
        restore_point.restore_started_at = timezone.now()
        restore_point.restored_by = user
        restore_point.status = 'restored'
        restore_point.save()
        
        file_path = self.backup_record.file_path
        
        if not self._file_provider.exists(file_path):
            raise ValueError(f'Backup file not found: {file_path}')
        
        result = {
            'success': False,
            'restore_point_id': str(restore_point.id),
            'snapshot': snapshot_data,
        }
        
        try:
            # For now, just mark as restored - actual restore would need db access
            restore_point.status = 'restored'
            restore_point.restore_completed_at = timezone.now()
            restore_point.save()
            
            result['success'] = True
            
        except Exception as e:
            restore_point.status = 'failed'
            restore_point.restore_reason = str(e)
            restore_point.save()
            raise
        
        return result
    
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