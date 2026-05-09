"""
Operational Alert System.
Lightweight alerting for operational issues.
"""
import logging
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List
from django.utils import timezone


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertCategory(Enum):
    """Alert categories."""
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"
    ACCOUNTING = "ACCOUNTING"
    INVENTORY = "INVENTORY"
    API = "API"
    DATABASE = "DATABASE"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"


class Alert:
    """Alert representation."""

    def __init__(
        self,
        severity: AlertSeverity,
        category: AlertCategory,
        title: str,
        message: str,
        details: dict = None
    ):
        self.severity = severity
        self.category = category
        self.title = title
        self.message = message
        self.details = details or {}
        self.timestamp = timezone.now()
        self.id = f"{category.value}_{int(self.timestamp.timestamp())}"

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'severity': self.severity.value,
            'category': self.category.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class AlertManager:
    """Alert management and notification."""

    _alerts: List[Alert] = []
    _max_alerts = 1000
    _logger = logging.getLogger('erp.alerts')

    @classmethod
    def create_alert(
        cls,
        severity: AlertSeverity,
        category: AlertCategory,
        title: str,
        message: str,
        details: dict = None
    ) -> Alert:
        """Create and log an alert."""
        alert = Alert(severity, category, title, message, details)

        cls._alerts.append(alert)
        if len(cls._alerts) > cls._max_alerts:
            cls._alerts = cls._alerts[-cls._max_alerts:]

        log_method = {
            AlertSeverity.INFO: cls._logger.info,
            AlertSeverity.WARNING: cls._logger.warning,
            AlertSeverity.ERROR: cls._logger.error,
            AlertSeverity.CRITICAL: cls._logger.critical
        }.get(severity, cls._logger.info)

        log_method(f"[{category.value}] {title}: {message}")

        return alert

    @classmethod
    def get_recent_alerts(cls, hours: int = 24, limit: int = 100) -> List[Alert]:
        """Get recent alerts."""
        cutoff = timezone.now() - timedelta(hours=hours)
        return [
            a for a in cls._alerts
            if a.timestamp >= cutoff
        ][-limit:]

    @classmethod
    def get_alerts_by_severity(cls, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity."""
        return [a for a in cls._alerts if a.severity == severity]

    @classmethod
    def get_alerts_by_category(cls, category: AlertCategory) -> List[Alert]:
        """Get alerts by category."""
        return [a for a in cls._alerts if a.category == category]

    @classmethod
    def clear_alerts(cls):
        """Clear all alerts."""
        cls._alerts = []


def alert_backup_failed(backup_name: str, error: str):
    """Alert for backup failures."""
    AlertManager.create_alert(
        severity=AlertSeverity.ERROR,
        category=AlertCategory.BACKUP,
        title="Backup Failed",
        message=f"Backup '{backup_name}' failed: {error}",
        details={'backup_name': backup_name, 'error': error}
    )


def alert_restore_failed(restore_point: str, error: str):
    """Alert for restore failures."""
    AlertManager.create_alert(
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.RESTORE,
        title="Restore Failed",
        message=f"Restore '{restore_point}' failed: {error}",
        details={'restore_point': restore_point, 'error': error}
    )


def alert_accounting_inconsistency(issue_type: str, details: dict):
    """Alert for accounting inconsistencies."""
    AlertManager.create_alert(
        severity=AlertSeverity.ERROR,
        category=AlertCategory.ACCOUNTING,
        title=f"Accounting Inconsistency: {issue_type}",
        message=f"Detected {issue_type}",
        details=details
    )


def alert_inventory_inconsistency(issue_type: str, details: dict):
    """Alert for inventory inconsistencies."""
    AlertManager.create_alert(
        severity=AlertSeverity.WARNING,
        category=AlertCategory.INVENTORY,
        title=f"Inventory Inconsistency: {issue_type}",
        message=f"Detected {issue_type}",
        details=details
    )


def alert_slow_request(endpoint: str, duration_ms: float):
    """Alert for slow API requests."""
    if duration_ms > 2000:
        AlertManager.create_alert(
            severity=AlertSeverity.WARNING,
            category=AlertCategory.API,
            title="Slow API Request",
            message=f"{endpoint} took {duration_ms}ms",
            details={'endpoint': endpoint, 'duration_ms': duration_ms}
        )


def alert_security_event(event_type: str, details: dict):
    """Alert for security events."""
    AlertManager.create_alert(
        severity=AlertSeverity.WARNING,
        category=AlertCategory.SECURITY,
        title=f"Security Event: {event_type}",
        message=f"Security event: {event_type}",
        details=details
    )