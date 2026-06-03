# Backup Tree Sanitization Report

**Date:** 2026-06-01
**Mode:** AUDIT ONLY (read-only, no source mutations)
**Phase:** 4 — Stage 1
**Scope:** All backup / snapshot / legacy / archive / `.bak` / `.dead` / `.governance_backup` / `.tmp` / `.orig` files and directories in the Pharmacy_ERP repository.

---

## 1. Executive Summary

The Pharmacy_ERP repository contains **5 distinct backup-tree locations** with a combined footprint of **~23,282 lines of Python / .bak / .dead content** spread across **107 files**. The most critical is `frontend/backups/batch_fix_20260508_042331/` (66 files, 18,002 LOC) which lives **inside the active frontend source tree**. Despite being listed in `.gitignore` (line 151: `backups/`), the files still exist on the working tree and could be picked up by glob-based build / lint / audit tools.

| # | Location | Files | LOC | In source tree? | Git-tracked? | Risk |
|---|---|---|---|---|---|---|
| 1 | `frontend/backups/batch_fix_20260508_042331/` | 66 | 18,002 | **YES** | NO (gitignored) | **CRITICAL** |
| 2 | `archive/legacy/` | 22 | 2,454 | NO (repo root) | YES | MEDIUM |
| 3 | `docs/archive/` | 16 | 2,543 | NO (docs/) | YES | LOW |
| 4 | `backend/archive/production_services/` | 1 | 283 | **YES (backend)** | YES | MEDIUM |
| 5 | `backend/test_output.txt.bak` + `backend/test_result.txt.bak` | 2 | small | **YES (backend)** | NO (gitignored) | LOW |
| **Total** | | **107** | **~23,282** | | | |

**Headline:** Stage 1 confirms 1 CRITICAL, 2 MEDIUM, and 2 LOW backup locations. All 5 require explicit human action before production deployment, but **none of them block Phase 4 stabilization work** (the CRITICAL one is in the working tree but excluded by gitignore and Python import rules, so the live system is unaffected today).

---

## 2. Detailed Inventory

### 2.1 CRITICAL — `frontend/backups/batch_fix_20260508_042331/`

| Attribute | Value |
|---|---|
| Absolute path | `E:\all downloads\Pharmacy_ERP\frontend\backups\batch_fix_20260508_042331\` |
| Parent | `frontend/backups/` (inside `frontend/` source tree) |
| File count | 66 (all `.py`) |
| Total LOC | 18,002 |
| Python LOC only | 18,002 |
| Git tracked? | NO (matched by `.gitignore:151:backups/`) |
| Imports in active code? | NONE verified (no `__init__.py`, no production import) |
| Oldest file size | 60 LOC (`ui/system/production_screen.py`) |
| Largest file | 926 LOC (`ui/main_window.py`) |
| File extension policy | All `.py` (would be importable if path were in `sys.path`) |
| Modified date | All files dated `2026-05-08 04:23:31` (single atomic snapshot) |

**Top 10 largest backup files (verified):**
| File | LOC |
|---|---|
| `ui/main_window.py` | 926 |
| `ui/sales/sales_invoice_screen.py` | 735 |
| `ui/purchases/purchase_invoice_screen.py` | 706 |
| `ui/system/control_center_screen.py` | 688 |
| `ui/purchases/supplier_screen.py` | 569 |
| `ui/sales/customer_screen.py` | 554 |
| `ui/system/user_management_screen.py` | 552 |
| `ui/returns/returns_screen.py` | 530 |
| `ui/accounting/journal_entry_screen.py` | 483 |
| `ui/hr/payroll_screen.py` | 448 |
| **Subtotal (top 10)** | **6,191** |
| **Remaining 56 files** | **11,811** |
| **Total** | **18,002** |

**Structural risk assessment:**
1. **Source-tree contamination.** Located at `frontend/backups/...`, three directory levels deep inside the active frontend. Any tool that uses `frontend/**/*.py` glob (pytest discovery, linters, governance scanners) will see these files and may treat them as candidates.
2. **Python path collision.** If a developer runs `from frontend.backups.batch_fix_20260508_042331.ui.main_window import MainWindow` (or any glob-importing code picks up a relative path), Python will load the **stale** version. The current `MainWindow` class is 1100 LOC; the backup version is 926 LOC. Subtle class-attribute or method-signature drift would cause silent corruption.
3. **Doubles maintenance liability.** The backup is 18,002 LOC = **34.6% of the active frontend** (51,949 LOC). Any future refactor that targets a duplicated filename must remember the backup exists or risk rewriting stale code.
4. **No `__init__.py` safety net.** The directory has no `__init__.py`, so it is not a package and cannot be imported as `frontend.backups...`. **This is the only reason production is not currently broken.**
5. **Gitignore hygiene issue.** `.gitignore:57` and `.gitignore:151` both list `backups/` — duplicate entries (line 57 is in the DJANGO section, line 151 is in the DATA/DATABASE section). This is harmless but indicates the rule was added twice for different reasons and never consolidated.

**Verdict:** Must be moved to a top-level `archive/` location or deleted before production deployment.

---

### 2.2 MEDIUM — `archive/legacy/`

| Attribute | Value |
|---|---|
| Absolute path | `E:\all downloads\Pharmacy_ERP\archive\legacy\` |
| Parent | `archive/` (at repo root, OUTSIDE source tree) |
| File count | 22 (18 Python + 3 `.governance_backup` + 1 Python `__init__`-like) |
| Total LOC | 2,454 |
| Python LOC only | 2,017 |
| Git tracked? | YES (22 files) |
| Imports in active code? | NONE verified (no `__init__.py` chain) |

**Largest files (verified):**
| File | LOC |
|---|---|
| `backend/pharmacy/services/rules_engine.py` | 243 |
| `frontend/ui/cognitive/cognitive_dashboard.py` | 238 |
| `frontend/ui/cognitive/cognitive_dashboard.py.governance_backup` | 236 |
| `frontend/ui/cognitive_reasoning/causal_engine.py` | 232 |
| `frontend/ui/cognitive_reasoning/what_if_impact_panel.py` | 173 |
| `frontend/ui/cognitive/fusion_engine.py` | 164 |
| `frontend/ui/cognitive_reasoning/why_analysis_panel.py` | 155 |
| `backend/transaction_service.py` | 130 |
| `frontend/ui/cognitive/global_bar.py` | 127 |
| `frontend/ui/cognitive/global_bar.py.governance_backup` | 126 |
| `frontend/ui/cognitive_reasoning/dependency_graph_view.py` | 124 |
| `frontend/ui/rendering/dialog_renderer.py` | 85 |

**Structural risk:**
1. **Cognitive / cognitive_reasoning modules archived.** These are the "decision intelligence" screens that were deprecated in earlier phases. They are correctly archived but their existence in the repo can confuse audit tools that walk the tree.
2. **Renderer layer archived.** `frontend/ui/rendering/{button,table,card,dialog,badge}_renderer.py` (305 LOC combined) were the pre-CANONICAL renderer classes. Phase 1 (Duplicate Components Audit) confirmed they have 0 callers in active code. They are correctly archived.
3. **Tracked in git history.** Future `git log -- archive/legacy/` will reveal deletion history. Acceptable.
4. **No `__init__.py`** — no Python import risk.
5. **Out of source tree.** Glob-based tools will not see these.

**Verdict:** Acceptable as-is. Optionally consolidate to `archive/frontend/legacy/` for clarity. The current 2-deep structure is fine.

---

### 2.3 LOW — `docs/archive/`

| Attribute | Value |
|---|---|
| Absolute path | `E:\all downloads\Pharmacy_ERP\docs\archive\` |
| Parent | `docs/` (documentation tree) |
| File count | 16 (all `.py.dead`) |
| Total LOC | 2,543 |
| Python LOC only | 2,543 |
| Git tracked? | YES (16 files) |
| Imports in active code? | NONE — `.py.dead` double-extension is not importable as Python |

**Largest files (verified):**
| File | LOC |
|---|---|
| `theme/enterprise_styling.py.dead` | 425 |
| `theme/theme_manager.py.dead` | 332 |
| `ui/accounting/accounting_dashboard.py.dead` | 306 |
| `ui/accounting/profit_loss_screen.py.dead` | 171 |
| `ui/control_tower/dashboard.py.dead` | 152 |
| `ui/autonomous/master_dashboard.py.dead` | 149 |
| `ui/autonomous/decision_options_screen.py.dead` | 131 |
| `ui/theme/theme_manager.py.dead` | 124 |
| `ui/autonomous/forecast_dashboard.py.dead` | 123 |
| `ui/accounting/balance_sheet_screen.py.dead` | 112 |
| `ui/hr/report_screens.py.dead` | 109 |
| `ui/payroll/report_screens.py.dead` | 102 |
| `ui/autonomous/anomaly_warning_center.py.dead` | 99 |
| `ui/accounting/trial_balance_screen.py.dead` | 81 |
| `ui/accounting/arap_ageing_screen.py.dead` | 72 |
| `ui/accounting/cash_flow_screen.py.dead` | 49 |

**Structural risk:**
1. **Lives in `docs/`** which is documentation, not source. Glob-based source scanners will not see these.
2. **`.py.dead` double extension** is the explicit dead-code marker used by the project — no production tool will import them.
3. **Theme / autonomous / control_tower / accounting dead screens** are pre-Phase 1 deletion targets. They were preserved as `.dead` files for git history reference.

**Verdict:** Acceptable as-is. The `.dead` convention is well-known and consistent.

---

### 2.4 MEDIUM — `backend/archive/production_services/`

| Attribute | Value |
|---|---|
| Absolute path | `E:\all downloads\Pharmacy_ERP\backend\archive\production_services\` |
| Parent | `backend/archive/` (inside `backend/` source tree) |
| File count | 1 (`optimization.py`, 283 LOC) |
| Git tracked? | YES |
| Imports in active code? | NONE verified (no `__init__.py`) |
| Risk | MEDIUM — Django's app-discovery mechanism walks all subdirectories of `backend/`. A directory without `__init__.py` is ignored, but if a future developer adds `apps.py` or `models.py` here by mistake, Django will try to register it. |

**Structural risk:**
1. **Django app discovery exposure.** `python manage.py check` walks every subdirectory of `backend/` looking for Django apps. A misstep (adding `apps.py` or `models.py`) would activate the archived code.
2. **Lives inside `backend/` source tree.** Phase 1 audit guidelines should be updated to add `backend/archive/` to the exclusion list of architecture scanners.

**Verdict:** Add `backend/archive/` to the audit-scanner exclusion list AND add a `README.md` inside the directory warning future developers.

---

### 2.5 LOW — Backend `.bak` files

| Attribute | Value |
|---|---|
| Paths | `backend/test_output.txt.bak`, `backend/test_result.txt.bak` |
| File count | 2 |
| Git tracked? | NO (gitignored via `*.bak`) |
| Risk | LOW — small text files, gitignored, not Python |

**Verdict:** Acceptable. Will be removed by future `git clean -fdX` or similar hygiene scripts.

---

## 3. Cross-cutting Issues

### 3.1 Gitignore hygiene

`.gitignore` contains `backups/` at **two** locations:
- Line 57 (DJANGO section): `backups/`
- Line 151 (DATA/DATABASE section): `backups/`

This is a duplicate. One of them should be removed. The DATA/DATABASE one is more semantically correct (backups-of-data is a different concern than Django fixtures-backups), so the line-57 entry should be deleted.

### 3.2 Missing audit-scanner exclusion list

The `frontend/scripts/screen_migration_audit.py` and `frontend/enterprise_certification/certifier.py` tools use a hardcoded skip-list to exclude dead-code paths. The skip-list should be expanded to include:
- `frontend/backups/`
- `archive/` (at root)
- `docs/archive/`
- `backend/archive/`

This prevents the backup trees from being re-discovered as "duplicates" or "violations" in future audits.

### 3.3 Convention drift

Three different conventions are in use for marking dead code:
1. **Deleted entirely** (preferred) — `frontend/ui/components/base_widgets.py` was deleted in Phase 3A.
2. **Renamed to `.dead`** — `docs/archive/**/*.py.dead` (16 files).
3. **Moved to `archive/legacy/`** — 18 Python + 3 `.governance_backup` files.
4. **Time-stamped snapshot directories** — `frontend/backups/batch_fix_20260508_042331/`.
5. **`.bak` extension on text files** — 2 files in `backend/`.

The project should adopt **one canonical convention** (recommendation: prefer #1 for true dead code; use #3 only when git history preservation is required; deprecate #4 entirely). The `.dead` and `.bak` conventions are inline-only and should be phased out.

---

## 4. Relocation Plan (DO NOT AUTO-EXECUTE)

This is a recommendation, not a script. Each action requires explicit human approval.

### 4.1 Action 1: Relocate `frontend/backups/batch_fix_20260508_042331/`

**Source:** `E:\all downloads\Pharmacy_ERP\frontend\backups\batch_fix_20260508_042331\`
**Target:** `E:\all downloads\Pharmacy_ERP\archive\frontend_pre_phase3_20260508\`

**Steps:**
1. Verify git is clean: `git status`
2. Move directory: `git mv frontend/backups/batch_fix_20260508_042331 archive/frontend_pre_phase3_20260508`
3. Update `.gitignore`:
   - Remove line 57 (`backups/`) — duplicate
   - Keep line 151 (`backups/`) — this is the data-backup rule
   - **DO NOT** add `archive/` to gitignore (the other archive dirs are intentionally tracked)
4. Update audit-scanner skip-list: replace `frontend/backups/` with `archive/frontend_pre_phase3_20260508/`
5. Verify: `git grep "frontend.backups.batch_fix"` should return 0 results
6. Verify: `git status` should show 1 rename + 1 gitignore change

**Effort:** 30 minutes
**Risk:** LOW (rename is git-tracked; nothing else references the path)
**LOC moved:** 18,002

**Decision required:** DELETE vs PRESERVE-as-archive. The audit recommends **PRESERVE-AS-ARCHIVE** for one release cycle (30 days), then DELETE in Phase 6.

---

### 4.2 Action 2: Mark `backend/archive/production_services/` as explicitly excluded

**Source:** `E:\all downloads\Pharmacy_ERP\backend\archive\production_services\`
**Action:** Add `README.md` to the directory:
```markdown
# backend/archive/

This directory contains Django-archived code that is NOT registered as a Django app.
Do NOT add `apps.py`, `models.py`, `__init__.py`, or any Django-discoverable file
to this directory or its subdirectories.
```
And add the directory to the audit-scanner skip-list.

**Effort:** 15 minutes
**Risk:** LOW (documentation only)
**LOC affected:** 283 (unchanged)

---

### 4.3 Action 3: Consolidate `.dead` convention

**Source:** `E:\all downloads\Pharmacy_ERP\docs\archive\` (16 files, 2,543 LOC)
**Action:** Move all `.py.dead` files to `archive/frontend_documented_dead_code/` with the `.dead` extension removed (or kept, depending on team preference). Update audit-scanner to recognize the new path.

**Effort:** 1 hour
**Risk:** LOW
**LOC affected:** 2,543

**Decision required:** This action has historical reference value but no operational value. Recommend PRESERVE for git history but consolidate to a single location.

---

### 4.4 Action 4: Delete backend `.bak` files

**Source:** `backend/test_output.txt.bak`, `backend/test_result.txt.bak`
**Action:** Delete both. They are not git-tracked and are not needed for any current operation.

**Effort:** 5 minutes
**Risk:** ZERO

---

### 4.5 Action 5: Consolidate gitignore

**Source:** `.gitignore:57` and `.gitignore:151`
**Action:** Remove line 57 (duplicate `backups/`). Keep line 151 (the semantically correct one).

**Effort:** 1 minute
**Risk:** ZERO

---

## 5. Risk Matrix

| # | Action | Severity | Effort | Risk | Reversible? |
|---|---|---|---|---|---|
| 1 | Relocate `frontend/backups/batch_fix_20260508_042331/` to `archive/frontend_pre_phase3_20260508/` | CRITICAL | 30 min | LOW | YES (git mv) |
| 2 | Document `backend/archive/production_services/` exclusion | MEDIUM | 15 min | LOW | YES |
| 3 | Consolidate `.dead` files into `archive/frontend_documented_dead_code/` | LOW | 1 hr | LOW | YES (git mv) |
| 4 | Delete backend `.bak` files | LOW | 5 min | ZERO | NO (but untracked) |
| 5 | Consolidate duplicate `backups/` gitignore entry | LOW | 1 min | ZERO | YES |

**Total effort:** ~2 hours
**Recommended execution window:** End of Phase 4, before Phase 5 begins.
**Recommended approval:** Principal Architect + Tech Lead sign-off required for Action 1.

---

## 6. What this audit did NOT do

- Did NOT move, delete, or rename any files.
- Did NOT modify `.gitignore`.
- Did NOT update audit-scanner skip-lists.
- Did NOT verify that every backup file is truly obsolete (some may contain business logic that is referenced elsewhere in non-obvious ways).
- Did NOT examine the semantic content of any backup file (all judgments are based on file extensions, sizes, and structural placement, not code semantics).

---

## 7. Sign-off Checklist

- [x] 5 backup locations identified
- [x] LOC counted for each (18,002 + 2,454 + 2,543 + 283 + 2 = 23,282)
- [x] Risk levels assigned (1 CRITICAL, 2 MEDIUM, 2 LOW)
- [x] Git tracked state verified for each
- [x] Relocation plan produced with 5 actions
- [x] Total estimated effort calculated (~2 hours)
- [x] All actions reversible status recorded
- [x] No source mutations performed
