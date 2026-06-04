"""
Phase 6.1 - Reports Part 3: WS-F, WS-G, WS-H
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(r"E:\all downloads\Pharmacy_ERP")
DOCS = ROOT / "docs" / "PHASE6_1"
EV = DOCS / "evidence"

ev = json.loads((EV / "target_structures.json").read_text(encoding="utf-8"))
ext = json.loads((EV / "extraction_plan.json").read_text(encoding="utf-8"))
AUDIT_ID = ev["audit_id"]
TS = ev["ts"]
TARGETS = ev["targets"]

# =============================================================================
# WS-F: ROLLBACK STRATEGY
# =============================================================================
ws_f = f"""# WS-F: Rollback Strategy

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
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
2. **Auth flow check:** `curl -X POST http://localhost:8000/api/security/login/ -d '{{"username":"test","password":"test"}}'` returns a valid token.
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
    bm = BackupManager(config={{'backup_dir': str(tmp_path), ...}})
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
"""
(DOCS / "PHASE6_1_ROLLBACK_PLAN.md").write_text(ws_f, encoding="utf-8")
print("[WS-F] written")

# =============================================================================
# WS-G: DEFINITION OF DONE
# =============================================================================
ws_g = f"""# WS-G: Definition of Done

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
**Purpose:** The 10 non-negotiable conditions that MUST be true before any refactor is considered complete. If any condition fails, the refactor is REJECTED.

---

## The 10 Conditions

### 1. Existing tests pass

**Verification:** `pytest tests/ -q` — must show the same test count and pass count as the Phase 5.9 baseline (≥1587 tests passing, 0 failures, 0 errors).

**For backup_system specifically:** `pytest tests/test_backup_restore.py tests/test_backup_hardening.py -v` — must show 100% pass.

**For all 4 targets:** `pytest tests/test_rollback_safety.py -v` (extended with new smoke tests) — must pass.

### 2. No new warnings

**Verification:** `python -W error -c "from <target_module> import *"` — must not raise any warning. Specifically:
- `DeprecationWarning` for any stdlib or Django API
- `PendingDeprecationWarning`
- `SyntaxWarning`
- `RuntimeWarning` for inefficient patterns
- `UserWarning` from Django (e.g., for non-atomic requests)

**Tool:** run pytest with `-W error` to promote all warnings to errors.

### 3. No query-count increase

**Verification:** For every method in WS-A's behavioral baseline, run with `CaptureQueriesContext`:

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as ctx:
    method_under_test()
assert len(ctx.captured_queries) == BASELINE_QUERY_COUNT
```

For validators: the baseline query count is whatever the original method produced (measured during refactor preparation). For `BackupManager.create_backup`: **0 queries** (no ORM calls in the hot path).

### 4. No query-plan change

**Verification:** For every SQL query captured in condition #3, run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` before and after the refactor. The JSON must be byte-identical (after whitespace normalization).

**Tool:** `psql -c "EXPLAIN ANALYZE ..."` and JSON diff.

**Note:** Validators in this codebase target SQLite (test) and PostgreSQL (production). The SQLite plan is the reference; the PG plan must not regress.

### 5. No memory growth

**Verification:** Run the validator / backup cycle 1000 times and measure RSS:

```python
import psutil, os, gc
gc.collect()
process = psutil.Process(os.getpid())
rss_before = process.memory_info().rss
for _ in range(1000):
    method_under_test()
gc.collect()
rss_after = process.memory_info().rss
assert rss_after < rss_before * 1.05  # < 5% growth
```

**Reference:** Phase 5.9 WS-E baseline shows 0% growth over 24h simulation. The refactor must maintain this.

### 6. No UI latency regression

**Verification:** Not applicable for the 3 standalone validators (no UI). For `backup_system`:

- The `frontend/ui/system/backup_screen.py` calls `BackupManager` through the REST API. Latency is measured at the REST endpoint level.
- `time.perf_counter()` around the backup list endpoint: must be <100ms (Phase 5.9 baseline).

### 7. No accounting regression

**Verification:** `InvariantRegistry` check:

```python
from governance.invariant_registry import InvariantRegistry
registry = InvariantRegistry()
results = registry.check_all()
assert all(r.passed for r in results), "Accounting invariant failed: " + str([r for r in results if not r.passed])
```

Specifically:
- **JOURNAL_ENTRY** invariant must pass (sum of debits = sum of credits)
- **STOCK** invariant must pass (sum of movements = batch remaining)
- **AR_AP** invariant must pass
- **ACCOUNTING_EQUATION** invariant must pass (Assets = Liab + Equity)

### 8. No inventory regression

**Verification:** `InvariantRegistry.STOCK` check + `Batch.objects.count()` matches expected value before/after refactor. For backup roundtrip: stock movements table is byte-identical after restore.

### 9. No API regression

**Verification:** `ContractGuard` check:

```python
from governance.contract_guard import ContractGuard
guard = ContractGuard()
results = guard.verify_all()
assert all(r.passed for r in results)
```

Specifically:
- `response_format` contract: all backup endpoints return the standard `success/data/meta` envelope.
- `error_format` contract: error responses return the standard `success/error/meta` envelope.
- `endpoint_naming` contract: backup endpoints follow kebab-case.
- `pagination_signature` contract: `list_backups` endpoint returns `count/next/previous/results` keys.

### 10. No architecture violation

**Verification:** Static check that the refactor does NOT introduce:

- A new framework (Django, DRF, PySide6, cryptography are the only allowed)
- A new dependency in `requirements.txt`
- A migration file (0001-* through latest)
- A model change (no `models.py` edits in scope)
- A new URL pattern
- A new permission class
- A change to the import path of any public symbol

**Tool:** `git diff --stat` must show changes ONLY in the 4 target files + their extracted modules + the rollback test file.

---

## Per-Target DoD Checklist

| # | Condition | hardening | migration | gate | backup_system |
|---|-----------|-----------|-----------|------|---------------|
| 1 | Existing tests pass | ✓ (no direct tests; indirect = validator rerun matches baseline) | ✓ | ✓ | ✓ (4 test files + 6 service tests) |
| 2 | No new warnings | ✓ | ✓ | ✓ | ✓ |
| 3 | No query-count increase | ✓ (read-only ORM, no change) | ✓ | ✓ | ✓ (BackupManager is 0-ORM) |
| 4 | No query-plan change | ✓ | ✓ | ✓ | ✓ (no SQL) |
| 5 | No memory growth | ✓ | ✓ | ✓ | ✓ |
| 6 | No UI latency regression | n/a | n/a | n/a | ✓ (REST endpoint) |
| 7 | No accounting regression | ✓ (read-only) | ✓ (read-only) | n/a | ✓ (BackupLog + BackupRecord) |
| 8 | No inventory regression | ✓ (read-only) | ✓ (read-only) | n/a | ✓ (no inventory table access) |
| 9 | No API regression | n/a | n/a | n/a | ✓ (ContractGuard) |
| 10 | No architecture violation | ✓ | ✓ | ✓ | ✓ |

---

## Gate Sequence (in order)

1. Run `pytest tests/ -q` → must show ≥1587 pass.
2. Run `pytest tests/test_backup_restore.py tests/test_backup_hardening.py -v` → 100% pass.
3. Run `pytest tests/test_rollback_safety.py -v` → 100% pass (new smoke tests added).
4. Run `python -W error -c "from <module> import <class>"` for each target.
5. Run validators and diff scores vs Phase 5.9 baseline (73 / 76 / 83).
6. Run `InvariantRegistry.check_all()` → all 6 invariants pass.
7. Run `ContractGuard.verify_all()` → all 4 contracts pass.
8. Run `git diff --stat` → confirm no scope creep.
9. Run `time.perf_counter()` performance smoke → ≤5% regression.
10. Run `psutil` memory smoke → ≤5% growth.
11. Manual code review → 2 reviewers required for backup_system, 1 for others.
12. Manual smoke: run `python manage.py create_backup --description refactor_smoke` and verify success.

If all 12 gates pass, the refactor is **DONE**.

---

## Conclusion

The 10 conditions + 12 gates form an objective, measurable Definition of Done. A refactor is **not complete** until all gates pass. Any failed gate triggers a rollback (WS-F).
"""
(DOCS / "PHASE6_1_DEFINITION_OF_DONE.md").write_text(ws_g, encoding="utf-8")
print("[WS-G] written")

# =============================================================================
# WS-H: EXECUTION PLAN
# =============================================================================
ws_h = f"""# WS-H: Execution Plan

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
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
"""
(DOCS / "PHASE6_1_EXECUTION_PLAN.md").write_text(ws_h, encoding="utf-8")
print("[WS-H] written")
print("WS-F, G, H complete.")
