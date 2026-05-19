"""
Unified Backup Control Plane — Single Source of Operational Truth (SSOT).

Aggregates state from all existing backup/restore/recovery services into
a single lightweight read-only DTO. All UI components MUST read from this
layer ONLY. No UI component should independently compute system state.

Architecture:
    ControlPlane.get_status()
        ├── BackupManager.stats()
        ├── RestoreLock.is_locked
        ├── BackupHealthMonitor.check_health()
        ├── OffsiteReplicator (config + queue status)
        ├── CorruptionScanner.scan()
        ├── RecoveryCertificationReport (lightweight)
        └── Overall status derivation

Design rules:
    - NO duplicate data storage
    - NO new database schema
    - READ-ONLY aggregation over existing services
    - Lightweight DTO output (dict only)
    - No background polling
    - Each service call is isolated — failure in one does not cascade

ARCHITECTURE LOCK:
    This is the ONLY source of system status for the UI.
    Do not add parallel status computation endpoints.
    All new status fields must be added here, not elsewhere.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('erp.backup.control_plane')


class UnifiedBackupStatus:
    """Lightweight DTO representing the unified system state.

    All fields are derived from existing services — no independent computation.
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @property
    def backup_status(self) -> str:
        """Overall backup system status: healthy, warning, critical."""
        return self._data.get('backup_status', 'unknown')

    @property
    def last_backup_time(self) -> Optional[str]:
        """ISO8601 timestamp of last successful backup."""
        return self._data.get('last_backup_time')

    @property
    def total_backups(self) -> int:
        return self._data.get('total_backups', 0)

    @property
    def total_size_mb(self) -> float:
        return self._data.get('total_size_mb', 0.0)

    @property
    def restore_lock_active(self) -> bool:
        return self._data.get('restore_lock_active', False)

    @property
    def certification_score(self) -> int:
        return self._data.get('certification_score', 0)

    @property
    def certification_status(self) -> str:
        """CERTIFIED, CONDITIONAL, or FAILED."""
        return self._data.get('certification_status', 'UNKNOWN')

    @property
    def corruption_warnings(self) -> list:
        return self._data.get('corruption_warnings', [])

    @property
    def email_status(self) -> str:
        """enabled, disabled, failure, pending."""
        return self._data.get('email_status', 'disabled')

    @property
    def email_pending_count(self) -> int:
        return self._data.get('email_pending_count', 0)

    @property
    def encryption_configured(self) -> bool:
        return self._data.get('encryption_configured', False)

    @property
    def warnings(self) -> list:
        return self._data.get('warnings', [])

    @property
    def errors(self) -> list:
        return self._data.get('errors', [])

    @property
    def can_restore(self) -> bool:
        """True if system is in a state that allows restore."""
        return (
            not self.restore_lock_active
            and self.backup_status != 'critical'
        )

    @property
    def can_backup(self) -> bool:
        """True if system is in a state that allows backup creation."""
        return not self.restore_lock_active

    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy()


class BackupControlPlane:
    """Unified control plane — single source of operational truth.

    Aggregates state from all existing services without duplicating data.
    All reads are on-demand — no background polling or caching.
    """

    def __init__(self):
        self._health_monitor = None
        self._corruption_scanner = None

    def _get_health_monitor(self):
        if self._health_monitor is None:
            from backup.services.health_monitor import BackupHealthMonitor
            self._health_monitor = BackupHealthMonitor()
        return self._health_monitor

    def _get_corruption_scanner(self):
        if self._corruption_scanner is None:
            from backup.services.corruption_scanner import CorruptionScanner
            self._corruption_scanner = CorruptionScanner()
        return self._corruption_scanner

    def get_status(self) -> UnifiedBackupStatus:
        """Get unified system status snapshot.

        This is the ONLY method UI components should call for system state.
        All data is read from existing services — no independent computation.
        Each service call is isolated — failure in one does not cascade.
        """
        data = {}

        # 1. Backup stats from BackupManager
        data.update(self._get_backup_stats())

        # 2. Restore lock status
        data.update(self._get_restore_lock_status())

        # 3. Health monitor results
        data.update(self._get_health_status())

        # 4. Email/offsite status
        data.update(self._get_email_status())

        # 5. Corruption scan (lightweight)
        data.update(self._get_corruption_status())

        # 6. Certification status
        data.update(self._get_certification_status())

        # 7. Encryption config
        data['encryption_configured'] = bool(os.environ.get('PHARMACY_ERP_BACKUP_PASSWORD'))

        # 8. Overall status derivation
        data['backup_status'] = self._derive_overall_status(data)

        return UnifiedBackupStatus(data)

    def _get_backup_stats(self) -> Dict[str, Any]:
        """Aggregate from BackupManager."""
        try:
            from backup.backup_system import BackupManager
            bm = BackupManager()
            stats = bm.get_backup_stats()
            return {
                'total_backups': stats.get('total_backups', 0),
                'total_size_mb': stats.get('total_size_mb', 0.0),
                'last_backup_time': stats.get('last_backup'),
            }
        except Exception as e:
            logger.warning(f"Failed to get backup stats: {e}")
            return {
                'total_backups': 0,
                'total_size_mb': 0.0,
                'last_backup_time': None,
                '_error': 'backup_stats_unavailable',
            }

    def _get_restore_lock_status(self) -> Dict[str, Any]:
        """Aggregate from RestoreLock."""
        try:
            from backup.services.restore_lock import RestoreLock
            lock = RestoreLock()
            return {
                'restore_lock_active': lock.is_locked,
            }
        except Exception as e:
            logger.warning(f"Failed to get restore lock status: {e}")
            return {'restore_lock_active': False}

    def _get_health_status(self) -> Dict[str, Any]:
        """Aggregate from BackupHealthMonitor."""
        try:
            monitor = self._get_health_monitor()
            health = monitor.check_health()
            return {
                'health_status': health.get('status', 'unknown'),
                'health_warnings': health.get('warnings', []),
                'health_errors': health.get('errors', []),
            }
        except Exception as e:
            logger.warning(f"Failed to get health status: {e}")
            return {
                'health_status': 'unknown',
                'health_warnings': [],
                'health_errors': [],
            }

    def _get_email_status(self) -> Dict[str, Any]:
        """Aggregate from OffsiteReplicator."""
        try:
            from backup.services.offsite_replication import (
                OffsiteReplicator, OffsiteReplicationConfig, RetryQueue,
            )
            from pathlib import Path

            config = OffsiteReplicationConfig().load()
            enabled = config.get('enabled', False)

            pending_count = 0
            if enabled:
                try:
                    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
                    retry_dir = Path(appdata) / 'PharmacyERP' / 'config' / 'offsite_retry'
                    queue = RetryQueue(retry_dir)
                    pending_count = len(queue.get_pending())
                except Exception:
                    pass

            status = 'disabled'
            if enabled:
                status = 'pending' if pending_count > 0 else 'enabled'

            return {
                'email_status': status,
                'email_pending_count': pending_count,
                'email_enabled': enabled,
            }
        except Exception as e:
            logger.warning(f"Failed to get email status: {e}")
            return {
                'email_status': 'disabled',
                'email_pending_count': 0,
                'email_enabled': False,
            }

    def _get_corruption_status(self) -> Dict[str, Any]:
        """Aggregate from CorruptionScanner (lightweight scan only)."""
        try:
            scanner = self._get_corruption_scanner()
            scan = scanner.scan()
            return {
                'corruption_valid': scan.get('valid', True),
                'corruption_warnings': scan.get('warnings', []),
                'corruption_errors': scan.get('errors', []),
            }
        except Exception as e:
            logger.warning(f"Failed to get corruption status: {e}")
            return {
                'corruption_valid': True,
                'corruption_warnings': [],
                'corruption_errors': [],
            }

    def _get_certification_status(self) -> Dict[str, Any]:
        """Aggregate from RecoveryCertificationReport (lightweight, no full validation)."""
        try:
            from backup.services.certification_report import RecoveryCertificationReport
            report = RecoveryCertificationReport(
                backup_checksum_valid=True,
                has_orphaned_records=False,
                rollback_tested=False,
            )
            confidence = report.calculate_confidence()
            status = report.determine_status(confidence)
            return {
                'certification_score': confidence,
                'certification_status': status,
            }
        except Exception as e:
            logger.warning(f"Failed to get certification status: {e}")
            return {
                'certification_score': 0,
                'certification_status': 'UNKNOWN',
            }

    def _derive_overall_status(self, data: Dict[str, Any]) -> str:
        """Derive overall status from aggregated data.

        Rules (evaluated in order):
        - critical: any health errors or corruption errors
        - warning: any health warnings or corruption warnings or no backups
        - healthy: everything OK
        """
        if data.get('health_errors') or data.get('corruption_errors'):
            return 'critical'

        if data.get('health_warnings') or data.get('corruption_warnings'):
            return 'warning'

        if data.get('total_backups', 0) == 0:
            return 'warning'

        return 'healthy'

    def get_restore_readiness(self) -> Dict[str, Any]:
        """Get restore readiness assessment.

        Returns metadata needed before initiating a restore:
        - lock status
        - available restore points
        - encryption status
        - emergency backup capability
        """
        status = self.get_status()
        result = {
            'can_restore': status.can_restore,
            'restore_lock_active': status.restore_lock_active,
            'encryption_configured': status.encryption_configured,
            'total_backups': status.total_backups,
            'warnings': status.warnings,
            'errors': status.errors,
        }

        if not status.can_restore:
            if status.restore_lock_active:
                result['block_reason'] = 'Restore already in progress'
            elif status.backup_status == 'critical':
                result['block_reason'] = 'System has critical errors — resolve before restore'

        return result

    def get_backup_readiness(self) -> Dict[str, Any]:
        """Get backup creation readiness assessment."""
        status = self.get_status()
        result = {
            'can_backup': status.can_backup,
            'restore_lock_active': status.restore_lock_active,
            'encryption_configured': status.encryption_configured,
            'warnings': [],
        }

        if not status.encryption_configured:
            result['warnings'].append(
                'PHARMACY_ERP_BACKUP_PASSWORD not set — backups will be unencrypted'
            )

        if status.restore_lock_active:
            result['warnings'].append('Restore in progress — backup may be slower')

        return result
