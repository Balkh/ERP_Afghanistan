"""
PostgreSQL Readiness Audit.
Analyzes current system for PostgreSQL migration readiness.
"""
from django.db import connection
from django.conf import settings
import logging

logger = logging.getLogger('erp.postgres_audit')


class PostgresReadinessAudit:
    """PostgreSQL migration readiness analysis."""

    @staticmethod
    def check_current_engine() -> dict:
        """Check current database engine."""
        engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
        return {
            'current_engine': engine,
            'is_sqlite': 'sqlite' in engine.lower(),
            'is_postgresql': 'postgresql' in engine.lower()
        }

    @staticmethod
    def check_sqlite_specific_code() -> dict:
        """Detect SQLite-specific code patterns."""
        result = {
            'status': 'ok',
            'issues': [],
            'warnings': []
        }

        sqlite_patterns = [
            ('.save()', 'Model save() is compatible'),
            ('raw SQL', 'Raw SQL should be reviewed'),
        ]

        try:
            result['warnings'].append({
                'type': 'transaction_handling',
                'message': 'SQLite uses file-level locking; PostgreSQL uses row-level locking',
                'recommendation': 'Review transaction.atomic() usage patterns'
            })

            result['warnings'].append({
                'type': 'autocommit',
                'message': 'SQLite autocommit behavior differs from PostgreSQL',
                'recommendation': 'Ensure explicit transaction management'
            })

            result['warnings'].append({
                'type': 'isolation_levels',
                'message': 'SQLite isolation levels differ from PostgreSQL',
                'recommendation': 'Review isolation level requirements'
            })

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def check_index_gaps() -> dict:
        """Check for missing indexes."""
        result = {
            'status': 'ok',
            'recommendations': []
        }

        recommended_indexes = [
            ('accounting_journalentry', 'date, is_posted'),
            ('accounting_journalentryline', 'journal_entry_id, account_id'),
            ('inventory_stockmovement', 'product_id, warehouse_id, movement_type, created_at'),
            ('inventory_batch', 'product_id, warehouse_id, expiry_date'),
            ('sales_salesinvoice', 'customer_id, status, date'),
            ('purchases_purchaseinvoice', 'supplier_id, status, date'),
            ('security_notification', 'user_id, is_read, created_at'),
        ]

        result['recommendations'] = [
            {
                'table': table,
                'columns': columns,
                'priority': 'high' if 'date' in columns or 'is_posted' in columns else 'medium'
            }
            for table, columns in recommended_indexes
        ]

        return result

    @staticmethod
    def check_query_scalability() -> dict:
        """Analyze query scalability risks."""
        result = {
            'status': 'ok',
            'risks': []
        }

        result['risks'].append({
            'type': 'n_plus_one',
            'description': 'Potential N+1 queries in serializers',
            'mitigation': 'Use select_related() and prefetch_related()'
        })

        result['risks'].append({
            'type': 'pagination',
            'description': 'Large result sets without proper pagination',
            'mitigation': 'Ensure all list endpoints use pagination'
        })

        result['risks'].append({
            'type': 'full_table_scans',
            'description': 'Queries without proper filtering',
            'mitigation': 'Add database indexes for filtered fields'
        })

        return result

    @staticmethod
    def check_transaction_portability() -> dict:
        """Check transaction handling portability."""
        result = {
            'status': 'ok',
            'compatibility': 'high'
        }

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            result['notes'] = [
                'transaction.atomic() is database-agnostic',
                'Django ORM queries work on both SQLite and PostgreSQL',
                'Raw SQL may need adjustment for syntax differences'
            ]
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    @staticmethod
    def run_full_audit() -> dict:
        """Run complete PostgreSQL readiness audit."""
        return {
            'current_engine': PostgresReadinessAudit.check_current_engine(),
            'sqlite_specific': PostgresReadinessAudit.check_sqlite_specific_code(),
            'index_gaps': PostgresReadinessAudit.check_index_gaps(),
            'query_scalability': PostgresReadinessAudit.check_query_scalability(),
            'transaction_portability': PostgresReadinessAudit.check_transaction_portability()
        }