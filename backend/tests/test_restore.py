import os
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from backup.models import BackupRecord, RestorePoint, RestoreValidation
from backup.services.restore_service import RestoreService


User = get_user_model()


class RestoreServiceTestCase(TestCase):
    """Test cases for RestoreService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.backup_record = BackupRecord.objects.create(
            backup_type='manual',
            status='completed',
            filename='backup_20240101.sql',
            file_path='/tmp/test_backup.sql',
            file_size_bytes=1024000,
            checksum='abc123def456',
            created_by=self.user,
        )
    
    def test_restore_point_creation(self):
        """Test restore point is created on validation"""
        restore_service = RestoreService(self.backup_record)
        
        with patch.object(restore_service, '_validate_file_exists'):
            pass
        
        restore_point = restore_service.validate_backup(user=self.user)
        
        self.assertIsNotNone(restore_point.id)
        self.assertEqual(restore_point.backup_record, self.backup_record)
        self.assertEqual(restore_point.status, 'validated')
    
    def test_validation_with_missing_file(self):
        """Test validation fails when file doesn't exist"""
        self.backup_record.file_path = '/nonexistent/file.sql'
        self.backup_record.save()
        
        restore_service = RestoreService(self.backup_record)
        restore_point = restore_service.validate_backup(user=self.user)
        
        self.assertFalse(restore_point.is_valid)
        self.assertTrue(len(restore_point.validation_errors) > 0)
        
        error_types = [e['type'] for e in restore_point.validation_errors]
        self.assertIn('file_exists', error_types)
    
    def test_validation_checksum_match(self):
        """Test validation passes when checksum matches"""
        test_content = b'test content for checksum'
        
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', MagicMock()), \
             patch('os.path.getsize', return_value=1024), \
             patch('hashlib.sha256', return_value=MagicMock(hexdigest=lambda: self.backup_record.checksum)):
            
            restore_service = RestoreService(self.backup_record)
            restore_point = restore_service.validate_backup(user=self.user)
            
            restores = RestoreValidation.objects.filter(
                restore_point=restore_point,
                validation_type='data_integrity'
            )
            self.assertTrue(restores.exists())
    
    def test_create_snapshot(self):
        """Test snapshot creation captures current state"""
        from accounting.models import Account
        
        Account.objects.create(
            code='1000',
            name='Test Account',
            account_type='ASSET',
            balance=Decimal('1000.00'),
        )
        
        restore_service = RestoreService(self.backup_record)
        snapshot = restore_service.create_snapshot()
        
        self.assertIn('created_at', snapshot)
        self.assertIn('record_counts', snapshot)
        self.assertIn('accounting_account', snapshot['record_counts'])
    
    def test_rollback_not_allowed(self):
        """Test rollback fails when not allowed"""
        restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='restored',
            can_rollback=False,
        )
        
        restore_service = RestoreService(self.backup_record)
        
        with self.assertRaises(ValueError) as ctx:
            restore_service.rollback(restore_point, user=self.user)
        
        self.assertIn('not allowed', str(ctx.exception))
    
    def test_rollback_with_snapshot(self):
        """Test rollback with valid snapshot"""
        restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='restored',
            can_rollback=True,
            snapshot_data={'test': 'data'},
        )
        
        restore_service = RestoreService(self.backup_record)
        result = restore_service.rollback(restore_point, user=self.user)
        
        self.assertTrue(result['success'])
        refresh_rp = RestorePoint.objects.get(id=restore_point.id)
        self.assertEqual(refresh_rp.status, 'rolled_back')


class RestorePointModelTestCase(TestCase):
    """Test cases for RestorePoint model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2',
            password='testpass123'
        )
        
        self.backup_record = BackupRecord.objects.create(
            backup_type='manual',
            status='completed',
            filename='backup_test.sql',
            file_path='/tmp/test.sql',
            file_size_bytes=1024,
            created_by=self.user,
        )
    
    def test_restore_point_str(self):
        """Test restore point string representation"""
        restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='pending',
        )
        
        self.assertIn(self.backup_record.filename, str(restore_point))
        self.assertIn('pending', str(restore_point))
    
    def test_default_values(self):
        """Test restore point default values"""
        restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
        )
        
        self.assertTrue(restore_point.can_rollback)
        self.assertFalse(restore_point.is_valid)
        self.assertEqual(restore_point.status, 'pending')


class RestoreValidationModelTestCase(TestCase):
    """Test cases for RestoreValidation model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser3',
            password='testpass123'
        )
        
        self.backup_record = BackupRecord.objects.create(
            backup_type='manual',
            status='completed',
            filename='backup_test2.sql',
            file_path='/tmp/test2.sql',
            file_size_bytes=1024,
            created_by=self.user,
        )
        
        self.restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='validated',
            is_valid=True,
        )
    
    def test_validation_str(self):
        """Test validation string representation"""
        validation = RestoreValidation.objects.create(
            restore_point=self.restore_point,
            validation_type='schema',
            is_valid=True,
        )
        
        self.assertIn('schema', str(validation))
        self.assertIn('PASS', str(validation))
    
    def test_validation_fail_str(self):
        """Test failed validation string representation"""
        validation = RestoreValidation.objects.create(
            restore_point=self.restore_point,
            validation_type='schema',
            is_valid=False,
            error_message='Test error',
        )
        
        self.assertIn('FAIL', str(validation))