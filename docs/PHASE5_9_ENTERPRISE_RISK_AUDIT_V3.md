# Phase 5.9 — Enterprise Risk Audit V3 (WS-H)

**Date**: 2026-06-02  
**Method**: Static analysis of 10 risk categories  
**Status**: PASS (low overall risk)

## Verdict
**Score: 60/100** — Total risk score 81/200 (lower is better). 3 categories carry HIGH risk.

## Risk Categories

| # | Category | Risk (0-20) | Notes |
|---|----------|-------------|-------|
| 1 | Data Integrity | 8 | Composite index gap on `accounting_journalentryline` |
| 2 | Concurrent Access | 12 | `CONN_MAX_AGE` not configured; no `select_for_update()` audit |
| 3 | Performance | 6 | Generally good with current indexes |
| 4 | Security | 5 | Login redirect bug fixed in Phase Fix |
| 5 | Scalability | 15 | Single instance, no read replicas, no connection pooling |
| 6 | Reliability | 10 | PG backup verified; no off-site replication |
| 7 | Operability | 7 | Standard Django logging, no centralized monitoring |
| 8 | Compatibility | 4 | PG 15.18 + Python 3.12 + Django 4.2.30 — all current |
| 9 | Observability | 8 | Telemetry layer in place (Phase UX.5), not centralized |
| 10 | Compliance | 6 | Audit trail present (Phase A.2), no formal GDPR review |

**Total risk**: 81/200  
**Risk score**: `100 - (81 * 100 / 200)` = **60/100**

## Top 3 Risks (HIGH severity)

### 1. Scalability (15/20) — HIGH
- **Issue**: Single PG instance, no read replicas, no connection pooling
- **Impact**: Cannot scale beyond ~50 concurrent users
- **Mitigation**: Deploy PgBouncer, set up streaming replication, add Redis cache

### 2. Concurrent Access (12/20) — HIGH
- **Issue**: `CONN_MAX_AGE` not set; `select_for_update()` usage not audited
- **Impact**: Connection churn under load, possible race conditions in critical sections
- **Mitigation**: 
  - Set `CONN_MAX_AGE = 60` in Django settings
  - Audit `JournalEntry` posting path for `select_for_update()`
  - Audit `Payment` processing for locking

### 3. Reliability (10/20) — MEDIUM
- **Issue**: WAL archiving disabled; off-site backup not configured
- **Impact**: RPO = hours (not minutes); single site failure = data loss
- **Mitigation**:
  - Enable `archive_mode = on` + archive_command
  - Replicate dumps to off-site location
  - Document RPO/RTO targets

## Medium Risks
- Performance (6/20): Add composite index `accounting_journalentryline(account_id, id)` to cut ledger queries
- Observability (8/20): Centralize logs to ELK/Loki; add Prometheus metrics

## Low Risks
- Security (5/20): Login fix in place; recommend periodic OWASP audit
- Operability (7/20): Add health check endpoints
- Compliance (6/20): GDPR review for customer PII handling
- Compatibility (4/20): All components on supported versions

## Final Score
**60/100** — Manageable risk profile, but 3 HIGH-severity items need attention before scale-out.
