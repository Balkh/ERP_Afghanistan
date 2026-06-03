# WS-B: Extraction Boundary Design

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** Identify every method that may be safely extracted, marked as CAUTION, or DO-NOT-EXTRACT — and define the target module for each.

---

## 1. Classification Rules

| Classification | Meaning | Allowed Action |
|----------------|---------|----------------|
| **SAFE** | Private state only, no external callers, no public-API change | Extract to new module. Public method on class delegates. |
| **CAUTION** | Public method but return value schema is contractually consumed (tests, REST endpoints, scripts) | Extract internal helpers as private methods on the same class. Public method body becomes a 2-3 line orchestrator. Verify return schema byte-for-byte. |
| **DO NOT EXTRACT** | Orchestrator / `run_all` / sequencing / report aggregator | Do not touch. The ordering and structure is the contract. |

---

## 2. Summary by Target

| File | SAFE | CAUTION | DO NOT EXTRACT | Total |
|------|------|---------|----------------|-------|
| `backend/pre_production_hardening/hardening_validator.py` | 7 | 1 | 1 | 9 |
| `backend/production_infrastructure/migration_validator.py` | 9 | 1 | 1 | 11 |
| `backend/production_gate/gate_validator.py` | 6 | 1 | 1 | 8 |
| `backend/backup/backup_system.py` | 25 | 8 | 0 | 33 |
| **Total** | **47** | **11** | **3** | **61** |

---

## 3. Extraction Candidates (Full List)

Headers: File | Class | Method | LOC | Classification | Risk Score

| File | Class | Method | LOC | Class | Risk |
|---|---|---|---|---|---|
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_database_hardening | 114 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_multi_user_operations | 250 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_operator_resilience | 171 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_session_security | 186 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_export_reliability | 169 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_deployment_recovery | 141 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | validate_performance | 195 | SAFE | 1 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | generate_audit_report | 84 | CAUTION | 2 |
| backend/pre_production_hardening/hardening_validator.py | PreProductionHardeningValidator | run_all | 51 | DO_NOT_EXTRACT | 99 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_postgresql_migration | 138 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_transaction_isolation | 166 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_connection_pooling | 75 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_redis_event_layer | 108 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_celery_execution | 71 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_security_hardening | 124 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_backup_automation | 73 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_performance | 106 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | validate_observability | 116 | SAFE | 1 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | generate_certification | 75 | CAUTION | 2 |
| backend/production_infrastructure/migration_validator.py | ProductionInfrastructureValidator | run_all | 54 | DO_NOT_EXTRACT | 99 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | validate_frontend | 55 | SAFE | 1 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | validate_workflows | 20 | SAFE | 1 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | validate_concurrency | 56 | SAFE | 1 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | validate_failure_injection | 100 | SAFE | 1 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | validate_backup_restore | 57 | SAFE | 1 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | validate_long_run | 65 | SAFE | 1 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | run_all | 13 | DO_NOT_EXTRACT | 99 |
| backend/production_gate/gate_validator.py | ProductionGateValidator | generate_report | 69 | CAUTION | 2 |
| backend/backup/backup_system.py | BackupConfig | __init__ | 8 | SAFE | 1 |
| backend/backup/backup_system.py | BackupConfig | get_default_config | 42 | SAFE | 1 |
| backend/backup/backup_system.py | BackupConfig | load_config | 13 | SAFE | 1 |
| backend/backup/backup_system.py | BackupConfig | save_config | 9 | SAFE | 1 |
| backend/backup/backup_system.py | BackupConfig | _merge_config | 9 | SAFE | 1 |
| backend/backup/backup_system.py | BackupValidator | calculate_checksum | 7 | SAFE | 1 |
| backend/backup/backup_system.py | BackupValidator | verify_database_integrity | 18 | SAFE | 1 |
| backend/backup/backup_system.py | BackupValidator | verify_backup_archive | 18 | SAFE | 1 |
| backend/backup/backup_system.py | BackupValidator | verify_backup_content | 19 | SAFE | 1 |
| backend/backup/backup_system.py | BackupEncryptor | generate_key | 13 | SAFE | 1 |
| backend/backup/backup_system.py | BackupEncryptor | encrypt_file | 20 | SAFE | 1 |
| backend/backup/backup_system.py | BackupEncryptor | decrypt_file | 19 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | __init__ | 15 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _ensure_db_path | 10 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _setup_logging | 10 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _check_pre_backup_safety | 24 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _post_backup_verify | 12 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | create_backup | 150 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | _log_db_event | 12 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _vacuum_database | 9 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _create_archive | 19 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _get_encryption_password | 15 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | _is_encryption_configured | 3 | SAFE | 1 |
| backend/backup/backup_system.py | BackupManager | restore_backup | 109 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | list_backups | 28 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | delete_backup | 16 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | cleanup_old_backups | 45 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | start_scheduler | 13 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | stop_scheduler | 6 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupManager | get_backup_stats | 22 | CAUTION | 3 |
| backend/backup/backup_system.py | BackupScheduler | __init__ | 6 | SAFE | 1 |
| backend/backup/backup_system.py | BackupScheduler | _check_missed_backup | 16 | SAFE | 1 |
| backend/backup/backup_system.py | BackupScheduler | _run_scheduler | 52 | SAFE | 1 |

---

## 4. Extraction Strategy per Target

### 4.1 hardening_validator.py

- 7 `validate_*` section methods → **SAFE** to extract to `pre_production_hardening/sections/*.py`
- 1 `generate_audit_report` → **CAUTION** — verify return schema byte-for-byte
- 1 `run_all` → **DO NOT EXTRACT** — section ordering is the contract
- Module-level `run_pre_production_hardening()` → SAFE to leave as a thin orchestrator

### 4.2 migration_validator.py

- 9 `validate_*` section methods → **SAFE** to extract to `production_infrastructure/sections/*.py`
- 1 `generate_certification` → **CAUTION** — verify return schema byte-for-byte
- 1 `run_all` → **DO NOT EXTRACT**

### 4.3 gate_validator.py

- 7 `validate_*` section methods → **SAFE** to extract to `production_gate/sections/*.py`
- 1 `generate_report` → **CAUTION** — verify return schema byte-for-byte
- 1 `run_all` → **DO NOT EXTRACT**

### 4.4 backup_system.py

- All `_private_*` methods on `BackupConfig`, `BackupValidator`, `BackupEncryptor`, `BackupManager`, `BackupScheduler` → **SAFE** to extract to `backup/extracts/<class>_<method>.py`
- Public API methods: `create_backup`, `restore_backup`, `list_backups`, `delete_backup`, `cleanup_old_backups`, `start_scheduler`, `stop_scheduler`, `get_backup_stats` → **CAUTION** — extract INTERNAL helpers only; keep the public method in the class with the same signature

---

## 5. Dependency Impact per Extraction

Each SAFE extraction moves ~50-150 LOC to a new module and re-imports as a function. **Zero cross-file coupling** is introduced because:

- Validators use only `self.issues`, `self.results`, and Django ORM
- Backup private helpers receive all their inputs as arguments
- No global state is touched
- No signals are emitted

The only DO-NOT-EXTRACT items are orchestrators that depend on section ordering.

---

## 6. Forbidden Extractions (Architectural Reasons)

The following would constitute an **architectural change** and are FORBIDDEN:

- Moving a section method to a different package (e.g., `pre_production_hardening` → `core`)
- Introducing a base class for `*Validator` (would change MRO)
- Introducing a `Registry` pattern for sections (would change `validate_*` resolution)
- Changing the signature of any public method
- Changing the return value schema of any public method

---

## 7. Conclusion

- **47** methods are SAFE to extract with **risk score 1** (LOW).
- **11** methods require return-schema verification (CAUTION, risk score 2-3).
- **3** methods are DO-NOT-EXTRACT (orchestrators).
- The plan produces ~58 new modules/files, all with byte-for-byte behavior preservation.
