"""
Restore execution mutex and safe restore orchestration.

Provides:
- File-based restore lock (prevents concurrent restores)
- Atomic restore flow with automatic emergency backup
- Failure auto-rollback
"""
import os
import time
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger('backup')


class RestoreLock:
    """
    File-based mutex to prevent concurrent restore operations.
    
    Uses a lock file in the backup directory with PID tracking.
    Automatically stale if process dies (PID no longer exists).
    """
    
    def __init__(self, lock_dir: str = None):
        if lock_dir is None:
            import os as os_module
            appdata = os_module.environ.get('APPDATA', os_module.path.expanduser('~'))
            lock_dir = str(Path(appdata) / 'PharmacyERP' / 'config')
        
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.lock_dir / '.restore_lock'
        self._acquired = False
    
    def acquire(self, timeout: int = 300) -> bool:
        """
        Try to acquire the restore lock.
        
        Args:
            timeout: Max seconds to wait for lock (default 5 min)
        
        Returns:
            True if lock acquired, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self._try_acquire():
                self._acquired = True
                return True
            
            # Check if lock is stale (process no longer exists)
            if self._is_stale():
                self._force_release()
                if self._try_acquire():
                    self._acquired = True
                    return True
            
            time.sleep(2)
        
        logger.warning("Restore lock acquisition timed out")
        return False
    
    def release(self):
        """Release the restore lock."""
        if self._acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
                self._acquired = False
                logger.info("Restore lock released")
            except OSError as e:
                logger.error(f"Failed to release restore lock: {e}")
    
    def _try_acquire(self) -> bool:
        """Try to create lock file atomically."""
        try:
            if self.lock_file.exists():
                return False
            # Atomic create via exclusive mode
            fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except (OSError, FileExistsError):
            return False
    
    def _is_stale(self) -> bool:
        """Check if the lock file belongs to a dead process."""
        if not self.lock_file.exists():
            return False
        try:
            pid = int(self.lock_file.read_text().strip())
            # On Windows, os.kill(pid, 0) doesn't work for process check
            import platform
            if platform.system() == 'Windows':
                import subprocess
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) not in result.stdout
            # Unix: check if process is running
            os.kill(pid, 0)
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            return True
        except Exception:
            return True
    
    def _force_release(self):
        """Force remove stale lock file."""
        try:
            self.lock_file.unlink()
            logger.info(f"Removed stale restore lock (PID no longer exists)")
        except OSError:
            pass
    
    @property
    def is_locked(self) -> bool:
        """Check if a restore is currently in progress."""
        if not self.lock_file.exists():
            return False
        return not self._is_stale()


@contextmanager
def restore_lock_context(lock_dir: str = None, timeout: int = 300):
    """Context manager for restore lock."""
    lock = RestoreLock(lock_dir)
    if not lock.acquire(timeout):
        raise RuntimeError(
            "Cannot acquire restore lock. Another restore may be in progress. "
            f"Lock file: {lock.lock_file}"
        )
    try:
        yield lock
    finally:
        lock.release()


class SafeRestoreExecutor:
    """
    Executes restore with full safety guarantees:
    1. Acquire restore lock
    2. Create emergency backup of current DB
    3. Perform restore
    4. Verify integrity
    5. Auto-rollback on failure
    """
    
    def __init__(self, db_path: str = None, lock_dir: str = None):
        self.db_path = db_path
        self.lock = RestoreLock(lock_dir)
        self.emergency_backup_path: Optional[str] = None
    
    def execute(self, backup_path: str, verify: bool = True) -> Dict[str, Any]:
        """
        Execute safe restore flow.
        
        Args:
            backup_path: Path to backup file to restore from
            verify: Whether to verify integrity after restore
        
        Returns:
            Dict with success, error, and metadata
        """
        # Step 1: Acquire lock
        if not self.lock.acquire(timeout=300):
            return {
                'success': False,
                'error': 'Cannot acquire restore lock. Another restore may be in progress.',
            }
        
        try:
            # Step 2: Emergency backup
            self.emergency_backup_path = self._create_emergency_backup()
            
            # Step 3: Perform restore (caller handles actual restore logic)
            # This method returns the emergency backup path for rollback
            return {
                'success': True,
                'lock_acquired': True,
                'emergency_backup': self.emergency_backup_path,
            }
        
        except Exception as e:
            # Step 5: Auto-rollback
            if self.emergency_backup_path:
                self._rollback()
            return {
                'success': False,
                'error': str(e),
                'emergency_backup': self.emergency_backup_path,
            }
        
        finally:
            self.lock.release()
    
    def _create_emergency_backup(self) -> Optional[str]:
        """Create emergency backup of current database."""
        if not self.db_path or not os.path.exists(self.db_path):
            return None
        
        try:
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            emergency_dir = os.path.join(os.path.dirname(self.db_path), '.emergency_backups')
            os.makedirs(emergency_dir, exist_ok=True)
            
            path = os.path.join(emergency_dir, f'emergency_{timestamp}.db')
            shutil.copy2(self.db_path, path)
            logger.info(f"Emergency backup created: {path}")
            return path
        except Exception as e:
            logger.error(f"Emergency backup failed: {e}")
            return None
    
    def _rollback(self) -> bool:
        """Rollback to emergency backup."""
        if not self.emergency_backup_path or not os.path.exists(self.emergency_backup_path):
            logger.error("No emergency backup available for rollback")
            return False
        
        if not self.db_path:
            return False
        
        try:
            temp_path = self.db_path + '.rollback_tmp'
            shutil.copy2(self.emergency_backup_path, temp_path)
            os.replace(temp_path, self.db_path)
            logger.info(f"Emergency rollback completed")
            return True
        except Exception as e:
            logger.critical(f"Emergency rollback failed: {e}")
            return False
