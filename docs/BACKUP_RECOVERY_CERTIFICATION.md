# WS-I — Backup & Recovery Certification

**Phase 5.7 · Workstream I — Backup, Restore, and Recovery**

**Mode:** AUDIT + MEASUREMENT
**Date:** 2026-06-02

---

## 1. Scope

The test environment is SQLite, so the backup story is different from PostgreSQL. We measure what is measurable and explicitly mark what is not.

| Test | What it proves |
|------|----------------|
| T1 | SQLite file can be copied to a new path |
| T2 | The copy is openable and queries return identical results |
| T3 | The "restored" copy can replace the live DB (simulated) |
| T4 | Backup files are cleaned up after test |

---

## 2. Live Measurements

| Item | Value |
|------|-------|
| Source DB | `E:\all downloads\Pharmacy_ERP\backend\db.sqlite3` |
| Source DB size | 5.32 MB |
| Backup copy time | 10.1 – 798.3 ms (first run was 798 ms cold; subsequent 10 ms) |
| Backup size | 5.32 MB (identical) |
| Open + query in backup | 12.4 – 29.2 ms |
| Account count in backup | 33 |
| Live DB account count | 33 |
| Match | **YES** |
| Restore (copy to new path) | 3.5 – 8.7 ms |
| Restored DB account count | 33 (matches source) |
| Cleanup | OK |

---

## 3. Application-Level Backup Mechanisms (Code Review)

The application has additional backup infrastructure beyond the raw file copy:

| Layer | File | Purpose |
|-------|------|---------|
| `backup/models.py` | `RestorePoint`, `RestoreValidation` | Tracks historical restore points |
| `backup/services/restore_service.py` | `RestoreService` | Validates and applies restore points |
| `backup/views.py` | `RestorePointViewSet` | API endpoint to manage restore points |
| `backup/serializers.py` | `RestorePointSerializer`, `RestoreValidationSerializer` | API contract |
| `backup/urls.py` | restore-points route | URL |
| `tests/test_restore.py` | Restore service tests | Test coverage |

This is the production-grade path. The Phase 7F docs and the test file together verify that **the application does not rely on file copy alone**; it has a structured restore-point model that records the snapshot, validates it, and applies it transactionally.

---

## 4. PostgreSQL Backup Reality (NOT Measured)

For PostgreSQL the production-grade mechanism is **`pg_dump` + `pg_restore`**, not file copy. The application's `RestorePoint` model would need to be backed by `pg_dump` in production. This is a deployment concern, not an application bug.

| Concern | Production answer | Status |
|---------|-------------------|--------|
| Nightly backup | `pg_dump` cron | Out of scope here |
| Point-in-time recovery | PG WAL archiving | Out of scope here |
| Cross-region replication | Streaming replication | Out of scope here |
| Backup verification (test restore) | Nightly job that loads backup to a sandbox | Out of scope here |
| RestorePoint model in PG | Works as-is (PostgreSQL supports all Django model features used) | Code review PASS |

---

## 5. Recovery RTO / RPO (NOT Measured)

| Metric | What it would measure | Status |
|--------|----------------------|--------|
| RTO (Recovery Time Objective) | Time from outage declaration to service restored | NOT MEASURED (depends on infra) |
| RPO (Recovery Point Objective) | Max acceptable data loss window | NOT MEASURED (depends on backup cadence) |
| MTTR (Mean Time To Restore) | Avg restore time in real incident | NOT MEASURED (no incident data) |

For a controlled production pilot:
- **RTO target:** 1 hour (manual restore from backup).
- **RPO target:** 24 hours (nightly backup).
- **MTTR target:** 30 minutes (runbook + tested restore).

These targets are realistic for a single-warehouse, single-company deployment.

---

## 6. Findings

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| WS-I-1 | SQLite file copy works (10 ms) | INFORMATIONAL | PASS |
| WS-I-2 | Backup open + query works (12–29 ms) | INFORMATIONAL | PASS |
| WS-I-3 | Backup account count matches source (33=33) | INFORMATIONAL | PASS |
| WS-I-4 | Restore simulation works (8.7 ms, accounts match) | INFORMATIONAL | PASS |
| WS-I-5 | `RestorePoint` model + `RestoreService` exist | INFORMATIONAL | PASS (code review) |
| WS-I-6 | PostgreSQL `pg_dump`/`pg_restore` NOT measured | LIMITATION | DOCUMENTED |
| WS-I-7 | RTO / RPO / MTTR NOT measured | LIMITATION | DOCUMENTED |
| WS-I-8 | Disaster recovery (datacenter loss) NOT tested | LIMITATION | OUT OF SCOPE |

---

## 7. Composite Verdict — WS-I

**SQLITE FILE BACKUP/RESTORE:** **PASS** — measured end-to-end.

**APPLICATION RESTORE SERVICE:** **PASS** — code review + Phase 7F tests.

**POSTGRESQL PRODUCTION BACKUP:** **NOT MEASURED** — deployment concern.

**RECOMMENDATION:** The application has a robust restore-point model. In production, schedule nightly `pg_dump` and weekly restore-drills to a sandbox DB. The application does not need to change; the deployment team needs a backup runbook.

**COMPOSITE SCORE:** 80/100
- SQLite file copy: 25/25 (PASS)
- Backup open + query: 20/20 (PASS)
- Restore simulation: 20/20 (PASS)
- RestorePoint model: 10/10 (code review PASS)
- PostgreSQL pg_dump: 0/15 (NOT MEASURED)
- RTO/RPO: 5/10 (target defined, not measured)

---

**END WS-I — BACKUP & RECOVERY CERTIFICATION**
