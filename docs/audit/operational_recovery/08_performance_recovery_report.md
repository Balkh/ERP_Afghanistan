# 08 — Performance Recovery Report

**Audit Date:** 2026-05-31
**Scope:** Backend and frontend performance characteristics
**Methodology:** Static analysis of database queries, timer intervals, rendering patterns, and resource usage

---

## Executive Summary

| Severity | Count |
|----------|-------|
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 8 |
| N/A (mitigated) | 2 |

---

## HIGH Severity

### H1. recalculate_all_balances() Full-Table Scan on Every Unpost
- **File:** `backend/accounting/services/journal_engine.py:278-396`
- **Issue:** Iterates ALL active accounts, queries ALL posted journal lines per account
- **Estimated impact:** 500-5000ms depending on data volume (O(accounts × journal_lines))
- **Trigger:** Called on every `unpost_entry()` operation
- **Recommendation:** Use `update_account_balances(entry)` (inverse logic) instead. Only use full recalc as on-demand admin tool.

### H2. update_account_balances() Redundant Per-Entry Re-Aggregation
- **File:** `backend/accounting/services/journal_engine.py:357-375`
- **Issue:** For each line in entry, queries ALL posted lines for that account to recalculate balance from scratch
- **Estimated impact:** 100-500ms per journal entry post (O(lines × posted_lines_per_account))
- **Recommendation:** Use incremental: `new_balance = current_balance + debit - credit` instead of re-aggregating all posted lines.

---

## MEDIUM Severity

### M1. BalanceSyncService Triple Aggregation
- **File:** `backend/core/balance_sync.py:52-71`
- **Issue:** Three separate aggregate queries per sync (invoices, payments, returns)
- **Estimated impact:** 50-200ms per sync, called on every invoice create/update/delete
- **Recommendation:** Acceptable for correctness. Consider caching with TTL or combining into single query with conditional aggregation.

### M2. EnterpriseTable._refresh_display() Blocks UI for Large Datasets
- **File:** `frontend/ui/components/tables.py:331-356`
- **Issue:** Synchronous row insertion in tight loop without chunking for datasets under 2000 rows
- **Estimated impact:** 100-5000ms freeze for >2000 rows (auto-chunks at 2000 via `set_data_chunked`)
- **Recommendation:** Auto-chunking mitigates this. `blockSignals(True)` already present. Acceptable.

### M3. ReportBrowser Uses QThread Without Lifecycle Management
- **File:** `frontend/ui/accounting/report_browser.py:180-195`
- **Issue:** `ReportWorker(QThread)` created without cleanup on screen close
- **Estimated impact:** Potential dangling thread if user navigates away during report fetch
- **Recommendation:** Store thread reference, call `thread.quit()` + `thread.wait()` on screen hide.

---

## LOW Severity

### L1. Status Bar Timer at 1-Second Interval
- **File:** `frontend/ui/main_window.py:113-116`
- **Issue:** `QTimer.start(1000)` updating clock display every second
- **Estimated impact:** ~1ms per tick, but unnecessary CPU wake-up 60×/min
- **Recommendation:** Change to 60000ms (1 minute) — display shows `HH:MM:SS` but seconds precision not needed in ERP.

### L2. Dashboard Refresh Timer Runs When Not Visible
- **File:** `frontend/ui/dashboard.py:31-33`
- **Issue:** `QTimer.start(120000)` — 2-minute refresh runs even when user is on another screen
- **Estimated impact:** One API call every 2 minutes regardless of user activity
- **Recommendation:** Stop timer when dashboard is not visible; restart on `showEvent`.

### L3. Control Center 15-Second Refresh Runs When Not Visible
- **File:** `frontend/ui/system/control_center_screen.py:341`
- **Issue:** `QTimer.start(15000)` — polls every 15 seconds even when hidden
- **Estimated impact:** Unnecessary API calls when screen not visible
- **Recommendation:** Pause timer on hide, resume on show.

### L4. System Health Screen 15-Second Refresh Runs When Not Visible
- **File:** `frontend/ui/control_tower/system_health_screen.py:53`
- **Issue:** Same as L3
- **Recommendation:** Pause on hide, resume on show.

### L5. Financial Integrity Screen 5-Minute Refresh Runs When Not Visible
- **File:** `frontend/ui/accounting/financial_integrity_screen.py:39`
- **Issue:** `QTimer.start(300000)` — 5-minute auto-refresh
- **Estimated impact:** Low frequency, but runs when screen is hidden
- **Recommendation:** Pause when not visible.

### L6. payroll_summary Endpoint Hard-Limits to 12 Records
- **File:** `backend/payroll/views.py:159`
- **Issue:** `PayrollCycle.objects.all()[:12]` — unbounded query sliced in Python
- **Recommendation:** Use DRF pagination or explicit `limit` parameter.

### L7. Loading Spinner Timer at 50ms Interval
- **File:** `frontend/ui/components/loading_spinner.py:22`
- **Issue:** `timer.start(50)` — animation timer at 20fps
- **Recommendation:** No change needed — standard animation pattern. Not a performance issue.

### L8. Multiple Screens Without Pagination Params
- **Files:** returns_explainability.py, financial_operations_console.py, customer_payment_workspace.py, supplier_payment_workspace.py, payment_allocation_explorer.py, journal_reversal_explorer.py
- **Issue:** API calls use `page_size=100` or `200` without server-side pagination
- **Recommendation:** Acceptable for bounded financial data. For unbounded lists, consider cursor-based pagination.

---

## Performance Hotspots Summary

| Location | Issue | Impact | Priority |
|----------|-------|--------|----------|
| `journal_engine.py:284` | Full recalc on unpost | 500-5000ms | HIGH |
| `journal_engine.py:357` | Redundant re-aggregation | 100-500ms | HIGH |
| `balance_sync.py:52` | Triple aggregation | 50-200ms | MEDIUM |
| `tables.py:331` | Blocking UI refresh | 100-5000ms | MEDIUM |
| `report_browser.py:180` | Dangling QThread | Variable | MEDIUM |
| `main_window.py:113` | 1s timer | 1ms/tick | LOW |
| `dashboard.py:31` | Timer runs when hidden | 1 API call/2min | LOW |
| `control_center_screen.py:341` | Timer runs when hidden | 1 API call/15s | LOW |
