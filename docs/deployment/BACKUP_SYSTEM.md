# Pharmacy ERP Backup System Documentation

## Overview

The Pharmacy ERP Backup System provides comprehensive backup infrastructure with:
- **Scheduled backups** - Automatic backups on configurable schedules
- **Encrypted backups** - AES-256 encryption via Fernet
- **Backup compression** - Tar.gz/Tar.bz2 compression
- **Backup validation** - SHA-256 checksums and integrity verification
- **Cleanup system** - Automatic retention policy enforcement
- **Restore preparation** - Full restore infrastructure with verification

## Architecture

### Components

| Component | Description |
|-----------|-------------|
| `backup_system.py` | Core backup engine with encryption, compression, validation |
| `models.py` | Django models for tracking backups, schedules, and logs |
| `views.py` | REST API endpoints for backup management |
| `serializers.py` | API serializers for backup data |
| `admin.py` | Django admin integration |
| `management/commands/` | CLI commands for backup operations |

### Models

#### BackupRecord
Tracks each backup operation with:
- Status tracking (pending, in_progress, completed, failed, verified, restored, deleted)
- File metadata (filename, size, checksum, encryption status)
- Timing information (started, completed, duration)
- User attribution (created_by, verified_by, restored_by)
- Verification results

#### BackupSchedule
Configures automated backup schedules:
- Frequency (hourly, daily, weekly, monthly)
- Time configuration
- Retention policy (max backups, max age)
- Encryption and compression settings

#### BackupLog
Audit trail for all backup operations:
- Event types (backup/restore started/completed/failed, cleanup, etc.)
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- References to backup records and schedules
- Additional details in JSON format

## Usage

### Command Line Interface

#### Create Backup
```bash
cd backend
python manage.py create_backup --description "Pre-maintenance backup"
```

Options:
- `--description`: Backup description
- `--db-path`: Custom database path
- `--include-files`: Additional files to include
- `--format`: Output format (json or text)

#### Restore Backup
```bash
python manage.py restore_backup /path/to/backup.tar.gz.enc
```

Options:
- `--target-db`: Target database path
- `--password`: Encryption password
- `--no-verify`: Skip verification

#### List Backups
```bash
python manage.py list_backups
```

#### Cleanup Old Backups
```bash
# Dry run (preview)
python manage.py cleanup_backups --dry-run

# Actual cleanup
python manage.py cleanup_backups --max-backups 30 --max-age-days 90
```

### REST API

#### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/backup/records/` | List all backup records |
| POST | `/api/backup/records/create_backup/` | Create new backup |
| GET | `/api/backup/records/stats/` | Get backup statistics |
| POST | `/api/backup/records/{id}/verify/` | Verify backup integrity |
| POST | `/api/backup/records/{id}/restore/` | Restore from backup |
| DELETE | `/api/backup/records/{id}/delete_backup/` | Delete backup |
| GET | `/api/backup/schedules/` | List backup schedules |
| POST | `/api/backup/schedules/` | Create backup schedule |
| GET | `/api/backup/logs/` | List backup logs |

#### Example: Create Backup via API

```bash
curl -X POST http://localhost:8000/api/backup/records/create_backup/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Manual backup",
    "encrypted": true,
    "compressed": true
  }'
```

#### Example: Restore via API

```bash
curl -X POST http://localhost:8000/api/backup/records/{id}/restore/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "backup_path": "/path/to/backup.tar.gz.enc",
    "password": "your-encryption-password",
    "verify": true
  }'
```

### Python API

```python
from backup.backup_system import BackupManager

# Create backup manager
backup_manager = BackupManager()

# Create backup
result = backup_manager.create_backup(
    db_path='/path/to/database.db',
    include_files=['/path/to/config.json'],
    description='Pre-update backup'
)

if result['success']:
    print(f"Backup created: {result['metadata']['filename']}")
    print(f"Size: {result['metadata']['size_mb']} MB")
    print(f"Checksum: {result['checksum']}")

# List backups
backups = backup_manager.list_backups()
for backup in backups:
    print(f"{backup['filename']} - {backup['size_mb']} MB")

# Restore backup
result = backup_manager.restore_backup(
    backup_path='/path/to/backup.tar.gz.enc',
    target_db_path='/path/to/restore.db',
    password='encryption-password'
)

# Get statistics
stats = backup_manager.get_backup_stats()
print(f"Total backups: {stats['total_backups']}")
print(f"Total size: {stats['total_size_mb']} MB")
```

## Configuration

### Backup Configuration File

Location: `%APPDATA%\PharmacyERP\config\backup_config.json`

```json
{
  "enabled": true,
  "backup_dir": "%APPDATA%\\PharmacyERP\\backups",
  "schedule": {
    "frequency": "daily",
    "time": "02:00",
    "day_of_week": "sunday",
    "day_of_month": 1
  },
  "retention": {
    "max_backups": 30,
    "max_age_days": 90,
    "min_free_space_mb": 1000
  },
  "compression": {
    "enabled": true,
    "level": 6,
    "format": "tar.gz"
  },
  "encryption": {
    "enabled": true,
    "algorithm": "fernet"
  },
  "database": {
    "path": "%APPDATA%\\PharmacyERP\\data\\pharmacy_erp.db",
    "vacuum_before_backup": true,
    "verify_after_backup": true
  },
  "notifications": {
    "on_success": false,
    "on_failure": true,
    "email": ""
  },
  "logging": {
    "level": "INFO",
    "file": "backup.log"
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PHARMACY_ERP_BACKUP_PASSWORD` | Encryption password for backups | Auto-generated (not recommended) |

## Backup Lifecycle

### 1. Creation
1. Database vacuum (optimize size)
2. Copy database to temporary location
3. Verify database integrity
4. Copy additional files (if specified)
5. Create compressed archive
6. Encrypt archive (if configured)
7. Move to backup directory
8. Calculate checksum
9. Save metadata
10. Cleanup old backups

### 2. Verification
1. Check archive integrity
2. Verify expected files present
3. Decrypt archive (if encrypted)
4. Extract to temporary location
5. Verify database integrity
6. Compare checksum

### 3. Restore
1. Decrypt archive (if encrypted)
2. Extract archive
3. Verify database integrity
4. Copy to target location
5. Verify target database
6. Update backup record

### 4. Cleanup
1. Check retention policy
2. Delete backups exceeding max count
3. Delete backups older than max age
4. Check free space
5. Delete oldest if space is low

## Security

### Encryption
- Algorithm: Fernet (AES-128-CBC with HMAC-SHA256)
- Key derivation: PBKDF2 with SHA-256
- Iterations: 100,000
- Salt: 16 bytes random

### Checksums
- Algorithm: SHA-256
- Calculated after encryption
- Stored in metadata and database record

### Access Control
- All API endpoints require authentication
- Admin users can manage all backups
- Audit trail tracks all operations

## Monitoring

### Backup Statistics
- Total backups count
- Total storage used
- Oldest/newest backup dates
- Last backup timestamp

### Log Analysis
Backup logs are stored in:
- `%APPDATA%\PharmacyERP\backups\backup.log`
- Django admin interface
- API endpoint: `/api/backup/logs/`

### Health Checks
- Database integrity verification
- Archive integrity verification
- Checksum validation
- Free space monitoring

## Troubleshooting

### Common Issues

#### Backup Fails
1. Check database path is correct
2. Verify sufficient disk space
3. Check file permissions
4. Review backup logs for details

#### Restore Fails
1. Verify backup file exists
2. Check encryption password is correct
3. Verify archive is not corrupt
4. Check target path is writable

#### Low Disk Space
1. Run cleanup with aggressive retention
2. Reduce backup frequency
3. Move backups to external storage
4. Increase retention limits

#### Encryption Issues
1. Verify PHARMACY_ERP_BACKUP_PASSWORD is set
2. Use same password for encrypt/decrypt
3. Check password is accessible during restore

## Best Practices

1. **Schedule regular backups** - Daily at minimum
2. **Test restores periodically** - Verify backups actually work
3. **Store backups offsite** - Use external storage or cloud
4. **Monitor disk space** - Set alerts for low space
5. **Keep encryption password secure** - Store in password manager
6. **Review logs regularly** - Check for warnings or failures
7. **Update retention policy** - Balance storage vs recovery needs
8. **Document backup procedures** - Ensure team knows how to restore

## Integration

### Scheduled Tasks (Windows)

Create a scheduled task to run daily backups:

```batch
schtasks /create /tn "Pharmacy ERP Backup" /tr "python manage.py create_backup" /sc daily /st 02:00
```

### Cron Jobs (Linux)

```cron
0 2 * * * cd /path/to/backend && python manage.py create_backup
```

### Application Integration

The backup system can be integrated with other parts of the application:
- Pre-update backups before system updates
- Pre-maintenance backups before database migrations
- Post-transaction backups for critical operations
- Automated cleanup as part of maintenance tasks

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-30 | Initial release with full backup infrastructure |