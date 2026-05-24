"""
Transaction Service - atomic operations helper with rollback-safe structure.
"""
import logging
from typing import Any, Optional, List, Callable
from django.db import transaction, connection
from django.core.exceptions import ValidationError

logger = logging.getLogger('core.services.transaction')


class TransactionService:
    """
    Provides atomic transaction helpers for complex operations.
    """
    
    @staticmethod
    def atomic(using=None):
        """Context manager for atomic operations."""
        return transaction.atomic(using=using)
    
    @staticmethod
    def savepoint(using=None):
        """Create a savepoint for nested transactions."""
        return transaction.savepoint(using=using)
    
    @staticmethod
    def savepoint_rollback(savepoint, using=None):
        """Rollback to a savepoint."""
        transaction.savepoint_rollback(savepoint, using=using)
    
    @staticmethod
    def savepoint_commit(savepoint, using=None):
        """Commit a savepoint."""
        transaction.savepoint_commit(savepoint, using=using)
    
    @classmethod
    def execute_with_rollback(
        cls,
        operations: List[Callable],
        on_failure: Optional[Callable] = None,
        using=None
    ) -> Any:
        """
        Execute a list of operations atomically with automatic rollback.
        
        Args:
            operations: List of callables to execute in order
            on_failure: Optional callback to execute on rollback
            using: Database connection to use
            
        Returns:
            Result of last operation
            
        Raises:
            Exception: If any operation fails, all are rolled back
        """
        savepoint = cls.savepoint(using)
        try:
            results = []
            for op in operations:
                results.append(op())
            cls.savepoint_commit(savepoint, using)
            return results[-1] if results else None
        except Exception as e:
            cls.savepoint_rollback(savepoint, using)
            logger.error(f"Transaction failed, rolled back: {e}")
            if on_failure:
                on_failure()
            raise
    
    @classmethod
    def validate_and_save(cls, instance, clean_kwargs=None):
        """
        Validate model instance and save in one atomic operation.
        
        Args:
            instance: Django model instance
            clean_kwargs: Optional kwargs for full_clean
            
        Raises:
            ValidationError: If validation fails
        """
        with cls.atomic():
            if clean_kwargs is not None:
                instance.full_clean(**clean_kwargs)
            else:
                instance.full_clean()
            instance.save()
            return instance


class RollbackMixin:
    """
    Mixin to provide rollback capability to any class.
    
    Usage:
        class MyService(RollbackMixin):
            def do_operation(self):
                self.savepoint = TransactionService.savepoint()
                try:
                    # operations
                except Exception:
                    self.rollback()
                    raise
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._savepoint = None
    
    @property
    def savepoint(self):
        return self._savepoint
    
    @savepoint.setter
    def savepoint(self, value):
        self._savepoint = value
    
    def begin_nested(self):
        """Begin a nested transaction (savepoint)."""
        self._savepoint = TransactionService.savepoint()
        return self._savepoint
    
    def commit_nested(self):
        """Commit the nested transaction."""
        if self._savepoint:
            TransactionService.savepoint_commit(self._savepoint)
            self._savepoint = None
    
    def rollback(self):
        """Rollback to the savepoint."""
        if self._savepoint:
            TransactionService.savepoint_rollback(self._savepoint)
            self._savepoint = None