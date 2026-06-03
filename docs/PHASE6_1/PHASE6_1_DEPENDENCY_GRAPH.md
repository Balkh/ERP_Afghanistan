# WS-E: Dependency Graph

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** Document the full inbound and outbound dependencies of each target — to identify circular risks, hidden coupling, service entanglement, and validator entanglement.

---

## 1. Outbound Dependencies (what each target imports)

### 1.1 hardening_validator.py

| Import | Purpose | Used in |
|--------|---------|---------|
| `django.conf.settings` | Read DB config, ATOMIC_REQUESTS, USE_TZ, PASSWORD_HASHERS, SESSION_COOKIE_SECURE, REST_FRAMEWORK, MIDDLEWARE, SIMPLE_JWT, CORS_ALLOWED_ORIGINS, RATE_LIMIT_CONFIG | All `validate_*` |
| `django.db.connection` | `SELECT 1` connectivity test | validate_database_hardening |
| `django.db.transaction` | `transaction.atomic()` for tests | validate_database_hardening, validate_multi_user_operations, validate_operator_resilience |
| `django.contrib.auth.get_user_model` | Find a test user for token test | validate_session_security |
| `accounting.models.Account` | Test accounts (cash 1000, equity, revenue) | validate_multi_user_operations, validate_operator_resilience |
| `accounting.models.JournalEntry` | Test journal posting | validate_multi_user_operations, validate_operator_resilience, validate_performance |
| `accounting.models.JournalEntryLine` | Test journal lines | validate_multi_user_operations, validate_operator_resilience, validate_performance |
| `accounting.services.financial_reports.FinancialReportEngine` | Report generation tests | validate_export_reliability, validate_performance |
| `accounting.services.report_exporter.ReportExporter` | CSV export test | validate_export_reliability |
| `inventory.models.Product` | Test products | validate_multi_user_operations, validate_performance |
| `inventory.models.Batch` | Test batches | validate_multi_user_operations, validate_performance |
| `inventory.models.StockMovement` | Test stock movements | validate_multi_user_operations, validate_performance |
| `inventory.models.Warehouse` | Test warehouse | validate_multi_user_operations |
| `payments.models.FinancialTransaction` | Partial payment test | validate_operator_resilience |
| `security.authentication.generate_jwt_token` | Token generation test | validate_session_security |
| `security.authentication.generate_refresh_token` | Token generation test | validate_session_security |
| `security.authentication.JWTAuthentication` | (imported but unused) | validate_session_security |
| `security.models.RevokedToken` | Token revocation test | validate_session_security |
| `backup.services.restore_service.RestoreService` | (imported but unused) | validate_deployment_recovery |
| `core.runner.snapshot_manager.SnapshotManager` | Snapshot integrity test | validate_deployment_recovery |
| `core.audit.engine.AuditEngine` | Audit speed test | validate_performance |
| `core.paginator.Paginator` | (actually `django.core.paginator.Paginator`) | validate_performance |
| `django.core.paginator.Paginator` | Pagination stability test | validate_performance |
| `django.apps.apps` | Model count walk | validate_deployment_recovery |
| `backup.models.BackupRecord` | Backup record test | validate_deployment_recovery |

**Total outbound modules:** 24
**Circular risks:** None. The target is a **leaf** in the import DAG.

### 1.2 migration_validator.py

| Import | Purpose |
|--------|---------|
| `core.infrastructure.database.detect_database_engine` | Detect engine |
| `core.infrastructure.database.database_connection_health` | Connection test |
| `core.infrastructure.database.check_migration_health` | Migration state |
| `core.infrastructure.database.check_postgresql_config` | PG config |
| `accounting.models.Account/JournalEntry/JournalEntryLine` | Atomic journal posting test |
| `inventory.models.Product/Batch/StockMovement/Warehouse` | Test (imported but not directly used) |
| `core.operations.concurrency.DoubleSpendPreventer` | Double-spend prevention check |
| `psycopg2` (optional) | Version check |
| `django.conf.settings` | Settings access |
| `django.db.connection`, `django.db.transaction` | DB access |

**Total outbound modules:** 12
**Circular risks:** None. The target is a **leaf**.

### 1.3 gate_validator.py

| Import | Purpose |
|--------|---------|
| `importlib` | Dynamic import of `frontend.ui.*` modules |
| `pathlib.Path` | Path manipulation for screen existence checks |
| `django.db.transaction`, `django.db.connection` | DB tests |
| `accounting.models.*`, `inventory.models.*` | Multi-user / inventory tests |
| `core.audit.engine.AuditEngine` | Audit engine test |
| `backup.services.restore_service.RestoreService` | Restore test |

**Total outbound modules:** ~10
**Circular risks:** None. The target is a **leaf**.

### 1.4 backup_system.py

| Import | Purpose |
|--------|---------|
| `cryptography.fernet.Fernet` | Encryption |
| `cryptography.hazmat.primitives.hashes` | KDF |
| `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC` | Key derivation |
| `base64` | Encoding |
| `hashlib` | Checksum |
| `shutil` | File operations |
| `sqlite3` | DB vacuum / integrity |
| `tarfile` | Archive |
| `tempfile` | Temp dir |
| `threading` | Scheduler |
| `logging` | Logs |
| `json` | Config + metadata |
| `os` (env vars APPDATA, PHARMACY_ERP_BACKUP_PASSWORD) | Config |
| `django.conf.settings` (lazy) | DB path |

**Total outbound modules:** 13 (heavy on stdlib + cryptography)
**Circular risks:** None. The target is a **leaf** in the dependency DAG (despite being heavily imported by other code).

---

## 2. Inbound Dependencies (who imports each target)

| Target | Imported By | Count |
|--------|-------------|-------|
| hardening_validator.py | (nothing) | 0 |
| migration_validator.py | (nothing) | 0 |
| gate_validator.py | (nothing) | 0 |
| backup_system.py | backup/views.py, backup/services/restore_service.py, backup/services/restore_testing.py, backup/services/health_monitor.py, backup/services/failure_injection.py, backup/services/control_plane.py, backup/management/commands (3 files: create_backup, restore_backup, cleanup_backups), config/tasks.py, tests/test_backup_hardening.py | 11 (production) + 1 (test) |

**Critical insight:** The 3 standalone validators are **leaves with no inbound dependencies** — extraction is observationally zero-risk.

**backup_system.py is a critical service** with 11 inbound import sites. Extraction MUST preserve:
- The exact import paths (`from backup.backup_system import BackupManager, BackupValidator, BackupEncryptor`)
- The exact class names
- The exact public method signatures
- The exact return value schemas

---

## 3. Dependency Graph Visualization

```
                    ┌─────────────────────────┐
                    │  Test harnesses         │
                    │  (Phase 5.x scripts)    │
                    └──────────┬──────────────┘
                               │ (run script)
                               ▼
        ┌──────────────────────────────────────────────┐
        │ hardening_validator.py                        │
        │ migration_validator.py                        │
        │ gate_validator.py                             │
        │ (ALL 3 ARE LEAVES - no inbound imports)       │
        └──────────┬───────────────────────────────────┘
                   │ (read-only ORM)
                   ▼
        ┌──────────────────────┐
        │  Django models       │
        │  (accounting,        │
        │   inventory, etc.)   │
        └──────────────────────┘

        ┌──────────────────────┐         ┌──────────────────────┐
        │ backup_system.py     │◄────────│ backup/views.py       │
        │ (BackupManager,      │         │ backup/services/*     │
        │  BackupValidator,    │         │ backup/management/*   │
        │  BackupEncryptor)    │         │ config/tasks.py       │
        └──────────┬───────────┘         │ tests/test_backup_*   │
                   │                     └──────────────────────┘
                   │ (heavy I/O)
                   ▼
        ┌──────────────────────┐
        │  Filesystem +        │
        │  cryptography +      │
        │  Django models       │
        │  (BackupRecord,      │
        │   BackupLog)         │
        └──────────────────────┘
```

---

## 4. Circular Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Validator module imports from `pre_production_hardening.sections.X` and `pre_production_hardening.sections.X` imports validator | LOW | HIGH | All extractions are leaves. Validator class imports section modules; sections do not import validator. |
| `backup.extracts.BackupManager_create_backup` imports `BackupManager` and `BackupManager` imports from `backup.extracts` | LOW | HIGH | Extracts are standalone functions. The class method delegates via a one-line call. No circular import. |
| Section module imports Django settings at module level → app-loading order | MEDIUM | LOW | Defer Django imports to function body (already done in original code). |

**No circular risks identified.**

---

## 5. Hidden Coupling to Watch

| Hidden Coupling | Source | Mitigation |
|------------------|--------|------------|
| `BackupManager` and `BackupLog` (in `backup.models`) are written to from `_log_db_event` | backup_system.py:483 | Do not extract `_log_db_event` — keep it on the class. |
| `BackupManager.__init__` reads `os.environ.get('APPDATA')` and `os.environ.get('PHARMACY_ERP_BACKUP_PASSWORD')` | backup_system.py:28, 543 | These are read at construction time. Extracting a helper that also reads them is OK because the helper is called from within the class. |
| `BackupValidator.calculate_checksum()` is called from `BackupManager._post_backup_verify` AND from `backup.services.health_monitor.py` | backup_system.py + health_monitor.py:168, 225, 329 | This is a SHARED utility. Extraction must NOT break the import path. Keep `calculate_checksum` as a module-level function in `backup_system.py` (do not move it). |
| `BackupEncryptor.encrypt_file/decrypt_file` are called from `BackupManager.create_backup` AND from `backup.services.failure_injection.py` | backup_system.py + failure_injection.py:275 | Same as above — keep the class in place. |
| `BackupManager._run_scheduler` references `BackupManager` itself (via `self`) | backup_system.py:835 | Extraction would break the closure. **DO NOT extract `_run_scheduler`**. |

---

## 6. Validator Entanglement

The 3 standalone validators are **not entangled** with each other — they each import from a different set of core modules and have no shared state.

The 3 standalone validators do **not** call each other.

The 3 standalone validators **do** share the same `SectionResult` dataclass pattern (but each defines their own `*Issue` dataclass with a different name):
- hardening: `HardeningIssue`, `SectionResult`
- migration: `InfraIssue`, `SectionResult`
- gate: `GateIssue`, `SectionResult`

**This is intentional duplication** — each validator is self-contained. The refactor MUST NOT extract the `SectionResult` to a shared module (that would be an architectural change). The duplication is acceptable.

---

## 7. Service Entanglement

`backup_system.py` contains 4 classes that are entangled:

```
BackupConfig (config loader)
       ↓ provides config dict
BackupManager (orchestrator)
       ↓ uses
BackupValidator (checksum + integrity)
       ↓ uses
BackupEncryptor (Fernet encryption)
       ↓ uses
BackupScheduler (thread that calls BackupManager)
```

This is a **tight but stable** entanglement. The refactor plan is to extract PRIVATE helpers (not the classes themselves). The classes remain in `backup_system.py` and continue to be imported by 11 sites.

---

## 8. Conclusion

- **Zero circular risks.**
- **Zero validator entanglement.**
- **One tight service entanglement** (backup_system) that is **stable and should not be disentangled**.
- The refactor plan respects all dependencies.
