# WORKFLOW & NAVIGATION AUDIT

## 1. Sidebar Structure

```
┌─ Dashboard ─────────────────────────────────┐
│  💊 Pharmacy ERP                            │
├──────────────────────────────────────────────┤
│  ▶ Dashboard                                 │
│                                              │
│  ▶ Inventory                                 │
│    Products (1)                             │
│    Categories (2)                           │
│    Warehouses (3)                           │
│    Batches (4)                              │
│                                              │
│  ▶ Sales                                     │
│    Sales Invoice (5)                        │
│    POS Terminal (10)                        │
│    Customers (7)                            │
│                                              │
│  ▶ Purchases                                 │
│    Purchase Invoice (6)                     │
│    Suppliers (8)                            │
│                                              │
│  ▶ Returns                                   │
│    Return Orders (9)                        │
│    Reconciliation (57)                      │
│                                              │
│  ▶ Accounting                                │
│    Chart of Accounts (10)                   │
│    Journal Entries (11)                     │
│    Account Ledger (12)                      │
│    Financial Integrity (58)                 │
│    Audit Log (59)                           │
│                                              │
│  ▶ Reports                                   │
│    Trial Balance (13)                       │
│    Profit & Loss (14)                       │
│    Balance Sheet (15)                       │
│    Cash Flow (48)                           │
│    AR Ageing (16)                           │
│    AP Ageing (17)                           │
│                                              │
│  ▶ Finance                                   │
│    Payments (18)                            │
│    Expenses (34)                            │
│    Budgeting (19)                           │
│    Tax (20)                                 │
│    Cost Centers (21)                        │
│    Cash Flow (22)                           │
│    Customer Payments (60)                   │
│    Supplier Payments (61)                   │
│    Allocation Explorer (62)                 │
│    Returns Explainability (63)              │
│    Journal Reversals (64)                   │
│    Operations Console (65)                  │
│                                              │
│  ▶ HR                                        │
│    Employees (23)                           │
│    Attendance (24)                          │
│    Leave (25)                               │
│    Payroll (26)                             │
│                                              │
│  ▶ HR Reports                                │
│    Employee Summary (49)                    │
│    Attendance Report (50)                   │
│    Leave Report (51)                        │
│    Overtime Report (52)                     │
│                                              │
│  ▶ Payroll Reports                           │
│    Payroll Summary (53)                     │
│    Payroll Trend (54)                       │
│    Dept Cost (55)                           │
│    Employee History (56)                    │
│                                              │
│  ▶ System                                    │
│    Intelligence Hub (32)                    │
│    Control Center (38)                      │
│    Observability Console (39)               │
│    Decision Support (47)                    │
│    Invoice Templates (33)                   │
│    Company Profile (34)                     │
│    Business Entities (35)                   │
│    Licensing (36)                           │
│    Fixed Assets (29)                        │
│    Backup & Restore (27)                    │
│    Audit Log (30)                           │
│    User Management (31)                     │
│    Role Management (48)                     │
│                                              │
│  Settings (28)                               │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │              Logout                   │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

## 2. Navigation Architecture

### 2.1 Navigation Systems
| System | Location | Status |
|--------|----------|--------|
| Sidebar → page_changed signal → MainWindow.change_page() | sidebar.py → main_window.py | ✅ Active |
| NavigationHeader (back/home/close) | main_window.py _update_nav_header | ✅ Active |
| Menubar (File/Edit/View/Operations/Reports/Tools/Help) | main_window.py create_menu_bar | ✅ Active |
| NavigationManager (QObject, forward/back stacks) | navigation/navigation_manager.py | 🗑️ Standalone (not wired) |
| Keyboard shortcuts (Alt+Left, Ctrl+Home, Escape) | main_window.py keyPressEvent | ✅ Active |
| Dashboard quick action buttons | dashboard.py _navigate_to | ✅ Active |
| Keyboard shortuts (Ctrl+1/2/3, Ctrl+N, Ctrl+Shift+S) | main_window.py create_menu_bar | ✅ Active |

### 2.2 Navigation History
- MainWindow maintains `navigation_history` stack (max 20 entries)
- Back navigation pops history and disables history recording
- `NavigationHeader` shows/hides based on current page (hidden on dashboard)
- Breadcrumbs built dynamically from page_map

### 2.3 Page-to-Module Mapping (for scope checks)
```python
page_to_module = {
    0: "dashboard",
    1: "inventory", 2: "inventory", 3: "inventory", 4: "inventory",
    5: "sales", 6: "purchases", 7: "sales", 8: "purchases",
    9: "returns",
    10: "accounting", 11: "accounting", 12: "accounting",
    58: "accounting", 59: "accounting",
    13: "reports", 14: "reports", 15: "reports", 16: "reports", 17: "reports",
    18: "finance", 19: "finance", 20: "finance", 21: "finance", 22: "finance",
    34: "finance",
    60: "finance", 61: "finance", 62: "finance", 63: "finance",
    64: "finance", 65: "finance",
    23: "hr", 24: "hr", 25: "hr", 26: "hr",
    49: "hr", 50: "hr", 51: "hr", 52: "hr",
    53: "hr", 54: "hr", 55: "hr", 56: "hr",
    27: "system", 28: "system", 29: "system", 30: "system",
    31: "system", 32: "system", 33: "system", 35: "system",
    36: "system", 37: "system", 38: "system", 39: "system",
    47: "system", 48: "system",
}
```

## 3. Workflow Continuity

### 3.1 Sales Workflow
```
Dashboard → New Sale → SalesInvoiceScreen
    ↓                              ↓
Customer selection            Line items entry
    ↓                              ↓
Payment collection           Dispatch/Post
    ↓                              ↓
Invoice printed           Journal entry auto-created
```
**Flow completeness:** ✅ Complete — all steps connected

### 3.2 Purchase Workflow
```
Dashboard → New Purchase → PurchaseInvoiceScreen
    ↓                              ↓
Supplier selection           Line items entry
    ↓                              ↓
Receive goods                Journal entry auto-created
    ↓                              ↓
Payment processing           Supplier balance updated
```
**Flow completeness:** ✅ Complete — all steps connected

### 3.3 Returns Workflow
```
ReturnsScreen → Create Return → ReturnOrderDialog
    ↓                              ↓
Invoice selection             Line items entry
    ↓                              ↓
Approve/Reject               Inventory reversal
    ↓                              ↓
Void (if approved)           Reconciliation
```
**Flow completeness:** ✅ Complete — approval, rejection, void, reconciliation

### 3.4 Accounting Workflow
```
Chart of Accounts → Journal Entry → Journal Entry Screen
    ↓                    ↓                 ↓
Account CRUD        Post entry      View/Reverse entry
    ↓                    ↓                 ↓
Trial Balance      Profit & Loss    Balance Sheet
    ↓                    ↓                 ↓
AR/AP Aging        Cash Flow        Financial Reports
```
**Flow completeness:** ✅ Complete — full double-entry cycle

### 3.5 Finance Workflow
```
Payments → Transactions → Customer Payments
    ↓          ↓                ↓
Expenses → Budgeting → Cost Centers
    ↓          ↓                ↓
Tax → Cash Flow → Financial Operations Console
```
**Flow completeness:** ⚠️ Partial — settlement workflow lacks UI

## 4. Issues Found

### 4.1 Duplicate Navigation
| Issue | Severity | Details |
|-------|----------|---------|
| "Cash Flow" in Reports AND Finance | HIGH | Sidebar has Cash Flow in Reports (idx 48) AND Finance (idx 22). Different indices, confusing users. |
| "Audit Log" in Accounting AND System | MEDIUM | Audit Log appears in both Accounting (idx 59) and System (idx 30). Different screens. |
| Index collision: idx 10 = POS AND ChartOfAccounts | CRITICAL | POS and ChartOfAccounts both registered at index 10. Last registration wins (ChartOfAccounts). |
| Index collision: idx 34 = Expenses AND CompanyProfile | CRITICAL | Expenses and CompanyProfile both at index 34. |
| Index collision: idx 48 = RoleManagement AND CashFlow | CRITICAL | RoleManagement and ReportBrowser(CashFlow) both at index 48. |
| OperationsDashboard at 38, 43, 45 | MEDIUM | Same screen registered 3 times at different indices |
| AnalyticsWorkspace at 40, 41, 42 | MEDIUM | Same screen registered 3 times at different indices |
| DecisionWorkspace at 46, 47 | MEDIUM | Same screen registered 2 times |

### 4.2 Navigation Gaps
| Issue | Severity | Details |
|-------|----------|---------|
| No notification center | LOW | Notifications endpoint exists but no UI screen |
| No stock movement history UI | LOW | Stock movement endpoint exists, no screen |
| No settlement management UI | LOW | Settlement endpoint exists, no screen |

### 4.3 Dead Navigation References
| Issue | Severity | Details |
|-------|----------|---------|
| Overflow indexes | MEDIUM | page_map references up to idx 57, but _lazy_screens registers up to idx 65 |
| Missing `navigate_to` mapping | MEDIUM | Many newer screens (60-65) not in _do_navigate page_map |

### 4.4 Sidebar Organization
| Issue | Severity | Details |
|-------|----------|---------|
| Finance group very large | LOW | 12 items vs recommended 8 max per group |
| System group very large | LOW | 13 items — should split into "Admin" and "Intelligence" |
| Default all groups collapsed | MEDIUM | All sidebar groups start collapsed, requiring 2 clicks to navigate |
