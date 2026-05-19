"""
Backup health monitoring service.

Provides:
- Last successful backup tracking
- Startup warning if no backup exists
- Corruption detection
- Restore dry-run validation
- Checksum revalidation
- Anomaly detection for suspicious backup size drops
"""
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('backup')


class BackupHealthMonitor:
    """
    Monitors backup system health and detects anomalies.
    
    Lightweight — no polling loops, no excessive threading.
    Called on-demand or at scheduled intervals.
    """
    
    def __init__(self, backup_dir: str = None, db_path: str = None):
        if backup_dir is None:
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            backup_dir = str(Path(appdata) / 'PharmacyERP' / 'backups')
        
        self.backup_dir = Path(backup_dir)
        self.db_path = db_path
    
    def check_health(self) -> Dict:
        """
        Run comprehensive health check.
        
        Returns dict with status, warnings, and recommendations.
        """
        result = {
            'status': 'healthy',
            'warnings': [],
            'errors': [],
            'last_backup': None,
            'total_backups': 0,
            'total_size_mb': 0,
            'checks_run': [],
        }
        
        # Check 1: Last backup age
        last = self._check_last_backup_age()
        result['checks_run'].append('last_backup_age')
        if last['warning']:
            result['warnings'].append(last['warning'])
        result['last_backup'] = last['last_backup']
        
        # Check 2: Backup count
        count = self._check_backup_count()
        result['checks_run'].append('backup_count')
        result['total_backups'] = count['count']
        
        # Check 3: Disk space
        space = self._check_disk_space()
        result['checks_run'].append('disk_space')
        if space['warning']:
            result['warnings'].append(space['warning'])
        if space['error']:
            result['errors'].append(space['error'])
            result['status'] = 'critical'
        
        # Check 4: Corruption detection
        corruption = self._check_corruption()
        result['checks_run'].append('corruption')
        result['errors'].extend(corruption['errors'])
        result['warnings'].extend(corruption['warnings'])
        if corruption['errors']:
            result['status'] = 'critical'
        
        # Check 5: Size anomaly detection
        anomaly = self._check_size_anomaly()
        result['checks_run'].append('size_anomaly')
        result['warnings'].extend(anomaly['warnings'])
        
        # Check 6: Encryption password
        enc = self._check_encryption_config()
        result['checks_run'].append('encryption_config')
        if enc['warning']:
            result['warnings'].append(enc['warning'])
        
        # Overall status
        if result['errors']:
            result['status'] = 'critical'
        elif result['warnings']:
            result['status'] = 'warning'
        
        # Calculate total size
        result['total_size_mb'] = self._calculate_total_size()
        
        return result
    
    def get_startup_warning(self) -> Optional[str]:
        """
        Check if startup warning is needed.
        Returns warning message or None.
        """
        # Warning if no backups exist
        backups = list(self.backup_dir.glob('pharmacy_erp_backup_*'))
        backups = [b for b in backups if b.suffix not in ['.json', '.log']]
        if not backups:
            return (
                "WARNING: No backups found. "
                "Create your first backup immediately via System > Backup & Restore."
            )
        
        # Warning if last backup is older than 7 days
        last_backup = self._get_last_backup()
        if last_backup:
            try:
                ts = last_backup.get('timestamp', '')
                if ts and ts != 'Unknown':
                    backup_date = datetime.fromisoformat(ts.split('+')[0])
                    days_ago = (datetime.now() - backup_date).days
                    if days_ago > 7:
                        return (
                            f"WARNING: Last backup is {days_ago} days old. "
                            f"Create a new backup to ensure data safety."
                        )
            except (ValueError, TypeError):
                pass
        
        # Warning if encryption password not set
        if not os.environ.get('PHARMACY_ERP_BACKUP_PASSWORD'):
            return (
                "WARNING: PHARMACY_ERP_BACKUP_PASSWORD is not set. "
                "Encrypted backups will be created without encryption. "
                "Set this environment variable for secure backups."
            )
        
        return None
    
    def dry_run_validate(self, backup_path: str) -> Dict:
        """
        Validate a backup file without actually restoring.
        Simulates restore flow to verify backup integrity.
        """
        result = {
            'valid': True,
            'checks': [],
            'errors': [],
        }
        
        if not os.path.exists(backup_path):
            result['valid'] = False
            result['errors'].append('Backup file does not exist')
            return result
        
        # Check 1: File size
        size = os.path.getsize(backup_path)
        if size < 1024:
            result['valid'] = False
            result['errors'].append(f'Backup suspiciously small: {size} bytes')
        result['checks'].append({'name': 'file_size', 'size_bytes': size})
        
        # Check 2: Archive integrity
        from backup.backup_system import BackupValidator
        validator = BackupValidator()
        valid, msg = validator.verify_backup_archive(backup_path)
        result['checks'].append({'name': 'archive_integrity', 'valid': valid, 'message': msg})
        if not valid:
            result['valid'] = False
            result['errors'].append(msg)
        
        # Check 3: Checksum verification
        metadata_path = Path(backup_path).with_suffix('.json')
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                stored_checksum = metadata.get('checksum', '')
                if stored_checksum:
                    actual_checksum = validator.calculate_checksum(str(backup_path))
                    match = stored_checksum == actual_checksum
                    result['checks'].append({
                        'name': 'checksum',
                        'stored': stored_checksum[:16] + '...',
                        'actual': actual_checksum[:16] + '...',
                        'match': match,
                    })
                    if not match:
                        result['valid'] = False
                        result['errors'].append('Checksum mismatch — backup may be corrupted')
            except Exception as e:
                result['checks'].append({'name': 'checksum', 'error': str(e)})
        
        # Check 4: Encrypted file check
        if str(backup_path).endswith('.enc'):
            if not os.environ.get('PHARMACY_ERP_BACKUP_PASSWORD'):
                result['valid'] = False
                result['errors'].append(
                    'Backup is encrypted but PHARMACY_ERP_BACKUP_PASSWORD is not set. '
                    'Cannot verify encrypted backup without password.'
                )
            result['checks'].append({'name': 'encryption', 'encrypted': True})
        
        return result
    
    def revalidate_all_checksums(self) -> Dict:
        """
        Revalidate checksums for all stored backups.
        Detects silent corruption.
        """
        results = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'missing_metadata': 0,
            'details': [],
        }
        
        from backup.backup_system import BackupValidator
        validator = BackupValidator()
        
        for backup_file in self.backup_dir.glob('pharmacy_erp_backup_*'):
            if backup_file.suffix in ['.json', '.log']:
                continue
            
            results['total'] += 1
            metadata_path = backup_file.with_suffix('.json')
            
            if not metadata_path.exists():
                results['missing_metadata'] += 1
                results['details'].append({
                    'file': backup_file.name,
                    'status': 'missing_metadata',
                })
                continue
            
            try:
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                stored_checksum = metadata.get('checksum', '')
                if not stored_checksum:
                    results['missing_metadata'] += 1
                    continue
                
                actual_checksum = validator.calculate_checksum(str(backup_file))
                is_valid = stored_checksum == actual_checksum
                
                if is_valid:
                    results['valid'] += 1
                else:
                    results['invalid'] += 1
                    logger.critical(
                        f"CHECKSUM MISMATCH: {backup_file.name} "
                        f"(stored: {stored_checksum[:16]}..., actual: {actual_checksum[:16]}...)"
                    )
                
                results['details'].append({
                    'file': backup_file.name,
                    'status': 'valid' if is_valid else 'corrupted',
                })
            except Exception as e:
                results['details'].append({
                    'file': backup_file.name,
                    'status': 'error',
                    'error': str(e),
                })
        
        return results
    
    def _check_last_backup_age(self) -> Dict:
        """Check how old the last backup is."""
        last = self._get_last_backup()
        result = {'last_backup': last, 'warning': None}
        
        if not last:
            result['warning'] = 'No backups found. Create a backup immediately.'
            return result
        
        try:
            ts = last.get('timestamp', '')
            if ts and ts != 'Unknown':
                backup_date = datetime.fromisoformat(ts.split('+')[0])
                days_ago = (datetime.now() - backup_date).days
                if days_ago > 30:
                    result['warning'] = f'Last backup is {days_ago} days old (recommended: within 7 days)'
                elif days_ago > 7:
                    result['warning'] = f'Last backup is {days_ago} days old'
        except (ValueError, TypeError):
            pass
        
        return result
    
    def _check_backup_count(self) -> Dict:
        """Count total backups."""
        backups = list(self.backup_dir.glob('pharmacy_erp_backup_*'))
        backups = [b for b in backups if b.suffix not in ['.json', '.log']]
        return {'count': len(backups)}
    
    def _check_disk_space(self) -> Dict:
        """Check available disk space."""
        import shutil
        result = {'warning': None, 'error': None}
        
        try:
            disk = shutil.disk_usage(self.backup_dir)
            free_mb = disk.free / (1024 * 1024)
            
            if free_mb < 100:
                result['error'] = f'Critical: Only {free_mb:.0f} MB free disk space'
            elif free_mb < 500:
                result['warning'] = f'Low disk space: {free_mb:.0f} MB free'
        except Exception as e:
            result['warning'] = f'Could not check disk space: {e}'
        
        return result
    
    def _check_corruption(self) -> Dict:
        """Check for corrupted backup files."""
        result = {'errors': [], 'warnings': []}
        
        from backup.backup_system import BackupValidator
        validator = BackupValidator()
        
        for backup_file in self.backup_dir.glob('pharmacy_erp_backup_*'):
            if backup_file.suffix in ['.json', '.log']:
                continue
            
            try:
                valid, msg = validator.verify_backup_archive(str(backup_file))
                if not valid:
                    result['errors'].append(f'Corrupted backup: {backup_file.name} ({msg})')
            except Exception as e:
                result['warnings'].append(f'Could not verify {backup_file.name}: {e}')
        
        return result
    
    def _check_size_anomaly(self) -> Dict:
        """Detect suspicious backup size drops."""
        result = {'warnings': []}
        
        backups = []
        for backup_file in self.backup_dir.glob('pharmacy_erp_backup_*'):
            if backup_file.suffix in ['.json', '.log']:
                continue
            metadata_path = backup_file.with_suffix('.json')
            if metadata_path.exists():
                try:
                    import json
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    size = metadata.get('size_bytes', 0)
                    ts = metadata.get('timestamp', '')
                    if size > 0 and ts and ts != 'Unknown':
                        backups.append((datetime.fromisoformat(ts.split('+')[0]), size))
                except Exception:
                    pass
        
        if len(backups) < 2:
            return result
        
        # Sort by timestamp
        backups.sort(key=lambda x: x[0])
        
        # Compare last two backups
        _, prev_size = backups[-2]
        _, curr_size = backups[-1]
        
        if prev_size > 0:
            drop_pct = ((prev_size - curr_size) / prev_size) * 100
            if drop_pct > 50:
                result['warnings'].append(
                    f'Suspicious backup size drop: {drop_pct:.0f}% '
                    f'({prev_size / (1024*1024):.1f} MB → {curr_size / (1024*1024):.1f} MB)'
                )
        
        return result
    
    def _check_encryption_config(self) -> Dict:
        """Check if encryption password is configured."""
        if not os.environ.get('PHARMACY_ERP_BACKUP_PASSWORD'):
            return {'warning': 'PHARMACY_ERP_BACKUP_PASSWORD not set — encrypted backups will be insecure'}
        return {'warning': None}
    
    def _get_last_backup(self) -> Optional[Dict]:
        """Get the most recent backup metadata."""
        import json
        
        backups = []
        for backup_file in self.backup_dir.glob('pharmacy_erp_backup_*'):
            if backup_file.suffix in ['.json', '.log']:
                continue
            metadata_path = backup_file.with_suffix('.json')
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    metadata['_file'] = str(backup_file)
                    backups.append(metadata)
                except Exception:
                    pass
        
        if not backups:
            return None
        
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backups[0]
    
    def _calculate_total_size(self) -> float:
        """Calculate total backup size in MB."""
        total = 0
        for backup_file in self.backup_dir.glob('pharmacy_erp_backup_*'):
            if backup_file.suffix in ['.json', '.log']:
                continue
            try:
                total += backup_file.stat().st_size
            except OSError:
                pass
        return round(total / (1024 * 1024), 2)
