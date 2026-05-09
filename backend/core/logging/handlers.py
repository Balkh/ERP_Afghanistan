"""
Custom logging handlers for Pharmacy ERP.
"""
import logging
from datetime import datetime


class DatabaseAuditHandler(logging.Handler):
    """
    Handler that stores audit-level log entries in the database.
    Only captures events at INFO level and above.
    """

    def emit(self, record: logging.LogRecord):
        try:
            from core.models.audit import AuditLog

            if record.levelno < logging.INFO:
                return

            AuditLog.objects.create(
                action=record.levelname,
                entity_type=record.name,
                entity_id=record.module or '',
                description=self.format(record),
                module=self._extract_module(record),
                after_state={
                    'message': record.getMessage(),
                    'timestamp': datetime.now().isoformat(),
                },
            )
        except Exception:
            pass

    def _extract_module(self, record: logging.LogRecord) -> str:
        """Extract module name from logger name."""
        name = record.name
        if name.startswith('erp.'):
            parts = name.split('.')
            return parts[1].upper() if len(parts) > 1 else 'SYSTEM'
        return 'SYSTEM'
