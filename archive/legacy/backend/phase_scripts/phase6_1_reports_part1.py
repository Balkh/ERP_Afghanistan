"""
Phase 6.1 - Safe Refactor Execution Plan - Master Report Generator
Produces 8 planning documents (no code changes).

Targets:
  1. pre_production_hardening/hardening_validator.py (1460 LOC)
  2. production_infrastructure/migration_validator.py (1080 LOC)
  3. production_gate/gate_validator.py (726 LOC)
  4. backup/backup_system.py (954 LOC)
"""
import os
import re
import ast
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, OrderedDict

ROOT = Path(r"E:\all downloads\Pharmacy_ERP")
DOCS = ROOT / "docs" / "PHASE6_1"
EV = DOCS / "evidence"
EV.mkdir(parents=True, exist_ok=True)

AUDIT_ID = "PHASE6_1_" + datetime.now().strftime("%Y%m%d_%H%M%S")
TS = datetime.now().isoformat()

TARGETS = [
    {
        "name": "PreProductionHardeningValidator",
        "file": "backend/pre_production_hardening/hardening_validator.py",
        "path": ROOT / "backend" / "pre_production_hardening" / "hardening_validator.py",
        "loc": 1460,
        "kind": "validator",
        "import_sites": [],
    },
    {
        "name": "ProductionInfrastructureValidator",
        "file": "backend/production_infrastructure/migration_validator.py",
        "path": ROOT / "backend" / "production_infrastructure" / "migration_validator.py",
        "loc": 1080,
        "kind": "validator",
        "import_sites": [],
    },
    {
        "name": "ProductionGateValidator",
        "file": "backend/production_gate/gate_validator.py",
        "path": ROOT / "backend" / "production_gate" / "gate_validator.py",
        "loc": 726,
        "kind": "validator",
        "import_sites": [],
    },
    {
        "name": "BackupManager + BackupValidator + BackupEncryptor + BackupConfig",
        "file": "backend/backup/backup_system.py",
        "path": ROOT / "backend" / "backup" / "backup_system.py",
        "loc": 954,
        "kind": "service",
        "import_sites": [
            "backend/backup/views.py",
            "backend/backup/services/restore_service.py",
            "backend/backup/services/restore_testing.py",
            "backend/backup/services/health_monitor.py",
            "backend/backup/services/failure_injection.py",
            "backend/backup/services/control_plane.py",
            "backend/backup/management/commands/cleanup_backups.py",
            "backend/backup/management/commands/restore_backup.py",
            "backend/backup/management/commands/create_backup.py",
            "backend/config/tasks.py",
            "backend/tests/test_backup_hardening.py",
        ],
    },
]

def md_table(headers, rows):
    if not rows:
        return f"| {' | '.join(headers)} |\n| {' | '.join(['---']*len(headers))} |\n| _(none)_ |\n"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)

# =============================================================================
# Static analysis pass over the 4 target files
# =============================================================================
def analyze_target(target):
    """Return AST-derived structure of a target file."""
    src = target["path"].read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, filename=str(target["path"]))

    classes = []
    module_funcs = []
    imports = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef):
            cls_methods = [m for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({
                "name": n.name,
                "lineno": n.lineno,
                "end_lineno": n.end_lineno or 0,
                "loc": (n.end_lineno or 0) - (n.lineno or 0) + 1,
                "method_count": len(cls_methods),
                "methods": [
                    {
                        "name": m.name,
                        "lineno": m.lineno,
                        "end_lineno": m.end_lineno or 0,
                        "loc": (m.end_lineno or 0) - (m.lineno or 0) + 1,
                        "is_public": not m.name.startswith("_") or m.name in ("__init__", "__post_init__"),
                        "args": [a.arg for a in m.args.args],
                    }
                    for m in cls_methods
                ],
            })
        elif isinstance(n, ast.FunctionDef) and n.col_offset == 0:
            module_funcs.append({
                "name": n.name,
                "lineno": n.lineno,
                "end_lineno": n.end_lineno or 0,
                "loc": (n.end_lineno or 0) - (n.lineno or 0) + 1,
                "is_public": not n.name.startswith("_"),
            })
        if isinstance(n, ast.Import):
            for a in n.names:
                imports.append(a.name)
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            for a in n.names:
                imports.append(f"{mod}.{a.name}" if mod else a.name)

    return {
        "src_lines": src.split("\n"),
        "classes": classes,
        "module_funcs": module_funcs,
        "imports": sorted(set(imports)),
    }

# Run static analysis
for t in TARGETS:
    t["analysis"] = analyze_target(t)

# Save raw data
with open(EV / "target_structures.json", "w", encoding="utf-8") as f:
    json.dump({
        "audit_id": AUDIT_ID,
        "ts": TS,
        "targets": [
            {
                "name": t["name"],
                "file": t["file"],
                "loc": t["loc"],
                "kind": t["kind"],
                "import_sites": t["import_sites"],
                "classes": t["analysis"]["classes"],
                "module_funcs": t["analysis"]["module_funcs"],
            }
            for t in TARGETS
        ],
    }, f, indent=2)
print("[evidence] target_structures.json written")

# =============================================================================
# WS-A: BEHAVIORAL BASELINE
# =============================================================================
ws_a_sections = []

for t in TARGETS:
    sec = f"""## Target: `{t['file']}` ({t['loc']} LOC)

**Class:** `{t['name']}`  
**Kind:** {t['kind']}  
**Import sites:** {len(t['import_sites'])}  
**Classes in file:** {len(t['analysis']['classes'])}  
**Module-level functions:** {len(t['analysis']['module_funcs'])}

### Public Methods

| Method | Lines | LOC | Public | Args |
|--------|-------|-----|--------|------|
"""
    for c in t["analysis"]["classes"]:
        for m in c["methods"]:
            if m["is_public"] and not m["name"].startswith("__"):
                args = ", ".join(m["args"][:6]) + ("..." if len(m["args"]) > 6 else "")
                sec += f"| `{c['name']}.{m['name']}` | {m['lineno']}-{m['end_lineno']} | {m['loc']} | YES | `{args}` |\n"

    sec += f"""
### Internal/Private Methods

| Method | Lines | LOC | Purpose (inferred) |
|--------|-------|-----|---------------------|
"""
    for c in t["analysis"]["classes"]:
        for m in c["methods"]:
            if not m["is_public"]:
                sec += f"| `{c['name']}.{m['name']}` | {m['lineno']}-{m['end_lineno']} | {m['loc']} | (helper) |\n"

    sec += f"""
### Module-Level Functions

| Function | Lines | LOC | Public |
|----------|-------|-----|--------|
"""
    for f in t["analysis"]["module_funcs"]:
        sec += f"| `{f['name']}` | {f['lineno']}-{f['end_lineno']} | {f['loc']} | {'YES' if f['is_public'] else 'no'} |\n"

    # Behavioral characteristics
    sec += f"""
### Behavioral Characteristics

| Dimension | Description |
|-----------|-------------|
| **Public surface** | {sum(1 for c in t['analysis']['classes'] for m in c['methods'] if m['is_public'] and not m['name'].startswith('__'))} public methods, {sum(1 for c in t['analysis']['classes'] for m in c['methods'] if not m['is_public'])} private methods |
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
"""
    ws_a_sections.append(sec)

ws_a = f"""# WS-A: Behavioral Baseline

**Audit ID:** `{AUDIT_ID}`  
**Generated:** {TS}  
**Purpose:** Document the complete behavioral contract of each of the 4 Wave-1 refactor targets BEFORE any code is modified. This is the contract that the refactor must preserve.

---

## Wave-1 Refactor Targets

| # | File | LOC | Classes | Public Methods | Import Sites | Risk Profile |
|---|------|-----|---------|----------------|--------------|--------------|
"""
for i, t in enumerate(TARGETS, 1):
    public_count = sum(1 for c in t["analysis"]["classes"] for m in c["methods"] if m["is_public"] and not m["name"].startswith("__"))
    ws_a += f"| {i} | `{t['file']}` | {t['loc']} | {len(t['analysis']['classes'])} | {public_count} | {len(t['import_sites'])} | {t['kind'].upper()} |\n"

ws_a += f"""
---

{chr(10).join(ws_a_sections)}

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
"""
(DOCS / "PHASE6_1_BEHAVIORAL_BASELINE.md").write_text(ws_a, encoding="utf-8")
print("[WS-A] written")
