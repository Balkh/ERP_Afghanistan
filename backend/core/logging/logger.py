"""
Central logger factory for Pharmacy ERP.
Provides structured, environment-aware logging.
"""
import logging
import os
from typing import Optional

from core.logging.config import get_log_level, is_production
from core.logging.formatters import JSONFormatter, HumanFormatter


class Logger:
    """Central logging facade for the ERP system."""

    _loggers = {}

    @classmethod
    def get(cls, name: str, level: Optional[str] = None) -> logging.Logger:
        """Get or create a named logger."""
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(level or get_log_level())
            logger.propagate = False

            if not logger.handlers:
                cls._add_handlers(logger)

            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def _add_handlers(cls, logger: logging.Logger):
        """Add appropriate handlers based on environment."""
        if is_production():
            handler = cls._file_handler()
            handler.setFormatter(JSONFormatter())
        else:
            handler = cls._console_handler()
            handler.setFormatter(HumanFormatter())

        logger.addHandler(handler)

        # Optional DB handler for audit events
        if os.environ.get('ENABLE_DB_LOGGING', 'false').lower() == 'true':
            db_handler = cls._db_handler()
            logger.addHandler(db_handler)

    @classmethod
    def _console_handler(cls):
        """Console handler for development."""
        import sys
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        return handler

    @classmethod
    def _file_handler(cls):
        """Rotating file handler for production."""
        import logging.handlers
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'erp.log')

        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setLevel(logging.INFO)
        return handler

    @classmethod
    def _db_handler(cls):
        """Database handler for audit events (optional)."""
        from core.logging.handlers import DatabaseAuditHandler
        return DatabaseAuditHandler()

    @classmethod
    def audit(cls) -> logging.Logger:
        """Get audit logger."""
        return cls.get('erp.audit')

    @classmethod
    def financial(cls) -> logging.Logger:
        """Get financial logger."""
        return cls.get('erp.financial')

    @classmethod
    def inventory(cls) -> logging.Logger:
        """Get inventory logger."""
        return cls.get('erp.inventory')

    @classmethod
    def security(cls) -> logging.Logger:
        """Get security logger."""
        return cls.get('erp.security')

    @classmethod
    def api(cls) -> logging.Logger:
        """Get API logger."""
        return cls.get('erp.api')

    @classmethod
    def performance(cls) -> logging.Logger:
        """Get performance logger."""
        return cls.get('erp.performance')

    @classmethod
    def error(cls) -> logging.Logger:
        """Get error logger."""
        return cls.get('erp.error')
