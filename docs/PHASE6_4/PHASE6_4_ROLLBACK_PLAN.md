# Phase 6.4 — Rollback Plan

**Status: VALIDATED** ✅
**Date:** 2026-06-02
**Scope:** Atomic rollback procedure for both refactored files

---

## 1. Rollback Architecture

Phase 6.4 uses **pure private-method decomposition** — no new files, no file
moves, no import changes, no API surface changes. The refactor is **atomic
and reversible at the file level** with a single `Copy-Item` per file.

### 1.1 What Was Touched
| File | LOC change | New files? | New imports? | API changes? |
|------|-----------:|:----------:|:------------:|:------------:|
| `frontend/ui/sales/sales_invoice_screen.py` | 894 → 910 (+16 boilerplate) | ❌ | ❌ | ❌ |
| `frontend/ui/purchases/purchase_invoice_screen.py` | 896 → 912 (+16 boilerplate) | ❌ | ❌ | ❌ |
| **Total touched files** | **2** | **0** | **0** | **0** |

### 1.2 Evidence Backups
| File | SHA256 | Path |
|------|--------|------|
| `sales_invoice_screen_BEFORE.py` | `debed68e72c084c8dc6203135b51bafadfcb728721e957e970793d5b9eb77e82` | `docs/PHASE6_4/evidence/` |
| `purchase_invoice_screen_BEFORE.py` | `3b5418290328321a82c9160f06a67da53aa5e2b37f84a1486d818dffacecfb5c` | `docs/PHASE6_4/evidence/` |

---

## 2. Rollback Scenarios

### 2.1 Scenario A — Rollback BOTH files (full Phase 6.4 reversal)
**Trigger:** Major regression discovered in production, need to revert
entire phase 6.4 wave.
**Time:** <10 seconds (2 file copies)
**Side effects:** None — `git status` will show 2 modified files

```powershell
# PowerShell
Copy-Item -Path "E:\all downloads\Pharmacy_ERP\docs\PHASE6_4\evidence\sales_invoice_screen_BEFORE.py" `
          -Destination "E:\all downloads\Pharmacy_ERP\frontend\ui\sales\sales_invoice_screen.py" `
          -Force

Copy-Item -Path "E:\all downloads\Pharmacy_ERP\docs\PHASE6_4\evidence\purchase_invoice_screen_BEFORE.py" `
          -Destination "E:\all downloads\Pharmacy_ERP\frontend\ui\purchases\purchase_invoice_screen.py" `
          -Force
```

```bash
# Bash (Git Bash / WSL)
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_4/evidence/sales_invoice_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/sales/sales_invoice_screen.py"

cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_4/evidence/purchase_invoice_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/purchases/purchase_invoice_screen.py"
```

### 2.2 Scenario B — Rollback ONLY sales_invoice_screen.py (Step 1 reversal)
**Trigger:** Regression only in sales invoice flow.
**Time:** <5 seconds
**Side effects:** None — Step 2 (purchase) remains refactored

```powershell
Copy-Item -Path "E:\all downloads\Pharmacy_ERP\docs\PHASE6_4\evidence\sales_invoice_screen_BEFORE.py" `
          -Destination "E:\all downloads\Pharmacy_ERP\frontend\ui\sales\sales_invoice_screen.py" `
          -Force
```

### 2.3 Scenario C — Rollback ONLY purchase_invoice_screen.py (Step 2 reversal)
**Trigger:** Regression only in purchase invoice flow.
**Time:** <5 seconds
**Side effects:** None — Step 1 (sales) remains refactored

```powershell
Copy-Item -Path "E:\all downloads\Pharmacy_ERP\docs\PHASE6_4\evidence\purchase_invoice_screen_BEFORE.py" `
          -Destination "E:\all downloads\Pharmacy_ERP\frontend\ui\purchases\purchase_invoice_screen.py" `
          -Force
```

### 2.4 Scenario D — Emergency rollback via git
**Trigger:** Evidence backup corrupted or unavailable.
**Time:** <30 seconds (git checkout + verification)
**Side effects:** Discards all uncommitted changes in those 2 files

```bash
# If the refactor was committed in a single "Phase 6.4" commit
git checkout HEAD~1 -- frontend/ui/sales/sales_invoice_screen.py
git checkout HEAD~1 -- frontend/ui/purchases/purchase_invoice_screen.py

# Or, if uncommitted, use the git reflog to find the pre-refactor blob
git reflog
# Find the commit hash BEFORE Phase 6.4
git checkout <pre-phase6_4-commit-hash> -- frontend/ui/sales/sales_invoice_screen.py
git checkout <pre-phase6_4-commit-hash> -- frontend/ui/purchases/purchase_invoice_screen.py
```

---

## 3. Rollback Verification

### 3.1 SHA256 verification after rollback

```powershell
Get-FileHash "E:\all downloads\Pharmacy_ERP\frontend\ui\sales\sales_invoice_screen.py" -Algorithm SHA256
# Expected: DEBED68E72C084C8DC6203135B51BAFADFCB728721E957E970793D5B9EB77E82

Get-FileHash "E:\all downloads\Pharmacy_ERP\frontend\ui\purchases\purchase_invoice_screen.py" -Algorithm SHA256
# Expected: 3B5418290328321A82C9160F06A67DA53AA5E2B37F84A1486D818DFFACECFB5C
```

### 3.2 Functional smoke test

```powershell
# Run custom verification scripts — they will FAIL if rollback is incomplete
E:\Pharmacy_ERP\venv\Scripts\python.exe -X utf8 "E:\all downloads\Pharmacy_ERP\docs\PHASE6_4\verify_sales_invoice.py"
# After full rollback: tests for _build_header etc will FAIL with AttributeError
# (this confirms you're running the BEFORE code, not the refactored code)

E:\Pharmacy_ERP\venv\Scripts\python.exe -X utf8 "E:\all downloads\Pharmacy_ERP\docs\PHASE6_4\verify_purchase_invoice.py"
# Same — AttributeError on _build_header proves pre-refactor state restored
```

### 3.3 Manual smoke test in MainWindow

```powershell
# Launch the app
cd "E:\all downloads\Pharmacy_ERP"
E:\Pharmacy_ERP\venv\Scripts\python.exe -X utf8 frontend/main.py
# Then: Sidebar → Sales → New Invoice
# Verify: form renders, customer combo populated, items table editable
# Then: Sidebar → Purchases → New Purchase Invoice
# Verify: form renders, supplier combo populated, DataEntryGrid editable
```

---

## 4. Why This Rollback is Safe

### 4.1 Pure Refactoring Discipline
Phase 6.4 followed the **Refactoring (Fowler) definition** — behavior-preserving
code transformation. The original BEFORE files were captured at SHA256-stable
points and stored in `docs/PHASE6_4/evidence/`. The refactored versions are
**structurally identical**:
- Same widget tree
- Same signal wiring
- Same public API
- Same business logic
- Same imports
- Same exception handling

### 4.2 Byte-Identical Backup
The BEFORE files are exact byte copies of the in-repo files at the moment
refactoring began. SHA256 fingerprints are stored in:
- This rollback plan (Section 1.2)
- `docs/PHASE6_3/evidence/` (redundant copies from earlier audit)
- The step reports (Section 4 of each step report)

### 4.3 No Database State Affected
Phase 6.4 is a **frontend-only** refactor. No migrations, no model changes,
no service-layer changes. The database state is completely independent of
the rollback. After rollback, the in-memory `QSettings` and `theme_preference.json`
remain untouched (date format preference is read on `__init__`).

### 4.4 No Test Files Modified
The custom verification scripts (`verify_sales_invoice.py`, `verify_purchase_invoice.py`)
are NEW files in `docs/PHASE6_4/`, not in the original code tree. They are
idempotent — they can stay or be deleted without affecting the refactor.
The pre-existing test suite was not modified by Phase 6.4.

---

## 5. Rollback Decision Matrix

| Symptom | Likely Cause | Recommended Action |
|---------|--------------|-------------------|
| `AttributeError: 'SalesInvoiceScreen' has no attribute '_build_header'` | Partial rollback (e.g., test cache stale) | Re-run Scenario A full rollback, restart Python |
| Sales invoice form won't render | Widget created in wrong zone | Re-run Scenario B full sales rollback |
| Purchase invoice form won't render | Widget created in wrong zone | Re-run Scenario C full purchase rollback |
| Signal handler not firing | `.connect()` not registered | Check `_wire_signals()` body via `inspect.getsource()` |
| Layout broken (overlapping widgets) | `self._zone2_layout` not added to parent | Re-run appropriate scenario |
| LSP errors increased | Unrelated PySide6 stub issue | NOT a Phase 6.4 regression — investigate elsewhere |
| Test data corruption | Data pollution in test DB | Unrelated — see Phase 6.2 notes on `test_restore.py` |

---

## 6. Pre-Rollback Checklist

Before executing rollback:

- [ ] Confirm regression is real (not test infrastructure or stale cache)
- [ ] Run `verify_*.py` script to see the exact failure
- [ ] Check `git log --oneline -5` for any cross-file changes
- [ ] Verify evidence backup SHA256 matches Section 1.2
- [ ] Notify team in chat (if applicable)
- [ ] Take current SHA256 of failing file (for diff comparison)
- [ ] Document the regression in `docs/PHASE6_4/INCIDENT_<date>.md`

## 7. Post-Rollback Checklist

After executing rollback:

- [ ] Verify SHA256 matches evidence backup
- [ ] Run `verify_*.py` — expect AttributeError on private builders (proves pre-refactor code)
- [ ] Manual smoke test: launch app, navigate to affected screen
- [ ] `git status` should show the 2 reverted files as modified
- [ ] Commit the rollback with message: `Revert: Phase 6.4 Step N — <reason>`
- [ ] Update this plan with actual incident details

---

## 8. Rollback Time Budget

| Step | Time |
|------|------|
| Decide to rollback | 1 min |
| Read this plan | 1 min |
| Execute `Copy-Item` | <5 sec |
| SHA256 verify | <5 sec |
| Smoke test | 30-60 sec |
| Document | 5 min |
| **Total** | **<10 min** |

---

## 9. Why Not Use `git revert`?

`git revert` is acceptable but inferior for this scenario because:
1. The 2 file changes are bundled in a single refactor — easier to revert as a unit
2. The evidence backup has explicit SHA256 fingerprint (definitive source of truth)
3. `git revert` requires the refactor to be already committed (Phase 6.4 may still be uncommitted)
4. SHA256-based rollback is portable across all branches and forks

**Use the SHA256-based rollback procedure (Section 2) as the primary method.**

---

## 10. Rollback Plan Validation: **VALID** ✅

- Evidence backups: **EXIST** with SHA256 fingerprints
- File scope: **2 files** (both in `frontend/ui/`)
- Time to rollback: **<10 seconds** (Scenarios A-C)
- No new files to remove
- No new imports to clean
- No API surface to migrate
- No DB state to restore

**Rollback is provably safe and atomic.**
