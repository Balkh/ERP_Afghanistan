# WS-D: Performance Safety Analysis

**Audit ID:** `PHASE6_1_20260602_160604`  
**Generated:** 2026-06-02T16:06:04.276867  
**Purpose:** Predict and document the worst-case performance impact of every proposed extraction.

---

## 1. Performance Baseline (Phase 5.9)

| Metric | Baseline | Tolerance |
|--------|----------|-----------|
| Hardening validator full run | ~30s on seeded DB | ±5% |
| Migration validator full run | ~25s on seeded DB | ±5% |
| Gate validator full run | ~20s on seeded DB | ±5% |
| Backup creation (200MB DB) | ~8s + archive | ±5% |
| Backup restoration (200MB DB) | ~12s + WAL replay | ±5% |
| Backup listing (10K records) | <100ms | ±5% |
| `BackupManager.create_backup` query count | 0 (no Django ORM calls) | 0 delta |
| `BackupManager.restore_backup` query count | 0 (no Django ORM calls) | 0 delta |

---

## 2. Worst-Case Impact Prediction per Refactor Type

### 2.1 SAFE Extraction (private helper → module function)

| Property | Predicted Impact | Rationale |
|----------|------------------|-----------|
| ORM query count | **0 delta** | The extracted function uses the same `self.issues`/`self.results` and the same ORM calls |
| Query plan | **identical** | Same WHERE clauses, same joins |
| Memory | **0 delta** | Function-level locals move with the function |
| Latency | **0 delta** | Python function call overhead is ~50ns; the validator runs for ~30s — negligible |
| Transaction scope | **identical** | The `with transaction.atomic():` block moves with the code |

**Verdict:** SAFE extractions are **PERFORMANCE-NEUTRAL**.

### 2.2 CAUTION Extraction (public method body → internal helpers)

| Property | Predicted Impact | Rationale |
|----------|------------------|-----------|
| ORM query count | **0 delta** | The ORM calls stay in the public method body |
| Query plan | **identical** | No SQL change |
| Memory | **0 delta** | Locals stay as locals |
| Latency | **+~0.1%** (one extra Python function call) | Negligible |
| Transaction scope | **identical** | The `with` blocks stay intact |

**Verdict:** CAUTION extractions are **PERFORMANCE-NEUTRAL OR NEGLIGIBLE** (<0.1% overhead).

### 2.3 DO NOT EXTRACT (orchestrators)

| Property | Predicted Impact |
|----------|------------------|
| All | **0 delta — not touched** |

---

## 3. Specific Hot-Path Analysis

### 3.1 hardening_validator.py `validate_performance` (line 1104-1298, ~195 LOC)

This method runs 7 performance tests. The most expensive ones:

- `JournalEntryLine.objects.all()[:5000]` — loads 5K lines into memory
- `Account.objects.all()` followed by `acct.balance` for each — N+1 pattern, but READ-ONLY
- `Paginator(all_journals, 50)` — pagination stability test

**Refactor impact:** if the body is split into 7 private helpers, the test logic moves with it. No additional ORM calls. No additional memory.

**Worst-case:** if a refactor accidentally wraps the body in a function that takes `self` by reference and re-calls `Account.objects.all()` — that would double the query count. **Mitigation:** WS-G DoD rule #3 forbids this.

### 3.2 backup_system.py `BackupManager.create_backup` (line 332-481, ~150 LOC)

This is a **HOT PATH** (called from REST endpoint and management command).

Steps:
1. `_check_pre_backup_safety()` — disk usage + DB connectivity check
2. `_vacuum_database()` — `VACUUM` (SQLite only)
3. `shutil.copy2()` — copy DB to temp
4. `verify_database_integrity()` — open + close DB
5. `_create_archive()` — tarfile
6. `encrypt_file()` (if configured) — Fernet
7. `shutil.move()` to backup dir
8. `calculate_checksum()` — SHA256 of file
9. Write metadata JSON
10. `_post_backup_verify()` — re-checksum
11. `cleanup_old_backups()`

**Refactor impact:** the steps are already private methods. Extracting them to modules does not change the call sequence. The worst case is:
- If extraction accidentally opens a new file handle per step — that would add `O(steps)` syscalls. The current code opens 1 handle per step already. **0 delta.**
- If extraction accidentally re-reads the config from disk per step — that would add latency. The current code reads it once in `__init__`. **0 delta.**

**Verdict:** SAFE.

### 3.3 backup_system.py `BackupManager.restore_backup` (line 546-654, ~108 LOC)

Steps:
1. Verify backup file exists
2. Decrypt (if encrypted)
3. Extract archive
4. Verify checksum
5. `shutil.copy2()` to target DB path
6. Verify target DB integrity
7. Return result dict

**Refactor impact:** identical to create_backup. **0 delta.**

---

## 4. Performance Anti-Patterns to Avoid

These MUST NOT appear in any extracted code:

| Anti-pattern | Why forbidden | Detection |
|--------------|---------------|-----------|
| Re-importing Django settings inside a function | Adds ~5ms per call; current code imports once | Linter / code review |
| Re-creating `logging.getLogger()` per call | Adds overhead; current code has module-level logger | Linter |
| Wrapping `with transaction.atomic():` in a new block that already has one | Doubles transaction scope | Code review |
| Adding `time.sleep()` in a refactored helper | Adds latency silently | Linter / git diff |
| Calling `.count()` before `.exists()` | Doubles the count query | Code review |
| Reading config from disk in a helper instead of using `self.config` | Adds file I/O per call | Code review |

---

## 5. Performance Test Plan

For each refactor, run the following BEFORE merge:

```python
def test_refactor_performance_neutrality():
    # 1. Validator runtime
    start = time.perf_counter()
    run_pre_production_hardening()  # or the relevant validator
    duration = time.perf_counter() - start
    assert duration < BASELINE * 1.05, "Validator regression: " + str(duration)

    # 2. Backup create/restore roundtrip
    start = time.perf_counter()
    bm = BackupManager()
    result = bm.create_backup(description="refactor_smoke")
    assert result["success"] is True
    duration_create = time.perf_counter() - start

    start = time.perf_counter()
    restore_result = bm.restore_backup(result["backup_path"])
    assert restore_result["success"] is True
    duration_restore = time.perf_counter() - start

    assert duration_create < BASELINE_CREATE * 1.05
    assert duration_restore < BASELINE_RESTORE * 1.05

    # 3. Query count
    with CaptureQueriesContext(connection) as ctx:
        bm.list_backups()
    assert len(ctx.captured_queries) == 0  # BackupManager does not hit Django ORM in list_backups
```

---

## 6. Conclusion

- All SAFE extractions are **performance-neutral** (0 delta).
- All CAUTION extractions are **performance-neutral to negligible** (<0.1% overhead).
- DO-NOT-EXTRACT items are not touched.
- The Phase 5.9 baseline is the reference; any refactor that exceeds the 5% tolerance in any metric is **REJECTED**.
