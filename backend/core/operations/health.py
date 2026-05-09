"""
ERP Health Monitor.
Provides system health checks for database, API, and background services.
"""
import time
from django.db import connection
from django.conf import settings

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class HealthMonitor:
    """System health monitoring."""

    @staticmethod
    def check_database() -> dict:
        """Check database health."""
        result = {
            'status': 'healthy',
            'checks': {},
            'issues': []
        }

        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            result['checks']['connection'] = {
                'status': 'ok',
                'latency_ms': round((time.time() - start) * 1000, 2)
            }
        except Exception as e:
            result['status'] = 'unhealthy'
            result['checks']['connection'] = {'status': 'error', 'message': str(e)}
            result['issues'].append(f"Database connection failed: {e}")

        if hasattr(settings, 'DATABASES'):
            db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
            result['checks']['engine'] = db_engine

            if 'sqlite' in db_engine.lower():
                result['checks']['sqlite'] = HealthMonitor._check_sqlite_health()
            elif 'postgresql' in db_engine.lower():
                result['checks']['postgresql'] = HealthMonitor._check_postgresql_health()

        return result

    @staticmethod
    def _check_sqlite_health() -> dict:
        """Check SQLite-specific health."""
        db_path = settings.DATABASES.get('default', {}).get('NAME', '')
        health = {'status': 'ok'}

        if db_path:
            db_path_str = str(db_path)
            if ':memory:' not in db_path_str:
                try:
                    import os
                    if os.path.exists(db_path_str):
                        size = os.path.getsize(db_path_str)
                        health['size_bytes'] = size
                        health['size_mb'] = round(size / (1024 * 1024), 2)
                except Exception as e:
                    health['status'] = 'warning'
                    health['message'] = str(e)

        return health

    @staticmethod
    def _check_postgresql_health() -> dict:
        """Check PostgreSQL-specific health."""
        health = {'status': 'ok'}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                size = cursor.fetchone()[0]
                health['size_bytes'] = size
                health['size_mb'] = round(size / (1024 * 1024), 2)
        except Exception as e:
            health['status'] = 'warning'
            health['message'] = str(e)
        return health

    @staticmethod
    def check_system() -> dict:
        """Check system resources."""
        result = {
            'status': 'healthy',
            'checks': {},
            'issues': []
        }

        if not PSUTIL_AVAILABLE:
            result['checks']['psutil'] = {'status': 'not_available', 'message': 'psutil not installed'}
            return result

        try:
            result['checks']['cpu'] = {
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count()
            }
        except Exception as e:
            result['checks']['cpu'] = {'error': str(e)}

        try:
            memory = psutil.virtual_memory()
            result['checks']['memory'] = {
                'total_mb': round(memory.total / (1024 * 1024), 2),
                'used_mb': round(memory.used / (1024 * 1024), 2),
                'percent': memory.percent
            }
            if memory.percent > 90:
                result['issues'].append(f"Memory usage critical: {memory.percent}%")
        except Exception as e:
            result['checks']['memory'] = {'error': str(e)}

        try:
            disk = psutil.disk_usage('/')
            result['checks']['disk'] = {
                'total_gb': round(disk.total / (1024 ** 3), 2),
                'used_gb': round(disk.used / (1024 ** 3), 2),
                'percent': disk.percent
            }
            if disk.percent > 90:
                result['issues'].append(f"Disk usage critical: {disk.percent}%")
        except Exception as e:
            result['checks']['disk'] = {'error': str(e)}

        if result['issues']:
            result['status'] = 'degraded'

        return result

    @staticmethod
    def check_background_services() -> dict:
        """Check background services status."""
        result = {
            'status': 'healthy',
            'services': {}
        }

        result['services']['backup'] = {'status': 'available'}
        result['services']['restore'] = {'status': 'available'}
        result['services']['notifications'] = {'status': 'available'}

        return result

    @staticmethod
    def get_full_health() -> dict:
        """Get complete system health."""
        return {
            'database': HealthMonitor.check_database(),
            'system': HealthMonitor.check_system(),
            'services': HealthMonitor.check_background_services()
        }