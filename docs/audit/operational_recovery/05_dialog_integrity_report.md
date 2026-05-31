# 05 — Dialog Integrity Report

**Audit Date:** 2026-05-31
**Scope:** All 25 dialogs (17 standalone + 8 inline)
**Methodology:** Static analysis of open/validate/save/cancel/close/parent-refresh lifecycle

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total dialogs | 25 |
| FUNCTIONAL | 20 (80%) |
| PARTIAL | 4 (16%) |
| BROKEN | 1 (4%) |
| All inherit EnterpriseDialog | 25/25 (100%) |
| All have cancel action | 25/25 (100%) |
| All close properly | 24/25 (96%) |

---

## Complete Dialog Inventory

### Base Dialogs

| # | Dialog | File | Open | Validate | Save | Cancel | Close | Parent Refresh | Status |
|---|--------|------|------|----------|------|--------|-------|----------------|--------|
| 1 | EnterpriseDialog | `components/dialogs.py` | YES | N/A | YES | YES | YES | N/A | FUNCTIONAL |
| 2 | ConfirmDialog | `components/dialogs.py` | YES | N/A | YES | YES | YES | N/A | FUNCTIONAL |
| 3 | AlertDialog | `components/dialogs.py` | YES | N/A | YES | N/A | YES | N/A | FUNCTIONAL |

### Standalone Dialogs

| # | Dialog | File | Open | Validate | Save | Cancel | Close | Parent Refresh | Status |
|---|--------|------|------|----------|------|--------|-------|----------------|--------|
| 4 | DocumentActionDialog | `components/document_action_dialog.py` | YES | YES | YES | YES | YES | N/A | FUNCTIONAL |
| 5 | AccountFormDialog | `accounting/components/account_form_dialog.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 6 | ReportPreviewDialog | `accounting/components/report_preview_dialog.py` | YES | N/A | N/A | YES | YES | N/A | FUNCTIONAL |
| 7 | ProductFormDialog | `inventory/components/product_form.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 8 | BatchFormDialog | `inventory/components/batch_form_dialog.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 9 | CategoryFormDialog | `inventory/components/category_form_dialog.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 10 | WarehouseFormDialog | `inventory/components/warehouse_form_dialog.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 11 | CreditWarningDialog | `sales/credit_warning_dialog.py` | YES | N/A | N/A | YES | YES | N/A | FUNCTIONAL |
| 12 | FIFOAllocationDialog | `sales/fifo_allocation_dialog.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 13 | PayslipDialog | `hr/payslip_dialog.py` | YES | N/A | N/A | YES | YES | N/A | FUNCTIONAL |
| 14 | EmailConfigDialog | `system/email_config_dialog.py` | YES | YES | YES | YES | YES | N/A | FUNCTIONAL |
| 15 | MixedPaymentBuilderDialog | `finance/mixed_payment_builder.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 16 | **LicenseManagerDialog** | `licensing/license_manager_dialog.py` | YES | N/A | YES | YES | YES | YES | **PARTIAL** |
| 17 | LoginDialog | `auth/login_screen.py` | YES | YES | YES | N/A | YES | N/A | FUNCTIONAL |
| 18 | **TOTPSetupDialog** | `auth/totp_setup_dialog.py` | YES | YES | YES | YES | YES | YES | **PARTIAL** |
| 19 | **ProductSelectionDialog** | `common/product_selection_dialog.py` | **NO** | YES | YES | YES | **NO** | N/A | **BROKEN** |

### Inline Dialogs

| # | Dialog | File | Open | Validate | Save | Cancel | Close | Parent Refresh | Status |
|---|--------|------|------|----------|------|--------|-------|----------------|--------|
| 20 | CustomerDialog | `sales/customer_screen.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 21 | SupplierDialog | `purchases/supplier_screen.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 22 | EmployeeDialog | `hr/employee_screen.py` | YES | YES | YES | YES | YES | YES | FUNCTIONAL |
| 23 | **SalaryStructureDialog** | `hr/payroll_screen.py` | YES | YES | YES | YES | YES | **NO** | **PARTIAL** |
| 24 | **ReturnOrderDialog** | `returns/returns_screen.py` | YES | YES | YES | YES | YES | **NO** | **PARTIAL** |
| 25 | RestoreConfirmDialog | `system/backup_screen.py` | YES | N/A | YES | YES | YES | YES | FUNCTIONAL |

---

## BROKEN Dialog Detail

### ProductSelectionDialog (BROKEN)
**File:** `frontend/ui/common/product_selection_dialog.py`
**Issue:** `_build_content()` is never called from `__init__`. The dialog opens with no UI content.
**Impact:** Dialog crashes on open — `self.search_input`, `self.table`, `self.select_btn` are all undefined when `perform_search()` tries to access them.
**Fix:** Add `self._build_content()` call in `__init__` after `super().__init__()`.

---

## PARTIAL Dialog Details

### LicenseManagerDialog (PARTIAL)
**File:** `frontend/ui/licensing/license_manager_dialog.py:116-121, 128-132`
**Issue:** `AlertDialog.info(self, "Title", "message")` — wrong argument order. `self` passed as title.
**Impact:** Dialog title shows QWidget reference instead of "Activation Successful"/"Activation Failed".

### TOTPSetupDialog (PARTIAL)
**File:** `frontend/ui/auth/totp_setup_dialog.py:169`
**Issue:** `AlertDialog.info(self, "Success", "message")` — wrong argument order.
**Impact:** Same as above.

### SalaryStructureDialog (PARTIAL)
**File:** `frontend/ui/hr/payroll_screen.py:378`
**Issue:** `dialog.exec()` result not checked — no parent refresh after save.
**Impact:** Newly created salary structure not visible until manual screen refresh.

### ReturnOrderDialog (PARTIAL)
**File:** `frontend/ui/returns/returns_screen.py:363-364`
**Issue:** `dialog.exec()` result not checked — no parent refresh after save.
**Impact:** Newly created return order not visible until manual screen refresh.

---

## Lifecycle Patterns

### Standard Pattern (20 dialogs)
```
dialog = MyDialog(parent, ...)
if dialog.exec():
    self.refresh_data()
```

### Broken Patterns Found
1. **Missing exec() check:** SalaryStructureDialog, ReturnOrderDialog — `dialog.exec()` called without checking result
2. **Wrong AlertDialog args:** LicenseManagerDialog, TOTPSetupDialog, ReconciliationScreen — `self` passed as title
3. **Missing content build:** ProductSelectionDialog — `_build_content()` never called

---

## Summary

| Category | Dialogs |
|----------|---------|
| Fully functional | EnterpriseDialog, ConfirmDialog, AlertDialog, DocumentActionDialog, AccountFormDialog, ReportPreviewDialog, ProductFormDialog, BatchFormDialog, CategoryFormDialog, WarehouseFormDialog, CreditWarningDialog, FIFOAllocationDialog, PayslipDialog, EmailConfigDialog, MixedPaymentBuilderDialog, LoginDialog, CustomerDialog, SupplierDialog, EmployeeDialog, RestoreConfirmDialog |
| Partial (AlertDialog args) | LicenseManagerDialog, TOTPSetupDialog |
| Partial (no parent refresh) | SalaryStructureDialog, ReturnOrderDialog |
| Broken (no content) | ProductSelectionDialog |
