"""
SECTION 1: DATABASE HARDENING
Extracted from PreProductionHardeningValidator.validate_database_hardening
"""
from pre_production_hardening.hardening_validator import (
    HardeningIssue, SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> SectionResult:
    issues: list = []
    try:
        from django.conf import settings

        db_engine = settings.DATABASES["default"]["ENGINE"]
        db_name = settings.DATABASES["default"].get("NAME", "")

        if "sqlite" in db_engine:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_MEDIUM,
                check="engine",
                detail=f"Database engine is SQLite ({db_engine}). PostgreSQL required for production.",
                evidence={"engine": db_engine},
            ))
        else:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_LOW,
                check="engine", detail=f"Database engine: {db_engine}", passed=True,
            ))

        atomic = getattr(settings, "ATOMIC_REQUESTS", False)
        if not atomic:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_MEDIUM,
                check="atomic_requests",
                detail="ATOMIC_REQUESTS is not enabled. Each view may leave partial transactions on error.",
            ))
        else:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_LOW,
                check="atomic_requests", detail="ATOMIC_REQUESTS is enabled", passed=True,
            ))

        conn_max_age = settings.DATABASES["default"].get("CONN_MAX_AGE", 0)
        if conn_max_age == 0:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_MEDIUM,
                check="connection_pooling",
                detail="CONN_MAX_AGE=0: new database connection per request. Set to 60-600 for production.",
            ))
        else:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_LOW,
                check="connection_pooling", detail=f"CONN_MAX_AGE={conn_max_age}s", passed=True,
            ))

        use_tz = getattr(settings, "USE_TZ", False)
        tz = getattr(settings, "TIME_ZONE", "not set")
        if not use_tz:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_HIGH,
                check="timezone_awareness",
                detail="USE_TZ=False: timestamps stored without timezone. Data corruption risk.",
            ))
        else:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_LOW,
                check="timezone_awareness",
                detail=f"USE_TZ=True, TIME_ZONE={tz}", passed=True,
            ))

        if "postgresql" in db_engine or "postgis" in db_engine:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_LOW,
                check="isolation_level",
                detail="PostgreSQL default isolation: READ_COMMITTED. Suitable for production.",
                passed=True,
            ))

        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    issues.append(HardeningIssue(
                        section="database_hardening", severity=ISSUE_LOW,
                        check="connection_alive", detail="Database connection verified", passed=True,
                    ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_HIGH,
                check="connection_alive", detail=f"Database connection failed: {e}",
            ))

        try:
            from django.db import transaction, connection
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_LOW,
                check="transaction_isolation", detail="Transaction atomic block works", passed=True,
            ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="database_hardening", severity=ISSUE_HIGH,
                check="transaction_isolation", detail=f"Atomic transaction failed: {e}",
            ))

    except Exception as e:
        issues.append(HardeningIssue(
            section="database_hardening", severity=ISSUE_CRITICAL,
            check="hardening_crash", detail=f"Database hardening crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    validator.results["database_hardening"] = SectionResult(
        name="Database Hardening", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues found",
    )
    validator.issues.extend(issues)
    return validator.results["database_hardening"]
