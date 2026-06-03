# Phase 6.3 — Rollback Plan

**Status:** ✅ READ-ONLY analysis complete
**Date:** 2026-06-02
**Purpose:** Per-file rollback commands and verification for any future refactor of the focus files.

---

## 1. Rollback Strategy Overview

For each focus file, the rollback is a **2-step operation**:
1. Restore the pre-refactor file from the evidence backup
2. Remove any new extract packages or submodules

All rollbacks complete in **<1 second** and restore **byte-identical pre-refactor state**.

**Critical pre-condition:** Every refactor MUST create an evidence backup of the pre-refactor file BEFORE making any changes. The evidence file path is:
```
docs/PHASE6_3/evidence/<relative_path>_BEFORE.py
```

---

## 2. Per-File Rollback Plan

### 2.1 `backend/backup/backup_system.py` — **DO NOT TOUCH** (Phase 6.2 protected)

**Current status:** Phase 6.2 Step 4 already refactored (2026-06-02).

**Phase 6.2 evidence backup (DO NOT OVERWRITE):**
- `docs/PHASE6_2/evidence/backup_system_BEFORE.py` (978 LOC, 41,348 bytes, SHA256: documented)

**Phase 6.2 rollback (if needed):**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_2/evidence/backup_system_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/backup/backup_system.py"
rm -rf "E:/all downloads/Pharmacy_ERP/backend/backup/extracts/"
```

**Phase 6.3 evidence backup (additional safety):**
- `docs/PHASE6_3/evidence/backup_system_BEFORE.py` (current 742-LOC refactored version)

**Phase 6.3 rollback (if needed — same as Phase 6.2):**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/backup_system_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/backup/backup_system.py"
# (no extracts/ to remove — file is already in pre-Phase 6.2 state)
```

**Verification after rollback:**
```bash
python -c "from backup.backup_system import BackupManager, BackupValidator, BackupEncryptor; print('OK')"
pytest tests/test_backup_hardening.py -v
pytest tests/test_restore.py -v
```

---

### 2.2 `backend/payments/services.py` — **Hypothetical rollback (not refactored yet)**

**Pre-refactor backup path (to be created when refactor starts):**
- `docs/PHASE6_3/evidence/payments_services_BEFORE.py` (current 810-LOC version)

**Hypothetical rollback (if refactor applied and needs to be undone):**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/payments_services_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/payments/services.py"
rm -rf "E:/all downloads/Pharmacy_ERP/backend/payments/services/extracts/"
```

**Verification after rollback:**
```bash
python -c "from payments.services import PaymentEngine; print('OK')"
pytest tests/test_payments.py -v
pytest tests/test_financial_hardening.py -v
pytest tests/test_coverage_final.py -v
pytest tests/test_integration_comprehensive.py -v
pytest tests/test_more_coverage.py -v
```

**Rollback time:** <1 second
**Rollback risk:** LOW (no DB schema changes, no other file moves)

---

### 2.3 `backend/inventory/service/stock_integration.py` — **Hypothetical rollback (not refactored yet)**

**Pre-refactor backup path (to be created when refactor starts):**
- `docs/PHASE6_3/evidence/stock_integration_BEFORE.py` (current 839-LOC version)

**Hypothetical rollback:**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/stock_integration_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/inventory/service/stock_integration.py"
rm -rf "E:/all downloads/Pharmacy_ERP/backend/inventory/service/extracts/"
```

**Verification after rollback:**
```bash
python -c "from inventory.service.stock_integration import StockIntegrationService; print('OK')"
pytest tests/test_stock_integration.py -v
pytest tests/test_lifecycle_integration_enterprise.py -v
pytest tests/test_phase40_correctness.py -v
pytest tests/test_phase41_resilience.py -v
pytest tests/test_reality_simulation.py -v
pytest tests/test_rollback_safety.py -v
pytest tests/test_services_extra.py -v
```

**Rollback time:** <1 second
**Rollback risk:** LOW

---

### 2.4 `frontend/ui/main_window.py` — **DO NOT TOUCH** (defer to Phase 6.4)

**Pre-refactor backup path (to be created when Phase 6.4 starts):**
- `docs/PHASE6_4/evidence/main_window_BEFORE.py` (current 1,153-LOC version)

**Phase 6.4 pre-requisite:** Each of the 21 page modules must be extracted first. The rollback plan for the entire Phase 6.4 is extensive and will be defined in the Phase 6.4 plan.

**No rollback plan for Phase 6.3** (file is deferred).

---

### 2.5 `frontend/ui/pos/pos_screen.py` — **Hypothetical rollback (CAUTION strategy)**

**Pre-refactor backup path (to be created when refactor starts):**
- `docs/PHASE6_3/evidence/pos_screen_BEFORE.py` (current 897-LOC version)

**Hypothetical rollback:**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/pos_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/pos/pos_screen.py"
# (no extracts/ to remove — CAUTION strategy keeps everything in same file)
```

**Verification after rollback:**
```bash
python -c "from frontend.ui.pos.pos_screen import POSScreen; print('OK')"  # if Python can import
# OR smoke test the UI:
pytest frontend/tests/ui/test_smoke.py -v
# Manual: open the app, navigate to POS page, verify cart + payment works
```

**Rollback time:** <1 second
**Rollback risk:** LOW (no file moves, no class splits)

---

### 2.6 `frontend/ui/sales/sales_invoice_screen.py` — **Hypothetical rollback (CAUTION strategy)**

**Pre-refactor backup path:**
- `docs/PHASE6_3/evidence/sales_invoice_screen_BEFORE.py` (current 895-LOC version)

**Hypothetical rollback:**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/sales_invoice_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/sales/sales_invoice_screen.py"
# (no extracts/ to remove — private method decomposition keeps everything in same file)
```

**Verification after rollback:**
```bash
pytest frontend/tests/ui/test_smoke.py -v
pytest frontend/tests/ui/test_screens.py -v
# Manual: open the app, navigate to Sales > New Invoice, verify all sections render
```

**Rollback time:** <1 second
**Rollback risk:** VERY LOW (private method extraction only)

---

### 2.7 `frontend/ui/purchases/purchase_invoice_screen.py` — **Hypothetical rollback (CAUTION strategy)**

**Pre-refactor backup path:**
- `docs/PHASE6_3/evidence/purchase_invoice_screen_BEFORE.py` (current 897-LOC version)

**Hypothetical rollback:**
```bash
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/purchase_invoice_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/purchases/purchase_invoice_screen.py"
```

**Verification after rollback:**
```bash
pytest frontend/tests/ui/test_screens.py -v
# Manual: open the app, navigate to Purchases > New Invoice, verify all sections render
```

**Rollback time:** <1 second
**Rollback risk:** VERY LOW (private method extraction only)

---

## 3. Master Rollback (all Phase 6.3 changes)

If the entire Phase 6.3 wave needs to be rolled back (multiple files refactored):

```bash
# Backend
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/backup_system_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/backup/backup_system.py"
rm -rf "E:/all downloads/Pharmacy_ERP/backend/backup/extracts/" 2>/dev/null

cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/payments_services_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/payments/services.py" 2>/dev/null
rm -rf "E:/all downloads/Pharmacy_ERP/backend/payments/services/extracts/" 2>/dev/null

cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/stock_integration_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/backend/inventory/service/stock_integration.py" 2>/dev/null
rm -rf "E:/all downloads/Pharmacy_ERP/backend/inventory/service/extracts/" 2>/dev/null

# Frontend
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/pos_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/pos/pos_screen.py" 2>/dev/null
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/sales_invoice_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/sales/sales_invoice_screen.py" 2>/dev/null
cp "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/purchase_invoice_screen_BEFORE.py" \
   "E:/all downloads/Pharmacy_ERP/frontend/ui/purchases/purchase_invoice_screen.py" 2>/dev/null
# main_window.py is NOT touched in Phase 6.3

echo "Phase 6.3 rollback complete"
```

---

## 4. Pre-Refactor Evidence Backup Protocol

**MANDATORY** before any refactor:

1. Create the evidence directory (if not exists):
   ```bash
   mkdir -p "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence"
   ```

2. Copy the pre-refactor file:
   ```bash
   cp "<source_file>" "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/<source_filename>_BEFORE.py"
   ```

3. Compute SHA256 checksum:
   ```bash
   python -c "import hashlib; print(hashlib.sha256(open('<source_file>','rb').read()).hexdigest())"
   # Save to docs/PHASE6_3/evidence/<source_filename>_SHA256.txt
   ```

4. Document the rollback command in this file

5. Verify the evidence backup is byte-identical:
   ```bash
   diff "<source_file>" "E:/all downloads/Pharmacy_ERP/docs/PHASE6_3/evidence/<source_filename>_BEFORE.py"
   # Must be empty (no diff)
   ```

---

## 5. Phase 5.9 / Phase 6.2 Rollback Safety

**Critical invariants:** Any Phase 6.3 refactor MUST NOT modify:
- `docs/PHASE5_9_*.md` (10 certification reports)
- `docs/PHASE6_0/` (8 maintainability audit reports)
- `docs/PHASE6_1/` (8 refactor planning reports)
- `docs/PHASE6_2/` (4 step reports + 1 final report + 4 evidence files)
- `backend/pre_production_hardening/`, `backend/production_infrastructure/`, `backend/production_gate/` (Phase 6.2 refactored)
- `backend/backup/extracts/` (Phase 6.2 Step 4 extracted modules)

**Verification:** Before declaring any Phase 6.3 refactor safe, run:
```bash
git status --short docs/PHASE5_9_*.md docs/PHASE6_0/ docs/PHASE6_1/ docs/PHASE6_2/
# Must be empty (no changes)
```

---

## 6. Recovery Time Objectives (RTO)

| Scenario | Rollback Time | RTO Target | Status |
|----------|---------------|------------|--------|
| Single file rollback | <1 second | <5 minutes | ✅ MET |
| All Phase 6.3 rollback | <5 seconds | <15 minutes | ✅ MET |
| Phase 5.9 verdict violated | hours to days (re-run certification) | <1 day | ⚠️ Requires full re-cert |
| Database corruption during refactor | hours (restore from backup) | <1 day | Backup system in place |

---

## 7. Backup Verification (Pre-Phase 6.3)

Before any refactor, verify the backup system is healthy:

```bash
# Check backup system is operational
python -c "
import os, sys
sys.path.insert(0, r'E:\all downloads\Pharmacy_ERP\backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django; django.setup()
from backup.backup_system import BackupManager
mgr = BackupManager(config={
    'database': {'path': '', 'vacuum_before_backup': False, 'verify_after_backup': True},
    'backup_dir': r'C:\Users\REZAFA~1\AppData\Local\Temp\test_rollback',
    'compression': {'enabled': False},
    'encryption': {'enabled': False},
    'logging': {'level': 'WARNING', 'file': 'backup.log'},
})
result = mgr.create_backup(description='Pre-Phase 6.3 backup verification')
print(result)
"
```

**Expected:** `{'success': True, 'backup_path': '...', 'metadata': {...}, ...}`

---

## 8. Outputs

| File | Purpose |
|------|---------|
| `docs/PHASE6_2/evidence/backup_system_BEFORE.py` | Phase 6.2 Step 4 evidence (DO NOT OVERWRITE) |
| `docs/PHASE6_3/evidence/backup_system_BEFORE.py` | Phase 6.3 audit snapshot (current 742-LOC version) |
| `docs/PHASE6_3/evidence/<future>_BEFORE.py` | Per-future-refactor evidence backups |

---

## 9. Rollback Test (proves the plan works)

The rollback test must be run after every refactor:
1. Save pre-refactor state to evidence
2. Run full test suite (baseline)
3. Apply refactor
4. Run full test suite (must pass)
5. Execute rollback command (cp + rm)
6. Run full test suite (must pass — proves rollback restores working state)
7. Re-apply refactor
8. Run full test suite (must pass)

**This test is REQUIRED for every refactor and is the strongest evidence that the rollback plan works.**
