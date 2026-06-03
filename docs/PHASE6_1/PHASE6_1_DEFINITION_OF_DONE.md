# WS-G: Definition of Done

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
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
