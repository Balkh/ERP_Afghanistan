"""
SECTION 8: FINAL HARDENING AUDIT REPORT
Extracted from PreProductionHardeningValidator.generate_audit_report

The return schema is the contract: this function is consumed by Phase 5.x
test harnesses. The return value MUST be byte-identical to pre-refactor.
"""
from pre_production_hardening.hardening_validator import (
    SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> dict:
    sections = [
        "database_hardening", "multi_user_validation",
        "operator_resilience", "session_security",
        "export_reliability", "deployment_recovery",
        "performance_validation",
    ]

    critical = [i for i in validator.issues if i.severity == ISSUE_CRITICAL]
    high = [i for i in validator.issues if i.severity == ISSUE_HIGH]
    medium = [i for i in validator.issues if i.severity == ISSUE_MEDIUM]
    low = [i for i in validator.issues if i.severity == ISSUE_LOW]

    total_crit = len(critical)
    total_high = len(high)
    total_medium = len(medium)
    total_low = len(low)

    score = 100
    score -= total_crit * 25
    score -= total_high * 10
    score -= total_medium * 3
    score -= total_low * 0
    score = max(0, min(100, score))

    section_results = {
        name: "PASS" if validator.results.get(name, SectionResult(name, False)).passed else "FAIL"
        for name in sections
    }

    blocked = total_crit > 0 or any(
        not validator.results.get(name, SectionResult(name, False)).passed
        for name in sections
    )

    remaining_risks = []
    for i in critical:
        remaining_risks.append(f"CRITICAL [{i.section}] {i.check}: {i.detail}")
    for i in high:
        remaining_risks.append(f"HIGH [{i.section}] {i.check}: {i.detail}")

    production_topology = {
        "database": "PostgreSQL 15+",
        "redis": "Recommended for session caching + rate limiting",
        "web_server": "Gunicorn + Nginx (4-8 workers)",
        "static_files": "WhiteNoise or CDN",
        "backup": "pg_dump daily + WAL archiving",
        "monitoring": "Django health check endpoint + DB monitoring",
    }

    backup_frequency = "Daily full backup (pg_dump) + continuous WAL archiving"
    pg_migration_readiness = (
        "READY with config: Set DATABASE_URL env var to PostgreSQL DSN. "
        "Review ATOMIC_REQUESTS=True and CONN_MAX_AGE=60 in production settings."
    )
    user_capacity = (
        "Estimated 50-100 concurrent users with default SQLite (single-writer). "
        "PostgreSQL enables 200-500+ concurrent users with connection pooling."
    )

    report = {
        "section_results": section_results,
        "critical": total_crit,
        "high": total_high,
        "medium": total_medium,
        "low": total_low,
        "production_readiness_score": score,
        "final_verdict": "DEPLOYMENT_READY" if not blocked else "DEPLOYMENT_BLOCKED",
        "remaining_risks": remaining_risks,
        "production_topology": production_topology,
        "backup_frequency_recommendation": backup_frequency,
        "postgresql_migration_readiness": pg_migration_readiness,
        "user_capacity_estimation": user_capacity,
        "recommended_topology": [
            "PostgreSQL 15+ with connection pooling (PgBouncer)",
            "Gunicorn with 4-8 workers behind Nginx reverse proxy",
            "Redis for session cache and rate limiting persistence",
            "Daily pg_dump + continuous WAL archiving for PITR",
            "Health-check monitoring endpoint at /api/health/",
            "Separate read-replica for heavy reporting queries",
        ],
    }

    validator.report = report
    return report
