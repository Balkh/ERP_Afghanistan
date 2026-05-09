"""
Custom logging formatters for Pharmacy ERP.
"""
import json
import logging
import traceback
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Structured JSON formatter for production logging.
    Each log entry is a JSON object with consistent structure.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add request ID if present
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id

        # Add user if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info),
            }

        return json.dumps(log_data)


class HumanFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    Color-coded output for terminal readability.
    """

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        request_id = getattr(record, 'request_id', '')
        request_prefix = f'[{request_id}] ' if request_id else ''

        parts = [
            f'{color}[{record.levelname}]{self.RESET}',
            f'{record.name}',
            f'- {request_prefix}{record.getMessage()}',
        ]

        if record.exc_info and record.exc_info[0] is not None:
            parts.append(f'\n{self.formatException(record.exc_info)}')

        return ' '.join(parts)
