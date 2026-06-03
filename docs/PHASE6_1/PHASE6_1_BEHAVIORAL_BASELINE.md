# WS-A: Behavioral Baseline

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** Document the complete behavioral contract of each of the 4 Wave-1 refactor targets BEFORE any code is modified. This is the contract that the refactor must preserve.

---

## Wave-1 Refactor Targets

| # | File | LOC | Classes | Public Methods | Import Sites | Risk Profile |
|---|------|-----|---------|----------------|--------------|--------------|
| 1 | `backend/pre_production_hardening/hardening_validator.py` | 1460 | 3 | 9 | 0 | VALIDATOR |
| 2 | `backend/production_infrastructure/migration_validator.py` | 1080 | 3 | 11 | 0 | VALIDATOR |
| 3 | `backend/production_gate/gate_validator.py` | 726 | 3 | 15 | 0 | VALIDATOR |
| 4 | `backend/backup/backup_system.py` | 954 | 5 | 20 | 11 | SERVICE |

---

## Target: `backend/pre_production_hardening/hardening_validator.py` (1460 LOC)

**Class:** `PreProductionHardeningValidator`  
**Kind:** validator  
**Import sites:** 0  
**Classes in file:** 3  
**Module-level functions:** 1

### Public Methods

| Method | Lines | LOC | Public | Args |
|--------|-------|-----|--------|------|
| `PreProductionHardeningValidator.validate_database_hardening` | 55-168 | 114 | YES | `self` |
| `PreProductionHardeningValidator.validate_multi_user_operations` | 172-421 | 250 | YES | `self` |
| `PreProductionHardeningValidator.validate_operator_resilience` | 425-595 | 171 | YES | `self` |
| `PreProductionHardeningValidator.validate_session_security` | 599-784 | 186 | YES | `self` |
| `PreProductionHardeningValidator.validate_export_reliability` | 788-956 | 169 | YES | `self` |
| `PreProductionHardeningValidator.validate_deployment_recovery` | 960-1100 | 141 | YES | `self` |
| `PreProductionHardeningValidator.validate_performance` | 1104-1298 | 195 | YES | `self` |
| `PreProductionHardeningValidator.generate_audit_report` | 1302-1385 | 84 | YES | `self` |
| `PreProductionHardeningValidator.run_all` | 1387-1437 | 51 | YES | `self` |

### Internal/Private Methods

| Method | Lines | LOC | Purpose (inferred) |
|--------|-------|-----|---------------------|

### Module-Level Functions

| Function | Lines | LOC | Public |
|----------|-------|-----|--------|
| `run_pre_production_hardening` | 1440-1456 | 17 | YES |

### Behavioral Characteristics

| Dimension | Description |
|-----------|-------------|
| **Public surface** | 9 public methods, 0 private methods |
| **Inputs** | Constructor params + per-method args (no global mutable state) |
| **Outputs** | `SectionResult` (passed flag + issues list) or `Dict[str, Any]` report; `BackupManager.create_backup()` returns `Dict` with success/checksum/metadata |
| **Side effects** | (1) Mutates `self.issues` and `self.results`; (2) Reads/writes Django ORM (accounting, inventory, payments); (3) Creates threads for concurrency tests; (4) Generates log output via `logger`; (5) `BackupManager` writes to disk, creates archives, encrypts, mutates DB |
| **Dependencies** | `django.db`, `django.conf.settings`, `accounting.models`, `inventory.models`, `payments.models`, `security.*`, `core.runner.snapshot_manager`, `core.audit.engine`, `core.operations.concurrency`, `backup.models` |
| **Signals** | None (these are read-only validators) |
| **Timers** | None (threading used for concurrency tests, not for periodic timers) |
| **File access** | `BackupManager` only — reads/writes backup archive files, config JSON |
| **Database access** | All 4 — read-only on Django models (accounting, inventory, payments, security, backup, core) |
| **Thread safety** | `BackupManager` instantiates its own `BackupScheduler` thread; validator methods use `threading.Thread` for concurrency tests but do not share state across threads (each thread creates its own transaction) |

### Refactor-Safe Subset (Behavioral Boundary)

The following subset of methods may be touched by a refactor without changing the behavioral contract:

- **`__init__`** — pure assignment; can be reorganized
- **All private methods (`_*`)** — internal helpers; can be extracted, renamed, or reorganized
- **`run_all`** — orchestration method; the order of section calls and the final report shape must remain identical

The following methods must NOT change their observable behavior:

- **All `validate_*` public methods** — their return type, return value structure, and side effects on `self.issues`/`self.results` must remain identical
- **`generate_audit_report` / `generate_certification` / `generate_report`** — return value schema is consumed by Phase 5.x test harnesses
- **`create_backup` / `restore_backup` / `list_backups` / `delete_backup`** — return value schemas are consumed by `views.py`, `restore_service.py`, management commands, and `config/tasks.py`

## Target: `backend/production_infrastructure/migration_validator.py` (1080 LOC)

**Class:** `ProductionInfrastructureValidator`  
**Kind:** validator  
**Import sites:** 0  
**Classes in file:** 3  
**Module-level functions:** 1

### Public Methods

| Method | Lines | LOC | Public | Args |
|--------|-------|-----|--------|------|
| `ProductionInfrastructureValidator.validate_postgresql_migration` | 58-195 | 138 | YES | `self` |
| `ProductionInfrastructureValidator.validate_transaction_isolation` | 199-364 | 166 | YES | `self` |
| `ProductionInfrastructureValidator.validate_connection_pooling` | 368-442 | 75 | YES | `self` |
| `ProductionInfrastructureValidator.validate_redis_event_layer` | 446-553 | 108 | YES | `self` |
| `ProductionInfrastructureValidator.validate_celery_execution` | 557-627 | 71 | YES | `self` |
| `ProductionInfrastructureValidator.validate_security_hardening` | 631-754 | 124 | YES | `self` |
| `ProductionInfrastructureValidator.validate_backup_automation` | 758-830 | 73 | YES | `self` |
| `ProductionInfrastructureValidator.validate_performance` | 834-939 | 106 | YES | `self` |
| `ProductionInfrastructureValidator.validate_observability` | 943-1058 | 116 | YES | `self` |
| `ProductionInfrastructureValidator.generate_certification` | 1062-1136 | 75 | YES | `self` |
| `ProductionInfrastructureValidator.run_all` | 1138-1191 | 54 | YES | `self` |

### Internal/Private Methods

| Method | Lines | LOC | Purpose (inferred) |
|--------|-------|-----|---------------------|

### Module-Level Functions

| Function | Lines | LOC | Public |
|----------|-------|-----|--------|
| `run_infrastructure_migration` | 1194-1203 | 10 | YES |

### Behavioral Characteristics

| Dimension | Description |
|-----------|-------------|
| **Public surface** | 11 public methods, 0 private methods |
| **Inputs** | Constructor params + per-method args (no global mutable state) |
| **Outputs** | `SectionResult` (passed flag + issues list) or `Dict[str, Any]` report; `BackupManager.create_backup()` returns `Dict` with success/checksum/metadata |
| **Side effects** | (1) Mutates `self.issues` and `self.results`; (2) Reads/writes Django ORM (accounting, inventory, payments); (3) Creates threads for concurrency tests; (4) Generates log output via `logger`; (5) `BackupManager` writes to disk, creates archives, encrypts, mutates DB |
| **Dependencies** | `django.db`, `django.conf.settings`, `accounting.models`, `inventory.models`, `payments.models`, `security.*`, `core.runner.snapshot_manager`, `core.audit.engine`, `core.operations.concurrency`, `backup.models` |
| **Signals** | None (these are read-only validators) |
| **Timers** | None (threading used for concurrency tests, not for periodic timers) |
| **File access** | `BackupManager` only — reads/writes backup archive files, config JSON |
| **Database access** | All 4 — read-only on Django models (accounting, inventory, payments, security, backup, core) |
| **Thread safety** | `BackupManager` instantiates its own `BackupScheduler` thread; validator methods use `threading.Thread` for concurrency tests but do not share state across threads (each thread creates its own transaction) |

### Refactor-Safe Subset (Behavioral Boundary)

The following subset of methods may be touched by a refactor without changing the behavioral contract:

- **`__init__`** — pure assignment; can be reorganized
- **All private methods (`_*`)** — internal helpers; can be extracted, renamed, or reorganized
- **`run_all`** — orchestration method; the order of section calls and the final report shape must remain identical

The following methods must NOT change their observable behavior:

- **All `validate_*` public methods** — their return type, return value structure, and side effects on `self.issues`/`self.results` must remain identical
- **`generate_audit_report` / `generate_certification` / `generate_report`** — return value schema is consumed by Phase 5.x test harnesses
- **`create_backup` / `restore_backup` / `list_backups` / `delete_backup`** — return value schemas are consumed by `views.py`, `restore_service.py`, management commands, and `config/tasks.py`

## Target: `backend/production_gate/gate_validator.py` (726 LOC)

**Class:** `ProductionGateValidator`  
**Kind:** validator  
**Import sites:** 0  
**Classes in file:** 3  
**Module-level functions:** 1

### Public Methods

| Method | Lines | LOC | Public | Args |
|--------|-------|-----|--------|------|
| `ProductionGateValidator.validate_frontend` | 58-112 | 55 | YES | `self` |
| `ProductionGateValidator.simulate_accountant_workflow` | 116-194 | 79 | YES | `self` |
| `ProductionGateValidator.simulate_cashier_workflow` | 196-243 | 48 | YES | `self` |
| `ProductionGateValidator.simulate_warehouse_workflow` | 245-319 | 75 | YES | `self` |
| `ProductionGateValidator.simulate_hr_workflow` | 321-366 | 46 | YES | `self` |
| `ProductionGateValidator.validate_workflows` | 368-387 | 20 | YES | `self` |
| `ProductionGateValidator.validate_concurrency` | 395-450 | 56 | YES | `self` |
| `ProductionGateValidator.validate_failure_injection` | 454-553 | 100 | YES | `self` |
| `ProductionGateValidator.assertFalse` | 555-556 | 2 | YES | `self, val` |
| `ProductionGateValidator.assertTrue` | 558-559 | 2 | YES | `self, val` |
| `ProductionGateValidator.assertEqual` | 561-562 | 2 | YES | `self, a, b` |
| `ProductionGateValidator.validate_backup_restore` | 566-622 | 57 | YES | `self` |
| `ProductionGateValidator.validate_long_run` | 635-699 | 65 | YES | `self` |
| `ProductionGateValidator.run_all` | 703-715 | 13 | YES | `self` |
| `ProductionGateValidator.generate_report` | 717-785 | 69 | YES | `self` |

### Internal/Private Methods

| Method | Lines | LOC | Purpose (inferred) |
|--------|-------|-----|---------------------|
| `ProductionGateValidator._wf_ok` | 389-391 | 3 | (helper) |
| `ProductionGateValidator._cleanup_gate_data` | 626-633 | 8 | (helper) |

### Module-Level Functions

| Function | Lines | LOC | Public |
|----------|-------|-----|--------|
| `run_gate_validation` | 788-839 | 52 | YES |

### Behavioral Characteristics

| Dimension | Description |
|-----------|-------------|
| **Public surface** | 15 public methods, 2 private methods |
| **Inputs** | Constructor params + per-method args (no global mutable state) |
| **Outputs** | `SectionResult` (passed flag + issues list) or `Dict[str, Any]` report; `BackupManager.create_backup()` returns `Dict` with success/checksum/metadata |
| **Side effects** | (1) Mutates `self.issues` and `self.results`; (2) Reads/writes Django ORM (accounting, inventory, payments); (3) Creates threads for concurrency tests; (4) Generates log output via `logger`; (5) `BackupManager` writes to disk, creates archives, encrypts, mutates DB |
| **Dependencies** | `django.db`, `django.conf.settings`, `accounting.models`, `inventory.models`, `payments.models`, `security.*`, `core.runner.snapshot_manager`, `core.audit.engine`, `core.operations.concurrency`, `backup.models` |
| **Signals** | None (these are read-only validators) |
| **Timers** | None (threading used for concurrency tests, not for periodic timers) |
| **File access** | `BackupManager` only — reads/writes backup archive files, config JSON |
| **Database access** | All 4 — read-only on Django models (accounting, inventory, payments, security, backup, core) |
| **Thread safety** | `BackupManager` instantiates its own `BackupScheduler` thread; validator methods use `threading.Thread` for concurrency tests but do not share state across threads (each thread creates its own transaction) |

### Refactor-Safe Subset (Behavioral Boundary)

The following subset of methods may be touched by a refactor without changing the behavioral contract:

- **`__init__`** — pure assignment; can be reorganized
- **All private methods (`_*`)** — internal helpers; can be extracted, renamed, or reorganized
- **`run_all`** — orchestration method; the order of section calls and the final report shape must remain identical

The following methods must NOT change their observable behavior:

- **All `validate_*` public methods** — their return type, return value structure, and side effects on `self.issues`/`self.results` must remain identical
- **`generate_audit_report` / `generate_certification` / `generate_report`** — return value schema is consumed by Phase 5.x test harnesses
- **`create_backup` / `restore_backup` / `list_backups` / `delete_backup`** — return value schemas are consumed by `views.py`, `restore_service.py`, management commands, and `config/tasks.py`

## Target: `backend/backup/backup_system.py` (954 LOC)

**Class:** `BackupManager + BackupValidator + BackupEncryptor + BackupConfig`  
**Kind:** service  
**Import sites:** 11  
**Classes in file:** 5  
**Module-level functions:** 1

### Public Methods

| Method | Lines | LOC | Public | Args |
|--------|-------|-----|--------|------|
| `BackupConfig.get_default_config` | 37-78 | 42 | YES | `self` |
| `BackupConfig.load_config` | 80-92 | 13 | YES | `self` |
| `BackupConfig.save_config` | 94-102 | 9 | YES | `self, config` |
| `BackupValidator.calculate_checksum` | 119-125 | 7 | YES | `file_path` |
| `BackupValidator.verify_database_integrity` | 128-145 | 18 | YES | `db_path` |
| `BackupValidator.verify_backup_archive` | 148-165 | 18 | YES | `archive_path` |
| `BackupValidator.verify_backup_content` | 168-186 | 19 | YES | `backup_path, expected_files` |
| `BackupEncryptor.generate_key` | 193-205 | 13 | YES | `password, salt` |
| `BackupEncryptor.encrypt_file` | 208-227 | 20 | YES | `input_path, output_path, password` |
| `BackupEncryptor.decrypt_file` | 230-248 | 19 | YES | `input_path, output_path, password` |
| `BackupManager.create_backup` | 332-481 | 150 | YES | `self, db_path, include_files, description` |
| `BackupManager.restore_backup` | 546-654 | 109 | YES | `self, backup_path, target_db_path, password, verify` |
| `BackupManager.list_backups` | 656-683 | 28 | YES | `self` |
| `BackupManager.delete_backup` | 685-700 | 16 | YES | `self, backup_path` |
| `BackupManager.cleanup_old_backups` | 702-746 | 45 | YES | `self` |
| `BackupManager.start_scheduler` | 748-760 | 13 | YES | `self` |
| `BackupManager.stop_scheduler` | 762-767 | 6 | YES | `self` |
| `BackupManager.get_backup_stats` | 769-790 | 22 | YES | `self` |
| `BackupScheduler.start` | 805-810 | 6 | YES | `self` |
| `BackupScheduler.stop` | 812-816 | 5 | YES | `self` |

### Internal/Private Methods

| Method | Lines | LOC | Purpose (inferred) |
|--------|-------|-----|---------------------|
| `BackupConfig._merge_config` | 104-112 | 9 | (helper) |
| `BackupManager._ensure_db_path` | 272-281 | 10 | (helper) |
| `BackupManager._setup_logging` | 283-292 | 10 | (helper) |
| `BackupManager._check_pre_backup_safety` | 294-317 | 24 | (helper) |
| `BackupManager._post_backup_verify` | 319-330 | 12 | (helper) |
| `BackupManager._log_db_event` | 483-494 | 12 | (helper) |
| `BackupManager._vacuum_database` | 496-504 | 9 | (helper) |
| `BackupManager._create_archive` | 506-524 | 19 | (helper) |
| `BackupManager._get_encryption_password` | 526-540 | 15 | (helper) |
| `BackupManager._is_encryption_configured` | 542-544 | 3 | (helper) |
| `BackupScheduler._check_missed_backup` | 818-833 | 16 | (helper) |
| `BackupScheduler._run_scheduler` | 835-886 | 52 | (helper) |

### Module-Level Functions

| Function | Lines | LOC | Public |
|----------|-------|-----|--------|
| `main` | 889-974 | 86 | YES |

### Behavioral Characteristics

| Dimension | Description |
|-----------|-------------|
| **Public surface** | 20 public methods, 12 private methods |
| **Inputs** | Constructor params + per-method args (no global mutable state) |
| **Outputs** | `SectionResult` (passed flag + issues list) or `Dict[str, Any]` report; `BackupManager.create_backup()` returns `Dict` with success/checksum/metadata |
| **Side effects** | (1) Mutates `self.issues` and `self.results`; (2) Reads/writes Django ORM (accounting, inventory, payments); (3) Creates threads for concurrency tests; (4) Generates log output via `logger`; (5) `BackupManager` writes to disk, creates archives, encrypts, mutates DB |
| **Dependencies** | `django.db`, `django.conf.settings`, `accounting.models`, `inventory.models`, `payments.models`, `security.*`, `core.runner.snapshot_manager`, `core.audit.engine`, `core.operations.concurrency`, `backup.models` |
| **Signals** | None (these are read-only validators) |
| **Timers** | None (threading used for concurrency tests, not for periodic timers) |
| **File access** | `BackupManager` only — reads/writes backup archive files, config JSON |
| **Database access** | All 4 — read-only on Django models (accounting, inventory, payments, security, backup, core) |
| **Thread safety** | `BackupManager` instantiates its own `BackupScheduler` thread; validator methods use `threading.Thread` for concurrency tests but do not share state across threads (each thread creates its own transaction) |

### Refactor-Safe Subset (Behavioral Boundary)

The following subset of methods may be touched by a refactor without changing the behavioral contract:

- **`__init__`** — pure assignment; can be reorganized
- **All private methods (`_*`)** — internal helpers; can be extracted, renamed, or reorganized
- **`run_all`** — orchestration method; the order of section calls and the final report shape must remain identical

The following methods must NOT change their observable behavior:

- **All `validate_*` public methods** — their return type, return value structure, and side effects on `self.issues`/`self.results` must remain identical
- **`generate_audit_report` / `generate_certification` / `generate_report`** — return value schema is consumed by Phase 5.x test harnesses
- **`create_backup` / `restore_backup` / `list_backups` / `delete_backup`** — return value schemas are consumed by `views.py`, `restore_service.py`, management commands, and `config/tasks.py`


---

## Cross-Target Behavioral Summary

| Target | Pure Read-Only | Side Effects | Hot Path | Critical Surface |
|--------|----------------|--------------|----------|------------------|
| hardening_validator | YES (mostly) | Mutates `self.issues`/`self.results`; creates threads | NO (one-shot) | Return schema of `validate_*` and `generate_audit_report` |
| migration_validator | YES (mostly) | Mutates `self.issues`/`self.results`; creates threads | NO (one-shot) | Return schema of `validate_*` and `generate_certification` |
| gate_validator | YES (mostly) | Mutates `self.issues`/`self.results`; creates threads | NO (one-shot) | Return schema of `validate_*` and `generate_report` |
| backup_system | NO | Disk I/O, encryption, ORM writes, scheduler thread | YES (one-shot per user action, but called from REST endpoints) | Return schema of `create_backup` / `restore_backup` / `list_backups` / `delete_backup` / `_post_backup_verify` |

---

## Behavioral Invariants to Preserve

1. **Method signatures** — every public method must keep its name, parameters, and return type.
2. **Return value schemas** — every public method must return the same JSON-serializable structure.
3. **Side effect order** — the order of `self.issues.extend(issues)` and `self.results[name] = ...` must remain identical.
4. **Thread creation pattern** — the threading pattern in concurrency tests (5/10/25 threads, `t.join(timeout=30)`) must remain unchanged.
5. **Transaction scope** — every `with transaction.atomic():` block must remain a single atomic unit.
6. **Logging behavior** — `logger.info()`, `logger.warning()`, `logger.error()` calls must remain in the same logical position.
7. **Exception handling** — every `try/except` block must catch the same exceptions and produce the same issue.
8. **Disk operations** (backup_system only) — file paths, archive formats, encryption behavior must remain identical.
