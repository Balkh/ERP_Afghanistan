"""
create_backup workflow — extracted from BackupManager.create_backup (L332-L481 of
pre-refactor backup_system.py, now removed).

Byte-identical to the original public method body. Receives the manager instance
and forwards all state reads/writes through it.

Execution phases (preserved exactly):
  1. Pre-backup safety check
  2. Database path resolution + existence check
  3. Vacuum database (if configured)
  4. Copy database into temp staging dir
  5. Verify database copy integrity (if configured)
  6. Copy additional include_files (if any)
  7. Create compressed archive (tar.gz / tar.bz2)
  8. Apply encryption (if configured + password available)
  9. Move archive into backup_dir with timestamped filename
 10. Calculate SHA256 checksum
 11. Build metadata dict
 12. Persist metadata sidecar JSON
 13. Auto-verify archive integrity via _post_backup_verify
 14. Apply retention policy via cleanup_old_backups
 15. Return success result dict

Failure paths (preserved exactly):
- Database path not found          -> {success: False, error: 'Database path not found', ...}
- Database copy verification failed -> {success: False, error: 'Database verification failed: ...', ...}
- Encryption failed                -> {success: False, error: 'Encryption failed', ...}
- Any other exception              -> {success: False, error: str(e), ...}
"""
import json
import os
import shutil
import tarfile
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def run(manager, db_path: str = None, include_files: List[str] = None,
        description: str = '') -> Dict:
    """
    Execute the create_backup workflow against the given manager.

    Public method signature preserved. Behavior byte-identical to original.
    """
    manager.logger.info("Starting backup creation...")
    start_time = datetime.now()

    try:
        safety = manager._check_pre_backup_safety()
        if not safety['safe']:
            manager.logger.warning(f"Pre-backup safety check: {safety.get('warning', 'unknown issue')}")

        if db_path is None:
            db_path = manager.config['database'].get('path')

        if not db_path or not os.path.exists(db_path):
            return {
                'success': False,
                'error': 'Database path not found',
                'timestamp': start_time.isoformat(),
            }

        if manager.config['database'].get('vacuum_before_backup', True):
            manager._vacuum_database(db_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            db_backup_path = temp_path / 'pharmacy_erp.db'
            shutil.copy2(db_path, db_backup_path)

            if manager.config['database'].get('verify_after_backup', True):
                valid, msg = manager.validator.verify_database_integrity(str(db_backup_path))
                if not valid:
                    manager.logger.error(f"Database verification failed: {msg}")
                    return {
                        'success': False,
                        'error': f'Database verification failed: {msg}',
                        'timestamp': start_time.isoformat(),
                    }

            files_to_backup = []
            if include_files:
                for file_path in include_files:
                    if os.path.exists(file_path):
                        dest_path = temp_path / Path(file_path).name
                        shutil.copy2(file_path, dest_path)
                        files_to_backup.append(Path(file_path).name)

            archive_format = manager.config['compression'].get('format', 'tar.gz')
            archive_path = manager._create_archive(temp_path, archive_format)

            if not manager.config['compression'].get('enabled', True):
                final_path = archive_path
            else:
                final_path = archive_path

            if manager.config['encryption'].get('enabled', True):
                if not manager._is_encryption_configured():
                    manager.logger.error(
                        "Encryption is enabled but PHARMACY_ERP_BACKUP_PASSWORD is not set. "
                        "Creating unencrypted backup instead. Set the env var for encrypted backups."
                    )
                else:
                    encrypted_path = final_path.with_suffix(final_path.suffix + '.enc')
                    password = manager._get_encryption_password()
                    if not manager.encryptor.encrypt_file(str(final_path), str(encrypted_path), password):
                        return {
                            'success': False,
                            'error': 'Encryption failed',
                            'timestamp': start_time.isoformat(),
                        }
                    final_path = encrypted_path
                    os.remove(str(archive_path))

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"pharmacy_erp_backup_{timestamp}{final_path.suffix}"
            backup_path = manager.backup_dir / backup_filename

            shutil.move(str(final_path), str(backup_path))

            checksum = manager.validator.calculate_checksum(str(backup_path))

            backup_size = backup_path.stat().st_size

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
                'encrypted': manager.config['encryption'].get('enabled', False),
                'compressed': manager.config['compression'].get('enabled', False),
                'format': archive_format,
                'version': '1.0.0',
            }

            metadata_path = backup_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            manager.logger.info(f"Backup created successfully: {backup_filename}")

            if not manager._post_backup_verify(str(backup_path), checksum):
                manager.logger.warning(f"Post-backup verification warned for {backup_filename}")

            manager.cleanup_old_backups()

            return {
                'success': True,
                'backup_path': str(backup_path),
                'metadata': metadata,
                'checksum': checksum,
                'verified': True,
            }

    except Exception as e:
        manager.logger.error(f"Backup creation failed: {e}")
        manager.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'timestamp': start_time.isoformat(),
        }
