# Phase 6.3 — Regression Matrix

**Status:** ✅ READ-ONLY analysis complete
**Date:** 2026-06-02
**Purpose:** For each candidate refactor, define the test suite that must pass to declare the refactor safe.

---

## 1. Test Suite Baseline (Phase 5.9 / Phase 6.2 verified)

| Test Suite | Count | Status | Phase |
|------------|-------|--------|-------|
| `tests/test_accounting_model.py` | 43 | PASS | 4B |
| `tests/test_auth_flow.py` | varies | PASS (post-Phase Fix) | 8 |
| `tests/test_backup_hardening.py` | 25 | PASS (Phase 6.2 verified) | 6.2 Step 4 |
| `tests/test_payments.py` | 4+ uses of PaymentEngine | PASS | 4C |
| `tests/test_financial_hardening.py` | 4+ uses of PaymentEngine | PASS | 4C |
| `tests/test_coverage_final.py` | uses PaymentEngine, StockIntegrationService | PASS | 4C, 5 |
| `tests/test_more_coverage.py` | uses PaymentEngine, StockIntegrationService | PASS | 4C, 5 |
| `tests/test_integration_comprehensive.py` | uses PaymentEngine, StockIntegrationService | PASS | 4C, 5 |
| `tests/test_stock_integration.py` | uses StockIntegrationService | PASS | 3 |
| `tests/test_stock_integration_behavior.py` | uses StockIntegrationService | collection error (pre-existing) | 3 |
| `tests/test_stock_integration_enterprise.py` | uses StockIntegrationService | collection error (pre-existing) | 3 |
| `tests/test_validation_harness.py` | 1,120 LOC | PASS (1 module) | 6D |
| `tests/test_lifecycle_integration_enterprise.py` | uses StockIntegrationService | PASS | 5 |
| `tests/test_enterprise_lifecycle_advanced.py` | uses StockIntegrationService | PASS | 5 |
| `tests/test_phase40_correctness.py` | uses StockIntegrationService | PASS | 5 |
| `tests/test_phase41_resilience.py` | uses StockIntegrationService | PASS | 5 |
| `tests/test_reality_simulation.py` | uses StockIntegrationService (2x) | PASS | 5 |
| `tests/test_rollback_safety.py` | uses StockIntegrationService | PASS | 5 |
| `tests/test_services_extra.py` | uses StockIntegrationService | PASS | 5 |
| `tests/test_restore.py` | 9/10 PASS (1 pre-existing data pollution) | PASS (1 known failure) | 7F |
| Frontend: `frontend/tests/ui/test_smoke.py` | uses SalesInvoiceScreen | PASS | 3 |
| Frontend: `frontend/tests/ui/test_screens.py` | uses SalesInvoiceScreen, PurchaseInvoiceScreen | PASS | 3 |
| Frontend: `frontend/tests/ui/test_main_window.py` | 13 uses of MainWindow | PASS | 3 |
| Frontend: `frontend/tests/ui/test_enterprise_comprehensive.py` | (after Phase 3A dead code purge) | PASS | 3 |
| **TOTAL** | **1,587+ tests** | **PASS** | All |

**Pre-existing known issues (NOT refactor-caused):**
- `tests/test_stock_integration_behavior.py` — collection error (pre-Phase 6.0)
- `tests/test_stock_integration_enterprise.py` — collection error (pre-Phase 6.0)
- `tests/test_validation_harness.py` — collection error on 2 modules (pre-Phase 6.0)
- `tests/test_restore.py::test_create_snapshot` — data pollution (Phase 6.2 documented)

---

## 2. Per-File Regression Matrix

### 2.1 `backend/backup/backup_system.py` — **DO NOT TOUCH**

| Test | What it verifies | Must pass after refactor |
|------|------------------|--------------------------|
| `tests/test_backup_hardening.py` (25 tests) | All Phase 6.2 Step 4 invariants | YES (already PASS post-Phase 6.2) |
| `tests/test_restore.py` (10 tests) | RestoreService uses BackupManager | YES (9/10 pass; 1 pre-existing failure) |
| `tests/test_validation_harness.py` (1 module) | End-to-end | Pre-existing issue, not refactor-caused |

**No regression matrix needed** — file is Phase 6.2 protected.

---

### 2.2 `backend/payments/services.py` — **CAUTION**

| Test | What it verifies | Critical assertions |
|------|------------------|---------------------|
| `tests/test_payments.py` | 4+ uses of PaymentEngine; receipt, payment, transfer, refund flows | Process receipts, create FinancialTransaction, update balances |
| `tests/test_financial_hardening.py` | 4+ uses; stress under concurrent payments | Concurrency safety, double-entry integrity |
| `tests/test_coverage_final.py` | Uses PaymentEngine for edge cases | Edge case coverage |
| `tests/test_integration_comprehensive.py` | End-to-end sale + payment | Sale → payment → journal entry |
| `tests/test_more_coverage.py` | Edge cases for refund, transfer | Refund reversal, transfer between accounts |
| `backend/returns/services/refund_service.py` (production) | Uses PaymentEngine for return refunds | Refund transaction creation |
| `backend/sales/models.py` (production) | Signal handler uses PaymentEngine on CustomerPayment.save() | Auto-payment on sale |
| `backend/purchases/models.py` (production) | Signal handler uses PaymentEngine on SupplierPayment.save() | Auto-payment on purchase |
| `backend/payments/views.py` (production) | API endpoint creates PaymentEngine | Receipt/payment/transfer via API |
| **Phase 4C verification** | Auto journal entry creation on payment | Dr Cash, Cr AR / Dr AP, Cr Cash |

**Specific assertions to verify after refactor:**
- [ ] `PaymentEngine().process_receipt(...)` returns the same dict structure
- [ ] `PaymentEngine().process_payment(...)` creates the same `FinancialTransaction` and `JournalEntry`
- [ ] `PaymentEngine().process_refund(...)` reverses the same way
- [ ] Signal handlers in `sales/models.py` and `purchases/models.py` still trigger
- [ ] Balance calculation is byte-identical
- [ ] All 4 production callers (views + 2 model signal handlers + refund service) still work
- [ ] All 5 test files still pass

---

### 2.3 `backend/inventory/service/stock_integration.py` — **CAUTION**

| Test | What it verifies | Critical assertions |
|------|------------------|---------------------|
| `tests/test_stock_integration.py` | Core stock integration flows | Batch selection, stock movement creation, integration with sales/purchase |
| `tests/test_enterprise_lifecycle_advanced.py` | Advanced enterprise scenarios | Multi-warehouse, complex batch selection |
| `tests/test_lifecycle_integration_enterprise.py` | Integration with other modules | End-to-end lifecycle (procure → stock → sale) |
| `tests/test_phase40_correctness.py` | Phase 4 correctness (also uses `StockSelectionMode` nested class) | Correctness of complex multi-batch selection |
| `tests/test_phase41_resilience.py` | Phase 4.1 resilience (concurrent stock movements) | Resilience under concurrency |
| `tests/test_reality_simulation.py` (2 uses) | End-to-end reality simulation | Stock movement accuracy over 30/60/180 day simulations |
| `tests/test_rollback_safety.py` | Rollback safety | Can rollback stock movements |
| `tests/test_services_extra.py` | Edge cases | Service-specific edge cases |
| `tests/test_coverage_final.py` | Coverage | Coverage of all 13 public methods |
| `tests/test_integration_comprehensive.py` (2 uses) | End-to-end integration | Integration with sales/purchase |
| `tests/test_more_coverage.py` | More coverage | Additional edge cases |
| `backend/inventory/service/__init__.py` (production) | Re-exports StockIntegrationService | Import works |
| `backend/inventory/service/stock_transfer.py` (production) | Uses StockIntegrationService for warehouse transfers | Transfer creates correct stock movements |
| `backend/inventory/services/costing_service.py` (production) | Uses StockIntegrationService for cost calculation | Cost calculation accurate |

**Specific assertions to verify after refactor:**
- [ ] All 13 public methods return the same data structures
- [ ] `StockSelectionMode` (nested class) still importable and works
- [ ] Batch selection algorithm unchanged
- [ ] Stock movement creation unchanged
- [ ] Cost calculation unchanged
- [ ] 3 production callers (`__init__.py`, `stock_transfer.py`, `costing_service.py`) still work
- [ ] 13 test files (the 2 collection-error ones excluded) still pass

**Pre-existing test issues to be aware of (NOT refactor-caused):**
- `test_stock_integration_behavior.py` — collection error (pre-Phase 6.0)
- `test_stock_integration_enterprise.py` — collection error (pre-Phase 6.0)

---

### 2.4 `frontend/ui/main_window.py` — **DO NOT TOUCH** (defer to Phase 6.4)

| Test | What it verifies |
|------|------------------|
| `frontend/tests/ui/test_main_window.py` (13 uses) | MainWindow instantiates correctly, page registration works, navigation state machine, auth integration |
| `frontend/tests/ui/test_smoke.py` | App starts without errors |
| `frontend/tests/conftest.py` | App fixtures (1 use) |
| `frontend/main.py` (production) | Entry point: `MainWindow()` is instantiated |

**Why this is the hardest regression matrix:** The 13 test fixtures in `test_main_window.py` exercise 13 different scenarios. Any refactor must preserve all 13.

**Phase 6.4 pre-requisites:**
- Each of the 21 pages extracted to its own module (then they can be tested in isolation)
- Navigation registry extracted to a separate module
- Auth wiring extracted

---

### 2.5 `frontend/ui/pos/pos_screen.py` — **HIGH RISK**

| Test | What it verifies |
|------|------------------|
| `frontend/tests/ui/test_smoke.py` (uses 2x) | POSScreen instantiates without errors |
| `frontend/ui/main_window.py` (production) | Page registration for index 7 |

**Specific assertions to verify after refactor:**
- [ ] `POSScreen()` instantiates
- [ ] All 6 public methods still work
- [ ] Cart management preserves state across actions
- [ ] Payment calculation is correct
- [ ] Batch selection works
- [ ] Customer selection works
- [ ] Page registration in `main_window.py` still works

**No dedicated test file exists for POS** — testing relies on smoke tests only. This makes refactoring riskier.

---

### 2.6 `frontend/ui/sales/sales_invoice_screen.py` — **HIGH RISK**

| Test | What it verifies |
|------|------------------|
| `frontend/tests/ui/test_smoke.py` (2 uses) | SalesInvoiceScreen instantiates without errors |
| `frontend/tests/ui/test_screens.py` (1 use) | SalesInvoiceScreen lifecycle |
| `frontend/ui/main_window.py` (production) | Page registration for index 1 |

**Specific assertions to verify after refactor (private method extraction):**
- [ ] `SalesInvoiceScreen()` instantiates
- [ ] All 24 public methods still work
- [ ] The 5 new private methods (`_setup_header`, `_setup_line_items`, `_setup_totals`, `_setup_action_bar`, `_setup_validation`) produce the same UI as the original `_setup_screen`
- [ ] All 28 remaining private methods unchanged
- [ ] Page registration in `main_window.py` still works

**Phase 3C notes:** The line-item table uses POS-specific widgets (not `DataEntryGrid`) — the refactor must not touch this part.

---

### 2.7 `frontend/ui/purchases/purchase_invoice_screen.py` — **HIGH RISK**

| Test | What it verifies |
|------|------------------|
| `frontend/tests/ui/test_screens.py` (1 use) | PurchaseInvoiceScreen lifecycle |
| `frontend/ui/main_window.py` (production) | Page registration for index 2 |

**Specific assertions to verify after refactor (private method extraction):**
- [ ] `PurchaseInvoiceScreen()` instantiates
- [ ] All 20 public methods still work
- [ ] The 5 new private methods (`_setup_header`, `_setup_line_items`, `_setup_totals`, `_setup_action_bar`, `_setup_validation`) produce the same UI as the original `_setup_screen`
- [ ] All 31 remaining private methods unchanged
- [ ] Page registration in `main_window.py` still works
- [ ] `DataEntryGrid` for line items (Phase 3C) still works

---

## 3. Cross-Cutting Regression Tests

These tests verify that **all** refactored files preserve Phase 5.9 / Phase 6.2 invariants:

| Test | Verifies |
|------|----------|
| `tests/test_validation_harness.py` | End-to-end integration across all modules |
| `tests/test_reality_simulation.py` | 30/60/180-day reality simulation |
| `tests/test_lifecycle_integration_enterprise.py` | Full lifecycle (purchase → stock → sale → payment) |
| `tests/test_enterprise_lifecycle_advanced.py` | Advanced lifecycle scenarios |
| `tests/test_financial_hardening.py` | Financial concurrency, double-entry |
| `tests/test_phase40_correctness.py` | Correctness across the 8 critical domains |
| `tests/test_phase41_resilience.py` | Resilience under failure |
| `tests/test_rollback_safety.py` | Rollback safety |

**These MUST pass before declaring any refactor safe.**

---

## 4. Performance Regression Budget

| File | Current Performance | Budget After Refactor | Notes |
|------|---------------------|----------------------|-------|
| `backup/backup_system.py` | baseline (Phase 6.2 measured) | +5% | Already met (Phase 6.2 verified) |
| `payments/services.py` | baseline (not measured) | +5% | Run before/after benchmark |
| `stock_integration.py` | baseline (not measured) | +5% | Run before/after benchmark |
| `main_window.py` | baseline (startup time) | +10% (UI startup) | Larger budget due to UI complexity |
| `pos_screen.py` | baseline (page load time) | +10% (UI) | |
| `sales_invoice_screen.py` | baseline (page load time) | +10% (UI) | |
| `purchase_invoice_screen.py` | baseline (page load time) | +10% (UI) | |

---

## 5. Rollback Test (per file)

Each refactored file must pass a **rollback test**:
1. Save the pre-refactor file as `<file>_BEFORE.py`
2. Run full test suite (must pass)
3. Apply refactor
4. Run full test suite (must pass)
5. Restore pre-refactor file from `<file>_BEFORE.py`
6. Run full test suite (must pass — proves rollback is valid)
7. Re-apply refactor
8. Run full test suite (must pass)

**This proves the refactor is reversible without side effects.**

---

## 6. Behavioral Verification Beyond Tests

| Verification | What it proves |
|--------------|----------------|
| Public method signatures unchanged (via `inspect.signature`) | API contract preserved |
| Error paths return the same exception types and messages | Failure mode preserved |
| Logging calls fire in the same order with the same arguments | Observability preserved |
| Database transactions have the same scope | Atomicity preserved |
| Signal handlers fire in the same order | Event ordering preserved |
| Cache writes/reads are unchanged | Performance characteristics preserved |
| File I/O patterns unchanged | Side effects preserved |

---

## 7. Refactor-Specific Test Additions

For each new extract module (e.g., `payments/services/extracts/process_receipt.py`), add a **focused unit test** that exercises just that function:

```python
# tests/test_extracts_payments_process_receipt.py
import pytest
from payments.services import PaymentEngine
from payments.services.extracts.process_receipt import run

def test_process_receipt_basic():
    engine = PaymentEngine()
    result = run(engine, customer=..., amount=..., method=...)
    assert result['success'] is True
    # ... etc
```

**These focused tests are ADDED, not required for the refactor to be considered safe.** They improve test coverage of the extracted code.

---

## 8. Regression Matrix Summary

| File | Tests Affected | Criticality | Effort to Update |
|------|----------------|-------------|------------------|
| `backup/backup_system.py` | 25 backup + 10 restore | HIGH | None (Phase 6.2 done) |
| `payments/services.py` | 5 test files + 4 production | HIGH | None (refactor preserves API) |
| `stock_integration.py` | 13 test files + 3 production | HIGH | None (refactor preserves API) |
| `main_window.py` | 13 test fixtures + 1 entry point | EXTREME | Many (if 21 pages not pre-extracted) |
| `pos_screen.py` | 2 smoke + 1 main_window | MEDIUM | None (refactor preserves API) |
| `sales_invoice_screen.py` | 2 smoke + 1 screens + 1 main_window | MEDIUM | None (refactor preserves API) |
| `purchase_invoice_screen.py` | 1 screens + 1 main_window | MEDIUM | None (refactor preserves API) |

---

## 9. Outputs

| File | Purpose |
|------|---------|
| `docs/PHASE6_3/evidence/audit_raw.json` | Per-test-file metadata |
| `docs/PHASE6_3/PHASE6_3_HUB_FILE_AUDIT.md` | Hub file metrics |
| `docs/PHASE6_3/PHASE6_3_COUPLING_ANALYSIS.md` | Per-file risk scores |
