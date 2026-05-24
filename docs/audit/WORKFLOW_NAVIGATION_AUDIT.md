# WORKFLOW & NAVIGATION AUDIT — Pharmacy ERP

## Navigation Architecture

**Primary system**: `Sidebar.page_changed → MainWindow.change_page → QStackedWidget`
**Secondary system**: `NavigationManager` (exists at `navigation/navigation_manager.py` but NEVER wired)

---

## CRITICAL: 13 Off-by-One Bugs in `navigate_to()` page_map

The `_do_navigate()` method at `main_window.py:1132-1184` maps page_ids to indices INCORRECTLY for accounting, reports, and finance pages. **Menu bar shortcuts and programmatic navigation navigate to the wrong screen.**

| page_id | Correct Index | page_map Index | Result (opens wrong screen) |
|---------|--------------|----------------|---------------------------|
| `chart_of_accounts` | 10 | **11** | JournalEntryScreen |
| `journal_entries` | 11 | **12** | AccountLedgerScreen |
| `account_ledger` | 12 | **13** | TrialBalance (ReportBrowser) |
| `trial_balance` | 13 | **14** | Profit & Loss (ReportBrowser) |
| `profit_loss` | 14 | **15** | Balance Sheet (ReportBrowser) |
| `balance_sheet` | 15 | **16** | AR Ageing (ReportBrowser) |
| `ar_ageing` | 16 | **17** | AP Ageing (ReportBrowser) |
| `ap_ageing` | 17 | **18** | PaymentScreen |
| `payments` | 18 | **19** | BudgetingScreen |
| `budgeting` | 19 | **20** | TaxScreen |
| `tax` | 20 | **21** | CostCentersScreen |
| `cost_centers` | 21 | **22** | CashflowScreen |
| `cashflow` | 22 | **22** | CORRECT (collides with cost_centers) |

**Impact**: Menu bar shortcuts (Ctrl+1/2/3), Reports menu, Operations menu — ALL broken for accounting/reports/finance.

---

## Sidebar Active Item Not Updated on Navigation

`self.sidebar.set_active_item(index)` is called ONCE at initialization (line 539) but **NOT called during `change_page()`**. The sidebar highlight does not follow:
- Menu bar navigation
- Keyboard shortcuts (Ctrl+1, etc.)
- Dashboard KPI card clicks
- NavigationHeader back/home/close

---

## Sidebar `group_items_map` Outdated

`sidebar.py:83-96` is used for role filtering but MISSING items:

| Group | Missing page_ids |
|-------|-----------------|
| `returns` | `"reconciliation"` |
| `finance` | `"customer_payments"`, `"supplier_payments"`, `"allocation_explorer"`, `"returns_explainability"`, `"journal_reversals"`, `"operations_console"` |
| `system` | `"intelligence_hub"`, `"control_center"` |

Plus dead entry: `"cash_flow"` key maps to `{"cash_flow"}` but no `_create_group()` call for this key.

---

## Missing Page-to-Module Auth Check Entries

In `change_page()` at `main_window.py:548-564`:

| Index | Screen | Missing from page_to_module | Impact |
|-------|--------|---------------------------|--------|
| 40 | AnalyticsWorkspace | ✅ BUT no sidebar entry | Phantom — not navigable |
| 57 | ReconciliationScreen | **Missing** | Falls back to `"dashboard"` scope |

Index 57 (Reconciliation) is in the sidebar but has NO auth scope check. It relies on `"dashboard"` being accessible.

---

## MainWindow `_apply_sidebar_scopes()` Outdated

`main_window.py:207-219` — missing the `"returns"` group entirely, and misses the same new finance modules as sidebar.

---

## Breadcrumb Gaps

`_build_breadcrumb()` at `main_window.py:640` has its own `page_map` that covers indices 0-39 and 57, 66 only. Missing:
- Index 40: AnalyticsWorkspace
- Index 47: DecisionWorkspace
- Index 48: RoleManagementScreen
- Indices 49-56: HR/Payroll reports
- Index 57: Reconciliation (gap)
- Index 58-59: Financial Integrity, Audit Log
- Indices 60-65: Finance operations screens

These screens show flat breadcrumbs `["Home", page_title]` — no hierarchical path.

---

## Index 40 (AnalyticsWorkspace) — Phantom Screen

- Registered in `main_window.py` at index 40
- **NOT present in sidebar** — no navigation path
- No `page_to_module` auth entry (falls to "dashboard")
- No breadcrumb mapping
- **Only accessible programmatically**

---

## Keyboard Shortcuts

| Shortcut | Action | Status |
|----------|--------|--------|
| `Alt+Left` | Go back | ✅ |
| `Ctrl+Home` | Home | ✅ |
| `Escape` | Close screen | ✅ |
| `F11` | Fullscreen | ✅ |
| `Ctrl+1` | Dashboard | ✅ (but broken for accounting) |
| `Ctrl+2` | Products | ✅ |
| `Ctrl+3` | Customers | ✅ |
| `Ctrl+N` | New Product | ✅ (menu bar) |
| `Ctrl+Shift+S` | New Sales Invoice | ✅ (menu bar) |

---

## Index Gaps

| Range | Status | Purpose Available |
|-------|--------|-------------------|
| 41-46 | Unused | ✅ 6 slots |
| 67+ | Unused | ✅ Unlimited |

---

## Workflow Completeness

| Workflow | Steps in Sidebar | Status |
|----------|-----------------|--------|
| **Sales cycle**: Create invoice → Dispatch → Record payment → View report | Sales Invoice (5), Customers (7), Reports (13-17) | ✅ Complete |
| **Purchase cycle**: Create PO → Receive → Record payment → View report | Purchase Invoice (6), Suppliers (8), Reports (13-17) | ✅ Complete |
| **Returns cycle**: Create return → Approve → Reconcile → Void | Return Orders (9), Reconciliation (57) | ✅ Complete |
| **Accounting cycle**: Chart → Journal → Ledger → Reports | Chart (10), Journal (11), Ledger (12), Reports (13-17) | ✅ Complete |
| **Finance**: Payments → Expenses → Budget → Tax → Cash Flow | Finance group (18-22, 34, 60-65) | ✅ Complete |
| **HR**: Employee → Attendance → Leave → Payroll | HR group (23-26) | ✅ Complete |
| **Background Jobs**: Monitor jobs → Retry failed → View history | ❌ No sidebar entry | ❌ Missing |
| **Insurance**: Providers → Policies → Claims | ❌ No sidebar entry | ❌ Missing |
| **Period Close**: Review → Close → Lock | ❌ No workflow UI | ❌ Missing |
| **Credit Approval**: View pending → Approve/Reject | ❌ No workflow UI | ❌ Missing |

---

## Excessive Clicks Analysis

| Action | Clicks Required |
|--------|----------------|
| Navigate to Products | 2 (click Inventory group, click Products) |
| Navigate to Reconciliation | 2 (click Returns group, click Reconciliation) |
| Navigate to Supplier Payments | 3 (click Finance group, scroll, click Supplier Payments) |
| Navigate to User Management | 2 (click System group, click User Management) |
| Navigate to Backup | 2 (click System group, scroll, click Backup & Restore) |

Finance group has **12 items** — requires more scrolling and visual scanning. Could benefit from sub-grouping.

---

## Navigation Recommendations

1. **Fix 13 off-by-one bugs** in `_do_navigate()` page_map — highest priority
2. **Add `set_active_item()` call** to `change_page()` — side effect: broken sidebar highlight
3. **Update `group_items_map`** in sidebar — add missing 10 page_ids, remove dead `cash_flow` entry
4. **Add reconciliation (57)** to `page_to_module` auth check
5. **Update `_apply_sidebar_scopes()`** — add `"returns"` group and new finance modules
6. **Consolidate breadcrumb and navigation page_maps** into single source of truth
7. **Add missing breadcrumb mappings** for indices 47-65
8. **Either register or remove** phantom screen at index 40
