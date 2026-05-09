"""
Base Service Pattern for Enterprise ERP.
Provides reusable service layer base class with transaction-safe execution.
"""
import logging
from typing import Any, Optional, Callable
from django.db import transaction
from django.core.exceptions import ValidationError

logger = logging.getLogger('core.services')


class BaseService:
    """
    Reusable base service class with transaction-safe execution pattern.
    
    Usage:
        class MyService(BaseService):
            def do_something(self):
                with self.atomic():
                    # your logic here
                    pass
    """
    
    def __init__(self, user=None):
        self.user = user
        self._errors = []
    
    @property
    def errors(self):
        return self._errors
    
    def has_errors(self):
        return len(self._errors) > 0
    
    def add_error(self, error: str):
        self._errors.append(error)
        logger.error(f"Service Error: {error}")
    
    def clear_errors(self):
        self._errors = []
    
    def atomic(self, using=None):
        """
        Context manager for atomic database operations.
        Automatically commits on success, rolls back on exception.
        
        Usage:
            with self.atomic():
                # database operations
        """
        return transaction.atomic(using=using)
    
    def execute_in_transaction(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function within a transaction.
        
        Args:
            func: Callable to execute
            *args, **kwargs: Arguments to pass to func
            
        Returns:
            Result of func execution
            
        Raises:
            Exception: If transaction fails, rolls back automatically
        """
        try:
            with self.atomic():
                return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Transaction failed: {e}")
            raise
    
    def validate_required_fields(self, data: dict, required_fields: list):
        """
        Validate that required fields are present and not empty.
        
        Args:
            data: Dictionary of data to validate
            required_fields: List of required field names
            
        Raises:
            ValidationError: If any required field is missing
        """
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")
    
    def log_operation(self, operation: str, details: dict = None):
        """Log service operation for audit purposes."""
        msg = f"Service: {self.__class__.__name__} - {operation}"
        if details:
            msg += f" | {details}"
        logger.info(msg)