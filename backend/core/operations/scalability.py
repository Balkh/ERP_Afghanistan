"""
Database Scalability & Safety Layer.
Query optimization, index recommendations, and performance monitoring.
"""
import logging
import time
from collections import defaultdict
from datetime import datetime
from django.db import connection, reset_queries
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('erp.db_scalability')


class QueryMonitor:
    """Monitor database query performance."""

    _slow_queries = []
    _n_plus_one_warnings = []
    _max_records = 500

    @classmethod
    def record_query(cls, query: str, duration_ms: float, caller: str = ""):
        """Record a query for analysis."""
        if duration_ms > 100:
            cls._slow_queries.append({
                'query': query[:200],
                'duration_ms': round(duration_ms, 2),
                'caller': caller,
                'timestamp': timezone.now().isoformat()
            })
            if len(cls._slow_queries) > cls._max_records:
                cls._slow_queries = cls._slow_queries[-cls._max_records:]

    @classmethod
    def detect_n_plus_one(cls, query: str, count: int):
        """Detect potential N+1 queries."""
        if count > 10:
            cls._n_plus_one_warnings.append({
                'query_pattern': query[:100],
                'execution_count': count,
                'timestamp': timezone.now().isoformat()
            })

    @classmethod
    def get_slow_queries(cls, hours: int = 1, limit: int = 50):
        """Get recent slow queries."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        return [
            q for q in cls._slow_queries
            if datetime.fromisoformat(q['timestamp']) > cutoff
        ][:limit]

    @classmethod
    def get_n_plus_one_warnings(cls, hours: int = 1, limit: int = 20):
        """Get N+1 query warnings."""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=hours)
        return [
            w for w in cls._n_plus_one_warnings
            if datetime.fromisoformat(w['timestamp']) > cutoff
        ][:limit]


class IndexAdvisor:
    """Database index recommendation system."""

    @staticmethod
    def get_recommended_indexes():
        """Get recommended indexes for PostgreSQL migration."""
        return [
            {
                'table': 'accounting_journalentry',
                'columns': ['date', 'is_posted', 'company_id'],
                'reason': 'Date range queries for reports',
                'priority': 'high'
            },
            {
                'table': 'accounting_journalentryline',
                'columns': ['journal_entry_id', 'account_id'],
                'reason': 'Join performance for ledger queries',
                'priority': 'high'
            },
            {
                'table': 'inventory_stockmovement',
                'columns': ['product_id', 'warehouse_id', 'movement_type', 'created_at'],
                'reason': 'Stock history queries',
                'priority': 'high'
            },
            {
                'table': 'inventory_batch',
                'columns': ['product_id', 'warehouse_id', 'expiry_date'],
                'reason': 'FEFO queries and expiry reports',
                'priority': 'high'
            },
            {
                'table': 'sales_salesinvoice',
                'columns': ['customer_id', 'status', 'date', 'company_id'],
                'reason': 'Sales reports and customer history',
                'priority': 'medium'
            },
            {
                'table': 'purchases_purchaseinvoice',
                'columns': ['supplier_id', 'status', 'date', 'company_id'],
                'reason': 'Purchase reports and supplier history',
                'priority': 'medium'
            },
            {
                'table': 'security_notification',
                'columns': ['user_id', 'is_read', 'created_at'],
                'reason': 'User notification queries',
                'priority': 'low'
            },
            {
                'table': 'hr_attendance',
                'columns': ['employee_id', 'date', 'company_id'],
                'reason': 'Attendance reports',
                'priority': 'medium'
            },
        ]

    @staticmethod
    def analyze_current_indexes():
        """Analyze current database indexes."""
        result = {
            'status': 'ok',
            'indexes': [],
            'missing_critical': []
        }

        try:
            with connection.cursor() as cursor:
                if 'sqlite' in connection.settings_dict['ENGINE'].lower():
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                    indexes = cursor.fetchall()
                    result['indexes'] = [idx[0] for idx in indexes]
                elif 'postgresql' in connection.settings_dict['ENGINE'].lower():
                    cursor.execute("""
                        SELECT indexname, tablename 
                        FROM pg_indexes 
                        WHERE schemaname = 'public'
                    """)
                    indexes = cursor.fetchall()
                    result['indexes'] = [{'index': idx[0], 'table': idx[1]} for idx in indexes]
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result


class DatabaseScaler:
    """Database scalability analysis and monitoring."""

    @staticmethod
    def get_record_counts():
        """Get approximate record counts for major tables."""
        from django.apps import apps

        tables = [
            'inventory.Product', 'inventory.Batch', 'inventory.StockMovement',
            'sales.SalesInvoice', 'sales.SalesInvoiceLine',
            'purchases.PurchaseInvoice', 'purchases.PurchaseInvoiceLine',
            'accounting.JournalEntry', 'accounting.JournalEntryLine',
            'hr.Employee', 'hr.Attendance'
        ]

        result = {'tables': {}, 'total_records': 0}

        for model_path in tables:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                count = model.objects.count()
                result['tables'][model_path] = count
                result['total_records'] += count
            except Exception:
                result['tables'][model_path] = 'N/A'

        return result

    @staticmethod
    def estimate_growth(months: int = 6):
        """Estimate growth trajectory."""
        counts = DatabaseScaler.get_record_counts()
        total = counts.get('total_records', 0)

        growth_factors = {
            'conservative': 1.1,
            'moderate': 1.25,
            'aggressive': 1.5
        }

        estimates = {}
        for scenario, factor in growth_factors.items():
            growth_rate = factor ** (months / 12)
            estimates[scenario] = {
                'current': total,
                'projected': int(total * growth_rate),
                'monthly_avg': int(total * (growth_rate - 1) / months)
            }

        return estimates

    @staticmethod
    def get_performance_recommendations():
        """Get performance-related recommendations."""
        recommendations = []

        counts = DatabaseScaler.get_record_counts()
        total = counts.get('total_records', 0)

        if total > 100000:
            recommendations.append({
                'priority': 'high',
                'category': 'scaling',
                'message': f'Database has {total} records - consider PostgreSQL migration',
                'action': 'Plan PostgreSQL migration'
            })

        if total > 50000:
            recommendations.append({
                'priority': 'medium',
                'category': 'indexing',
                'message': 'Add indexes on date and company fields',
                'action': 'Run IndexAdvisor recommendations'
            })

        return recommendations


def run_scalability_audit():
    """Run complete database scalability audit."""
    return {
        'record_counts': DatabaseScaler.get_record_counts(),
        'growth_estimates': DatabaseScaler.estimate_growth(),
        'index_analysis': IndexAdvisor.analyze_current_indexes(),
        'recommended_indexes': IndexAdvisor.get_recommended_indexes(),
        'performance_recommendations': DatabaseScaler.get_performance_recommendations(),
        'slow_queries': QueryMonitor.get_slow_queries(),
        'n_plus_one_warnings': QueryMonitor.get_n_plus_one_warnings()
    }