# WS-F: Rollback Strategy

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** For every proposed extraction, define the rollback trigger, rollback procedure, rollback validation, and rollback test suite.

---

## 1. Universal Rollback Discipline

**Every refactor PR is structured as 2 commits:**

1. **Commit 1 — REFACTOR:** the actual code movement.
2. **Commit 2 — TEST:** the verification that behavior is preserved.

**Rollback = `git revert <commit-1>` (and optionally commit-2).**

This is the simplest, fastest, and safest rollback. The merge to `main` is gated by the 10-point Definition of Done (WS-G); if any check fails post-merge, the refactor is reverted in a single commit.

---

## 2. Per-Target Rollback Plan

### 2.1 hardening_validator.py

| Step | Action |
|------|--------|
| Rollback trigger | (a) `run_pre_production_hardening()` returns a different score than the Phase 5.9 baseline (73/100); (b) any `validate_*` raises an exception not raised before; (c) the import resolution fails at app startup |
| Rollback procedure | `git revert <refactor-commit-sha>` and redeploy |
| Rollback validation | `python pre_production_hardening/hardening_validator.py` and diff output vs Phase 5.9 snapshot |
| Rollback test suite | (1) `python -c "from pre_production_hardening.hardening_validator import PreProductionHardeningValidator"` — must import OK. (2) `python pre_production_hardening/hardening_validator.py` — must run to completion. (3) Compare section_results dict to baseline. |

### 2.2 migration_validator.py

| Step | Action |
|------|--------|
| Rollback trigger | (a) `ProductionInfrastructureValidator.run_all()` returns a different `production_readiness_score` than baseline (76/100); (b) any `validate_*` raises an exception not raised before; (c) PostgreSQL connection check fails (false negative) |
| Rollback procedure | `git revert <refactor-commit-sha>` and redeploy |
| Rollback validation | `python production_infrastructure/migration_validator.py` and diff against Phase 5.9 snapshot |
| Rollback test suite | (1) Direct import. (2) Run validator. (3) Compare `report["section_results"]` to baseline dict. |

### 2.3 gate_validator.py

| Step | Action |
|------|--------|
| Rollback trigger | (a) `ProductionGateValidator.run_all()` returns a different `production_gate_score` than baseline (83/100); (b) any `validate_*` raises an exception not raised before; (c) frontend screen existence checks now report missing screens that exist |
| Rollback procedure | `git revert <refactor-commit-sha>` and redeploy |
| Rollback validation | `python production_gate/gate_validator.py` and diff against Phase 5.9 snapshot |
| Rollback test suite | (1) Direct import. (2) Run validator. (3) Compare `report["section_results"]` to baseline dict. (4) Verify all 9 required screens are still detected. |

### 2.4 backup_system.py

| Step | Action |
|------|--------|
| Rollback trigger | (a) `from backup.backup_system import BackupManager` raises ImportError; (b) `BackupManager.create_backup()` raises an exception not raised before; (c) backup metadata schema changes; (d) post-backup verification fails; (e) restore roundtrip produces a non-identical DB; (f) `BackupLog` write fails |
| Rollback procedure | `git revert <refactor-commit-sha>` and redeploy |
| Rollback validation | (1) All 11 import sites still resolve. (2) Create backup → restore roundtrip is byte-identical. (3) `tests/test_backup_restore.py` and `tests/test_backup_hardening.py` pass 100%. (4) `python manage.py create_backup --description smoke` succeeds. |
| Rollback test suite | (1) `python -c "from backup.backup_system import BackupManager, BackupValidator, BackupEncryptor, BackupConfig; print('OK')"`. (2) `pytest tests/test_backup_restore.py tests/test_backup_hardening.py -v`. (3) `pytest backup/services/ -v` (covers all 6 services that import from backup_system). (4) End-to-end: create → restore → diff. (5) Verify BackupLog rows are written correctly. |

---

## 3. Rollback Trigger Matrix

| Trigger | Detection Method | Severity | Auto-Rollback? |
|---------|------------------|----------|----------------|
| ImportError at app startup | gunicorn worker boot logs | CRITICAL | YES (block deploy) |
| Validator score change > 0 | Phase 5.x baseline diff | HIGH | NO (manual review) |
| `BackupManager.create_backup` failure | `tests/test_backup_hardening.py` | CRITICAL | YES (block merge) |
| Backup metadata schema change | JSON diff in `tests/test_backup_restore.py` | HIGH | NO (manual review) |
| Restore roundtrip non-byte-identical | SHA256 diff in smoke test | CRITICAL | YES (block merge) |
| `BackupLog` write failure | `tests/test_backup_hardening.py` | MEDIUM | NO (manual review) |
| ORM query count delta > 0 | `CaptureQueriesContext` assertion | HIGH | NO (manual review) |
| Performance regression > 5% | time.perf_counter() in test | HIGH | NO (manual review) |
| `BackupValidator.calculate_checksum` returns wrong value | integrity test | CRITICAL | YES (block merge) |

---

## 4. Rollback Validation Protocol

After any rollback, run the following in order:

1. **Service health check:** `curl http://localhost:8000/api/health/` returns 200.
2. **Auth flow check:** `curl -X POST http://localhost:8000/api/security/login/ -d '{"username":"test","password":"test"}'` returns a valid token.
3. **Backup roundtrip:** create a backup, restore it, SHA256-compare.
4. **Validator rerun:** run the 3 standalone validators; scores must match Phase 5.9 baseline.
5. **Test suite:** `pytest tests/ -q` — must show ≥1587 tests passing (the existing baseline).
6. **Coverage check:** `pytest --cov=backend --cov-report=term-missing` — must not drop below 85% in CRITICAL modules.

---

## 5. Rollback Test Suite (Common)

These tests are added to `tests/test_rollback_safety.py` (already exists, will be extended):

```python
def test_rollback_hardening_import():
    from pre_production_hardening.hardening_validator import PreProductionHardeningValidator
    assert PreProductionHardeningValidator is not None

def test_rollback_migration_import():
    from production_infrastructure.migration_validator import ProductionInfrastructureValidator
    assert ProductionInfrastructureValidator is not None

def test_rollback_gate_import():
    from production_gate.gate_validator import ProductionGateValidator
    assert ProductionGateValidator is not None

def test_rollback_backup_import():
    from backup.backup_system import BackupManager, BackupValidator, BackupEncryptor
    assert BackupManager is not None
    assert BackupValidator is not None
    assert BackupEncryptor is not None

def test_rollback_backup_roundtrip(tmp_path):
    bm = BackupManager(config={'backup_dir': str(tmp_path), ...})
    result = bm.create_backup(description='rollback_test')
    assert result['success']
    # Note: actual roundtrip requires the real DB path; this is a smoke test
```

---

## 6. Multi-Stage Rollback

If multiple extractions are merged in a single PR, rollback is **per-commit**, not per-PR. Each commit is independently revertable. The PR description must enumerate the commits in dependency order.

---

## 7. Conclusion

- Rollback is a **single `git revert`** per refactor commit.
- Validation is **byte-for-byte comparison** against the Phase 5.9 baseline.
- Test suite additions are pre-defined (rollback smoke tests).
- Auto-rollback triggers cover CRITICAL failures; HIGH/MEDIUM triggers require human review.
- The system can be restored to the certified state in **< 5 minutes** (revert + redeploy).
