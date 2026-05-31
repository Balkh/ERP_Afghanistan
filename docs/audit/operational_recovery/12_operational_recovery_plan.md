# 12 — Operational Recovery Plan

**Audit Date:** 2026-05-31
**Scope:** All findings from Sections 1-10, prioritized by severity and business impact
**Methodology:** Classify issues into 4 priority levels, estimate effort and dependencies

---

## Executive Summary

| Priority | Issues | Effort | Impact |
|----------|--------|--------|--------|
| P1 — System Breaking | 4 issues | ~2 hours | Crashes on multiple screens |
| P2 — Operational Blocking | 5 issues | ~4 hours | Broken features, missing data |
| P3 — Productivity Loss | 4 issues | ~3 hours | Degraded UX, misleading UI |
| P4 — Cosmetic | 3 issues | ~2 hours | Resource waste, dead code |

---

## P1 — System Breaking (Fix Immediately)

### P1-1: Fix AlertDialog/ConfirmDialog Argument Order
- **Severity:** CRITICAL
- **Business Impact:** Reconciliation screen, Journal Entry Form, BaseScreen navigation guard, License Manager, TOTP Setup all crash at runtime
- **Effort:** 30 minutes
- **Affected Files:**
  - `frontend/ui/returns/reconciliation_screen.py` — 10 calls
  - `frontend/ui/accounting/components/journal_entry_form.py` — 5 calls
  - `frontend/ui/screens/base_screen.py` — 1 call
  - `frontend/ui/licensing/license_manager_dialog.py` — 2 calls
  - `frontend/ui/auth/totp_setup_dialog.py` — 1 call
- **Fix:** Swap `AlertDialog.info(self, "Title", "msg")` → `AlertDialog.info("Title", "msg", self)` in all 19 calls
- **Dependencies:** None

### P1-2: Fix Malformed API URLs
- **Severity:** HIGH
- **Business Impact:** Financial Integrity screen and Financial Audit Log screen cannot load data (404 errors)
- **Effort:** 30 minutes
- **Affected Files:**
  - `frontend/ui/accounting/financial_integrity_screen.py` — fix URLs, use `get_endpoint()`
  - `frontend/ui/accounting/financial_audit_log_screen.py` — fix URL prefix
- **Fix:** Replace hardcoded URLs with `get_endpoint()` calls
- **Dependencies:** None

### P1-3: Fix API Response Handling (Dict vs Response)
- **Severity:** HIGH
- **Business Impact:** Company name, theme settings, currency settings, printed invoice info all silently fail
- **Effort:** 1 hour
- **Affected Files:**
  - `frontend/ui/main_window.py:180-181`
  - `frontend/ui/system/settings_screen.py:69,70,89,90,99,100,165,305`
  - `frontend/ui/common/printable_invoice.py:39-40`
- **Fix:** Change `resp.status_code` → `isinstance(resp, dict) and resp.get("success")` and `resp.json()` → `resp.get("data", {})`
- **Dependencies:** None

### P1-4: Fix Non-Existent Backend Endpoints
- **Severity:** HIGH
- **Business Impact:** Salary structure CRUD returns 404; Financial integrity check returns 404
- **Effort:** 1 hour
- **Affected Files:**
  - `frontend/ui/hr/payroll_screen.py` — `salary-structures/` endpoint doesn't exist
  - `frontend/ui/accounting/financial_integrity_screen.py` — `financial_integrity/` and `fix_balances/` don't exist
- **Fix:** Either add backend endpoints or update frontend to use existing endpoints
- **Dependencies:** May require backend changes

---

## P2 — Operational Blocking (Fix Before Release)

### P2-1: Fix Missing f-string Prefix on Stylesheets
- **Severity:** HIGH
- **Business Impact:** Customer Payment Workspace and Supplier Payment Workspace combo boxes have broken styling
- **Effort:** 5 minutes
- **Affected Files:**
  - `frontend/ui/finance/customer_payment_workspace.py:219-241`
  - `frontend/ui/finance/supplier_payment_workspace.py:217-239`
- **Fix:** Add `f` prefix to return strings
- **Dependencies:** None

### P2-2: Wire Payroll Dead Buttons
- **Severity:** HIGH
- **Business Impact:** Payroll Generate, Approve, and Export buttons are non-functional
- **Effort:** 2 hours
- **Affected Files:**
  - `frontend/ui/hr/payroll_screen.py:155,156,184`
- **Fix:** Implement and connect button handlers to `/api/payroll/generate/`, `/api/payroll/approve/`, and CSV export
- **Dependencies:** Requires backend `/api/payroll/salary-structures/` endpoint (P1-4)

### P2-3: Fix Missing Parent Refresh After Dialog Save
- **Severity:** MEDIUM
- **Business Impact:** Newly created salary structures and return orders not visible until manual refresh
- **Effort:** 10 minutes
- **Affected Files:**
  - `frontend/ui/hr/payroll_screen.py:378`
  - `frontend/ui/returns/returns_screen.py:363-364`
- **Fix:** Add `if dialog.exec(): self.load_data()` pattern
- **Dependencies:** None

### P2-4: Fix ProductSelectionDialog Broken Content
- **Severity:** HIGH
- **Business Impact:** Product selection dialog crashes on open — no UI content rendered
- **Effort:** 15 minutes
- **Affected Files:**
  - `frontend/ui/common/product_selection_dialog.py`
- **Fix:** Add `self._build_content()` call in `__init__` after `super().__init__()`
- **Dependencies:** None

### P2-5: Fix ProductSelectionDialog AlertDialog Args
- **Severity:** MEDIUM
- **Business Impact:** Product selection dialog shows wrong content in alerts
- **Effort:** 5 minutes
- **Affected Files:**
  - `frontend/ui/common/product_selection_dialog.py`
- **Fix:** Swap AlertDialog argument order
- **Dependencies:** P2-4

---

## P3 — Productivity Loss (Fix Before Deployment)

### P3-1: Implement POS Hold/Recall/Print
- **Severity:** MEDIUM
- **Business Impact:** POS cashiers click Hold/Recall/Print buttons and get zero response
- **Effort:** 2 hours
- **Affected Files:**
  - `frontend/ui/pos/pos_screen.py:781-786,758-759`
- **Fix:** Implement hold_sale, recall_sale, _print_last_invoice methods or show "Coming Soon" dialog
- **Dependencies:** None

### P3-2: Wire Customer/Supplier Payment "Process Payment" Buttons
- **Severity:** MEDIUM
- **Business Impact:** "Coming Soon" message shown when trying to process payments
- **Effort:** 2 hours
- **Affected Files:**
  - `frontend/ui/finance/customer_payment_workspace.py:69-72`
  - `frontend/ui/finance/supplier_payment_workspace.py:69-72`
- **Fix:** Implement payment processing dialog or connect to existing payment engine
- **Dependencies:** None

### P3-3: Fix LoadingDialog.set_message Indentation
- **Severity:** MEDIUM
- **Business Impact:** LoadingDialog missing set_message method (dead code due to indentation error)
- **Effort:** 5 minutes
- **Affected Files:**
  - `frontend/ui/components/dialogs.py:341-343`
- **Fix:** Dedent `set_message` to be a method of `LoadingDialog`
- **Dependencies:** None

### P3-4: Fix Double QStatusBar Creation
- **Severity:** MEDIUM
- **Business Impact:** First status bar orphaned, 3 labels invisible
- **Effort:** 15 minutes
- **Affected Files:**
  - `frontend/ui/main_window.py:264-266 vs 94-97`
- **Fix:** Remove duplicate status bar creation
- **Dependencies:** None

---

## P4 — Cosmetic (Tech Debt)

### P4-1: Timer Lifecycle Management
- **Severity:** LOW
- **Business Impact:** Unnecessary API calls when screens not visible
- **Effort:** 1 hour
- **Affected Files:**
  - `frontend/ui/dashboard.py:31`
  - `frontend/ui/system/control_center_screen.py:341`
  - `frontend/ui/control_tower/system_health_screen.py:53`
  - `frontend/ui/accounting/financial_integrity_screen.py:39`
- **Fix:** Add `hideEvent`/`showEvent` handlers to pause/resume timers
- **Dependencies:** None

### P4-2: Remove Orphaned Screen Files
- **Severity:** LOW
- **Business Impact:** Dead code increases codebase size
- **Effort:** 15 minutes
- **Files to remove:**
  - `frontend/ui/system/control_center_screen.py`
  - `frontend/ui/system/workflow_intelligence_screen.py`
  - `frontend/ui/system/correlation_screen.py`
  - `frontend/ui/system/drift_intelligence_screen.py`
  - `frontend/ui/system/integrity_screen.py`
  - `frontend/ui/control_tower/system_health_screen.py`
  - `frontend/ui/control_tower/workflow_execution_screen.py`
  - `frontend/ui/control_tower/financial_control_tower_screen.py`
  - `frontend/ui/observability/observability_screen.py`
  - `frontend/ui/observability/replay_screen.py`
  - `frontend/ui/investigation/anomaly_investigation_screen.py`
- **Dependencies:** None

### P4-3: Remove POS Dead Signals
- **Severity:** LOW
- **Business Impact:** Unused signals in codebase
- **Effort:** 5 minutes
- **Affected Files:**
  - `frontend/ui/pos/pos_screen.py:63,64`
- **Fix:** Remove `sale_completed` and `sale_failed` signal definitions if not needed
- **Dependencies:** P3-1 (implement or remove POS features first)

---

## Execution Plan

### Phase 1: Immediate Fixes (P1) — ~2 hours
1. P1-1: Fix AlertDialog args (5 files, 19 calls)
2. P1-2: Fix malformed URLs (2 files)
3. P1-3: Fix API response handling (3 files, ~10 call sites)
4. P1-4: Fix non-existent endpoints (2 files + possible backend)

### Phase 2: Pre-Release Fixes (P2) — ~4 hours
1. P2-1: Fix f-string prefix (2 files, 2 chars)
2. P2-2: Wire payroll dead buttons (1 file, 3 handlers)
3. P2-3: Fix parent refresh (2 files, 2 lines)
4. P2-4: Fix ProductSelectionDialog (1 file)
5. P2-5: Fix ProductSelectionDialog args (1 file)

### Phase 3: Pre-Deployment Fixes (P3) — ~3 hours
1. P3-1: Implement POS Hold/Recall/Print (1 file)
2. P3-2: Wire payment workspace buttons (2 files)
3. P3-3: Fix LoadingDialog indentation (1 file)
4. P3-4: Fix double status bar (1 file)

### Phase 4: Tech Debt (P4) — ~2 hours
1. P4-1: Timer lifecycle management (4 files)
2. P4-2: Remove orphaned files (11 files)
3. P4-3: Remove dead signals (1 file)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fixing P1-1 breaks other AlertDialog callers | LOW | HIGH | Grep for all AlertDialog calls before fixing |
| P1-4 requires backend changes | MEDIUM | MEDIUM | Check if endpoints exist under different paths |
| P2-2 payroll buttons need new backend endpoints | MEDIUM | MEDIUM | Check `/api/payroll/generate/` and `/api/payroll/approve/` exist |
| P3-1 POS features need significant implementation | HIGH | LOW | Show "Coming Soon" dialog as interim fix |

---

## Total Estimated Effort

| Phase | Effort |
|-------|--------|
| P1 (System Breaking) | ~2 hours |
| P2 (Operational Blocking) | ~4 hours |
| P3 (Productivity Loss) | ~3 hours |
| P4 (Cosmetic) | ~2 hours |
| **Total** | **~11 hours** |
