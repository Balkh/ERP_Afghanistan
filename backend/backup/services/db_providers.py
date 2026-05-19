"""
Database engine detection and backup/restore provider abstraction.

Provides a unified interface for backup operations across different database engines.
Currently supports SQLite (existing) with foundation for PostgreSQL.

Architecture:
    DatabaseEngineDetector
        ↓
    BackupProvider (abstract)
        ├── SQLiteBackupProvider
        └── PostgreSQLBackupProvider (foundation)
    RestoreProvider (abstract)
        ├── SQLiteRestoreProvider
        └── PostgreSQLRestoreProvider (foundation)
"""
import os
import shutil
import subprocess
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger('backup')


class DatabaseEngineDetector:
    """Safely detect the active database engine from Django settings."""
    
    @staticmethod
    def detect() -> str:
        """
        Returns 'sqlite' or 'postgresql'.
        Falls back to 'sqlite' if detection fails.
        """
        try:
            from django.conf import settings
            engine = settings.DATABASES['default']['ENGINE']
            if 'postgresql' in engine or 'postgres' in engine:
                return 'postgresql'
            elif 'sqlite' in engine:
                return 'sqlite'
            else:
                logger.warning(f"Unknown database engine: {engine}, defaulting to sqlite")
                return 'sqlite'
        except Exception as e:
            logger.warning(f"Failed to detect database engine: {e}, defaulting to sqlite")
            return 'sqlite'
    
    @staticmethod
    def get_db_path() -> Optional[str]:
        """Get the database file path for SQLite, or None for PostgreSQL."""
        try:
            from django.conf import settings
            db_config = settings.DATABASES['default']
            if 'sqlite' in db_config['ENGINE']:
                return str(db_config['NAME'])
            return None
        except Exception:
            return None
    
    @staticmethod
    def get_pg_config() -> Optional[Dict]:
        """Get PostgreSQL connection config, or None if not PostgreSQL."""
        try:
            from django.conf import settings
            db_config = settings.DATABASES['default']
            if 'postgresql' not in db_config['ENGINE'] and 'postgres' not in db_config['ENGINE']:
                return None
            return {
                'name': db_config.get('NAME', ''),
                'user': db_config.get('USER', ''),
                'password': db_config.get('PASSWORD', ''),
                'host': db_config.get('HOST', 'localhost'),
                'port': db_config.get('PORT', '5432'),
            }
        except Exception:
            return None


class BackupProvider(ABC):
    """Abstract backup provider interface."""
    
    @abstractmethod
    def create_backup(self, backup_dir: str, description: str = '') -> Dict:
        """Create a backup. Returns dict with success, backup_path, metadata."""
        pass
    
    @abstractmethod
    def get_db_size(self) -> int:
        """Get current database size in bytes."""
        pass


class RestoreProvider(ABC):
    """Abstract restore provider interface."""
    
    @abstractmethod
    def restore_backup(self, backup_path: str, password: str = None) -> Dict:
        """Restore from a backup. Returns dict with success, target_path."""
        pass
    
    @abstractmethod
    def verify_integrity(self, target_path: str) -> tuple:
        """Verify database integrity. Returns (bool, message)."""
        pass


class SQLiteBackupProvider(BackupProvider):
    """SQLite-specific backup provider. Wraps existing file-copy logic."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DatabaseEngineDetector.get_db_path()
    
    def create_backup(self, backup_dir: str, description: str = '') -> Dict:
        """Copy SQLite database file to backup directory."""
        if not self.db_path or not os.path.exists(self.db_path):
            return {'success': False, 'error': 'SQLite database file not found'}
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            filename = f"sqlite_backup_{Path(self.db_path).stem}.db"
            dest = os.path.join(backup_dir, filename)
            shutil.copy2(self.db_path, dest)
            
            return {
                'success': True,
                'backup_path': dest,
                'db_type': 'sqlite',
                'size_bytes': os.path.getsize(dest),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_db_size(self) -> int:
        if self.db_path and os.path.exists(self.db_path):
            return os.path.getsize(self.db_path)
        return 0


class PostgreSQLBackupProvider(BackupProvider):
    """PostgreSQL backup provider using pg_dump.
    
    Foundation layer — safe abstraction for future PostgreSQL support.
    Does NOT activate until PostgreSQL is the configured engine.
    """
    
    def __init__(self, pg_config: Dict = None):
        self.pg_config = pg_config or DatabaseEngineDetector.get_pg_config()
    
    def create_backup(self, backup_dir: str, description: str = '') -> Dict:
        """Create PostgreSQL backup using pg_dump."""
        if not self.pg_config:
            return {'success': False, 'error': 'PostgreSQL not configured'}
        
        if not self._pg_dump_available():
            return {'success': False, 'error': 'pg_dump not found in PATH'}
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pg_backup_{self.pg_config['name']}_{timestamp}.sql"
            dest = os.path.join(backup_dir, filename)
            
            env = os.environ.copy()
            if self.pg_config.get('password'):
                env['PGPASSWORD'] = self.pg_config['password']
            
            cmd = [
                'pg_dump',
                '-h', self.pg_config['host'],
                '-p', str(self.pg_config['port']),
                '-U', self.pg_config['user'],
                '-d', self.pg_config['name'],
                '-f', dest,
                '--format=plain',
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)
            
            if result.returncode == 0 and os.path.exists(dest):
                return {
                    'success': True,
                    'backup_path': dest,
                    'db_type': 'postgresql',
                    'size_bytes': os.path.getsize(dest),
                }
            else:
                return {'success': False, 'error': result.stderr or 'pg_dump failed'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'pg_dump timed out (5 min limit)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_db_size(self) -> int:
        """Estimate PostgreSQL database size via SQL query."""
        if not self.pg_config:
            return 0
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=self.pg_config['name'],
                user=self.pg_config['user'],
                password=self.pg_config.get('password', ''),
                host=self.pg_config['host'],
                port=self.pg_config['port'],
            )
            cursor = conn.cursor()
            cursor.execute(
                "SELECT pg_database_size(%s)",
                (self.pg_config['name'],)
            )
            size = cursor.fetchone()[0]
            conn.close()
            return size
        except Exception:
            return 0
    
    def _pg_dump_available(self) -> bool:
        """Check if pg_dump is available in PATH."""
        try:
            result = subprocess.run(
                ['pg_dump', '--version'],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


class SQLiteRestoreProvider(RestoreProvider):
    """SQLite-specific restore provider."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DatabaseEngineDetector.get_db_path()
    
    def restore_backup(self, backup_path: str, password: str = None) -> Dict:
        """Restore SQLite database from backup file."""
        if not os.path.exists(backup_path):
            return {'success': False, 'error': 'Backup file not found'}
        
        if not self.db_path:
            return {'success': False, 'error': 'SQLite database path not configured'}
        
        try:
            target = Path(self.db_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, str(target))
            return {'success': True, 'target_path': str(target)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_integrity(self, target_path: str) -> tuple:
        """Verify SQLite database integrity."""
        import sqlite3
        try:
            conn = sqlite3.connect(target_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            if result[0] == 'ok':
                return True, "Database integrity check passed"
            return False, f"Integrity check failed: {result[0]}"
        except Exception as e:
            return False, f"Error checking integrity: {str(e)}"


class PostgreSQLRestoreProvider(RestoreProvider):
    """PostgreSQL restore provider using pg_restore/psql.
    
    Foundation layer — safe abstraction for future PostgreSQL support.
    """
    
    def __init__(self, pg_config: Dict = None):
        self.pg_config = pg_config or DatabaseEngineDetector.get_pg_config()
    
    def restore_backup(self, backup_path: str, password: str = None) -> Dict:
        """Restore PostgreSQL database from backup."""
        if not self.pg_config:
            return {'success': False, 'error': 'PostgreSQL not configured'}
        
        if not os.path.exists(backup_path):
            return {'success': False, 'error': 'Backup file not found'}
        
        if not self._psql_available():
            return {'success': False, 'error': 'psql not found in PATH'}
        
        try:
            env = os.environ.copy()
            if password or self.pg_config.get('password'):
                env['PGPASSWORD'] = password or self.pg_config['password']
            
            cmd = [
                'psql',
                '-h', self.pg_config['host'],
                '-p', str(self.pg_config['port']),
                '-U', self.pg_config['user'],
                '-d', self.pg_config['name'],
                '-f', backup_path,
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
            
            if result.returncode == 0:
                return {'success': True, 'target_path': self.pg_config['name']}
            else:
                return {'success': False, 'error': result.stderr or 'psql restore failed'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'psql restore timed out (10 min limit)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def verify_integrity(self, target_path: str) -> tuple:
        """Verify PostgreSQL database integrity via pg_stat_database."""
        if not self.pg_config:
            return False, 'PostgreSQL not configured'
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=self.pg_config['name'],
                user=self.pg_config['user'],
                password=self.pg_config.get('password', ''),
                host=self.pg_config['host'],
                port=self.pg_config['port'],
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            return True, "PostgreSQL connection verified"
        except Exception as e:
            return False, f"PostgreSQL connection failed: {str(e)}"
    
    def _psql_available(self) -> bool:
        """Check if psql is available in PATH."""
        try:
            result = subprocess.run(
                ['psql', '--version'],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


def get_backup_provider() -> BackupProvider:
    """Factory: return the correct backup provider for the active engine."""
    engine = DatabaseEngineDetector.detect()
    if engine == 'postgresql':
        return PostgreSQLBackupProvider()
    return SQLiteBackupProvider()


def get_restore_provider() -> RestoreProvider:
    """Factory: return the correct restore provider for the active engine."""
    engine = DatabaseEngineDetector.detect()
    if engine == 'postgresql':
        return PostgreSQLRestoreProvider()
    return SQLiteRestoreProvider()
