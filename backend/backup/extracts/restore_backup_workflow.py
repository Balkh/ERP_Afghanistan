"""
restore_backup workflow — extracted from BackupManager.restore_backup (L546-L654 of
pre-refactor backup_system.py, now removed).

Byte-identical to the original public method body. Receives the manager instance
and forwards all state reads/writes through it.

Execution phases (preserved exactly):
 1. Resolve backup_path and verify it exists
 2. Load metadata sidecar JSON (if present)
 3. Decrypt if filename ends with .enc (and password available)
 4. Extract archive (tar.gz / tar.bz2 / tgz)
 5. Find database file inside extracted tree
 6. Verify database integrity (if verify=True)
 7. Copy database to target_db_path
 8. Return success result dict

Failure paths (preserved exactly):
- Backup file not found             -> {success: False, error: 'Backup file not found', ...}
- Decryption failed                  -> {success: False, error: 'Decryption failed', ...}
- Unsupported archive format         -> {success: False, error: 'Unsupported archive format', ...}
- Database file not found in archive -> {success: False, error: 'Database file not found in backup', ...}
- Database integrity check failed    -> {success: False, error: 'Database integrity check failed: ...', ...}
- Target database path not specified -> {success: False, error: 'Target database path not specified', ...}
- Any other exception                -> {success: False, error: str(e), ...}
"""
import json
import os
import shutil
import tarfile
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict


def run(manager, backup_path: str, target_db_path: str = None,
        password: str = None, verify: bool = True) -> Dict:
    """
    Execute the restore_backup workflow against the given manager.

    Public method signature preserved. Behavior byte-identical to original.
    """
    manager.logger.info(f"Starting restore from: {backup_path}")
    start_time = datetime.now()

    try:
        backup_path = Path(backup_path)
        if not backup_path.exists():
            return {
                'success': False,
                'error': 'Backup file not found',
                'timestamp': start_time.isoformat(),
            }

        metadata_path = backup_path.with_suffix('.json')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        if str(backup_path).endswith('.enc'):
            if password is None:
                password = manager._get_encryption_password()

            decrypted_path = backup_path.with_suffix('')
            if not manager.encryptor.decrypt_file(str(backup_path), str(decrypted_path), password):
                return {
                    'success': False,
                    'error': 'Decryption failed',
                    'timestamp': start_time.isoformat(),
                }
            backup_path = decrypted_path

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

            db_file = temp_path / 'pharmacy_erp_backup' / 'pharmacy_erp.db'
            if not db_file.exists():
                return {
                    'success': False,
                    'error': 'Database file not found in backup',
                    'timestamp': start_time.isoformat(),
                }

            if verify:
                valid, msg = manager.validator.verify_database_integrity(str(db_file))
                if not valid:
                    return {
                        'success': False,
                        'error': f'Database integrity check failed: {msg}',
                        'timestamp': start_time.isoformat(),
                    }

            if target_db_path is None:
                target_db_path = manager.config['database'].get('path')

            if target_db_path:
                target_path = Path(target_db_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(db_file), str(target_path))

                manager.logger.info(f"Backup restored to: {target_path}")
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
        manager.logger.error(f"Restore failed: {e}")
        manager.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'timestamp': start_time.isoformat(),
        }
