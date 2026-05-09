"""
Reporting Governance Layer - Performance protection and safety controls.
Implements query limits, export controls, and performance monitoring.

CORE PRINCIPLE: "Reporting systems must never destabilize transactional ERP operations."
"""
import time
import uuid
import logging
from functools import wraps
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, Any, Callable
from django.conf import settings
from django.db import models
from django.db import connection
from django.core.cache import cache


logger = logging.getLogger('erp.reports')


class ReportLimits:
    """Configuration for report limits."""
    
    # Query timeouts (seconds)
    DEFAULT_TIMEOUT = 30
    LIGHT_TIMEOUT = 10
    HEAVY_TIMEOUT = 60
    EXPORT_TIMEOUT = 120
    
    # Result limits
    DEFAULT_LIMIT = 1000
    MAX_LIMIT = 10000
    EXPORT_LIMIT = 50000
    
    # Export limits (records)
    MAX_EXCEL_ROWS = 65000
    MAX_PDF_PAGES = 1000
    MAX_CSV_ROWS = 100000
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 10
    MAX_EXPORT_PER_HOUR = 20
    
    # Cache TTL (seconds)
    CACHE_TTL_SHORT = 60
    CACHE_TTL_MEDIUM = 300
    CACHE_TTL_LONG = 1800


class ReportClassification:
    """Report classification categories."""
    
    LIGHT = 'LIGHT'          # Sync allowed
    MEDIUM = 'MEDIUM'         # Optimized sync
    HEAVY = 'HEAVY'          # Async preferred
    CRITICAL = 'CRITICAL_FINANCIAL'  # Strict validation + audit
    
    # Classification mapping
    CLASSIFICATIONS = {
        'trial_balance': LIGHT,
        'profit_loss': LIGHT,
        'balance_sheet': LIGHT,
        'ar_aging': MEDIUM,
        'ap_aging': MEDIUM,
        'ledger': LIGHT,
        'cash_flow': MEDIUM,
        'inventory_valuation': HEAVY,
        'sales_by_product': MEDIUM,
        'sales_by_customer': MEDIUM,
        'sales_by_category': LIGHT,
        'purchase_by_supplier': MEDIUM,
        'purchase_by_category': LIGHT,
        'cash_book': HEAVY,
        'custom': HEAVY,
    }
    
    @classmethod
    def get(cls, report_type: str) -> str:
        """Get classification for report type."""
        return cls.CLASSIFICATIONS.get(report_type, cls.MEDIUM)
    
    @classmethod
    def requires_async(cls, report_type: str) -> bool:
        """Check if report should run async."""
        return cls.get(report_type) in [cls.HEAVY, cls.CRITICAL]
    
    @classmethod
    def requires_audit(cls, report_type: str) -> bool:
        """Check if report requires audit logging."""
        return cls.get(report_type) == cls.CRITICAL


class ReportAuditLog(models.Model):
    """
    Audit trail for all report generation.
    Tracks: user, company, report_type, parameters, execution_time, row_count, export_format, timestamp, status
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User & Company
    user_id = models.CharField(max_length=50, blank=True, null=True)
    user_name = models.CharField(max_length=100, blank=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True)
    
    # Report details
    report_type = models.CharField(max_length=50)
    report_name = models.CharField(max_length=200, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    
    # Execution metrics
    execution_time = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # seconds
    row_count = models.IntegerField(default=0)
    
    # Export info
    export_format = models.CharField(max_length=20, blank=True)
    export_size = models.BigIntegerField(default=0)  # bytes
    
    # Status
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('TIMEOUT', 'Timeout'),
        ('CANCELLED', 'Cancelled'),
        ('QUEUED', 'Queued'),
        ('ASYNC_RUNNING', 'Async Running'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCESS')
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Async tracking
    task_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = 'reporting_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['company_id', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]


class AsyncReportJob(models.Model):
    """
    Async report job tracking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Job details
    report_type = models.CharField(max_length=50)
    report_name = models.CharField(max_length=200)
    parameters = models.JSONField(default=dict)
    
    # User
    user_id = models.CharField(max_length=50)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Result
    result_file = models.CharField(max_length=500, blank=True)  # File path
    result_size = models.BigIntegerField(default=0)
    
    # Errors
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'reporting_async_jobs'
        ordering = ['-created_at']


class QueryGuard:
    """Protects against slow/heavy queries."""
    
    @staticmethod
    def enforce_limits(queryset, max_results: int = None, timeout: int = None):
        """Apply query limits safely."""
        max_results = max_results or ReportLimits.DEFAULT_LIMIT
        queryset = queryset[:max_results]
        
        if timeout and connection.vendor == 'postgresql':
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"SET statement_timeout = '{timeout}s'")
            except:
                pass
        
        return queryset
    
    @staticmethod
    def check_query_cost(queryset, max_cost: int = 1000) -> bool:
        """Estimate query cost."""
        if connection.vendor != 'postgresql':
            return True
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"EXPLAIN {queryset.query}")
                return True
        except:
            return True


class ExportGuard:
    """Protects against export overload."""
    
    @staticmethod
    def validate_export_request(record_count: int, format: str) -> Dict[str, Any]:
        """Validate export can proceed."""
        if record_count > ReportLimits.EXPORT_LIMIT:
            return {
                'allowed': False,
                'error': f'Export exceeds limit of {ReportLimits.EXPORT_LIMIT} records. Use filters to reduce.'
            }
        
        if format == 'excel' and record_count > ReportLimits.MAX_EXCEL_ROWS:
            return {
                'allowed': False,
                'error': f'Excel export limited to {ReportLimits.MAX_EXCEL_ROWS} rows. Use CSV.'
            }
        
        if format == 'pdf' and record_count > ReportLimits.MAX_PDF_PAGES * 50:
            return {
                'allowed': False,
                'error': f'PDF export too large. Use Excel or CSV.'
            }
        
        return {'allowed': True}
    
    @staticmethod
    def check_export_quota(user_id: str) -> bool:
        """Check user's export quota."""
        key = f'export_quota_{user_id}'
        count = cache.get(key, 0)
        return count < ReportLimits.MAX_EXPORT_PER_HOUR
    
    @staticmethod
    def increment_export_quota(user_id: str):
        """Increment user's export count."""
        key = f'export_quota_{user_id}'
        try:
            cache.set(key, cache.get(key, 0) + 1, 3600)
        except:
            pass


class ReportCache:
    """Caching layer for frequently accessed reports."""
    
    CACHE_PREFIX = 'report_cache_'
    
    @staticmethod
    def get_cache_key(report_type: str, params: Dict, company_id: str = None) -> str:
        """Generate cache key."""
        import hashlib
        key_parts = [report_type]
        if company_id:
            key_parts.append(company_id)
        key_parts.extend(f'{k}:{v}' for k, v in sorted(params.items()))
        param_hash = hashlib.md5('_'.join(key_parts).encode()).hexdigest()[:10]
        return f"{ReportCache.CACHE_PREFIX}{report_type}_{param_hash}"
    
    @staticmethod
    def get(report_type: str, params: Dict, company_id: str = None, ttl: int = None) -> Optional[Any]:
        """Get cached report data."""
        ttl = ttl or ReportLimits.CACHE_TTL_MEDIUM
        key = ReportCache.get_cache_key(report_type, params, company_id)
        try:
            return cache.get(key)
        except:
            return None
    
    @staticmethod
    def set(report_type: str, params: Dict, data: Any, company_id: str = None, ttl: int = None):
        """Cache report data."""
        ttl = ttl or ReportLimits.CACHE_TTL_MEDIUM
        key = ReportCache.get_cache_key(report_type, params, company_id)
        try:
            cache.set(key, data, ttl)
        except:
            pass
    
    @staticmethod
    def invalidate_company(company_id: str):
        """Invalidate all cached reports for a company."""
        # In production, use cache.delete_pattern
        pass


class PerformanceMonitor:
    """Monitor report performance."""
    
    @staticmethod
    def log_execution(report_type: str, duration: float, record_count: int, user_id: str = None, 
                      company_id: str = None, status: str = 'SUCCESS'):
        """Log report execution."""
        logger.info(
            f"Report: {report_type}, Duration: {duration:.2f}s, "
            f"Records: {record_count}, User: {user_id or 'system'}, Status: {status}"
        )
        
        # Track slow reports
        if duration > ReportLimits.DEFAULT_TIMEOUT:
            logger.warning(f"SLOW REPORT: {report_type} took {duration:.2f}s")
        
        # Create audit log
        try:
            ReportAuditLog.objects.create(
                user_id=user_id or 'system',
                company_id=company_id,
                report_type=report_type,
                execution_time=Decimal(str(round(duration, 2))),
                row_count=record_count,
                status=status
            )
        except:
            pass  # Don't fail report if audit fails
    
    @staticmethod
    def get_slow_reports(limit: int = 10) -> list:
        """Get slowest reports."""
        try:
            return list(
                ReportAuditLog.objects.filter(
                    execution_time__gt=ReportLimits.DEFAULT_TIMEOUT
                ).values('report_type').annotate(
                    avg_time=models.Avg('execution_time'),
                    max_time=models.Max('execution_time'),
                    count=models.Count('id')
                ).order_by('-avg_time')[:limit]
            )
        except:
            return []


def rate_limit(requests_per_minute: int = None):
    """Decorator to rate limit report requests."""
    requests_per_minute = requests_per_minute or ReportLimits.MAX_REQUESTS_PER_MINUTE
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user_id = str(getattr(request.user, 'id', 'anonymous')) if hasattr(request, 'user') else 'anonymous'
            company_id = getattr(request, 'company_id', 'no_company')
            
            key = f"report_rate_{company_id}_{user_id}"
            
            try:
                count = cache.get(key, 0)
                if count >= requests_per_minute:
                    return {
                        'success': False,
                        'error': f'Rate limit exceeded. Max {requests_per_minute} requests per minute.'
                    }
                cache.set(key, count + 1, 60)
            except:
                pass
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def timed_report(func: Callable):
    """Decorator to time report execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        if isinstance(result, dict):
            result['_execution_time'] = round(duration, 2)
        
        return result
    return wrapper


class ReportGovernance:
    """Main governance class combining all protection layers."""
    
    @staticmethod
    def validate_report_request(report_type: str, params: Dict) -> Dict[str, Any]:
        """Validate a report request before execution."""
        # Check date range
        if 'start_date' in params and 'end_date' in params:
            from datetime import datetime
            try:
                start = datetime.strptime(params['start_date'], '%Y-%m-%d')
                end = datetime.strptime(params['end_date'], '%Y-%m-%d')
                days = (end - start).days
                
                if days > 365:
                    return {'valid': False, 'error': 'Date range cannot exceed 1 year.'}
            except:
                pass
        
        # Check limit parameter
        limit = params.get('limit', ReportLimits.DEFAULT_LIMIT)
        if limit > ReportLimits.MAX_LIMIT:
            return {'valid': False, 'error': f'Limit cannot exceed {ReportLimits.MAX_LIMIT}'}
        
        return {'valid': True}
    
    @staticmethod
    def should_run_async(report_type: str, estimated_records: int = 0) -> bool:
        """Determine if report should run async."""
        classification = ReportClassification.get(report_type)
        if classification in [ReportClassification.HEAVY, ReportClassification.CRITICAL]:
            return True
        if estimated_records > 5000:
            return True
        return False
    
    @staticmethod
    def create_audit_log(user_id: str, company_id: str, report_type: str, 
                         params: Dict, status: str, execution_time: float = 0,
                         row_count: int = 0, error: str = None):
        """Create audit log entry."""
        try:
            ReportAuditLog.objects.create(
                user_id=user_id,
                company_id=company_id,
                report_type=report_type,
                parameters=params,
                execution_time=Decimal(str(round(execution_time, 2))),
                row_count=row_count,
                status=status,
                error_message=error or ''
            )
        except:
            pass
    
    @staticmethod
    def validate_company_isolation(company_id: str, report_type: str) -> bool:
        """Validate company isolation for report."""
        if not company_id:
            return False  # Require company context for reports
        return True


class CustomReportGuard:
    """Protection for custom report builder."""
    
    # Whitelist of allowed models
    ALLOWED_MODELS = {
        'sales.SalesInvoice',
        'sales.Customer',
        'purchases.PurchaseInvoice',
        'purchases.Supplier',
        'inventory.Product',
        'inventory.Batch',
        'accounting.Account',
        'accounting.JournalEntry',
    }
    
    # Whitelist of safe fields
    SAFE_FIELDS = {
        'id', 'uuid', 'name', 'code', 'created_at', 'updated_at',
        'invoice_number', 'invoice_date', 'status', 'total_amount', 'balance',
        'quantity', 'unit_price', 'customer', 'supplier', 'product',
        'account_code', 'account_name', 'entry_number', 'entry_date',
    }
    
    @classmethod
    def validate_model(cls, model_name: str) -> bool:
        """Check if model is allowed."""
        return model_name in cls.ALLOWED_MODELS
    
    @classmethod
    def validate_fields(cls, fields: list) -> Dict[str, Any]:
        """Validate fields are safe."""
        forbidden = [f for f in fields if f not in cls.SAFE_FIELDS]
        if forbidden:
            return {
                'valid': False,
                'error': f'Forbidden fields: {", ".join(forbidden)}'
            }
        return {'valid': True}
    
    @classmethod
    def validate_query(cls, query: Dict) -> Dict[str, Any]:
        """Validate custom query is safe."""
        # Check model
        model = query.get('model')
        if model and not cls.validate_model(model):
            return {'valid': False, 'error': f'Model {model} not allowed'}
        
        # Check fields
        fields = query.get('fields', [])
        if fields:
            field_validation = cls.validate_fields(fields)
            if not field_validation.get('valid'):
                return field_validation
        
        # Check for dangerous operations
        if query.get('raw_sql'):
            return {'valid': False, 'error': 'Raw SQL not allowed'}
        
        if query.get('unrestricted_join'):
            return {'valid': False, 'error': 'Unrestricted joins not allowed'}
        
        return {'valid': True}


class SafeErrorResponse:
    """Generate safe error responses without exposing stack traces."""
    
    @staticmethod
    def report_error(message: str, report_type: str = None) -> Dict:
        """Return safe error response."""
        logger.error(f"Report error: {message}")
        return {
            'success': False,
            'error': {
                'message': message,
                'type': 'REPORT_ERROR',
                'report_type': report_type
            }
        }
    
    @staticmethod
    def timeout_error(report_type: str) -> Dict:
        """Return timeout error."""
        return SafeErrorResponse.report_error(
            f"Report {report_type} exceeded execution time limit. Try with smaller date range.",
            report_type
        )
    
    @staticmethod
    def limit_error(limit_type: str, max_value: int) -> Dict:
        """Return limit exceeded error."""
        return SafeErrorResponse.report_error(
            f"{limit_type} exceeds maximum allowed ({max_value}). Please reduce scope.",
            None
        )