# WS-H: Execution Plan

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** Step-by-step execution sequence. For each step: prerequisite, expected duration, validation gate, rollback gate.

---

## 1. Execution Order (Risk-Ordered)

The 4 targets are ordered from **lowest risk** to **highest risk**:

| Step | Target | Risk Score | Estimated Duration | Rollback Time |
|------|--------|------------|---------------------|---------------|
| **1** | hardening_validator.py | LOW (leaf, 0 inbound imports) | 1-2 hours | < 1 minute |
| **2** | migration_validator.py | LOW (leaf, 0 inbound imports) | 1-2 hours | < 1 minute |
| **3** | gate_validator.py | LOW (leaf, 0 inbound imports) | 1-2 hours | < 1 minute |
| **4** | backup_system.py | MEDIUM (11 inbound imports, hot path) | 4-6 hours | < 5 minutes |

**Total estimated time:** 7-12 hours of focused work, spread across 1-2 sprints.

---

## 2. Step 1: hardening_validator.py

### Prerequisite
- Branch: `refactor/phase6_1-01-hardening-validator` cut from `main`
- Working tree clean
- All Phase 5.9 tests passing on `main`

### Sub-Steps

| Sub-step | Action | Duration | Validation Gate | Rollback Gate |
|----------|--------|----------|------------------|---------------|
| 1.1 | Extract 7 `validate_*` section methods to `pre_production_hardening/sections/*.py` | 45 min | Each section file imports cleanly | `git revert` |
| 1.2 | Public `validate_*` methods on the class delegate to the section module (one line) | 15 min | Class import + instance creation | `git revert` |
| 1.3 | Extract `generate_audit_report` to `pre_production_hardening/sections/report.py` (CAUTION) | 15 min | `report == baseline_report` (byte diff) | `git revert` |
| 1.4 | Run full validator and diff output vs Phase 5.9 baseline (73/100) | 10 min | Score matches exactly | `git revert` |
| 1.5 | Run pytest | 5 min | All tests pass | `git revert` |
| 1.6 | Code review (1 reviewer) + merge | 30 min | Reviewer approval | n/a |

### Validation Gates
- [ ] All 7 sections extractable to separate modules without import errors
- [ ] `PreProductionHardeningValidator().run_all()` returns identical dict to baseline
- [ ] `pytest tests/ -q` — 100% pass
- [ ] No new warnings
- [ ] No query-count change
- [ ] No memory growth

### Rollback Gate
- [ ] `git revert` works cleanly (no merge conflicts)
- [ ] Validator rerun returns baseline score
- [ ] All tests still pass

---

## 3. Step 2: migration_validator.py

### Prerequisite
- Step 1 merged to `main`
- Branch: `refactor/phase6_1-02-migration-validator` cut from `main`

### Sub-Steps

| Sub-step | Action | Duration | Validation Gate | Rollback Gate |
|----------|--------|----------|------------------|---------------|
| 2.1 | Extract 9 `validate_*` section methods to `production_infrastructure/sections/*.py` | 60 min | Each section file imports cleanly | `git revert` |
| 2.2 | Public `validate_*` methods delegate to section module | 15 min | Class import + instance creation | `git revert` |
| 2.3 | Extract `generate_certification` to `production_infrastructure/sections/certification.py` (CAUTION) | 20 min | `report == baseline_report` | `git revert` |
| 2.4 | Run full validator and diff output vs Phase 5.9 baseline (76/100) | 10 min | Score matches exactly | `git revert` |
| 2.5 | Run pytest | 5 min | All tests pass | `git revert` |
| 2.6 | Code review (1 reviewer) + merge | 30 min | Reviewer approval | n/a |

### Validation Gates
- [ ] All 9 sections extractable without import errors
- [ ] `ProductionInfrastructureValidator().run_all()` returns identical dict to baseline
- [ ] `pytest tests/ -q` — 100% pass
- [ ] No new warnings
- [ ] No query-count change

### Rollback Gate
- [ ] `git revert` works cleanly
- [ ] Validator rerun returns baseline score

---

## 4. Step 3: gate_validator.py

### Prerequisite
- Step 2 merged to `main`
- Branch: `refactor/phase6_1-03-gate-validator` cut from `main`

### Sub-Steps

| Sub-step | Action | Duration | Validation Gate | Rollback Gate |
|----------|--------|----------|------------------|---------------|
| 3.1 | Extract 7 `validate_*` section methods to `production_gate/sections/*.py` | 45 min | Each section file imports cleanly | `git revert` |
| 3.2 | Public `validate_*` methods delegate to section module | 15 min | Class import + instance creation | `git revert` |
| 3.3 | Extract `generate_report` to `production_gate/sections/report.py` (CAUTION) | 15 min | `report == baseline_report` | `git revert` |
| 3.4 | Run full validator and diff output vs Phase 5.9 baseline (83/100) | 10 min | Score matches exactly | `git revert` |
| 3.5 | Run pytest | 5 min | All tests pass | `git revert` |
| 3.6 | Code review (1 reviewer) + merge | 30 min | Reviewer approval | n/a |

### Validation Gates
- [ ] All 7 sections extractable without import errors
- [ ] `ProductionGateValidator().run_all()` returns identical dict to baseline
- [ ] `pytest tests/ -q` — 100% pass
- [ ] No new warnings
- [ ] No query-count change

### Rollback Gate
- [ ] `git revert` works cleanly
- [ ] Validator rerun returns baseline score

---

## 5. Step 4: backup_system.py (HIGHEST RISK)

### Prerequisite
- Step 3 merged to `main`
- Branch: `refactor/phase6_1-04-backup-system` cut from `main`
- **2 reviewers** assigned (this is the only target requiring dual review)

### Sub-Steps

| Sub-step | Action | Duration | Validation Gate | Rollback Gate |
|----------|--------|----------|------------------|---------------|
| 4.1 | Extract `BackupConfig` private methods (`_merge_config`) to `backup/extracts/backup_config__merge.py` | 20 min | `from backup.extracts.backup_config__merge import merge_config; merge_config(d, c) == original` | `git revert` |
| 4.2 | Extract `BackupValidator` static methods (`calculate_checksum`, `verify_database_integrity`, `verify_backup_archive`, `verify_backup_content`) to `backup/extracts/backup_validator_methods.py` | 45 min | Each static method, when called as standalone, returns same value | `git revert` |
| 4.3 | Extract `BackupEncryptor` static methods (`generate_key`, `encrypt_file`, `decrypt_file`) to `backup/extracts/backup_encryptor_methods.py` | 45 min | Roundtrip: encrypt → decrypt returns original | `git revert` |
| 4.4 | Extract `BackupManager._check_pre_backup_safety` to `backup/extracts/backup_manager__pre_check.py` | 15 min | Returns identical dict | `git revert` |
| 4.5 | Extract `BackupManager._post_backup_verify` to `backup/extracts/backup_manager__post_verify.py` | 15 min | Returns identical bool | `git revert` |
| 4.6 | Extract `BackupManager._vacuum_database` to `backup/extracts/backup_manager__vacuum.py` | 10 min | Vacuum completes without error | `git revert` |
| 4.7 | Extract `BackupManager._create_archive` to `backup/extracts/backup_manager__archive.py` | 15 min | Archive is byte-identical | `git revert` |
| 4.8 | Extract `BackupManager._log_db_event` to `backup/extracts/backup_manager__log_event.py` | 15 min | BackupLog row created | `git revert` |
| 4.9 | Refactor `BackupManager.create_backup` body to call extracted helpers (CAUTION) | 60 min | `pytest tests/test_backup_restore.py tests/test_backup_hardening.py -v` → 100% | `git revert` |
| 4.10 | Refactor `BackupManager.restore_backup` body to call extracted helpers (CAUTION) | 60 min | `pytest tests/test_backup_restore.py -v` → 100% | `git revert` |
| 4.11 | Refactor `BackupManager.list_backups` body (CAUTION) | 20 min | List result identical | `git revert` |
| 4.12 | Refactor `BackupManager.delete_backup` body (CAUTION) | 20 min | Delete returns True for valid file | `git revert` |
| 4.13 | Refactor `BackupManager.cleanup_old_backups` body (CAUTION) | 20 min | Old backups removed, recent kept | `git revert` |
| 4.14 | Extract `BackupScheduler._run_scheduler` private helper (CAUTION) | 30 min | Scheduler still fires | `git revert` |
| 4.15 | End-to-end backup → restore roundtrip test | 30 min | SHA256 of restored DB == SHA256 of original | `git revert` |
| 4.16 | Run full pytest suite | 10 min | All tests pass | `git revert` |
| 4.17 | Code review (2 reviewers) + merge | 60 min | Both reviewers approve | n/a |

### Validation Gates
- [ ] All 11 import sites still resolve
- [ ] `pytest tests/test_backup_restore.py tests/test_backup_hardening.py -v` → 100%
- [ ] `pytest backup/services/ -v` → 100% (covers all 6 services that import from backup_system)
- [ ] `python manage.py create_backup --description smoke` succeeds
- [ ] Backup → restore roundtrip is byte-identical (SHA256)
- [ ] `pytest tests/ -q` → ≥1587 tests pass
- [ ] `InvariantRegistry.check_all()` → all 6 pass
- [ ] `ContractGuard.verify_all()` → all 4 pass
- [ ] No new warnings (`python -W error`)
- [ ] No query-count increase (CaptureQueriesContext)
- [ ] No memory growth (psutil 1000-iter loop)
- [ ] `git diff --stat` shows only 4 target files + extracted modules + rollback tests

### Rollback Gate
- [ ] `git revert` works cleanly
- [ ] All tests still pass after revert
- [ ] Backup roundtrip still works after revert

---

## 6. Cross-Step Gates

After each step is merged to `main`:

1. **Smoke test:** `pytest tests/ -q` shows ≥1587 pass.
2. **Validator rerun:** all 3 standalone validators return their Phase 5.9 baseline scores.
3. **Backup smoke:** `python manage.py create_backup --description post-step-N` and verify success.
4. **Production deploy:** deploy to staging → smoke test → deploy to prod (if staging passes).

If any cross-step gate fails, the step is rolled back per WS-F.

---

## 7. Final Answer to the Program Question

> **"What is the safest possible refactoring sequence that maximizes maintainability gains while minimizing certification risk?"**

**Answer:** Execute in the order **hardening → migration → gate → backup_system** (Steps 1-4 above).

| Rank | Target | Risk Score | ROI Score | Rollback Complexity | Validation Requirements |
|------|--------|------------|-----------|----------------------|--------------------------|
| 1 | hardening_validator.py | 1 (LOW) | 90 (HIGH) | 1 (single revert) | Validator rerun + pytest |
| 2 | migration_validator.py | 1 (LOW) | 90 (HIGH) | 1 (single revert) | Validator rerun + pytest |
| 3 | gate_validator.py | 1 (LOW) | 90 (HIGH) | 1 (single revert) | Validator rerun + pytest + screen check |
| 4 | backup_system.py | 3 (MEDIUM) | 65 (HIGH) | 2 (revert + 11 import smoke) | 4 test files + 6 service tests + roundtrip + InvariantRegistry + ContractGuard + 2 reviewers |

**Why this order:**

1. **Start with leaves, end with hubs.** The 3 standalone validators have ZERO inbound imports — they are the safest to refactor and the easiest to roll back. They build confidence in the extraction pattern.
2. **Validators first, services last.** Validators are CI-time tools. They are not on the request/response hot path. Errors are caught by humans reviewing the certification report.
3. **Backup system last.** It has 11 inbound imports and is on the REST hot path. By the time we reach it, the extraction pattern is battle-tested and the team has 3 successful refactors in the bank.
4. **Each step is independently revertable.** A failure at any step does not block the others.

---

## 8. Conclusion

- 4 steps, 7-12 hours of focused work.
- Steps 1-3 are LOW risk (leaves, no inbound imports).
- Step 4 is MEDIUM risk (11 inbound imports, hot path).
- Each step has explicit validation gates and rollback gates.
- The 10-point DoD (WS-G) gates every step.
- The plan protects the Phase 5.9 certification.
