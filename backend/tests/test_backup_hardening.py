"""
Tests for hardened backup/restore services.

Tests cover:
- Unified restore core (RestoreService delegates to BackupManager)
- Restore lock/mutex
- Encryption safety (no password = no encrypted backup)
- Offsite replication
- Health monitoring
- PostgreSQL provider abstraction
- Emergency backup and rollback
"""
import os
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase, override_settings
from django.utils import timezone

from backup.models import BackupRecord, RestorePoint, RestoreValidation
from backup.services.restore_service import RestoreService
from backup.services.restore_lock import RestoreLock, SafeRestoreExecutor
from backup.services.health_monitor import BackupHealthMonitor
from backup.services.offsite_replication import OffsiteReplicator, RetryQueue
from backup.services.db_providers import (
    DatabaseEngineDetector,
    SQLiteBackupProvider,
    SQLiteRestoreProvider,
)


class UnifiedRestoreCoreTests(TestCase):
    """Tests for unified restore orchestration."""

    def setUp(self):
        self.backup_record = BackupRecord.objects.create(
            backup_type='manual',
            status='completed',
            filename='test_backup.tar.gz',
            file_path='/tmp/test_backup.tar.gz',
            file_size_bytes=1024000,
            checksum='abc123',
        )
        self.restore_point = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='validated',
            is_valid=True,
        )

    def test_restore_service_has_backup_manager(self):
        """RestoreService should have a BackupManager instance."""
        from backup.backup_system import BackupManager
        service = RestoreService(self.backup_record)
        self.assertIsNotNone(service._backup_manager)
        self.assertIsInstance(service._backup_manager, BackupManager)

    def test_restore_service_accepts_custom_backup_manager(self):
        """RestoreService should accept custom BackupManager for testing."""
        mock_bm = MagicMock()
        service = RestoreService(self.backup_record, backup_manager=mock_bm)
        self.assertEqual(service._backup_manager, mock_bm)

    def test_restore_requires_validated_point(self):
        """Restore should fail without a validated restore point."""
        from backup.services.providers import MockFileProvider
        from unittest.mock import MagicMock
        
        file_provider = MockFileProvider()
        file_provider.add_file('/tmp/test_backup.tar.gz', exists=True, size=100)

        mock_bm = MagicMock()
        mock_bm.config = {'database': {'path': ''}}
        
        service = RestoreService(self.backup_record, file_provider=file_provider, backup_manager=mock_bm)
        unvalidated_rp = RestorePoint.objects.create(
            backup_record=self.backup_record,
            status='pending',
            is_valid=False,
        )

        with self.assertRaises(ValueError) as ctx:
            service.restore(restore_point=unvalidated_rp)
        self.assertIn('No validated restore point', str(ctx.exception))

    def test_restore_requires_file_exists(self):
        """Restore should fail if backup file doesn't exist."""
        from backup.services.providers import MockFileProvider
        file_provider = MockFileProvider()
        file_provider.add_file('/tmp/test_backup.tar.gz', exists=False)

        service = RestoreService(self.backup_record, file_provider=file_provider)
        with self.assertRaises(ValueError) as ctx:
            service.restore(restore_point=self.restore_point)
        self.assertIn('not found', str(ctx.exception))


class RestoreLockTests(TestCase):
    """Tests for restore mutex/lock."""

    def test_lock_acquire_and_release(self):
        """Lock should be acquired and released."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = RestoreLock(tmpdir)
            self.assertFalse(lock.is_locked)
            
            acquired = lock.acquire(timeout=5)
            self.assertTrue(acquired)
            self.assertTrue(lock.is_locked)
            
            lock.release()
            self.assertFalse(lock.is_locked)

    def test_lock_prevents_concurrent_acquire(self):
        """Second lock acquire should fail while first is held."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock1 = RestoreLock(tmpdir)
            lock2 = RestoreLock(tmpdir)
            
            self.assertTrue(lock1.acquire(timeout=5))
            
            # Second lock should fail with short timeout
            acquired = lock2.acquire(timeout=1)
            self.assertFalse(acquired)
            
            lock1.release()

    def test_stale_lock_detection(self):
        """Stale lock (dead PID) should be detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = RestoreLock(tmpdir)
            lock.acquire(timeout=5)
            
            # Simulate stale lock by writing a non-existent PID
            lock_file = lock.lock_file
            with open(lock_file, 'w') as f:
                f.write('999999999')  # Non-existent PID
            
            self.assertTrue(lock._is_stale())
            lock.release()


class EncryptionSafetyTests(TestCase):
    """Tests for encryption password safety."""

    def test_no_password_raises_error(self):
        """_get_encryption_password should raise ValueError if env var not set."""
        from backup.backup_system import BackupManager
        
        with patch.dict(os.environ, {'PHARMACY_ERP_BACKUP_PASSWORD': ''}, clear=False):
            if 'PHARMACY_ERP_BACKUP_PASSWORD' in os.environ:
                del os.environ['PHARMACY_ERP_BACKUP_PASSWORD']
            
            bm = BackupManager()
            with self.assertRaises(ValueError) as ctx:
                bm._get_encryption_password()
            self.assertIn('PHARMACY_ERP_BACKUP_PASSWORD', str(ctx.exception))

    def test_password_from_env_var(self):
        """_get_encryption_password should return env var value."""
        from backup.backup_system import BackupManager
        
        with patch.dict(os.environ, {'PHARMACY_ERP_BACKUP_PASSWORD': 'test-password-123'}):
            bm = BackupManager()
            password = bm._get_encryption_password()
            self.assertEqual(password, 'test-password-123')

    def test_is_encryption_configured(self):
        """_is_encryption_configured should return True only when env var is set."""
        from backup.backup_system import BackupManager
        
        with patch.dict(os.environ, {}, clear=False):
            if 'PHARMACY_ERP_BACKUP_PASSWORD' in os.environ:
                del os.environ['PHARMACY_ERP_BACKUP_PASSWORD']
            
            bm = BackupManager()
            self.assertFalse(bm._is_encryption_configured())
        
        with patch.dict(os.environ, {'PHARMACY_ERP_BACKUP_PASSWORD': 'test'}):
            bm = BackupManager()
            self.assertTrue(bm._is_encryption_configured())


class HealthMonitorTests(TestCase):
    """Tests for backup health monitoring."""

    def test_health_check_returns_status(self):
        """Health check should return status dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = BackupHealthMonitor(backup_dir=tmpdir)
            health = monitor.check_health()
            
            self.assertIn('status', health)
            self.assertIn('warnings', health)
            self.assertIn('errors', health)
            self.assertIn('checks_run', health)
            self.assertGreater(len(health['checks_run']), 0)

    def test_startup_warning_no_backups(self):
        """Should warn if no backups exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = BackupHealthMonitor(backup_dir=tmpdir)
            warning = monitor.get_startup_warning()
            self.assertIsNotNone(warning)
            self.assertIn('No backups found', warning)

    def test_dry_run_validate_missing_file(self):
        """Dry run should fail for non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = BackupHealthMonitor(backup_dir=tmpdir)
            result = monitor.dry_run_validate('/nonexistent/backup.tar.gz')
            
            self.assertFalse(result['valid'])
            self.assertTrue(len(result['errors']) > 0)

    def test_revalidate_checksums_empty_dir(self):
        """Revalidate should handle empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = BackupHealthMonitor(backup_dir=tmpdir)
            result = monitor.revalidate_all_checksums()
            
            self.assertEqual(result['total'], 0)
            self.assertEqual(result['valid'], 0)
            self.assertEqual(result['invalid'], 0)


class OffsiteReplicationTests(TestCase):
    """Tests for offsite replication."""

    def test_offline_queues_backup(self):
        """Offline scenario should queue backup for retry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retry_dir = os.path.join(tmpdir, 'retry')
            os.makedirs(retry_dir, exist_ok=True)
            config = {
                'enabled': True,
                'smtp_host': 'smtp.test.com',
                'smtp_port': 587,
                'from_email': 'test@test.com',
                'recipients': ['admin@test.com'],
                'retry_dir': retry_dir,
            }
            replicator = OffsiteReplicator(config)
            
            # Create a temp backup file
            backup_file = os.path.join(tmpdir, 'test_backup.sql')
            with open(backup_file, 'w') as f:
                f.write('-- test backup')
            
            # Force offline
            with patch.object(replicator, 'is_online', return_value=False):
                result = replicator.send_backup(backup_file)
                
                self.assertFalse(result['success'])
                self.assertTrue(result.get('queued', False))

    def test_retry_queue_enqueue_and_get(self):
        """Retry queue should store and retrieve pending entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            retry_dir = Path(tmpdir) / 'retry'
            retry_dir.mkdir(parents=True, exist_ok=True)
            queue = RetryQueue(retry_dir)
            queue.enqueue('/tmp/test.sql', ['admin@test.com'], {'description': 'test'})
            
            pending = queue.get_pending()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]['recipients'], ['admin@test.com'])

    def test_disabled_replication(self):
        """Disabled replication should return error."""
        config = {'enabled': False}
        replicator = OffsiteReplicator(config)
        result = replicator.send_backup('/tmp/test.sql')
        
        self.assertFalse(result['success'])
        self.assertIn('disabled', result['error'].lower())

    def test_no_recipients_error(self):
        """No recipients should return error."""
        config = {'enabled': True, 'recipients': []}
        replicator = OffsiteReplicator(config)
        result = replicator.send_backup('/tmp/test.sql')
        
        self.assertFalse(result['success'])
        self.assertIn('recipients', result['error'].lower())


class DatabaseProviderTests(TestCase):
    """Tests for database provider abstraction."""

    def test_detect_sqlite_engine(self):
        """Should detect SQLite engine."""
        engine = DatabaseEngineDetector.detect()
        self.assertEqual(engine, 'sqlite')

    def test_get_sqlite_db_path(self):
        """Should return SQLite db path."""
        db_path = DatabaseEngineDetector.get_db_path()
        self.assertIsNotNone(db_path)

    def test_get_pg_config_returns_none_for_sqlite(self):
        """Should return None for non-PostgreSQL."""
        pg_config = DatabaseEngineDetector.get_pg_config()
        self.assertIsNone(pg_config)

    def test_sqlite_backup_provider(self):
        """SQLite backup provider should handle missing db gracefully."""
        provider = SQLiteBackupProvider(db_path='/nonexistent/db.sqlite3')
        result = provider.create_backup(tempfile.mkdtemp())
        
        self.assertFalse(result['success'])

    def test_sqlite_restore_provider(self):
        """SQLite restore provider should handle missing db gracefully."""
        provider = SQLiteRestoreProvider(db_path='/nonexistent/db.sqlite3')
        result = provider.restore_backup('/nonexistent/backup.sql')
        
        self.assertFalse(result['success'])


class EmergencyBackupTests(TestCase):
    """Tests for emergency backup and rollback."""

    def test_create_emergency_backup_no_db(self):
        """Should return None if no database path configured."""
        from backup.services.providers import MockFileProvider
        
        backup_record = BackupRecord.objects.create(
            backup_type='manual',
            status='completed',
            filename='test.sql',
            file_path='/tmp/test.sql',
        )
        
        mock_bm = MagicMock()
        mock_bm.config = {'database': {'path': ''}}
        
        service = RestoreService(backup_record, backup_manager=mock_bm)
        result = service._create_emergency_backup()
        self.assertIsNone(result)

    def test_rollback_to_missing_backup(self):
        """Should fail if emergency backup doesn't exist."""
        from backup.services.providers import MockFileProvider
        
        backup_record = BackupRecord.objects.create(
            backup_type='manual',
            status='completed',
            filename='test.sql',
            file_path='/tmp/test.sql',
        )
        
        mock_bm = MagicMock()
        mock_bm.config = {'database': {'path': '/tmp/test_target.db'}}
        
        service = RestoreService(backup_record, backup_manager=mock_bm)
        result = service._rollback_to_emergency_backup(
            '/nonexistent/emergency.db',
            '/tmp/test_target.db'
        )
        self.assertFalse(result)
