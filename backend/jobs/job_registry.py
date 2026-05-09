"""
Job Registry
Central registry of all background job types with handlers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class BaseJobHandler(ABC):
    """Base class for job handlers"""
    
    @property
    @abstractmethod
    def job_type(self) -> str:
        """Return the job type identifier"""
        pass
    
    @abstractmethod
    def execute(self, job: 'BackgroundJob', payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the job with given payload"""
        pass
    
    def pre_execute(self, job: 'BackgroundJob', payload: Dict[str, Any]) -> bool:
        """Pre-execution validation. Return False to abort."""
        return True
    
    def post_execute(self, job: 'BackgroundJob', result: Dict[str, Any]) -> None:
        """Post-execution hook"""
        pass
    
    def on_failure(self, job: 'BackgroundJob', error: Exception) -> None:
        """Failure handler"""
        pass
    
    def get_idempotency_key(self, payload: Dict[str, Any]) -> Optional[str]:
        """Return idempotency key for this job to prevent duplicate execution"""
        return None


class JobRegistry:
    """
    Central registry for all job types.
    Provides job discovery, execution, and management.
    """
    _handlers: Dict[str, BaseJobHandler] = {}
    _jobs: Dict[str, type] = {}
    
    @classmethod
    def register(cls, job_type: str, handler: BaseJobHandler):
        """Register a job handler"""
        cls._handlers[job_type] = handler
        logger.info(f"Registered job handler: {job_type}")
    
    @classmethod
    def get_handler(cls, job_type: str) -> Optional[BaseJobHandler]:
        """Get handler for job type"""
        return cls._handlers.get(job_type)
    
    @classmethod
    def get_all_job_types(cls) -> list:
        """Get list of all registered job types"""
        return list(cls._handlers.keys())
    
    @classmethod
    def execute_job(cls, job: 'BackgroundJob') -> Dict[str, Any]:
        """Execute a job using its registered handler"""
        handler = cls.get_handler(job.job_type)
        
        if not handler:
            raise ValueError(f"No handler registered for job type: {job.job_type}")
        
        # Pre-execution check
        if not handler.pre_execute(job, job.payload):
            job.fail("Pre-execution validation failed")
            return {'success': False, 'error': 'Pre-execution validation failed'}
        
        # Execute
        try:
            result = handler.execute(job, job.payload)
            return {'success': True, 'result': result}
        except Exception as e:
            logger.exception(f"Job execution failed: {job.id}")
            handler.on_failure(job, e)
            raise


# Import and register built-in job handlers
# These will be imported after models are ready


def register_builtin_jobs():
    """Register all built-in job handlers"""
    from jobs.handlers import (
        ReportGenerationHandler,
        ExportGenerationHandler,
        FinancialReconciliationHandler,
        AnomalyScanHandler,
        InventoryExpiryScanHandler,
        NotificationDispatchHandler,
        CleanupTaskHandler,
        OverdueScanHandler,
    )
    
    handlers = [
        ReportGenerationHandler(),
        ExportGenerationHandler(),
        FinancialReconciliationHandler(),
        AnomalyScanHandler(),
        InventoryExpiryScanHandler(),
        NotificationDispatchHandler(),
        CleanupTaskHandler(),
        OverdueScanHandler(),
    ]
    
    for handler in handlers:
        JobRegistry.register(handler.job_type, handler)


# Auto-register on import
register_builtin_jobs()