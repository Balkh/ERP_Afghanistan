import logging
import os
import sys
import time
import uuid
import threading
from decimal import Decimal
from datetime import date, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

"""SECTION: PostgreSQL Migration Foundation — extracted from migration_validator.py
Behavior-preserving extraction. Original method body lifted byte-for-byte;
only the indent level is changed (method body → function body).
"""
from production_infrastructure.migration_validator import (
    InfraIssue, SectionResult, CRITICAL, HIGH, MEDIUM, LOW, logger,
)


def run(self) -> SectionResult:
    issues: List[InfraIssue] = []
    try:
        from core.infrastructure.database import (
            detect_database_engine, database_connection_health,
            check_migration_health, check_postgresql_config,
        )

        engine = detect_database_engine()
        issues.append(InfraIssue(
            section="postgresql_migration", severity=LOW,
            check="engine", detail=f"Active engine: {engine}", passed=True,
        ))

        health = database_connection_health()
        if health["connected"]:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="connection", detail=f"Connected, latency={health['latency_ms']}ms", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=CRITICAL,
                check="connection", detail=f"DB connection failed: {health['error']}",
            ))

        migrate_health = check_migration_health()
        if migrate_health["all_applied"]:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="migrations", detail="All migrations applied", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=HIGH,
                check="migrations",
                detail=f"{migrate_health['count']} unapplied migrations: {migrate_health['unapplied']}",
            ))

        pg_config = check_postgresql_config()
        if engine == "postgresql":
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="server_version", detail=f"PostgreSQL {pg_config.get('server_version')}", passed=True,
            ))
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="isolation", detail=f"Isolation: {pg_config.get('isolation_level')}", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=MEDIUM,
                check="postgresql_not_active",
                detail="PostgreSQL not active. Set DATABASE_URL env var for PostgreSQL.",
            ))

        try:
            import psycopg2
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="psycopg2", detail=f"psycopg2 {psycopg2.__version__} available", passed=True,
            ))
        except ImportError:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=HIGH,
                check="psycopg2", detail="psycopg2 not installed. Required for PostgreSQL.",
            ))

        from django.conf import settings
        has_database_url = bool(os.environ.get("DATABASE_URL"))
        if has_database_url:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="database_url", detail="DATABASE_URL environment variable set", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=MEDIUM,
                check="database_url",
                detail="DATABASE_URL not set. PostgreSQL will not activate.",
            ))

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="sql_execution", detail="SQL execution confirmed", passed=True,
            ))
        except Exception as e:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=HIGH,
                check="sql_execution", detail=f"SQL execution failed: {e}",
            ))

        from django.conf import settings as s
        use_tz = getattr(s, "USE_TZ", False)
        tz = getattr(s, "TIME_ZONE", "UTC")
        if use_tz:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="timezone", detail=f"USE_TZ=True, TIME_ZONE={tz}", passed=True,
            ))
        else:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=HIGH,
                check="timezone", detail="USE_TZ=False — timezone-naive timestamps risk",
            ))

        try:
            from decimal import Decimal
            from django.db import connection as conn2
            with conn2.cursor() as cur:
                cur.execute("SELECT CAST(1 AS DECIMAL(10,2))" if engine == "postgresql" else "SELECT 1.00")
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="decimal_precision", detail="Decimal precision verified", passed=True,
            ))
        except Exception:
            issues.append(InfraIssue(
                section="postgresql_migration", severity=LOW,
                check="decimal_precision", detail="Decimal check skipped (SQLite)", passed=True,
            ))

    except Exception as e:
        issues.append(InfraIssue(
            section="postgresql_migration", severity=CRITICAL,
            check="validator_crash", detail=f"PostgreSQL validation crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (CRITICAL, HIGH)]) == 0
    self.results["postgresql_migration"] = SectionResult(
        name="PostgreSQL Migration Foundation", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues",
    )
    self.issues.extend(issues)
    return self.results["postgresql_migration"]
