# 02 — Button Wiring Report

**Audit Date:** 2026-05-31
**Scope:** All buttons in all screens and dialogs
**Methodology:** Static analysis of signal/slot connections, button states, and runtime risks

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total buttons found | ~215 |
| CONNECTED (signal → valid slot) | ~202 (94%) |
| DEAD (no signal connected) | 3 (1%) |
| PARTIAL (connected but empty/no-op) | 3 (1%) |
| CRITICAL (runtime exception risk) | 6 (3%) |
| Raw QPushButton usage | 0 (all use EnterpriseButton) |

---

## CRITICAL Issues (Runtime Exception Risk)

### CRITICAL-1: ReconciliationScreen — Wrong AlertDialog API calls
**File:** `frontend/ui/returns/reconciliation_screen.py`
**Lines:** 278, 284, 295, 323, 327, 329, 334, 356, 358, 360

All alert dialogs pass `self` as title instead of parent:
```python
# WRONG: AlertDialog.info(self, "Title", "message")
# RIGHT: AlertDialog.info("Title", "message", self)
```
**Impact:** 10 dialog calls will throw TypeError at runtime. Entire Reconciliation screen is broken.

### CRITICAL-2: JournalEntryForm — Wrong AlertDialog API calls
**File:** `frontend/ui/accounting/components/journal_entry_form.py`
**Lines:** 323, 326, 333, 346, 349

Same pattern — validation error dialogs pass `self` as title.
**Impact:** Every validation error on journal entry creation will crash.

### CRITICAL-3: BaseScreen — Wrong ConfirmDialog API call
**File:** `frontend/ui/screens/base_screen.py`
**Lines:** 253-255

```python
# WRONG: ConfirmDialog.confirm(self, "Unsaved Changes", "message")
# RIGHT: ConfirmDialog.confirm("Unsaved Changes", "message", self)
```
**Impact:** Any screen with unsaved changes that triggers navigation will crash.

### CRITICAL-4: LicenseManagerDialog — Wrong AlertDialog API calls
**File:** `frontend/ui/licensing/license_manager_dialog.py`
**Lines:** 116-121, 128-132

Same pattern — activation success/failure dialogs pass `self` as title.

### CRITICAL-5: TOTPSetupDialog — Wrong AlertDialog API call
**File:** `frontend/ui/auth/totp_setup_dialog.py`
**Line:** 169

Same pattern — success dialog passes `self` as title.

---

## DEAD Buttons (No Signal Connection)

### DEAD-1: PayrollScreen — "Generate Payroll" button
**File:** `frontend/ui/hr/payroll_screen.py:155`
```python
generate_btn = EnterpriseButton(text="Generate Payroll", variant=ButtonVariant.PRIMARY)
# No .clicked.connect() — button is DEAD
```

### DEAD-2: PayrollScreen — "Approve" button
**File:** `frontend/ui/hr/payroll_screen.py:156`
```python
approve_btn = EnterpriseButton(text="Approve", variant=ButtonVariant.SUCCESS)
# No .clicked.connect() — button is DEAD
```

### DEAD-3: PayrollScreen — "Export to Excel" button
**File:** `frontend/ui/hr/payroll_screen.py:184`
```python
export_btn = EnterpriseButton(text="Export to Excel", variant=ButtonVariant.SECONDARY)
# No .clicked.connect() — button is DEAD
```

---

## PARTIAL Buttons (Connected but No-Op)

### PARTIAL-1: POSScreen — "Hold (F6)" button
**File:** `frontend/ui/pos/pos_screen.py:115` → `hold_sale` (line 781)
**Body:** `pass` — does nothing.

### PARTIAL-2: POSScreen — "Recall (F7)" button
**File:** `frontend/ui/pos/pos_screen.py:118` → `recall_sale` (line 785)
**Body:** `pass` — does nothing.

### PARTIAL-3: POSScreen — "Print (F8)" button
**File:** `frontend/ui/pos/pos_screen.py:415` → `_print_last_invoice` (line 758)
**Body:** `pass` — does nothing.

---

## Complete Button Inventory by Screen

### Dashboard (5 buttons)
| Button | Connected | Slot | Status |
|--------|-----------|------|--------|
| Refresh | YES | refresh_data | CONNECTED |
| New Sale | YES | _navigate_to(5) | CONNECTED |
| New Purchase | YES | _navigate_to(6) | CONNECTED |
| Products | YES | _navigate_to(1) | CONNECTED |
| Reports | YES | _navigate_to(13) | CONNECTED |

### Inventory Screens (4 buttons each, 16 total)
All inventory screens use BaseInventoryScreen with Add/Edit/Delete/Refresh — all CONNECTED via signals.

### Sales Invoice Screen (12 buttons)
| Button | Connected | Status |
|--------|-----------|--------|
| + Add Product | YES → show_product_selector | CONNECTED |
| Remove | YES → remove_selected_item | CONNECTED |
| Save Invoice | YES → save_draft | CONNECTED |
| Confirm & Dispatch | YES → confirm_invoice | CONNECTED |
| More ▾ (QMenu) | 4 items all connected | CONNECTED |
| Create Return | YES → create_return | CONNECTED |
| Submit for Approval | YES → perform_workflow_action | CONNECTED |
| Approve | YES → perform_workflow_action | CONNECTED |
| Reject | YES → perform_workflow_action | CONNECTED |
| Post | YES → perform_workflow_action | CONNECTED |
| Select Batch (dynamic) | YES → select_batch_for_row | CONNECTED |
| Remove (dynamic) | YES → items_table.removeRow | CONNECTED |

### Customer Screen (4 buttons)
All connected: Add, Edit, Delete, Refresh.

### Purchase Invoice Screen (11 buttons)
All connected: + Add Product, Remove, Save, Confirm & Receive, More ▾, Create Return, workflow buttons.

### Supplier Screen (4 buttons)
All connected: Add, Edit, Delete, Refresh.

### Returns Screen (7 buttons)
All connected: Refresh, + New Return, Approve, Reject, Void, Print Receipt, Export CSV.

### Reconciliation Screen (5 buttons)
All connected but 3 have CRITICAL AlertDialog API bugs.

### Chart of Accounts (4 buttons)
All connected: Add Account, Edit, Delete, Refresh.

### Journal Entry Screen (7 buttons)
All connected: Refresh, New Entry, View Details, Post, Unpost, Reverse, Apply Filters.

### Account Ledger (3 buttons)
All connected: Load Ledger, Export CSV, Print Preview.

### Report Browser (2 buttons)
All connected: Run Report, Export CSV.

### Financial Integrity (2 buttons)
All connected: Run Validation, Auto-Fix Balances.

### Financial Audit Log (1 button)
Connected: Refresh.

### Payment Screen (2 buttons)
All connected: Refresh, Apply Filters.

### Customer Payment Workspace (3 buttons)
| Button | Connected | Status |
|--------|-----------|--------|
| Refresh | YES → refresh_workspace | CONNECTED |
| + Process Payment | YES → _on_process_payment | PARTIAL (shows "Coming Soon") |
| Allocate FIFO | YES → _on_allocate_fifo | CONNECTED |

### Supplier Payment Workspace (3 buttons)
Same pattern — Process Payment shows "Coming Soon".

### Employee Screen (4 buttons)
All connected: Refresh, + Add Employee, Edit, Delete.

### Attendance Screen (1 button)
Connected: Refresh.

### Leave Screen (1 button)
Connected: Refresh.

### Payroll Screen (6 buttons)
| Button | Connected | Status |
|--------|-----------|--------|
| Refresh | YES → load_data | CONNECTED |
| + Add Structure | YES → _add_salary_structure | CONNECTED |
| Generate Payroll | **NO** | **DEAD** |
| Approve | **NO** | **DEAD** |
| Generate Payslip | YES → _generate_payslip | CONNECTED |
| Export to Excel | **NO** | **DEAD** |

### POS Screen (8 buttons)
| Button | Connected | Status |
|--------|-----------|--------|
| Hold (F6) | YES → hold_sale | PARTIAL (pass) |
| Recall (F7) | YES → recall_sale | PARTIAL (pass) |
| New Sale (F2) | YES → new_sale | CONNECTED |
| Complete Sale (F10) | YES → _process_payment | CONNECTED |
| Print (F8) | YES → _print_last_invoice | PARTIAL (pass) |
| Cancel (Esc) | YES → new_sale | CONNECTED |
| Search "+" (dynamic) | YES → _add_search_result_to_cart | CONNECTED |
| Cart "✕" (dynamic) | YES → _remove_item | CONNECTED |

### Backup Screen (9 buttons)
All connected: Create Backup, Refresh, Send Email, Email Config, Restore, Verify, Delete, Process Retry Queue, Retry Selected.

### Settings Screen (2 buttons)
All connected: Save Settings, Reset to Defaults.

### Login Screen (4 actions)
All connected: Sign In, Show Password, Username Enter, Password Enter.

### EnterpriseDialog Base (5 button types)
All connected: Yes/No (CONFIRM), OK (ALERT), Cancel/Save (CUSTOM).

### Finance Screens (Expense, Tax, Cashflow, Cost Centers, Budgeting)
All have Refresh connected to load_data.

### Fixed Assets Screen (1 button)
Connected: Refresh.

---

## Summary by Category

| Category | Total | CONNECTED | DEAD | PARTIAL | CRITICAL |
|----------|-------|-----------|------|---------|----------|
| Dashboard | 5 | 5 | 0 | 0 | 0 |
| Inventory (4 screens) | 16 | 16 | 0 | 0 | 0 |
| Sales (2 screens) | 16 | 16 | 0 | 0 | 0 |
| Purchases (2 screens) | 15 | 15 | 0 | 0 | 0 |
| Returns (2 screens) | 12 | 9 | 0 | 0 | 3 |
| Accounting (6 screens) | 22 | 22 | 0 | 0 | 0 |
| Finance (12 screens) | 24 | 22 | 0 | 2 | 0 |
| HR (4 screens) | 12 | 9 | 3 | 0 | 0 |
| POS (1 screen) | 8 | 5 | 0 | 3 | 0 |
| System (16 screens) | 24 | 24 | 0 | 0 | 0 |
| Dialogs (25 dialogs) | 40 | 37 | 0 | 0 | 3 |
| **TOTAL** | **~215** | **~202** | **3** | **5** | **6** |
