"""
Database infrastructure utilities.
PostgreSQL migration support, connection health checks, migration verification.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger("erp.infrastructure.database")


def detect_database_engine() -> str:
    """Return the active database engine name: 'postgresql', 'sqlite', or 'unknown'."""
    try:
        from django.conf import settings
        engine = settings.DATABASES["default"]["ENGINE"]
        if "postgresql" in engine or "postgis" in engine:
            return "postgresql"
        elif "sqlite" in engine:
            return "sqlite"
        elif "mysql" in engine:
            return "mysql"
        return "unknown"
    except Exception:
        return "unknown"


def is_postgresql() -> bool:
    """Check if the active database engine is PostgreSQL."""
    return detect_database_engine() == "postgresql"


def database_connection_health() -> dict:
    """Run basic database health checks."""
    result = {
        "connected": False,
        "engine": detect_database_engine(),
        "latency_ms": None,
        "error": None,
    }
    try:
        import time
        from django.db import connection
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        result["connected"] = row is not None and row[0] == 1
        result["latency_ms"] = round((time.time() - start) * 1000, 2)
    except Exception as e:
        result["error"] = str(e)
    return result


def check_migration_health() -> dict:
    """Verify all migrations are applied."""
    result = {"all_applied": False, "unapplied": [], "count": 0}
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        executor = MigrationExecutor(connections["default"])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        unapplied = [(m[0].app_label, m[0].name) for m in plan]
        result["all_applied"] = len(unapplied) == 0
        result["unapplied"] = [f"{app}.{name}" for app, name in unapplied]
        result["count"] = len(unapplied)
    except Exception as e:
        result["error"] = str(e)
    return result


def check_postgresql_config() -> dict:
    """Validate PostgreSQL-specific configuration when running on PostgreSQL."""
    result = {
        "connection_pooling": False,
        "atomic_requests": False,
        "timezone_aware": False,
        "isolation_level": None,
        "server_version": None,
    }
    try:
        from django.conf import settings
        db_config = settings.DATABASES["default"]
        result["connection_pooling"] = db_config.get("CONN_MAX_AGE", 0) > 0
        result["atomic_requests"] = db_config.get("ATOMIC_REQUESTS", False)

        from django.conf import settings as s
        result["timezone_aware"] = getattr(s, "USE_TZ", False)

        if is_postgresql():
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SHOW server_version")
                result["server_version"] = cursor.fetchone()[0]
                cursor.execute("SHOW transaction_isolation")
                result["isolation_level"] = cursor.fetchone()[0]
    except Exception as e:
        result["error"] = str(e)
    return result
