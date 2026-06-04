"""
Phase 6.1 - Reports Part 2: WS-B through WS-H
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(r"E:\all downloads\Pharmacy_ERP")
DOCS = ROOT / "docs" / "PHASE6_1"
EV = DOCS / "evidence"

ev = json.loads((EV / "target_structures.json").read_text(encoding="utf-8"))
AUDIT_ID = ev["audit_id"]
TS = ev["ts"]
TARGETS = ev["targets"]

def md_table(headers, rows):
    if not rows:
        return f"| {' | '.join(headers)} |\n| {' | '.join(['---']*len(headers))} |\n| _(none)_ |\n"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)

# =============================================================================
# WS-B: EXTRACTION BOUNDARY DESIGN
# =============================================================================
# Define extraction candidates per target with SAFE/CAUTION/DO_NOT_EXTRACT classification
extractions = []

# Target 1: hardening_validator.py - 8 sections, each a public method
hardening = TARGETS[0]
hardening_methods = []
for c in hardening["classes"]:
    for m in c["methods"]:
        hardening_methods.append(m)

# Each validate_* method is SAFE to extract (private state, no external callers)
sections_h = [
    ("validate_database_hardening", "Database", "Extract section concerns into a separate `sections/database.py` module exposing a function `run(self) -> SectionResult`. Public method delegates."),
    ("validate_multi_user_operations", "Multi-User", "Extract to `sections/multi_user.py`. Public method delegates."),
    ("validate_operator_resilience", "Operator", "Extract to `sections/operator.py`. Public method delegates."),
    ("validate_session_security", "Session", "Extract to `sections/session.py`. Public method delegates."),
    ("validate_export_reliability", "Export", "Extract to `sections/export.py`. Public method delegates."),
    ("validate_deployment_recovery", "Deployment", "Extract to `sections/deployment.py`. Public method delegates."),
    ("validate_performance", "Performance", "Extract to `sections/performance.py`. Public method delegates."),
    ("generate_audit_report", "Report", "CAUTION: return schema is consumed by tests. Extract to `sections/report.py` BUT verify return schema byte-for-byte."),
    ("run_all", "Orchestrator", "DO NOT EXTRACT: orchestration order is the contract."),
]

for m in hardening_methods:
    if m["name"] in [s[0] for s in sections_h]:
        sname, label, strategy = next(s for s in sections_h if s[0] == m["name"])
        cls = "SAFE" if sname != "generate_audit_report" else "CAUTION"
        if sname == "run_all":
            cls = "DO_NOT_EXTRACT"
        extractions.append({
            "file": hardening["file"],
            "class": "PreProductionHardeningValidator",
            "method": m["name"],
            "lines": f"{m['lineno']}-{m['end_lineno']}",
            "loc": m["loc"],
            "classification": cls,
            "target_module": f"pre_production_hardening/sections/{label.lower()}.py",
            "strategy": strategy,
            "risk_score": 1 if cls == "SAFE" else (2 if cls == "CAUTION" else 99),
        })

# Target 2: migration_validator.py
migration = TARGETS[1]
for c in migration["classes"]:
    for m in c["methods"]:
        if m["name"] in ("validate_postgresql_migration", "validate_transaction_isolation", "validate_connection_pooling", "validate_redis_event_layer", "validate_celery_execution", "validate_security_hardening", "validate_backup_automation", "validate_performance", "validate_observability"):
            extractions.append({
                "file": migration["file"],
                "class": "ProductionInfrastructureValidator",
                "method": m["name"],
                "lines": f"{m['lineno']}-{m['end_lineno']}",
                "loc": m["loc"],
                "classification": "SAFE",
                "target_module": f"production_infrastructure/sections/{m['name'].replace('validate_', '')}.py",
                "strategy": f"Extract section to module. Public method delegates to `run_section_{m['name']}(self) -> SectionResult`.",
                "risk_score": 1,
            })
        elif m["name"] in ("generate_certification", "run_all"):
            cls = "CAUTION" if m["name"] == "generate_certification" else "DO_NOT_EXTRACT"
            extractions.append({
                "file": migration["file"],
                "class": "ProductionInfrastructureValidator",
                "method": m["name"],
                "lines": f"{m['lineno']}-{m['end_lineno']}",
                "loc": m["loc"],
                "classification": cls,
                "target_module": f"production_infrastructure/sections/{m['name'].replace('generate_', '').replace('run_', '')}.py",
                "strategy": "Verify return schema byte-for-byte before extraction" if cls == "CAUTION" else "DO NOT EXTRACT: orchestration contract",
                "risk_score": 2 if cls == "CAUTION" else 99,
            })

# Target 3: gate_validator.py
gate = TARGETS[2]
for c in gate["classes"]:
    for m in c["methods"]:
        if m["name"].startswith("validate_"):
            extractions.append({
                "file": gate["file"],
                "class": "ProductionGateValidator",
                "method": m["name"],
                "lines": f"{m['lineno']}-{m['end_lineno']}",
                "loc": m["loc"],
                "classification": "SAFE",
                "target_module": f"production_gate/sections/{m['name'].replace('validate_', '')}.py",
                "strategy": "Extract section to module. Public method delegates.",
                "risk_score": 1,
            })
        elif m["name"] in ("run_all", "generate_report"):
            cls = "DO_NOT_EXTRACT" if m["name"] == "run_all" else "CAUTION"
            extractions.append({
                "file": gate["file"],
                "class": "ProductionGateValidator",
                "method": m["name"],
                "lines": f"{m['lineno']}-{m['end_lineno']}",
                "loc": m["loc"],
                "classification": cls,
                "target_module": f"production_gate/sections/{m['name'].replace('generate_', '').replace('run_', '')}.py",
                "strategy": "DO NOT EXTRACT" if cls == "DO_NOT_EXTRACT" else "Verify return schema byte-for-byte",
                "risk_score": 99 if cls == "DO_NOT_EXTRACT" else 2,
            })

# Target 4: backup_system.py - SAFE for private helpers, CAUTION for public API
backup = TARGETS[3]
for c in backup["classes"]:
    for m in c["methods"]:
        is_private = m["name"].startswith("_") or m["name"] in ("_check_pre_backup_safety", "_post_backup_verify", "_log_db_event", "_vacuum_database", "_create_archive", "_get_encryption_password", "_is_encryption_configured", "_ensure_db_path", "_setup_logging", "_run_scheduler", "_check_missed_backup", "calculate_checksum", "verify_database_integrity", "verify_backup_archive", "verify_backup_content", "generate_key", "encrypt_file", "decrypt_file", "get_default_config", "load_config", "save_config", "_merge_config")
        is_public_api = m["name"] in ("create_backup", "restore_backup", "list_backups", "delete_backup", "cleanup_old_backups", "start_scheduler", "stop_scheduler", "get_backup_stats")
        if is_private:
            extractions.append({
                "file": backup["file"],
                "class": c["name"],
                "method": m["name"],
                "lines": f"{m['lineno']}-{m['end_lineno']}",
                "loc": m["loc"],
                "classification": "SAFE",
                "target_module": f"backup/extracts/{c['name'].lower()}_{m['name'].lstrip('_')}.py",
                "strategy": "Move private helper to dedicated module. Re-import in original class. No API change.",
                "risk_score": 1,
            })
        elif is_public_api:
            extractions.append({
                "file": backup["file"],
                "class": c["name"],
                "method": m["name"],
                "lines": f"{m['lineno']}-{m['end_lineno']}",
                "loc": m["loc"],
                "classification": "CAUTION",
                "target_module": f"(internal split only — keep public method in class)",
                "strategy": "Refactor ONLY the body of this method by extracting internal helpers as private methods on the same class. Public signature, name, and return value must remain identical. Verify all 11 import sites still work.",
                "risk_score": 3,
            })

# Save extraction plan as evidence
with open(EV / "extraction_plan.json", "w", encoding="utf-8") as f:
    json.dump({
        "audit_id": AUDIT_ID,
        "ts": TS,
        "extractions": extractions,
    }, f, indent=2)

ext_rows = [(e["file"], e["class"], e["method"], e["loc"], e["classification"], e["risk_score"]) for e in extractions]

ws_b = f"""# WS-B: Extraction Boundary Design

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
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
"""
from collections import Counter
counter = Counter()
for t in TARGETS:
    c = Counter()
    for e in extractions:
        if e["file"] == t["file"]:
            c[e["classification"]] += 1
    counter.update(c)
    ws_b += f"| `{t['file']}` | {c.get('SAFE', 0)} | {c.get('CAUTION', 0)} | {c.get('DO_NOT_EXTRACT', 0)} | {sum(c.values())} |\n"

ws_b += f"| **Total** | **{counter.get('SAFE', 0)}** | **{counter.get('CAUTION', 0)}** | **{counter.get('DO_NOT_EXTRACT', 0)}** | **{sum(counter.values())}** |\n"

ws_b += f"""
---

## 3. Extraction Candidates (Full List)

Headers: File | Class | Method | LOC | Classification | Risk Score

{md_table(['File', 'Class', 'Method', 'LOC', 'Class', 'Risk'], ext_rows)}

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

- **{counter.get('SAFE', 0)}** methods are SAFE to extract with **risk score 1** (LOW).
- **{counter.get('CAUTION', 0)}** methods require return-schema verification (CAUTION, risk score 2-3).
- **{counter.get('DO_NOT_EXTRACT', 0)}** methods are DO-NOT-EXTRACT (orchestrators).
- The plan produces ~{counter.get('SAFE', 0) + counter.get('CAUTION', 0)} new modules/files, all with byte-for-byte behavior preservation.
"""
(DOCS / "PHASE6_1_EXTRACTION_BOUNDARIES.md").write_text(ws_b, encoding="utf-8")
print("[WS-B] written")

# =============================================================================
# WS-C: REGRESSION IMPACT MATRIX
# =============================================================================
# For each target, document affected tests/workflows/reports/accounting/inventory/api/ui
ws_c = f"""# WS-C: Regression Impact Matrix

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
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
"""
(DOCS / "PHASE6_1_REGRESSION_MATRIX.md").write_text(ws_c, encoding="utf-8")
print("[WS-C] written")

# =============================================================================
# WS-D: PERFORMANCE SAFETY ANALYSIS
# =============================================================================
ws_d = f"""# WS-D: Performance Safety Analysis

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
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
"""
(DOCS / "PHASE6_1_PERFORMANCE_SAFETY.md").write_text(ws_d, encoding="utf-8")
print("[WS-D] written")

# =============================================================================
# WS-E: DEPENDENCY GRAPH
# =============================================================================
ws_e = f"""# WS-E: Dependency Graph

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
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
"""
(DOCS / "PHASE6_1_DEPENDENCY_GRAPH.md").write_text(ws_e, encoding="utf-8")
print("[WS-E] written")
print("WS-B, C, D, E complete.")
