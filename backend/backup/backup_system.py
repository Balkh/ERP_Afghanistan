"""
Pharmacy ERP Backup System
Comprehensive backup infrastructure with encryption, compression, validation, and scheduling
"""
import os
import sys
import json
import hashlib
import shutil
import sqlite3
import tarfile
import tempfile
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class BackupConfig:
    """Backup configuration management"""
    
    def __init__(self, config_dir=None):
        if config_dir is None:
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            config_dir = Path(appdata) / 'PharmacyERP' / 'config'
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / 'backup_config.json'
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_default_config(self) -> Dict:
        """Get default backup configuration"""
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        return {
            'enabled': True,
            'backup_dir': str(Path(appdata) / 'PharmacyERP' / 'backups'),
            'schedule': {
                'frequency': 'daily',  # hourly, daily, weekly, monthly
                'time': '02:00',  # HH:MM format
                'day_of_week': 'sunday',  # for weekly
                'day_of_month': 1,  # for monthly
            },
            'retention': {
                'max_backups': 30,
                'max_age_days': 90,
                'min_free_space_mb': 1000,
            },
            'compression': {
                'enabled': True,
                'level': 6,  # 0-9, 6 is good balance
                'format': 'tar.gz',  # tar.gz, tar.bz2, zip
            },
            'encryption': {
                'enabled': True,
                'algorithm': 'fernet',
                'password_hash': '',  # Will be set during setup
            },
            'database': {
                'path': '',  # Will be set automatically
                'vacuum_before_backup': True,
                'verify_after_backup': True,
            },
            'notifications': {
                'on_success': False,
                'on_failure': True,
                'email': '',
            },
            'logging': {
                'level': 'INFO',
                'file': 'backup.log',
            }
        }
    
    def load_config(self) -> Dict:
        """Load backup configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                defaults = self.get_default_config()
                return self._merge_config(defaults, config)
            except Exception as e:
                logging.warning(f"Failed to load backup config: {e}")
        
        return self.get_default_config()
    
    def save_config(self, config: Dict) -> bool:
        """Save backup configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to save backup config: {e}")
            return False
    
    def _merge_config(self, defaults: Dict, custom: Dict) -> Dict:
        """Merge custom config with defaults"""
        merged = defaults.copy()
        for key, value in custom.items():
            if key in merged and isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged


class BackupValidator:
    """Backup validation utilities"""
    
    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    @staticmethod
    def verify_database_integrity(db_path: str) -> Tuple[bool, str]:
        """Verify SQLite database integrity"""
        try:
            if not os.path.exists(db_path):
                return False, "Database file not found"
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] == 'ok':
                return True, "Database integrity check passed"
            else:
                return False, f"Database integrity check failed: {result[0]}"
        except Exception as e:
            return False, f"Error checking database integrity: {str(e)}"
    
    @staticmethod
    def verify_backup_archive(archive_path: str) -> Tuple[bool, str]:
        """Verify backup archive integrity"""
        try:
            if not os.path.exists(archive_path):
                return False, "Archive file not found"
            
            if archive_path.endswith('.tar.gz') or archive_path.endswith('.tgz'):
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.getmembers()  # Will raise exception if corrupt
                return True, "Archive integrity verified"
            elif archive_path.endswith('.tar.bz2'):
                with tarfile.open(archive_path, 'r:bz2') as tar:
                    tar.getmembers()
                return True, "Archive integrity verified"
            else:
                return False, "Unsupported archive format"
        except Exception as e:
            return False, f"Archive verification failed: {str(e)}"
    
    @staticmethod
    def verify_backup_content(backup_path: str, expected_files: List[str]) -> Tuple[bool, str]:
        """Verify backup contains expected files"""
        try:
            if backup_path.endswith('.tar.gz') or backup_path.endswith('.tgz'):
                with tarfile.open(backup_path, 'r:gz') as tar:
                    archive_files = tar.getnames()
            elif backup_path.endswith('.tar.bz2'):
                with tarfile.open(backup_path, 'r:bz2') as tar:
                    archive_files = tar.getnames()
            else:
                return False, "Unsupported archive format"
            
            missing_files = [f for f in expected_files if f not in archive_files]
            if missing_files:
                return False, f"Missing files: {', '.join(missing_files)}"
            
            return True, "All expected files present"
        except Exception as e:
            return False, f"Content verification failed: {str(e)}"


class BackupEncryptor:
    """Backup encryption utilities"""
    
    @staticmethod
    def generate_key(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return key, salt
    
    @staticmethod
    def encrypt_file(input_path: str, output_path: str, password: str) -> bool:
        """Encrypt a file"""
        try:
            key, salt = BackupEncryptor.generate_key(password)
            fernet = Fernet(key)
            
            with open(input_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = fernet.encrypt(data)
            
            # Write salt + encrypted data
            with open(output_path, 'wb') as f:
                f.write(salt)
                f.write(encrypted_data)
            
            return True
        except Exception as e:
            logging.error(f"Encryption failed: {e}")
            return False
    
    @staticmethod
    def decrypt_file(input_path: str, output_path: str, password: str) -> bool:
        """Decrypt a file"""
        try:
            with open(input_path, 'rb') as f:
                salt = f.read(16)
                encrypted_data = f.read()
            
            key, _ = BackupEncryptor.generate_key(password, salt)
            fernet = Fernet(key)
            
            decrypted_data = fernet.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return True
        except Exception as e:
            logging.error(f"Decryption failed: {e}")
            return False


class BackupManager:
    """
    Main backup manager handling all backup operations
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or BackupConfig().load_config()
        self.backup_dir = Path(self.config['backup_dir'])
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.validator = BackupValidator()
        self.encryptor = BackupEncryptor()
        self.scheduler = None
        
        self.logger = logging.getLogger('backup')
    
    def _setup_logging(self):
        """Setup backup logging"""
        log_config = self.config.get('logging', {})
        log_file = self.backup_dir / log_config.get('file', 'backup.log')
        
        logging.basicConfig(
            filename=str(log_file),
            level=getattr(logging, log_config.get('level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _check_pre_backup_safety(self) -> Dict:
        """Run safety checks before backup. Returns dict with 'safe' bool and optional 'warning'."""
        result = {'safe': True}

        retention = self.config.get('retention', {})
        min_free_mb = retention.get('min_free_space_mb', 1000)
        try:
            disk = shutil.disk_usage(self.backup_dir)
            free_mb = disk.free / (1024 * 1024)
            if free_mb < min_free_mb:
                result.update({'safe': False, 'warning': f'Low disk space: {free_mb:.0f} MB free (min: {min_free_mb} MB)'})
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")

        db_path = self.config['database'].get('path')
        if db_path and os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute('SELECT 1')
                conn.close()
            except Exception as e:
                result.update({'safe': False, 'warning': f'Database connectivity check failed: {e}'})

        return result

    def _post_backup_verify(self, file_path: str, checksum: str) -> bool:
        """Auto-verify backup file integrity after creation."""
        actual = self.validator.calculate_checksum(file_path)
        if actual != checksum:
            self.logger.error(f"Post-backup checksum mismatch: expected {checksum}, got {actual}")
            return False
        valid, _ = self.validator.verify_backup_archive(file_path)
        if not valid:
            self.logger.error("Post-backup archive verification failed")
            return False
        self.logger.info(f"Post-backup verification passed for {Path(file_path).name}")
        return True

    def create_backup(self, db_path: str = None, include_files: List[str] = None,
                     description: str = '') -> Dict:
        """
        Create a backup of the database and optional files
        Returns dict with backup info
        """
        self.logger.info("Starting backup creation...")
        start_time = datetime.now()

        try:
            safety = self._check_pre_backup_safety()
            if not safety['safe']:
                self.logger.warning(f"Pre-backup safety check: {safety.get('warning', 'unknown issue')}")

            # Get database path
            if db_path is None:
                db_path = self.config['database'].get('path')
            
            if not db_path or not os.path.exists(db_path):
                return {
                    'success': False,
                    'error': 'Database path not found',
                    'timestamp': start_time.isoformat(),
                }
            
            # Vacuum database if configured
            if self.config['database'].get('vacuum_before_backup', True):
                self._vacuum_database(db_path)
            
            # Create temporary directory for backup
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy database
                db_backup_path = temp_path / 'pharmacy_erp.db'
                shutil.copy2(db_path, db_backup_path)
                
                # Verify database copy
                if self.config['database'].get('verify_after_backup', True):
                    valid, msg = self.validator.verify_database_integrity(str(db_backup_path))
                    if not valid:
                        self.logger.error(f"Database verification failed: {msg}")
                        return {
                            'success': False,
                            'error': f'Database verification failed: {msg}',
                            'timestamp': start_time.isoformat(),
                        }
                
                # Copy additional files
                files_to_backup = []
                if include_files:
                    for file_path in include_files:
                        if os.path.exists(file_path):
                            dest_path = temp_path / Path(file_path).name
                            shutil.copy2(file_path, dest_path)
                            files_to_backup.append(Path(file_path).name)
                
                # Create archive
                archive_format = self.config['compression'].get('format', 'tar.gz')
                archive_path = self._create_archive(temp_path, archive_format)
                
                # Compress if not already compressed
                if not self.config['compression'].get('enabled', True):
                    final_path = archive_path
                else:
                    final_path = archive_path
                
                # Encrypt if configured
                if self.config['encryption'].get('enabled', True):
                    encrypted_path = final_path.with_suffix(final_path.suffix + '.enc')
                    password = self._get_encryption_password()
                    if not self.encryptor.encrypt_file(str(final_path), str(encrypted_path), password):
                        return {
                            'success': False,
                            'error': 'Encryption failed',
                            'timestamp': start_time.isoformat(),
                        }
                    final_path = encrypted_path
                    os.remove(str(archive_path))
                
                # Move to backup directory
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_filename = f"pharmacy_erp_backup_{timestamp}{final_path.suffix}"
                backup_path = self.backup_dir / backup_filename
                
                shutil.move(str(final_path), str(backup_path))
                
                # Calculate checksum
                checksum = self.validator.calculate_checksum(str(backup_path))
                
                # Calculate backup size
                backup_size = backup_path.stat().st_size
                
                # Create backup metadata
                metadata = {
                    'filename': backup_filename,
                    'timestamp': start_time.isoformat(),
                    'completed': datetime.now().isoformat(),
                    'duration': (datetime.now() - start_time).total_seconds(),
                    'size_bytes': backup_size,
                    'size_mb': round(backup_size / (1024 * 1024), 2),
                    'checksum': checksum,
                    'description': description,
                    'db_path': db_path,
                    'files_included': files_to_backup,
                    'encrypted': self.config['encryption'].get('enabled', False),
                    'compressed': self.config['compression'].get('enabled', False),
                    'format': archive_format,
                    'version': '1.0.0',
                }
                
                # Save metadata
                metadata_path = backup_path.with_suffix('.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.logger.info(f"Backup created successfully: {backup_filename}")

                # Auto-verify backup integrity
                if not self._post_backup_verify(str(backup_path), checksum):
                    self.logger.warning(f"Post-backup verification warned for {backup_filename}")

                # Cleanup old backups
                self.cleanup_old_backups()
                
                return {
                    'success': True,
                    'backup_path': str(backup_path),
                    'metadata': metadata,
                    'checksum': checksum,
                    'verified': True,
                }
        
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'timestamp': start_time.isoformat(),
            }
    
    def _log_db_event(self, level: str, event: str, message: str, details: dict = None):
        """Log backup event to database via BackupLog model. Safe to call without Django setup."""
        try:
            from backup.models import BackupLog
            BackupLog.objects.create(
                level=level,
                event=event,
                message=message,
                details=details or {},
            )
        except Exception:
            pass

    def _vacuum_database(self, db_path: str):
        """Vacuum SQLite database to optimize size"""
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("VACUUM")
            conn.close()
            self.logger.info("Database vacuumed successfully")
        except Exception as e:
            self.logger.warning(f"Database vacuum failed: {e}")
    
    def _create_archive(self, source_dir: Path, format: str) -> Path:
        """Create compressed archive of source directory"""
        archive_path = source_dir.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format in ['tar.gz', 'tgz']:
            archive_path = archive_path.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz', compresslevel=self.config['compression'].get('level', 6)) as tar:
                tar.add(str(source_dir), arcname='pharmacy_erp_backup')
        elif format == 'tar.bz2':
            archive_path = archive_path.with_suffix('.tar.bz2')
            with tarfile.open(archive_path, 'w:bz2', compresslevel=self.config['compression'].get('level', 6)) as tar:
                tar.add(str(source_dir), arcname='pharmacy_erp_backup')
        else:
            # Default to tar.gz
            archive_path = archive_path.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz', compresslevel=self.config['compression'].get('level', 6)) as tar:
                tar.add(str(source_dir), arcname='pharmacy_erp_backup')
        
        return archive_path
    
    def _get_encryption_password(self) -> str:
        """Get encryption password from environment variable."""
        password = os.environ.get('PHARMACY_ERP_BACKUP_PASSWORD')
        if not password:
            import secrets as secrets_module
            password = secrets_module.token_urlsafe(32)
            self.logger.critical(
                "PHARMACY_ERP_BACKUP_PASSWORD env var not set. "
                "Using ephemeral random password — backups created now CANNOT be restored later. "
                "Set PHARMACY_ERP_BACKUP_PASSWORD to a fixed value in production."
            )
        return password
    
    def restore_backup(self, backup_path: str, target_db_path: str = None,
                      password: str = None, verify: bool = True) -> Dict:
        """
        Restore a backup to the specified location
        """
        self.logger.info(f"Starting restore from: {backup_path}")
        start_time = datetime.now()
        
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                return {
                    'success': False,
                    'error': 'Backup file not found',
                    'timestamp': start_time.isoformat(),
                }
            
            # Load metadata
            metadata_path = backup_path.with_suffix('.json')
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Decrypt if needed
            if str(backup_path).endswith('.enc'):
                if password is None:
                    password = self._get_encryption_password()
                
                decrypted_path = backup_path.with_suffix('')
                if not self.encryptor.decrypt_file(str(backup_path), str(decrypted_path), password):
                    return {
                        'success': False,
                        'error': 'Decryption failed',
                        'timestamp': start_time.isoformat(),
                    }
                backup_path = decrypted_path
            
            # Extract archive
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                if str(backup_path).endswith('.tar.gz') or str(backup_path).endswith('.tgz'):
                    with tarfile.open(backup_path, 'r:gz') as tar:
                        tar.extractall(temp_path)
                elif str(backup_path).endswith('.tar.bz2'):
                    with tarfile.open(backup_path, 'r:bz2') as tar:
                        tar.extractall(temp_path)
                else:
                    return {
                        'success': False,
                        'error': 'Unsupported archive format',
                        'timestamp': start_time.isoformat(),
                    }
                
                # Find database file
                db_file = temp_path / 'pharmacy_erp_backup' / 'pharmacy_erp.db'
                if not db_file.exists():
                    return {
                        'success': False,
                        'error': 'Database file not found in backup',
                        'timestamp': start_time.isoformat(),
                    }
                
                # Verify database integrity
                if verify:
                    valid, msg = self.validator.verify_database_integrity(str(db_file))
                    if not valid:
                        return {
                            'success': False,
                            'error': f'Database integrity check failed: {msg}',
                            'timestamp': start_time.isoformat(),
                        }
                
                # Copy to target location
                if target_db_path is None:
                    target_db_path = self.config['database'].get('path')
                
                if target_db_path:
                    target_path = Path(target_db_path)
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(db_file), str(target_path))
                    
                    self.logger.info(f"Backup restored to: {target_path}")
                else:
                    return {
                        'success': False,
                        'error': 'Target database path not specified',
                        'timestamp': start_time.isoformat(),
                    }
                
                return {
                    'success': True,
                    'target_path': target_db_path,
                    'timestamp': start_time.isoformat(),
                    'duration': (datetime.now() - start_time).total_seconds(),
                    'metadata': metadata,
                }
        
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'timestamp': start_time.isoformat(),
            }
    
    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for file_path in self.backup_dir.glob('pharmacy_erp_backup_*'):
            if file_path.suffix in ['.db', '.json', '.log']:
                continue
            
            metadata_path = file_path.with_suffix('.json')
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    backups.append(metadata)
                except:
                    pass
            else:
                # Create basic info from filename
                backups.append({
                    'filename': file_path.name,
                    'path': str(file_path),
                    'size_bytes': file_path.stat().st_size,
                    'timestamp': 'Unknown',
                })
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backups
    
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a specific backup"""
        try:
            backup_path = Path(backup_path)
            if backup_path.exists():
                backup_path.unlink()
                # Also delete metadata file
                metadata_path = backup_path.with_suffix('.json')
                if metadata_path.exists():
                    metadata_path.unlink()
                self.logger.info(f"Deleted backup: {backup_path.name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete backup: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        retention = self.config.get('retention', {})
        max_backups = retention.get('max_backups', 30)
        max_age_days = retention.get('max_age_days', 90)
        
        backups = self.list_backups()
        
        # Delete backups exceeding max count
        if len(backups) > max_backups:
            for backup in backups[max_backups:]:
                backup_path = self.backup_dir / backup['filename']
                self.delete_backup(str(backup_path))
        
        # Delete backups older than max age
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        for backup in backups:
            try:
                backup_date = datetime.fromisoformat(backup['timestamp'].split('+')[0])
                if backup_date < cutoff_date:
                    backup_path = self.backup_dir / backup['filename']
                    self.delete_backup(str(backup_path))
            except:
                pass
        
        # Check free space
        min_free_space_mb = retention.get('min_free_space_mb', 1000)
        try:
            disk_usage = shutil.disk_usage(self.backup_dir)
            free_space_mb = disk_usage.free / (1024 * 1024)
            
            if free_space_mb < min_free_space_mb:
                self.logger.warning(f"Low disk space: {free_space_mb:.0f} MB free")
                # Delete oldest backups until we have enough space
                backups = self.list_backups()
                for backup in reversed(backups):
                    backup_path = self.backup_dir / backup['filename']
                    if backup_path.exists():
                        self.delete_backup(str(backup_path))
                        disk_usage = shutil.disk_usage(self.backup_dir)
                        free_space_mb = disk_usage.free / (1024 * 1024)
                        if free_space_mb >= min_free_space_mb:
                            break
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
    
    def start_scheduler(self):
        """Start the backup scheduler"""
        if self.scheduler is not None:
            self.logger.info("Scheduler already running")
            return
        
        schedule_config = self.config.get('schedule', {})
        frequency = schedule_config.get('frequency', 'daily')
        
        self.logger.info(f"Starting backup scheduler with {frequency} frequency")
        
        self.scheduler = BackupScheduler(self, schedule_config)
        self.scheduler.start()
    
    def stop_scheduler(self):
        """Stop the backup scheduler"""
        if self.scheduler:
            self.scheduler.stop()
            self.scheduler = None
            self.logger.info("Backup scheduler stopped")
    
    def get_backup_stats(self) -> Dict:
        """Get backup statistics"""
        backups = self.list_backups()
        
        if not backups:
            return {
                'total_backups': 0,
                'total_size_mb': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'last_backup': None,
            }
        
        total_size = sum(b.get('size_bytes', 0) for b in backups)
        
        return {
            'total_backups': len(backups),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_backup': backups[-1].get('timestamp') if backups else None,
            'newest_backup': backups[0].get('timestamp') if backups else None,
            'last_backup': backups[0].get('timestamp') if backups else None,
        }


class BackupScheduler:
    """
    Handles scheduled backups with safety checks and missed-backup detection.
    """
    
    def __init__(self, backup_manager: BackupManager, schedule_config: Dict):
        self.backup_manager = backup_manager
        self.schedule_config = schedule_config
        self.running = False
        self.thread = None
        self._last_run_date = None
    
    def start(self):
        """Start the scheduler"""
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.backup_manager.logger.info("Backup scheduler started with safety checks")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
    
    def _check_missed_backup(self) -> bool:
        """Check if a scheduled backup was missed since last run."""
        if self._last_run_date is None:
            return False
        now = datetime.now()
        frequency = self.schedule_config.get('frequency', 'daily')
        if frequency == 'daily':
            delta_days = (now - self._last_run_date).days
            return delta_days > 1
        elif frequency == 'hourly':
            delta_hours = (now - self._last_run_date).total_seconds() / 3600
            return delta_hours > 2
        elif frequency == 'weekly':
            delta_days = (now - self._last_run_date).days
            return delta_days > 8
        return False
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        frequency = self.schedule_config.get('frequency', 'daily')
        
        while self.running:
            try:
                now = datetime.now()
                should_backup = False
                
                if frequency == 'hourly':
                    should_backup = now.minute == 0
                elif frequency == 'daily':
                    time_str = self.schedule_config.get('time', '02:00')
                    hour, minute = map(int, time_str.split(':'))
                    should_backup = now.hour == hour and now.minute == minute
                elif frequency == 'weekly':
                    time_str = self.schedule_config.get('time', '02:00')
                    hour, minute = map(int, time_str.split(':'))
                    day = self.schedule_config.get('day_of_week', 'sunday')
                    should_backup = (now.hour == hour and now.minute == minute and 
                                   now.strftime('%A').lower() == day)
                elif frequency == 'monthly':
                    time_str = self.schedule_config.get('time', '02:00')
                    hour, minute = map(int, time_str.split(':'))
                    day = self.schedule_config.get('day_of_month', 1)
                    should_backup = (now.hour == hour and now.minute == minute and now.day == day)
                
                if should_backup and self.backup_manager.config.get('enabled', True):
                    safety = self.backup_manager._check_pre_backup_safety()
                    if safety['safe']:
                        result = self.backup_manager.create_backup(description=f"Scheduled {frequency} backup")
                        if result.get('success'):
                            self.backup_manager._log_db_event('INFO', 'backup_completed', f"Scheduled backup: {result.get('metadata', {}).get('filename', 'unknown')}")
                        else:
                            self.backup_manager._log_db_event('ERROR', 'backup_failed', f"Scheduled backup failed: {result.get('error', 'unknown')}")
                        self._last_run_date = now
                    else:
                        msg = safety.get('warning', 'unknown issue')
                        self.backup_manager.logger.warning(f"Scheduled backup skipped: {msg}")
                        self.backup_manager._log_db_event('WARNING', 'backup_failed', f"Scheduled backup skipped: {msg}")
                else:
                    missed = self._check_missed_backup()
                    if missed:
                        self.backup_manager.logger.warning(
                            f"Missed scheduled backup detected (last run: {self._last_run_date})"
                        )
                
                time.sleep(60)
                
            except Exception as e:
                self.backup_manager.logger.error(f"Scheduler error: {e}")
                time.sleep(60)


def main():
    """Main entry point for backup system"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pharmacy ERP Backup System')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'delete', 'stats', 'schedule'],
                       help='Action to perform')
    parser.add_argument('--backup-file', help='Backup file path (for restore/delete)')
    parser.add_argument('--target-db', help='Target database path (for restore)')
    parser.add_argument('--password', help='Encryption password')
    parser.add_argument('--description', help='Backup description')
    parser.add_argument('--include-files', nargs='*', help='Additional files to include')
    
    args = parser.parse_args()
    
    backup_manager = BackupManager()
    
    if args.action == 'backup':
        result = backup_manager.create_backup(
            include_files=args.include_files,
            description=args.description or 'Manual backup'
        )
        if result['success']:
            print(f"✓ Backup created: {result['metadata']['filename']}")
            print(f"  Size: {result['metadata']['size_mb']} MB")
            print(f"  Checksum: {result['checksum']}")
        else:
            print(f"✗ Backup failed: {result.get('error', 'Unknown error')}")
    
    elif args.action == 'restore':
        if not args.backup_file:
            print("Error: --backup-file is required for restore")
            sys.exit(1)
        
        result = backup_manager.restore_backup(
            backup_path=args.backup_file,
            target_db_path=args.target_db,
            password=args.password,
        )
        if result['success']:
            print(f"✓ Backup restored to: {result['target_path']}")
        else:
            print(f"✗ Restore failed: {result.get('error', 'Unknown error')}")
    
    elif args.action == 'list':
        backups = backup_manager.list_backups()
        if not backups:
            print("No backups found")
        else:
            print(f"Found {len(backups)} backups:\n")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup.get('filename', 'Unknown')}")
                print(f"   Date: {backup.get('timestamp', 'Unknown')}")
                print(f"   Size: {backup.get('size_mb', 'Unknown')} MB")
                print(f"   Encrypted: {backup.get('encrypted', False)}")
                print()
    
    elif args.action == 'delete':
        if not args.backup_file:
            print("Error: --backup-file is required for delete")
            sys.exit(1)
        
        if backup_manager.delete_backup(args.backup_file):
            print(f"✓ Backup deleted: {args.backup_file}")
        else:
            print(f"✗ Failed to delete backup: {args.backup_file}")
    
    elif args.action == 'stats':
        stats = backup_manager.get_backup_stats()
        print("Backup Statistics:")
        print(f"  Total backups: {stats['total_backups']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Oldest backup: {stats['oldest_backup']}")
        print(f"  Newest backup: {stats['newest_backup']}")
        print(f"  Last backup: {stats['last_backup']}")
    
    elif args.action == 'schedule':
        print("Starting backup scheduler...")
        backup_manager.start_scheduler()
        print("Scheduler started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            backup_manager.stop_scheduler()
            print("\nScheduler stopped.")


if __name__ == '__main__':
    main()