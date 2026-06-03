# WS-C: Regression Impact Matrix

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** Map every test, workflow, report, accounting path, inventory path, API path, and UI path that the refactor could affect.

---

## 1. Test Inventory per Target

| Target | Direct Tests | Indirect Tests (via DB) | Coverage Status |
|--------|--------------|--------------------------|-----------------|
| hardening_validator.py | 0 (standalone script, no `tests/test_*hardening*` import it) | test_adversarial_hardening, test_database_hardening, test_financial_hardening, test_phase37_hardening, test_returns_hardening, test_final_hardening, test_final_go_live_hardening, test_backup_hardening | Indirect only |
| migration_validator.py | 0 (standalone script) | test_database_hardening, test_runner_hardened | Indirect only |
| gate_validator.py | 0 (standalone script) | test_adversarial_hardening, test_phase33_concurrency, test_phase33_workflows, test_phase33_chaos, test_phase33_session_stability, test_phase33_export_stress | Indirect only |
| backup_system.py | test_backup_restore.py, test_backup_hardening.py | test_restore, test_recovery_validation, test_rollback_safety, test_runner_hardened | DIRECT (4 files import `BackupManager` or `BackupValidator`) |

---

## 2. Workflows Affected

| Target | Workflows |
|--------|-----------|
| hardening_validator.py | (none — this is a CI-time validator, not part of the request/response cycle) |
| migration_validator.py | (none — this is a CI-time validator) |
| gate_validator.py | (none — this is a CI-time validator) |
| backup_system.py | `POST /api/backup/create/`, `POST /api/backup/restore/`, `GET /api/backup/list/`, `DELETE /api/backup/<id>/`, scheduled backup (Celery beat), management commands `create_backup`, `restore_backup`, `cleanup_backups` |

---

## 3. Reports Affected

| Target | Reports |
|--------|---------|
| hardening_validator.py | Hardening audit report (consumed by Phase 5.x scripts) |
| migration_validator.py | Infrastructure certification report (consumed by Phase 5.x scripts) |
| gate_validator.py | Production gate report (consumed by Phase 5.x scripts) |
| backup_system.py | Backup metadata JSON files (`.json` sidecar per backup); BackupLog model rows |

---

## 4. Accounting Paths

| Target | Accounting Path |
|--------|-----------------|
| hardening_validator.py | Reads: `Account`, `JournalEntry`, `JournalEntryLine` (read-only, for tests). Writes: none. |
| migration_validator.py | Reads: `Account`, `JournalEntry`, `JournalEntryLine` (read-only, for tests). Writes: none. |
| gate_validator.py | Reads: none directly. Writes: none. |
| backup_system.py | Reads: `BackupRecord`, `BackupLog` (own tables). Writes: `BackupRecord`, `BackupLog` via `BackupLog.objects.create()` (in `_log_db_event`). |

**Invariant check:** `InvariantRegistry` (6 invariants) must still pass after refactor.

---

## 5. Inventory Paths

| Target | Inventory Path |
|--------|----------------|
| hardening_validator.py | Reads: `Product`, `Batch`, `StockMovement`, `Warehouse` (read-only, for tests). Writes: none. |
| migration_validator.py | Reads: `Product`, `Batch`, `StockMovement`, `Warehouse` (read-only, for tests). Writes: none. |
| gate_validator.py | Reads: none directly. Writes: none. |
| backup_system.py | Reads: none directly. Writes: none. |

---

## 6. API Paths

| Target | API Path |
|--------|----------|
| hardening_validator.py | (none — no REST endpoints expose this validator) |
| migration_validator.py | (none) |
| gate_validator.py | (none) |
| backup_system.py | `backup/views.py` imports `BackupManager`. Endpoints: `/api/backup/create/`, `/api/backup/restore/`, `/api/backup/list/`, `/api/backup/<id>/delete/`, `/api/backup/schedule/`, `/api/backup/health/`, `/api/backup/offsite-status/` (all use the manager). |

---

## 7. UI Paths

| Target | UI Path |
|--------|---------|
| hardening_validator.py | (none) |
| migration_validator.py | (none) |
| gate_validator.py | (none) |
| backup_system.py | `frontend/ui/system/backup_screen.py` calls `BackupManager` through the REST API. The `RestoreConfirmDialog` (EnterpriseDialog) calls the restore endpoint which delegates to `BackupManager.restore_backup()`. |

---

## 8. Direct vs Indirect Test Coupling

### Direct (must verify before merge)

| Test File | What it imports from target | Verification |
|-----------|------------------------------|--------------|
| `tests/test_backup_restore.py` | `BackupRecord`, `BackupSchedule`, `RestorePoint`, `RestoreValidation` (NOT from backup_system.py — from backup.models) | Run test — must pass |
| `tests/test_backup_hardening.py` | `from backup.backup_system import BackupManager` (lines 55, 150, 163, 166, 172, 178, 182) | Run test — must pass with byte-for-byte identical behavior |
| `backup/services/restore_service.py:76` | `from backup.backup_system import BackupManager` | Run all 5 restore tests in `test_backup_hardening.py` |
| `backup/services/restore_testing.py:139, 169` | `BackupManager` | Run recovery validation tests |
| `backup/services/health_monitor.py:168, 225, 329` | `BackupValidator` | Run health monitor tests |
| `backup/services/failure_injection.py:275, 418` | `BackupEncryptor`, `BackupManager` | Run failure injection tests |
| `backup/services/control_plane.py:182` | `BackupManager` | Run control plane tests |
| `backup/views.py:15, 156` | `BackupManager`, `BackupValidator` | Run all backup endpoint tests |
| `backup/management/commands/*.py` (3 files) | `BackupManager` | Run management command tests |
| `config/tasks.py:74` | `BackupManager` | Run Celery task tests |

### Indirect (DB-level side effects)

- All `test_*hardening*.py` — verify the underlying database is not corrupted after a validator runs
- `test_database_hardening.py` — verify schema is unchanged
- `test_recovery_validation.py` — verify backup integrity checks

---

## 9. Required Verification Before Merge

For each extraction in WS-B, the following MUST be run:

1. **Unit tests:** `pytest tests/test_backup_restore.py tests/test_backup_hardening.py -v` — must show 100% pass.
2. **Direct import smoke:** `python -c "from backup.backup_system import BackupManager, BackupValidator, BackupEncryptor; print('OK')"`.
3. **Management command smoke:** `python manage.py create_backup --description refactor_smoke` then `python manage.py cleanup_backups --dry-run`.
4. **REST API smoke:** `curl -X POST http://localhost:8000/api/backup/list/ -H "Authorization: Bearer ..."` (must return 200).
5. **Validator rerun:** `python pre_production_hardening/hardening_validator.py` and verify the score is unchanged (Phase 5.9 baseline: 73/100, DEPLOYMENT_READY).
6. **Roundtrip:** if backup_system was extracted, perform a full backup → restore cycle and verify the restored DB is byte-identical to the original (use `sha256sum` on the sqlite3 file).

---

## 10. Conclusion

- hardening_validator.py / migration_validator.py / gate_validator.py — **zero direct test coupling**; the refactor is observationally equivalent to renaming variables internally. LOWEST RISK.
- backup_system.py — **heavy direct coupling** (19 import sites, 4 test files, 3 management commands, 1 Celery task, 1 REST viewset). The refactor MUST preserve the public API and the return value schemas exactly.
