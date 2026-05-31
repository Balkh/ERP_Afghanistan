# 07 — Runtime Failure Report

**Audit Date:** 2026-05-31
**Scope:** All frontend/ui/ files
**Methodology:** Static analysis for AttributeError, NameError, TypeError, RuntimeError, dead signals, event flow failures

---

## Executive Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 6 |
| MEDIUM | 4 |
| LOW | 3 |
| **Total** | **16** |

---

## CRITICAL — Will Crash at Runtime

### C1. AlertDialog wrong argument order — reconciliation_screen.py
- **File:** `frontend/ui/returns/reconciliation_screen.py:278,284,295,323,327,329,334,356,358,360`
- **Type:** TypeError
- **Crashes:** YES
- **Description:** 10 calls pass `self` (QWidget) as title parameter. `EnterpriseDialog.__init__` calls `setWindowTitle(self._title)` which expects str → TypeError.
- **Fix:** Swap `AlertDialog.info(self, "Title", "msg")` → `AlertDialog.info("Title", "msg", self)`

### C2. AlertDialog wrong argument order — journal_entry_form.py
- **File:** `frontend/ui/accounting/components/journal_entry_form.py:323,326,333,346,349`
- **Type:** TypeError
- **Crashes:** YES
- **Description:** 5 validation error dialogs pass `self` as title. Every journal entry validation error will crash.
- **Fix:** Same as C1

### C3. ConfirmDialog wrong argument order — base_screen.py
- **File:** `frontend/ui/screens/base_screen.py:253-255`
- **Type:** TypeError
- **Crashes:** YES
- **Description:** `ConfirmDialog.confirm(self, "Unsaved Changes", "message")` — dirty-state navigation guard for EVERY BaseScreen. Any screen with unsaved changes that triggers navigation will crash.
- **Fix:** `ConfirmDialog.confirm("Unsaved Changes", "message", self)`

---

## HIGH — Likely Failure / Broken Functionality

### H1. _combo_style() not an f-string — customer_payment_workspace.py
- **File:** `frontend/ui/finance/customer_payment_workspace.py:219-241`
- **Type:** RuntimeError (broken stylesheet)
- **Crashes:** NO (silent visual failure)
- **Description:** Returns regular string, not f-string. `{COLOR_BG_ELEVATED}` is literal text, not interpolated. All QComboBox styling broken.
- **Fix:** Add `f` prefix to return string

### H2. _combo_style() not an f-string — supplier_payment_workspace.py
- **File:** `frontend/ui/finance/supplier_payment_workspace.py:217-239`
- **Type:** Same as H1
- **Crashes:** NO (silent visual failure)
- **Description:** Identical issue — broken combo box styling.

### H3. load_accounts() treats dict as list — journal_entry_form.py
- **File:** `frontend/ui/accounting/components/journal_entry_form.py:199-210`
- **Type:** AttributeError (caught by except)
- **Crashes:** NO (silently fails)
- **Description:** `api_client.get()` returns wrapped dict `{"success": true, "data": [...]}`. Code iterates dict keys instead of list items. `except Exception: self.accounts = []` catches it — accounts never load in dropdown.
- **Fix:** Extract `data` key from response before iterating

### H4. API response treated as requests.Response — main_window.py
- **File:** `frontend/ui/main_window.py:180-181`
- **Type:** AttributeError (caught)
- **Crashes:** NO (silently fails)
- **Description:** `resp.status_code` and `resp.json()` called on dict. Company name never loads — window always shows "Pharmacy ERP".
- **Fix:** Change to `if isinstance(resp, dict) and resp.get("success"): data = resp.get("data", {})`

### H5. API response treated as requests.Response — settings_screen.py
- **File:** `frontend/ui/system/settings_screen.py:69,70,89,90,99,100,165,305`
- **Type:** Same as H4
- **Crashes:** NO (silently fails)
- **Description:** Multiple methods use `.status_code` and `.json()` on API dict. Theme settings, company currency never load from backend.
- **Fix:** Same pattern as H4

### H6. API response treated as requests.Response — printable_invoice.py
- **File:** `frontend/ui/common/printable_invoice.py:39-40`
- **Type:** Same as H4
- **Crashes:** NO (silently fails)
- **Description:** `_load_company_info()` uses `.status_code` and `.json()` on API dict. Printed invoices always show defaults.
- **Fix:** Same pattern as H4

---

## MEDIUM — Degraded Functionality

### M1. LoadingDialog.set_message misplaced — dialogs.py
- **File:** `frontend/ui/components/dialogs.py:341-343`
- **Type:** AttributeError (dead code)
- **Crashes:** NO (method unreachable)
- **Description:** `set_message()` defined inside `confirm_dialog()` function due to indentation error. `LoadingDialog` class is missing its method.
- **Fix:** Dedent `set_message` to be a method of `LoadingDialog`

### M2. Double QStatusBar creation — main_window.py
- **File:** `frontend/ui/main_window.py:264-266 vs 94-97`
- **Type:** RuntimeError (orphaned widgets)
- **Crashes:** NO (first status bar orphaned, labels invisible)
- **Description:** `_build_ui()` creates QStatusBar with device_id/license/connection labels. `_setup_status_bar()` creates SECOND status bar with user/health/conn/time labels. First becomes orphaned.
- **Fix:** Remove duplicate status bar creation

### M3. hold_sale() no-op — pos_screen.py
- **File:** `frontend/ui/pos/pos_screen.py:781-783`
- **Type:** Logic error
- **Crashes:** NO (button does nothing)
- **Description:** Checks `if not self.cart_items: return` but no implementation for non-empty case.

### M4. recall_sale() no-op — pos_screen.py
- **File:** `frontend/ui/pos/pos_screen.py:785-786`
- **Type:** Logic error
- **Crashes:** NO (button does nothing)
- **Description:** `pass` — button does nothing.

---

## LOW — Minor Issues

### L1. _print_last_invoice() no-op — pos_screen.py
- **File:** `frontend/ui/pos/pos_screen.py:758-759`
- **Type:** Logic error
- **Description:** `pass` — Print (F8) button does nothing.

### L2. Dead signal: sale_completed — pos_screen.py
- **File:** `frontend/ui/pos/pos_screen.py:63,719`
- **Type:** Dead signal
- **Description:** `sale_completed = Signal(dict)` defined and emitted but never connected.

### L3. Dead signal: sale_failed — pos_screen.py
- **File:** `frontend/ui/pos/pos_screen.py:64,730,738`
- **Type:** Dead signal
- **Description:** `sale_failed = Signal(str)` defined and emitted but never connected.

---

## Root Cause Patterns

### Pattern 1: Inconsistent AlertDialog Argument Order (3 CRITICAL + 2 HIGH)
**Files affected:** reconciliation_screen.py, journal_entry_form.py, base_screen.py, license_manager_dialog.py, totp_setup_dialog.py
**Root cause:** Some files use `(parent, title, message)` instead of `(title, message, parent)`
**Fix scope:** ~20 AlertDialog/ConfirmDialog calls across 5 files

### Pattern 2: API Client Returns Dict, Not Response (3 HIGH)
**Files affected:** main_window.py, settings_screen.py, printable_invoice.py
**Root cause:** Files written against raw `requests` API using `.status_code` and `.json()`
**Fix scope:** ~10 API call sites across 3 files

### Pattern 3: Missing f-string Prefix (2 HIGH)
**Files affected:** customer_payment_workspace.py, supplier_payment_workspace.py
**Root cause:** Missing `f` prefix on return strings with `{COLOR_*}` tokens
**Fix scope:** 2 files, simple one-character fix each
