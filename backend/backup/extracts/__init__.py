"""
Backup system — workflow extraction package.

This package decomposes the two large public methods of BackupManager
(create_backup, restore_backup) into focused workflow modules.

Behavior contract (byte-identical to pre-refactor):
- The public method signatures, return payloads, side effects, logging
  behavior, exception handling, and execution order are preserved.
- The public methods on BackupManager become thin delegators to
  `run(manager, ...)` defined here.
- All instance state (config, validator, encryptor, logger, backup_dir)
  and all private helper methods (_check_pre_backup_safety,
  _post_backup_verify, _vacuum_database, _create_archive, _log_db_event,
  _get_encryption_password, _is_encryption_configured, cleanup_old_backups)
  remain on the BackupManager class — only the giant orchestrator bodies
  were extracted.
"""
