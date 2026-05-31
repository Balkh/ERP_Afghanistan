# 11 — Root Cause Analysis

**Audit Date:** 2026-05-31
**Scope:** All findings from Sections 1-10
**Methodology:** Synthesize symptoms into root causes, identify systemic patterns

---

## Executive Summary

| Root Cause Category | Issues Affected | Severity |
|---------------------|----------------|----------|
| RC-1: Inconsistent AlertDialog/ConfirmDialog Argument Order | 5 files, ~20 calls | CRITICAL |
| RC-2: API Client Returns Dict, Not Response | 3 files, ~10 call sites | HIGH |
| RC-3: Missing f-string Prefix on Stylesheet Strings | 2 files | HIGH |
| RC-4: Dead Button Signal Connections | 3 buttons, 1 screen | HIGH |
| RC-5: Missing Parent Refresh After Dialog Save | 2 dialogs | MEDIUM |
| RC-6: Malformed API URLs | 2 screens | HIGH |
| RC-7: Non-Existent Backend Endpoints | 2 screens | HIGH |
| RC-8: No-Op Method Implementations | 3 methods, 1 screen | MEDIUM |
| RC-9: Timer Lifecycle Management | 4 screens | LOW |
| RC-10: Orphaned Screen Files | 11 files | LOW |

---

## Root Cause Details

### RC-1: Inconsistent AlertDialog/ConfirmDialog Argument Order (CRITICAL)
**Pattern:** Some files call `AlertDialog.info(parent, title, message)` instead of `AlertDialog.info(title, message, parent)`
**Files affected:**
- `frontend/ui/returns/reconciliation_screen.py` — 10 calls
- `frontend/ui/accounting/components/journal_entry_form.py` — 5 calls
- `frontend/ui/screens/base_screen.py` — 1 call (ConfirmDialog)
- `frontend/ui/licensing/license_manager_dialog.py` — 2 calls
- `frontend/ui/auth/totp_setup_dialog.py` — 1 call

**Root cause:** No centralized documentation of the AlertDialog API signature. Files were written by different developers at different times with different assumptions about argument order.

**Impact:** 19 dialog calls will throw TypeError at runtime. Reconciliation screen, Journal Entry Form, BaseScreen navigation guard, License Manager, and TOTP Setup are all broken.

**Fix scope:** Swap arguments in 19 calls across 5 files.

---

### RC-2: API Client Returns Dict, Not Response (HIGH)
**Pattern:** Files use `resp.status_code` and `resp.json()` which are `requests.Response` methods, but `api_client.get()` returns a parsed dict.
**Files affected:**
- `frontend/ui/main_window.py:180-181` — company name never loads
- `frontend/ui/system/settings_screen.py:69,70,89,90,99,100,165,305` — settings never load from API
- `frontend/ui/common/printable_invoice.py:39-40` — company info on printed invoices always defaults

**Root cause:** `APIClient` was refactored from returning raw `requests.Response` to returning parsed dicts, but these 3 files were not updated.

**Impact:** Company name, theme settings, currency settings, and printed invoice company info all silently fail. Users see hardcoded defaults instead of actual configuration.

**Fix scope:** Change `resp.status_code` → `isinstance(resp, dict) and resp.get("success")` and `resp.json()` → `resp.get("data", {})` in ~10 call sites across 3 files.

---

### RC-3: Missing f-string Prefix on Stylesheet Strings (HIGH)
**Pattern:** `_combo_style()` methods return regular strings with `{COLOR_*}` tokens instead of f-strings.
**Files affected:**
- `frontend/ui/finance/customer_payment_workspace.py:219-241`
- `frontend/ui/finance/supplier_payment_workspace.py:217-239`

**Root cause:** Copy-paste without adding `f` prefix. The double-brace `{{` Qt syntax looks correct syntactically but without `f` prefix, the `{COLOR_*}` tokens are literal text.

**Impact:** All QComboBox widgets in Customer Payment Workspace and Supplier Payment Workspace render with no custom styling — they look like native OS widgets instead of matching the enterprise theme.

**Fix scope:** Add `f` prefix to 2 return strings.

---

### RC-4: Dead Button Signal Connections (HIGH)
**Pattern:** Buttons are created with `EnterpriseButton(...)` but `.clicked.connect()` is never called.
**Files affected:**
- `frontend/ui/hr/payroll_screen.py:155,156,184` — Generate Payroll, Approve, Export to Excel

**Root cause:** Buttons were created as part of UI layout but the backend integration (payroll generation, approval, export) was never implemented or wired.

**Impact:** Payroll module's core workflow buttons are non-functional. Users can view payroll data but cannot generate, approve, or export.

**Fix scope:** Implement and connect 3 button handlers.

---

### RC-5: Missing Parent Refresh After Dialog Save (MEDIUM)
**Pattern:** `dialog.exec()` called without checking result, no `load_data()` call after.
**Files affected:**
- `frontend/ui/hr/payroll_screen.py:378` — SalaryStructureDialog
- `frontend/ui/returns/returns_screen.py:363-364` — ReturnOrderDialog

**Root cause:** Inconsistent dialog result handling pattern. Some dialogs use `if dialog.exec(): self.refresh()`, others just call `dialog.exec()`.

**Impact:** Newly created salary structures and return orders not visible until manual screen refresh.

**Fix scope:** Add `if dialog.exec(): self.load_data()` in 2 locations.

---

### RC-6: Malformed API URLs (HIGH)
**Pattern:** URLs missing `/api/` prefix or using wrong path.
**Files affected:**
- `frontend/ui/accounting/financial_integrity_screen.py` — `sales/customer-payments/financial_integrity/`
- `frontend/ui/accounting/financial_audit_log_screen.py` — `audit/audit-trails/`

**Root cause:** URLs hardcoded without using `get_endpoint()` registry. Written before the endpoint registry was standardized.

**Impact:** Financial Integrity screen and Financial Audit Log screen cannot load data — endpoints return 404.

**Fix scope:** Replace hardcoded URLs with `get_endpoint()` calls and fix endpoint registry.

---

### RC-7: Non-Existent Backend Endpoints (HIGH)
**Pattern:** Frontend references endpoints that don't exist in backend URL configuration.
**Files affected:**
- `frontend/ui/hr/payroll_screen.py` — `salary-structures/` (not in `payroll/urls.py`)
- `frontend/ui/accounting/financial_integrity_screen.py` — `financial_integrity/` and `fix_balances/` (not in `sales/urls.py`)

**Root cause:** Frontend was built against planned backend endpoints that were never implemented or were implemented under different paths.

**Impact:** Salary structure CRUD returns 404. Financial integrity check returns 404.

**Fix scope:** Either add the missing backend endpoints or update frontend to use existing endpoints.

---

### RC-8: No-Op Method Implementations (MEDIUM)
**Pattern:** Methods connected to buttons but body is `pass`.
**Files affected:**
- `frontend/ui/pos/pos_screen.py:781-783` — `hold_sale()`
- `frontend/ui/pos/pos_screen.py:785-786` — `recall_sale()`
- `frontend/ui/pos/pos_screen.py:758-759` — `_print_last_invoice()`

**Root cause:** POS screen was built with UI placeholders for features not yet implemented.

**Impact:** Hold, Recall, and Print buttons in POS appear functional but silently do nothing. Misleading for cashiers.

**Fix scope:** Implement 3 methods or show "Coming Soon" dialog.

---

### RC-9: Timer Lifecycle Management (LOW)
**Pattern:** QTimer instances run even when their parent screen is not visible.
**Files affected:**
- `frontend/ui/dashboard.py:31` — 2-min refresh
- `frontend/ui/system/control_center_screen.py:341` — 15-sec refresh
- `frontend/ui/control_tower/system_health_screen.py:53` — 15-sec refresh
- `frontend/ui/accounting/financial_integrity_screen.py:39` — 5-min refresh

**Root cause:** Timers started in `__init__` or `_setup_screen()` without corresponding stop/pause in `hideEvent`.

**Impact:** Unnecessary API calls and CPU usage when screens are not visible.

**Fix scope:** Add `hideEvent`/`showEvent` handlers to pause/resume timers.

---

### RC-10: Orphaned Screen Files (LOW)
**Pattern:** Screen files exist but are not registered in `screen_registry.py` or accessible from sidebar.
**Files affected:** 11 files across `system/`, `control_tower/`, `observability/`, `investigation/`

**Root cause:** Screens were created during development phases but superseded by newer implementations without being cleaned up.

**Impact:** Dead code increases codebase size and creates confusion about which screen is canonical.

**Fix scope:** Remove or archive 11 orphaned files.

---

## Systemic Issues

### Issue 1: No Centralized API Response Handling
Files inconsistently handle API responses — some use `get_endpoint()` + dict unpacking, others use raw `.status_code` + `.json()`. No standard pattern enforced.

### Issue 2: No AlertDialog API Documentation
The `AlertDialog` class has a specific argument order `(title, message, parent)` but this is not documented or enforced. Different files use different orders.

### Issue 3: Dead Feature Placeholders
Multiple screens have buttons/features that are placeholders (POS hold/recall/print, payroll generate/approve, payment workspace "Coming Soon"). These should be either implemented or hidden.

### Issue 4: Timer Resource Leaks
Timers started without lifecycle management create background API traffic when screens are hidden.

---

## Fix Priority Matrix

| Root Cause | Severity | Effort | Files | Priority |
|------------|----------|--------|-------|----------|
| RC-1: AlertDialog args | CRITICAL | LOW (swap args) | 5 | P0 |
| RC-2: API response handling | HIGH | LOW (pattern replace) | 3 | P1 |
| RC-6: Malformed URLs | HIGH | LOW (fix URLs) | 2 | P1 |
| RC-7: Non-existent endpoints | HIGH | MEDIUM (add endpoints or fix FE) | 2 | P1 |
| RC-3: Missing f-string | HIGH | LOW (add 'f' prefix) | 2 | P1 |
| RC-4: Dead buttons | HIGH | MEDIUM (implement handlers) | 1 | P1 |
| RC-5: Missing parent refresh | MEDIUM | LOW (add if/refresh) | 2 | P2 |
| RC-8: No-op methods | MEDIUM | MEDIUM (implement or hide) | 1 | P2 |
| RC-9: Timer lifecycle | LOW | LOW (add hide/show handlers) | 4 | P3 |
| RC-10: Orphaned files | LOW | LOW (delete files) | 11 | P3 |
