# Frontend Reachability Audit

**Date:** 2026-06-03
**Mission:** Read-only reachability analysis. Trace every UI surface from `MainWindow` down to screens, dialogs, and actions. No code modifications, no commits, no refactoring.
**Scope:** All QWidget / QDialog / QMainWindow subclasses in `frontend/ui/`.
**Excluded from analysis:** `venv/`, `__pycache__/`, `enterprise_certification/`, `frontend/tests/`.

---

## Executive Summary

| Metric | Value |
|---|---:|
| UI Python files inventoried | 145 |
| QWidget / QDialog / QMainWindow subclasses | **168** |
| Screens registered in `screen_registry.py` (lazy loaders) | **44** (indices 1-67, sparse) |
| Sidebar navigation groups | 12 collapsible + Dashboard + Settings |
| Menu actions in `main_window.create_menu_bar()` | 17 |
| Dashboard shortcut links (KPI cards) | 4 (dashboard.py:475) |
| Dialogs launched from screens (`dialog.exec()`) | 35+ |
| **REACHABLE** screens | **41** |
| **CONDITIONALLY_REACHABLE** (role-gated) | **3** |
| **UNREACHABLE** screens / dialogs / widgets | **19** |

**Entry path:** `frontend/main.py` → [`LoginDialog`] → [`MainWindow`] → `QStackedWidget` ↔ `Sidebar` (12 groups + dashboard) + `MenuBar` (File/Edit/View/Operations/Reports/Tools/Help) + `Dashboard` (index 0) + 44 lazy-loaded screens.

**Critical finding:** `AnalyticsWorkspace` (index 40 in `screen_registry.py`) is **registered but broken** — `analytics_workspace.py:14` imports a non-existent `ui.investigation.anomaly_investigation_screen`, which will crash the `main_window` import. This blocks the entire "Analytics" sidebar entry.

---

## 1. Entry Point & Navigation Architecture

### 1.1 Application Entry Point

```
frontend/main.py
    │
    ├── generate_device_id()               # device fingerprint
    ├── license_validator = LicenseValidator(...)
    │   └── if invalid → license_dialog (alert)
    ├── LoginDialog(api_client, auth_manager)   # modal login
    │   └── if accepted → credentials acquired
    │   └── if rejected → sys.exit
    │
    └── MainWindow(license_validator, user_data, api_client, auth_manager)
            ├── self.dashboard = Dashboard(role, api_client)   # QStackedWidget[0]
            ├── self._lazy_screens = LazyScreenManager(self.pages, self.api_client)
            │   └── screen_registry.register_all_screens()     # registers 44 screens
            ├── self.sidebar = Sidebar(role=self.user_role)
            │   └── 12 collapsible groups + Dashboard + Settings
            └── self.create_menu_bar()      # 17 menu actions
```

### 1.2 Navigation Sources (5 categories)

| # | Source | Mechanism | Discoverable by users? |
|---:|---|---|---|
| 1 | **`main_window.create_menu_bar()`** | File/Edit/View/Operations/Reports/Tools/Help menus | Yes — keyboard shortcuts |
| 2 | **`sidebar.py` (12 groups + 2 standalone buttons)** | Click → `page_changed.emit(index, title)` → `change_page()` | Yes — primary navigation |
| 3 | **`dashboard.py:_navigate_to()` (line 470-479)** | KPI cards call `change_page(1, "Products")` / `change_page(5, "Sales Invoice")` / `change_page(6, "Purchase Invoice")` / `change_page(13, "Trial Balance")` | Yes — dashboard shortcuts |
| 4 | **In-screen action buttons** | Each screen has its own buttons that call `change_page()` or launch dialogs | Yes — context-dependent |
| 5 | **LazyScreenManager** | `screen_registry.py` provides 44 builders; first navigation imports the module | Yes — on first click |

### 1.3 Role-Based Visibility Filter

`sidebar.py:apply_role_filter()` consults `role_manager.ROLE_PERMISSIONS` (9 roles: ADMIN, MANAGER, ACCOUNTANT, WAREHOUSE, HR, PHARMACIST, SUPERVISOR, CASHIER, GENERAL). Each role has an explicit set of `page_id`s it can see. If a user has role X and screen S is not in X's set, the button is hidden (but the screen is still in the QStackedWidget and reachable by direct `change_page()` call from a menu action).

This makes some screens **CONDITIONALLY_REACHABLE** depending on the logged-in user's role.

---

## 2. Navigation Map (Reachability by Index)

### 2.1 Registered Screens in `screen_registry.py` (Lazy Loader Targets)

| Index | Class | Module | Sidebar Group | Reachable via | Role gated? |
|---:|---|---|---|---|---|
| **0** | `Dashboard` | `ui.dashboard` | (always visible) | Sidebar (Dashboard button) + View→Go to Dashboard (Ctrl+1) | NO |
| **1** | `ProductScreen` | `ui.inventory.product_screen` | Inventory → Products | Sidebar + View→Go to Products (Ctrl+2) | NO |
| **2** | `CategoryScreen` | `ui.inventory.category_screen` | Inventory → Categories | Sidebar | NO |
| **3** | `WarehouseScreen` | `ui.inventory.warehouse_screen` | Inventory → Warehouses | Sidebar | NO |
| **4** | `BatchScreen` | `ui.inventory.batch_screen` | Inventory → Batches | Sidebar | NO |
| **5** | `SalesInvoiceScreen` | `ui.sales.sales_invoice_screen` | Sales → Sales Invoice | Sidebar + Operations→New Sales Invoice (Ctrl+Shift+S) | NO |
| **6** | `PurchaseInvoiceScreen` | `ui.purchases.purchase_invoice_screen` | Purchases → Purchase Invoice | Sidebar | NO |
| **7** | `CustomerScreen` | `ui.sales.customer_screen` | Sales → Customers | Sidebar + View→Go to Customers (Ctrl+3) | NO |
| **8** | `SupplierScreen` | `ui.purchases.supplier_screen` | Purchases → Suppliers | Sidebar | NO |
| **9** | `ReturnsScreen` | `ui.returns.returns_screen` | Returns → Return Orders | Sidebar | NO |
| **10** | `ChartOfAccountsScreen` | `ui.accounting.chart_of_accounts_screen` | Accounting → Chart of Accounts | Sidebar | NO |
| **11** | `JournalEntryScreen` | `ui.accounting.journal_entry_screen` | Accounting → Journal Entries | Sidebar | NO |
| **12** | `AccountLedgerScreen` | `ui.accounting.account_ledger_screen` | Accounting → Account Ledger | Sidebar | NO |
| **13** | `ReportBrowser("trial_balance")` | `ui.accounting.report_browser` | Reports → Trial Balance | Sidebar + Reports→Trial Balance menu | NO |
| **14** | `ReportBrowser("profit_loss")` | `ui.accounting.report_browser` | Reports → Profit & Loss | Sidebar + Reports→P&L menu | NO |
| **15** | `ReportBrowser("balance_sheet")` | `ui.accounting.report_browser` | Reports → Balance Sheet | Sidebar + Reports→Balance Sheet menu | NO |
| **16** | `ReportBrowser("ar_aging")` | `ui.accounting.report_browser` | Reports → AR Ageing | Sidebar + Reports→AR Ageing menu | NO |
| **17** | `ReportBrowser("ap_aging")` | `ui.accounting.report_browser` | Reports → AP Ageing | Sidebar + Reports→AP Ageing menu | NO |
| **18** | `PaymentScreen` | `ui.finance.payment_screen` | Finance → Payments | Sidebar | NO |
| **19** | `BudgetingScreen` | `ui.finance.budgeting_screen` | Finance → Budgeting | Sidebar | NO |
| **20** | `TaxScreen` | `ui.finance.tax_screen` | Finance → Tax | Sidebar | NO |
| **21** | `CostCentersScreen` | `ui.finance.cost_centers_screen` | Finance → Cost Centers | Sidebar | NO |
| **22** | `CashflowScreen` | `ui.finance.cashflow_screen` | Finance → Cash Flow | Sidebar | NO |
| **23** | `EmployeeScreen` | `ui.hr.employee_screen` | HR → Employees | Sidebar | NO |
| **24** | `AttendanceScreen` | `ui.hr.attendance_screen` | HR → Attendance | Sidebar | NO |
| **25** | `LeaveScreen` | `ui.hr.leave_screen` | HR → Leave | Sidebar | NO |
| **26** | `PayrollScreen` | `ui.hr.payroll_screen` | HR → Payroll | Sidebar | NO |
| **27** | `BackupControlScreen` | `ui.system.backup_screen` | System → Backup & Restore | Sidebar + Tools→Backup Database | NO |
| **28** | `SettingsScreen` | `ui.system.settings_screen` | (standalone, sidebar bottom) | Sidebar (Settings button) | NO |
| **29** | `FixedAssetsScreen` | `ui.system.fixed_assets_screen` | System → Fixed Assets | Sidebar | NO |
| **30** | `AuditScreen` | `ui.system.audit_screen` | System → Audit Log | Sidebar | NO |
| **31** | `UserManagementScreen` | `ui.system.user_management_screen` | System → User Management | Sidebar | NO |
| **32** | `IntelligenceHubScreen` | `ui.system.intelligence_hub_screen` | System → Intelligence Hub | Sidebar | NO |
| **33** | `InvoiceTemplateManager` | `ui.system.invoice_template_manager` | System → Invoice Templates | Sidebar | NO |
| **34** | `ExpenseScreen` | `ui.finance.expense_screen` | Finance → Expenses | Sidebar | NO |
| **35** | `EntityManagementScreen` | `ui.system.entity_management_screen` | System → Business Entities | Sidebar | NO |
| **36** | `LicensingScreen` | `ui.system.licensing_screen` | System → Licensing | Sidebar | NO |
| **37** | `POSScreen` | `ui.pos.pos_screen` | Sales → POS Terminal | Sidebar | CONDITIONALLY_REACHABLE (PHARMACIST/CASHIER) |
| **38** | `OperationsDashboard` | `ui.control_tower.operations_dashboard` | System → Control Center | Sidebar | NO |
| **39** | `ObservabilityConsole` | `ui.observability.observability_console` | System → Observability Console | Sidebar | NO |
| **40** | `AnalyticsWorkspace` ⚠️ | `ui.system.analytics_workspace` | System → Analytics | Sidebar (broken import) | UNREACHABLE (broken) |
| **47** | `DecisionWorkspace` | `ui.causal_scoring.decision_workspace` | System → Decision Support | Sidebar | NO |
| **48** | `RoleManagementScreen` | `ui.system.role_management_screen` | System → Role Management | Sidebar | NO |
| **49** | `ReportBrowser("employee_summary")` | `ui.accounting.report_browser` | HR Reports → Employee Summary | Sidebar | NO |
| **50** | `ReportBrowser("attendance_report")` | `ui.accounting.report_browser` | HR Reports → Attendance Report | Sidebar | NO |
| **51** | `ReportBrowser("leave_report")` | `ui.accounting.report_browser` | HR Reports → Leave Report | Sidebar | NO |
| **52** | `ReportBrowser("overtime_report")` | `ui.accounting.report_browser` | HR Reports → Overtime Report | Sidebar | NO |
| **53** | `ReportBrowser("payroll_summary")` | `ui.accounting.report_browser` | Payroll Reports → Payroll Summary | Sidebar | NO |
| **54** | `ReportBrowser("payroll_trend")` | `ui.accounting.report_browser` | Payroll Reports → Payroll Trend | Sidebar | NO |
| **55** | `ReportBrowser("payroll_dept_cost")` | `ui.accounting.report_browser` | Payroll Reports → Dept Cost | Sidebar | NO |
| **56** | `ReportBrowser("payroll_emp_history")` | `ui.accounting.report_browser` | Payroll Reports → Employee History | Sidebar | NO |
| **57** | `ReconciliationScreen` | `ui.returns.reconciliation_screen` | Returns → Reconciliation | Sidebar | NO |
| **58** | `FinancialIntegrityScreen` | `ui.accounting.financial_integrity_screen` | Accounting → Financial Integrity | Sidebar | NO |
| **59** | `FinancialAuditLogScreen` | `ui.accounting.financial_audit_log_screen` | Accounting → Financial Audit Log | Sidebar | NO |
| **60** | `CustomerPaymentWorkspace` | `ui.finance.customer_payment_workspace` | Finance → Customer Payments | Sidebar | NO |
| **61** | `SupplierPaymentWorkspace` | `ui.finance.supplier_payment_workspace` | Finance → Supplier Payments | Sidebar | NO |
| **62** | `PaymentAllocationExplorer` | `ui.finance.payment_allocation_explorer` | Finance → Allocation Explorer | Sidebar | NO |
| **63** | `ReturnsExplainabilityScreen` | `ui.finance.returns_explainability` | Finance → Returns Explainability | Sidebar | NO |
| **64** | `JournalReversalExplorer` | `ui.finance.journal_reversal_explorer` | Finance → Journal Reversals | Sidebar | NO |
| **65** | `FinancialOperationsConsole` | `ui.finance.financial_operations_console` | Finance → Operations Console | Sidebar | NO |
| **66** | `CompanyProfileScreen` | `ui.system.company_profile_screen` | System → Company Profile | Sidebar | NO |
| **67** | `DepartmentsScreen` | `ui.hr.departments_screen` | HR → Departments & Positions | Sidebar | NO |

**Total registered screens: 44 unique classes** (ReportBrowser is reused 11 times with different `report_type` arguments).

### 2.2 Menu Actions in `main_window.create_menu_bar()`

| Menu | Action | Trigger | Destination |
|---|---|---|---|
| File | Refresh | QAction → `refresh_current_view()` | (refresh current view, no nav) |
| File | Logout | QAction → `logout()` | (logout flow → LoginDialog) |
| Edit | Preferences | QAction → `show_preferences()` | (placeholder AlertDialog) |
| View | Fullscreen | QAction → `fullscreen_action` | (toggle fullscreen) |
| View | Go to Dashboard (Ctrl+1) | QAction → `navigate_to("dashboard")` | index 0 |
| View | Go to Products (Ctrl+2) | QAction → `navigate_to("products")` | index 1 |
| View | Go to Customers (Ctrl+3) | QAction → `navigate_to("customers")` | index 7 |
| Operations | New Product (Ctrl+N) | QAction → `new_product()` | (placeholder AlertDialog) |
| Operations | New Sales Invoice (Ctrl+Shift+S) | QAction → `navigate_to("sales_invoice")` | index 5 |
| Operations | Stock Alert Report | QAction → `show_stock_alerts()` | (placeholder AlertDialog) |
| Reports | Trial Balance | QAction → `navigate_to("trial_balance")` | index 13 |
| Reports | Profit & Loss | QAction → `navigate_to("profit_loss")` | index 14 |
| Reports | Balance Sheet | QAction → `navigate_to("balance_sheet")` | index 15 |
| Reports | AR Ageing Report | QAction → `navigate_to("ar_ageing")` | index 16 |
| Reports | AP Ageing Report | QAction → `navigate_to("ap_aging")` | index 17 |
| Tools | Calculator | QAction → `open_calculator()` | (system calc.exe) |
| Tools | Calendar | QAction → `open_calendar()` | (system calendar) |
| Tools | Backup Database | QAction → `navigate_to("backup")` | index 27 |
| Help | License Manager | QAction → `show_license_manager()` | LicenseManagerDialog (modal) |
| Help | About | QAction → `show_about()` | (placeholder AlertDialog) |

**17 menu actions; 4 are non-navigating stubs** (Refresh, Preferences, New Product, Stock Alerts, About, Calculator, Calendar — many are placeholders).

### 2.3 Dialogs Launched from Screens (in-screen `.exec()` calls)

| Parent Screen | Dialog | File | Purpose |
|---|---|---|---|
| `customer_screen.py:185,198` | `CustomerDialog` | `sales/customer_screen.py:225` | Add/Edit customer |
| `returns_screen.py:365` | `ReturnOrderDialog` | `returns/returns_screen.py:577` | Create return order |
| `pos_screen.py:532,793,810` | (multiple POS dialogs) | `pos/pos_screen.py` | POS payment flow |
| `employee_screen.py:185,204` | `EmployeeDialog` | `hr/employee_screen.py:238` | Add/Edit employee |
| `expense_screen.py:170` | `AddExpenseDialog` | `finance/expense_screen.py:173` | Add expense |
| `cost_centers_screen.py:193` | `CostCenterDialog` | `finance/cost_centers_screen.py:199` | Add/Edit cost center |
| `chart_of_accounts_screen.py:275,288` | `AccountFormDialog` | `accounting/components/account_form_dialog.py:19` | Add/Edit account |
| `journal_entry_screen.py:372,439` | `JournalEntryFormDialog` | `accounting/components/journal_entry_form.py:24` | Add/Edit journal entry; also `JournalEntryDetailDialog` |
| `account_ledger_screen.py:304` | `JournalEntryDetailDialog` | `accounting/components/journal_entry_detail.py:35` | View journal entry |
| `purchase_invoice_screen.py:790,803` | (purchase flow) | `purchases/purchase_invoice_screen.py` | Add line items / save |
| `sales_invoice_screen.py:516,584,781,794` | (sales flow) | `sales/sales_invoice_screen.py` | Add line items / payment |
| `payslip_dialog.py:201,209` | (print dialog) | `hr/payslip_dialog.py:201` | Print payslip |
| `printable_invoice.py:313,320` | (print dialog) | `common/printable_invoice.py:313` | Print invoice |
| `fixed_assets_screen.py:273` | `AssetDialog` | `system/fixed_assets_screen.py:282` | Add/Edit asset |
| `license_manager_dialog.py:131` | (license dialog chain) | `licensing/license_manager_dialog.py` | License activation flow |
| `license_status_screen.py:277` | (license details) | `licensing/license_status_screen.py:285` | LicenseDetailsDialog |
| `backup_screen.py:678,790` | `RestoreConfirmDialog` | `system/backup_screen.py:132` | Confirm restore |
| `departments_screen.py:136,141` | `DepartmentDialog`, `PositionDialog` | `hr/departments_screen.py:145,210` | Add/Edit dept/position |
| `role_management_screen.py:239,246` | `RoleDialog` | `system/role_management_screen.py:303` | Add/Edit role |
| `user_management_screen.py:208,220` | `UserDialog` | `system/user_management_screen.py:244` | Add/Edit user |
| `supplier_screen.py:189,202` | `SupplierDialog` | `purchases/supplier_screen.py:229` | Add/Edit supplier |
| `product_screen.py:160` | `ProductFormDialog` | `inventory/components/product_form.py:15` | Add/Edit product |
| `entity_management_screen.py:104,112` | `EntityDialog` | `system/entity_management_screen.py:133` | Add/Edit entity |
| `payroll_screen.py:376,380` | `SalaryStructureDialog` | `hr/payroll_screen.py:426` | Add/Edit salary structure |
| `category_screen.py:141` | `CategoryFormDialog` | `inventory/components/category_form_dialog.py:15` | Add/Edit category |
| `batch_screen.py:155` | `BatchFormDialog` | `inventory/components/batch_form_dialog.py:14` | Add/Edit batch |
| `warehouse_screen.py:143` | `WarehouseFormDialog` | `inventory/components/warehouse_form_dialog.py:14` | Add/Edit warehouse |
| `report_preview_dialog.py:91` | (print/export) | `accounting/components/report_preview_dialog.py:13` | Export report |

**Total in-screen dialog launches: 35+.** All reachable via their parent screen.

### 2.4 Modal Dialogs Launched from `main_window` Itself

| Trigger | Dialog | File | Purpose |
|---|---|---|---|
| Help → License Manager (or invalid license at startup) | `LicenseManagerDialog` | `licensing/license_manager_dialog.py:21` | Manage license (contains `ActivationScreen` and `LicenseStatusScreen` as embedded pages) |
| Login (always) | `LoginDialog` | `auth/login_screen.py:23` | Authentication |
| (startup, if license invalid) | `ActivationScreen` | `licensing/activation_screen.py:28` | First-time license activation |

---

## 3. Per-Screen Reachability Classification

### 3.1 REACHABLE (44 registered screens + 1 Dashboard + LoginDialog + LicenseManagerDialog)

All screens in `screen_registry.py` (indices 0-67, sparse) plus the login flow and the modal license manager are **REACHABLE**. They have at least one entry point: sidebar, menu, or KPI card.

| # | Screen / Dialog | Class | Entry path | Navigation source | References | Verdict |
|---:|---|---|---|---|---:|---|
| 1 | Dashboard | `ui.dashboard.Dashboard` | index 0 | Sidebar (always) + View→Go to Dashboard (Ctrl+1) | (always mounted) | **KEEP** |
| 2 | LoginDialog | `ui.auth.login_screen.LoginDialog` | (modal, pre-MainWindow) | main.py | (pre-MainWindow) | **KEEP** |
| 3 | LicenseManagerDialog | `ui.licensing.license_manager_dialog.LicenseManagerDialog` | Help→License Manager | main_window.show_license_manager | 1 | **KEEP** |
| 4 | ProductScreen | `ui.inventory.product_screen.ProductScreen` | index 1 | Sidebar + View→Go to Products (Ctrl+2) + Dashboard KPI | 3 | **KEEP** |
| 5 | CategoryScreen | `ui.inventory.category_screen.CategoryScreen` | index 2 | Sidebar | 1 | **KEEP** |
| 6 | WarehouseScreen | `ui.inventory.warehouse_screen.WarehouseScreen` | index 3 | Sidebar | 1 | **KEEP** |
| 7 | BatchScreen | `ui.inventory.batch_screen.BatchScreen` | index 4 | Sidebar | 1 | **KEEP** |
| 8 | SalesInvoiceScreen | `ui.sales.sales_invoice_screen.SalesInvoiceScreen` | index 5 | Sidebar + Operations→New Sales Invoice (Ctrl+Shift+S) | 2 | **KEEP** |
| 9 | PurchaseInvoiceScreen | `ui.purchases.purchase_invoice_screen.PurchaseInvoiceScreen` | index 6 | Sidebar | 1 | **KEEP** |
| 10 | CustomerScreen | `ui.sales.customer_screen.CustomerScreen` | index 7 | Sidebar + View→Go to Customers (Ctrl+3) | 2 | **KEEP** |
| 11 | SupplierScreen | `ui.purchases.supplier_screen.SupplierScreen` | index 8 | Sidebar | 1 | **KEEP** |
| 12 | ReturnsScreen | `ui.returns.returns_screen.ReturnsScreen` | index 9 | Sidebar | 1 | **KEEP** |
| 13 | ChartOfAccountsScreen | `ui.accounting.chart_of_accounts_screen.ChartOfAccountsScreen` | index 10 | Sidebar | 1 | **KEEP** |
| 14 | JournalEntryScreen | `ui.accounting.journal_entry_screen.JournalEntryScreen` | index 11 | Sidebar | 1 | **KEEP** |
| 15 | AccountLedgerScreen | `ui.accounting.account_ledger_screen.AccountLedgerScreen` | index 12 | Sidebar | 1 | **KEEP** |
| 16 | ReportBrowser (×11) | `ui.accounting.report_browser.ReportBrowser` | indices 13-17, 49-56 | Sidebar + Reports menu | 12+ | **KEEP** |
| 17 | PaymentScreen | `ui.finance.payment_screen.PaymentScreen` | index 18 | Sidebar | 1 | **KEEP** |
| 18 | BudgetingScreen | `ui.finance.budgeting_screen.BudgetingScreen` | index 19 | Sidebar | 1 | **KEEP** |
| 19 | TaxScreen | `ui.finance.tax_screen.TaxScreen` | index 20 | Sidebar | 1 | **KEEP** |
| 20 | CostCentersScreen | `ui.finance.cost_centers_screen.CostCentersScreen` | index 21 | Sidebar | 1 | **KEEP** |
| 21 | CashflowScreen | `ui.finance.cashflow_screen.CashflowScreen` | index 22 | Sidebar | 1 | **KEEP** |
| 22 | EmployeeScreen | `ui.hr.employee_screen.EmployeeScreen` | index 23 | Sidebar | 1 | **KEEP** |
| 23 | AttendanceScreen | `ui.hr.attendance_screen.AttendanceScreen` | index 24 | Sidebar | 1 | **KEEP** |
| 24 | LeaveScreen | `ui.hr.leave_screen.LeaveScreen` | index 25 | Sidebar | 1 | **KEEP** |
| 25 | PayrollScreen | `ui.hr.payroll_screen.PayrollScreen` | index 26 | Sidebar | 1 | **KEEP** |
| 26 | BackupControlScreen | `ui.system.backup_screen.BackupControlScreen` | index 27 | Sidebar + Tools→Backup Database | 2 | **KEEP** |
| 27 | SettingsScreen | `ui.system.settings_screen.SettingsScreen` | index 28 | Sidebar (Settings button, bottom) | 1 | **KEEP** |
| 28 | FixedAssetsScreen | `ui.system.fixed_assets_screen.FixedAssetsScreen` | index 29 | Sidebar | 1 | **KEEP** |
| 29 | AuditScreen | `ui.system.audit_screen.AuditScreen` | index 30 | Sidebar | 1 | **KEEP** |
| 30 | UserManagementScreen | `ui.system.user_management_screen.UserManagementScreen` | index 31 | Sidebar | 1 | **KEEP** |
| 31 | IntelligenceHubScreen | `ui.system.intelligence_hub_screen.IntelligenceHubScreen` | index 32 | Sidebar | 1 | **KEEP** |
| 32 | InvoiceTemplateManager | `ui.system.invoice_template_manager.InvoiceTemplateManager` | index 33 | Sidebar | 1 | **KEEP** |
| 33 | ExpenseScreen | `ui.finance.expense_screen.ExpenseScreen` | index 34 | Sidebar | 1 | **KEEP** |
| 34 | EntityManagementScreen | `ui.system.entity_management_screen.EntityManagementScreen` | index 35 | Sidebar | 1 | **KEEP** |
| 35 | LicensingScreen | `ui.system.licensing_screen.LicensingScreen` | index 36 | Sidebar | 1 | **KEEP** |
| 36 | POSScreen | `ui.pos.pos_screen.POSScreen` | index 37 | Sidebar | 1 | **KEEP** (CONDITIONAL on role) |
| 37 | OperationsDashboard | `ui.control_tower.operations_dashboard.OperationsDashboard` | index 38 | Sidebar | 1 | **KEEP** |
| 38 | ObservabilityConsole | `ui.observability.observability_console.ObservabilityConsole` | index 39 | Sidebar | 1 | **KEEP** |
| 39 | DecisionWorkspace | `ui.causal_scoring.decision_workspace.DecisionWorkspace` | index 47 | Sidebar | 1 | **KEEP** |
| 40 | RoleManagementScreen | `ui.system.role_management_screen.RoleManagementScreen` | index 48 | Sidebar | 1 | **KEEP** |
| 41 | ReconciliationScreen | `ui.returns.reconciliation_screen.ReconciliationScreen` | index 57 | Sidebar | 1 | **KEEP** |
| 42 | FinancialIntegrityScreen | `ui.accounting.financial_integrity_screen.FinancialIntegrityScreen` | index 58 | Sidebar | 1 | **KEEP** |
| 43 | FinancialAuditLogScreen | `ui.accounting.financial_audit_log_screen.FinancialAuditLogScreen` | index 59 | Sidebar | 1 | **KEEP** |
| 44 | CustomerPaymentWorkspace | `ui.finance.customer_payment_workspace.CustomerPaymentWorkspace` | index 60 | Sidebar | 1 | **KEEP** |
| 45 | SupplierPaymentWorkspace | `ui.finance.supplier_payment_workspace.SupplierPaymentWorkspace` | index 61 | Sidebar | 1 | **KEEP** |
| 46 | PaymentAllocationExplorer | `ui.finance.payment_allocation_explorer.PaymentAllocationExplorer` | index 62 | Sidebar | 1 | **KEEP** |
| 47 | ReturnsExplainabilityScreen | `ui.finance.returns_explainability.ReturnsExplainabilityScreen` | index 63 | Sidebar | 1 | **KEEP** |
| 48 | JournalReversalExplorer | `ui.finance.journal_reversal_explorer.JournalReversalExplorer` | index 64 | Sidebar | 1 | **KEEP** |
| 49 | FinancialOperationsConsole | `ui.finance.financial_operations_console.FinancialOperationsConsole` | index 65 | Sidebar | 1 | **KEEP** |
| 50 | CompanyProfileScreen | `ui.system.company_profile_screen.CompanyProfileScreen` | index 66 | Sidebar | 1 | **KEEP** |
| 51 | DepartmentsScreen | `ui.hr.departments_screen.DepartmentsScreen` | index 67 | Sidebar | 1 | **KEEP** |

**41 unique screen classes + 1 Dashboard + LoginDialog + LicenseManagerDialog = 44 REACHABLE** (sub-total).

### 3.2 CONDITIONALLY_REACHABLE (3 screens)

These are reachable only for certain roles OR rely on edge conditions.

| # | Screen | Class | Condition | Reachable when | Verdict |
|---:|---|---|---|---|---|
| 1 | POSScreen | `ui.pos.pos_screen.POSScreen` | Role filter | Visible in sidebar only for PHARMACIST, CASHIER (or all roles, depending on `ROLE_PERMISSIONS`); but the screen itself is reachable via `change_page(37)` from any code path | **KEEP** (always in QStackedWidget) |
| 2 | ActivationScreen | `ui.licensing.activation_screen.ActivationScreen` | Embedded in `LicenseManagerDialog` | Only when user opens License Manager dialog (Help→License Manager) — never a top-level screen | **KEEP** |
| 3 | LicenseStatusScreen | `ui.licensing.license_status_screen.LicenseStatusScreen` | Embedded in `LicenseManagerDialog` | Same as ActivationScreen | **KEEP** |

### 3.3 UNREACHABLE (19 items)

These classes are defined but have **no entry point** — not in `screen_registry.py`, not in any sidebar group, not launched by any menu, dialog, or screen.

| # | Class | File | Reason | Verdict | Confidence |
|---:|---|---|---|---|---:|
| 1 | **`AnalyticsWorkspace`** ⚠️ | `frontend/ui/system/analytics_workspace.py:19` | **Registered at index 40 in screen_registry.py but BROKEN IMPORT**: line 14 `from ui.investigation.anomaly_investigation_screen import AnomalyInvestigationScreen` — that file does NOT exist. The whole `main_window` will crash when the Analytics button is clicked. | **ARCHIVE** (or fix the import) | 100 |
| 2 | `EventStoreScreen` | `frontend/ui/truth/event_store_screen.py:22` | Sole importer is `analytics_workspace.py:14` (which is broken). Not in `screen_registry.py`. Not in sidebar. Not launched anywhere. | **ARCHIVE** | 95 |
| 3 | `EventInvestigationScreen` | `frontend/ui/investigation/event_investigation_screen.py:24` | Same as EventStoreScreen — only imported by broken `analytics_workspace.py` | **ARCHIVE** | 95 |
| 4 | `CausalStrengthPanel` | `frontend/ui/causal_scoring/causal_strength_panel.py:27` | Internal widget, never launched standalone (not in registry, not in sidebar). May be used inside `DecisionRankingDashboard` — verify. | **NEEDS_REVIEW** | 70 |
| 5 | `DecisionIntelligenceDashboard` | `frontend/ui/causal_scoring/decision_ranking_dashboard.py:27` | Not in registry; not in sidebar. May be an old/alternate view for `DecisionWorkspace` (index 47). | **NEEDS_REVIEW** | 70 |
| 6 | `SystemCorrelationScreen` | `frontend/ui/system/correlation_screen.py:6` | Empty class definition (likely a stub). Not in registry. Not in sidebar. | **DELETE** | 90 |
| 7 | `DriftIntelligenceScreen` | `frontend/ui/system/drift_intelligence_screen.py:6` | Empty class definition (stub). Not in registry. | **DELETE** | 90 |
| 8 | `ControlCenterScreen` | `frontend/ui/system/control_center_screen.py:6` | Empty class definition (stub). Not in registry. (`OperationsDashboard` is the actual implementation at index 38.) | **DELETE** | 95 |
| 9 | `SystemIntegrityScreen` | `frontend/ui/system/integrity_screen.py:6` | Empty class definition (stub). Not in registry. | **DELETE** | 90 |
| 10 | `WorkflowIntelligenceScreen` | `frontend/ui/system/workflow_intelligence_screen.py:6` | Empty class definition (stub). Not in registry. | **DELETE** | 90 |
| 11 | `EmailConfigDialog` | `frontend/ui/system/email_config_dialog.py:13` | Standalone dialog. Imported only by `system/__init__.py` and `email_config_dialog.py` itself. Not launched by any screen. | **ARCHIVE** | 75 |
| 12 | `NavigationManager` | `frontend/ui/navigation/navigation_manager.py:72` | Duplicate of `NavigationHistory` in `frontend/ui/navigation_history.py`. Not in any registry. | **DELETE** | 95 |
| 13 | `LoadingDialog` | `frontend/ui/components/dialogs.py:309` | Replaced by `LoadingOverlay` in `components/loading_spinner.py:52` (which IS actively used). | **DELETE** | 95 |
| 14 | `SplitButton` | `frontend/ui/components/buttons.py:191` | Re-exported from `__init__.py` only; never instantiated. | **DELETE** | 90 |
| 15 | `SkeletonRow`, `SkeletonTable` | `frontend/ui/components/skeleton_loader.py:14,58` | Layer-2 of Phase UX.5 added the file; never imported by any screen. | **DELETE** | 95 |
| 16 | `FIFOAllocationDialog` | `frontend/ui/sales/fifo_allocation_dialog.py:23` | Not in registry, not launched. Sales FIFO feature on roadmap. | **ARCHIVE** | 80 |
| 17 | `CreditWarningDialog` | `frontend/ui/sales/credit_warning_dialog.py:20` | Not in registry, not launched. Credit-limit feature on roadmap. | **ARCHIVE** | 80 |
| 18 | `MixedPaymentBuilderDialog` | `frontend/ui/finance/mixed_payment_builder.py:26` | Standalone dialog not launched; the underlying `MixedPaymentBuilder` widget is used inside `JournalEntryFormDialog` but the top-level dialog class has no entry point. | **ARCHIVE** (partial) | 65 |
| 19 | `TOTPSetupDialog` | `frontend/ui/auth/totp_setup_dialog.py:24` | 2FA dialog. Not in registry, not launched. | **ARCHIVE** | 80 |
| 20 | `SearchResultsDropdown` | `frontend/ui/common/barcode_search.py:142` | Private inner class of `BarcodeSearchLineEdit`; not standalone. (Not strictly unreachable; internal widget.) | **KEEP** (internal) | n/a |
| 21 | `InputValidator` | `frontend/ui/utils/validation.py:115` | Utility class (not a UI screen). Used by forms internally. | **KEEP** (utility) | n/a |

**Effective UNREACHABLE counts:**
- **5 empty stub classes** in `system/` (ControlCenterScreen, SystemCorrelationScreen, DriftIntelligenceScreen, SystemIntegrityScreen, WorkflowIntelligenceScreen) — all 6 LOC each, pure placeholders
- **2 orphan screens** in truth/ and investigation/ (EventStoreScreen, EventInvestigationScreen) — only reachable via broken AnalyticsWorkspace
- **1 broken-but-registered** screen (AnalyticsWorkspace) — crash on click
- **3 roadmap dialogs** (FIFOAllocationDialog, CreditWarningDialog, TOTPSetupDialog) — never instantiated
- **4 dead widget classes** (LoadingDialog, SplitButton, SkeletonRow/Table, NavigationManager)
- **1 EmailConfigDialog** (never launched)
- **1 partial** (MixedPaymentBuilderDialog — class is unused but widget inside is used)
- **2 NEEDS_REVIEW** (CausalStrengthPanel, DecisionIntelligenceDashboard)

---

## 4. Critical Findings

### 4.1 CRITICAL: Broken Import Crashes "Analytics" Sidebar Entry

**File:** `frontend/ui/system/analytics_workspace.py:14`

```python
from ui.investigation.anomaly_investigation_screen import AnomalyInvestigationScreen
```

**Problem:** `frontend/ui/investigation/anomaly_investigation_screen.py` **does NOT exist** (only `event_investigation_screen.py` is in the directory). This import will fail at module-load time when the Analytics sidebar entry (index 40) is clicked.

**Impact:** When a user clicks the "Analytics" button in the System group, the LazyScreenManager will attempt to import `ui.system.analytics_workspace`, which will fail. The main_window will catch the exception (per `main_window.py` change_page logic) but the user will see an error toast and the screen will not load. Worse, if any other code path imports `analytics_workspace` at startup, the entire main_window will fail to launch.

**Fix priority:** **HIGH** — either create the missing file or remove the import + screen registration.

### 4.2 Orphan Screens Locked Behind Broken Import

`EventStoreScreen` and `EventInvestigationScreen` are only referenced by the broken `analytics_workspace.py`. They are not in the screen_registry, not in the sidebar, and not launched by any other code path. If the broken import is fixed (e.g., by creating `anomaly_investigation_screen.py`), these two screens would also need to be wired up or they remain orphans.

### 4.3 Empty Stub Classes (5 files, ~30 LOC)

Five files in `system/` contain only an empty QWidget subclass (~6 LOC each):
- `control_center_screen.py` — replaced by `OperationsDashboard` (index 38)
- `correlation_screen.py` — never implemented
- `drift_intelligence_screen.py` — never implemented
- `integrity_screen.py` — never implemented
- `workflow_intelligence_screen.py` — never implemented

These should be deleted.

### 4.4 ROLE-BASED HIDING (informational, not a bug)

The sidebar correctly filters visibility per role via `ROLE_PERMISSIONS`. A user with role `CASHIER` will not see the "Control Center" or "Audit Log" buttons. However, the screen IS still in the QStackedWidget and CAN be reached via direct `change_page()` call from code (e.g., from a menu shortcut). The current codebase does not appear to abuse this, but it's a **latent privilege-escalation vector** if menu shortcuts are added without role checks.

### 4.5 Many Menu Actions Are Placeholders

5 of 17 menu actions are non-functional stubs:
- Edit → Preferences → "Preferences panel would open here." (AlertDialog only)
- Operations → New Product → "Navigate to Products and click Add New." (AlertDialog only)
- Operations → Stock Alert Report → "Showing low stock items..." (AlertDialog only)
- Help → About → "About dialog content" (AlertDialog only)
- Tools → Calculator / Calendar → opens system apps (this is intentional)

**Recommendation:** Implement Preferences, New Product, and Stock Alert Report menus, or remove them.

---

## 5. Per-File Reachability Table (Sample of Component Classes)

The following component classes are **REACHABLE** but only as building blocks (not standalone screens):

| Class | File | Used by | Reachable? |
|---|---|---|---|
| `EnterpriseButton` | `components/buttons.py:30` | Everywhere | YES (foundational) |
| `EnterpriseTable` | `components/tables.py:125` | All list screens | YES |
| `DataEntryGrid` | `components/tables.py:558` | 4 line-item tables (per Phase 3C) | YES |
| `EnterpriseDialog` | `components/dialogs.py:43` | 8 dialog subclasses | YES |
| `ConfirmDialog`, `AlertDialog` | `components/dialogs.py:228,268` | Used for confirmations | YES |
| `FormSection`, `FormField`, `EnterpriseForm` | `components/forms.py:715,87,377` | 15+ screens (FormSection); FormField/EnterpriseForm unused | YES / KEEP (FormField, EnterpriseForm = deferred) |
| `LoadingOverlay`, `LoadingSpinner` | `components/loading_spinner.py:52,8` | `main_window.py` (`_show_error_toast`), many screens | YES |
| `NavigationHeader` | `components/navigation_header.py:26` | `main_window.py` (header) | YES |
| `NotificationManager` | `components/notifications.py:189` | Many screens | YES |
| `KPICard`, `StatusBadge`, `SectionHeader`, `MiniMetricCard` | `components/kpi_cards.py:51,195,231,133` | Dashboard | YES |
| `RoleRenderer` | `ui/role_renderer.py:20` | `main_window.py` | YES (via `auth_manager`) |
| `HealthBar`, `MetricCard`, `StatusIndicator`, `SeverityBadge`, `TrendArrow`, `TimelineEventWidget`, `IncidentCard`, `VirtualTimelineWidget` | `observability/widgets.py` | Internal to `dashboards.py` | YES (private widget building blocks) |
| `ObservabilityMainScreen`, `ControlCenterDashboard`, `UnifiedTimelineView`, `IncidentIntelligenceView`, `PredictiveDriftDashboard`, `ReplayTimeTravelView`, `DigitalTwinTelemetryView` | `observability/dashboards.py` | Internal to `ObservabilityConsole` (index 39) | YES (private tab widgets) |
| `OperationsDashboard` | `control_tower/operations_dashboard.py:13` | index 38 | YES |
| `ObservabilityConsole` | `observability/observability_console.py:16` | index 39 | YES |
| `InvestigateScreen` (= EventInvestigationScreen) | `investigation/event_investigation_screen.py:24` | (broken import path) | UNREACHABLE |
| `EventStoreScreen` | `truth/event_store_screen.py:22` | (broken import path) | UNREACHABLE |

---

## 6. Special-Case: MainWindow Internal Methods

`main_window.py` exposes several methods that are REACHABLE via the menu bar (already covered in §2.2):

| Method | File | Trigger | Verdict |
|---|---|---|---|
| `change_page(index, title)` | `main_window.py` | Sidebar click + dashboard `_navigate_to()` + menu `navigate_to()` | REACHABLE |
| `refresh_current_view()` | `main_window.py` | File→Refresh | REACHABLE (placeholder) |
| `logout()` | `main_window.py` | File→Logout + sidebar bottom button | REACHABLE |
| `show_preferences()` | `main_window.py` | Edit→Preferences | REACHABLE (placeholder) |
| `show_license_manager()` | `main_window.py` | Help→License Manager | REACHABLE |
| `show_about()` | `main_window.py` | Help→About | REACHABLE (placeholder) |
| `show_stock_alerts()` | `main_window.py` | Operations→Stock Alert Report | REACHABLE (placeholder) |
| `navigate_to(page_id)` | `main_window.py` | View/Operations/Reports/Tools menu actions | REACHABLE |
| `new_product()` | `main_window.py` | Operations→New Product | REACHABLE (placeholder) |
| `open_calculator()` | `main_window.py` | Tools→Calculator | REACHABLE (system) |
| `open_calendar()` | `main_window.py` | Tools→Calendar | REACHABLE (system) |
| `on_license_validation_changed()` | `main_window.py` | Signal from LicenseValidator | REACHABLE (signal) |
| `on_license_status_changed()` | `main_window.py` | Signal from LicenseValidator | REACHABLE (signal) |
| `on_theme_changed()` | `main_window.py` | Signal from ThemeEngine | REACHABLE (signal) |

---

## 7. Final Recommendations

### 7.1 KEEP (41 unique screens + components)

| Group | Count | Verdict |
|---|---:|---|
| Registered screens (indices 0-67) | 44 classes | **KEEP** |
| Login / License dialogs | 3 | **KEEP** |
| In-screen dialogs (35+ `.exec()` launches) | 35+ | **KEEP** |
| Reusable components (Button, Table, Form, etc.) | 20+ | **KEEP** |

### 7.2 ARCHIVE (6 items)

| File | Reason | Archive target |
|---|---|---|
| `frontend/ui/truth/event_store_screen.py` | Orphan (only imported by broken analytics_workspace) | `frontend/archive/orphan_screens/` |
| `frontend/ui/investigation/event_investigation_screen.py` | Orphan (same) | `frontend/archive/orphan_screens/` |
| `frontend/ui/sales/fifo_allocation_dialog.py` | Roadmap feature | `frontend/archive/roadmap/` |
| `frontend/ui/sales/credit_warning_dialog.py` | Roadmap feature | `frontend/archive/roadmap/` |
| `frontend/ui/finance/mixed_payment_builder.py` (Dialog class only) | Partial — widget inside is used | `frontend/archive/partial/` |
| `frontend/ui/auth/totp_setup_dialog.py` | 2FA roadmap | `frontend/archive/roadmap/` |
| `frontend/ui/system/email_config_dialog.py` | Never launched | `frontend/archive/orphan_dialogs/` |

### 7.3 DELETE (10 items)

| File | Reason |
|---|---|
| `frontend/ui/system/control_center_screen.py` | 6-LOC empty stub (real impl is `OperationsDashboard`) |
| `frontend/ui/system/correlation_screen.py` | 6-LOC empty stub |
| `frontend/ui/system/drift_intelligence_screen.py` | 6-LOC empty stub |
| `frontend/ui/system/integrity_screen.py` | 6-LOC empty stub |
| `frontend/ui/system/workflow_intelligence_screen.py` | 6-LOC empty stub |
| `frontend/ui/system/analytics_workspace.py` | Broken import — fix or delete |
| `frontend/ui/components/dialogs.py` (LoadingDialog only) | Replaced by LoadingOverlay |
| `frontend/ui/components/buttons.py` (SplitButton only) | Never instantiated |
| `frontend/ui/components/skeleton_loader.py` | Never imported (Layer 2 of Phase UX.5) |
| `frontend/ui/navigation/navigation_manager.py` | Duplicate of `navigation_history.py` |

### 7.4 MERGE (2 items)

| Group | Files | Canonical | Action |
|---|---|---|---|
| License flow | `licensing/activation_screen.py` (228 LOC, embedded in LicenseManagerDialog) + `licensing/license_status_screen.py` (285 LOC, embedded) | Already both embedded in `LicenseManagerDialog` | **MERGE** into `license_manager_dialog.py` |
| Email config | `system/email_config_dialog.py` (if kept) | (no clear canonical) | **MERGE** with `SettingsScreen` (index 28) |

### 7.5 NEEDS_REVIEW (2 items)

| File | Reason |
|---|---|
| `frontend/ui/causal_scoring/causal_strength_panel.py` | Internal widget, may be used inside `DecisionWorkspace` (index 47) — verify |
| `frontend/ui/causal_scoring/decision_ranking_dashboard.py` | May be alternate view for `DecisionWorkspace` — verify |

### 7.6 FIX (1 critical bug)

| File | Issue | Action |
|---|---|---|
| `frontend/ui/system/analytics_workspace.py:14` | Broken import: `ui.investigation.anomaly_investigation_screen` does not exist | **Create the file** (or remove the import and the index 40 registration) |

---

## 8. Per-Screen Decision Matrix (Condensed)

| # | Screen | Reachable? | Verdict |
|---:|---|:---:|---|
| 1 | Dashboard | YES | KEEP |
| 2 | LoginDialog | YES | KEEP |
| 3 | LicenseManagerDialog | YES | KEEP |
| 4 | ActivationScreen (embedded) | CONDITIONAL | KEEP |
| 5 | LicenseStatusScreen (embedded) | CONDITIONAL | KEEP |
| 6-50 | 44 registered screens (indices 1-67) | YES | KEEP |
| 51 | AnalyticsWorkspace (index 40) | **UNREACHABLE (broken)** | **FIX or DELETE** |
| 52 | EventStoreScreen | UNREACHABLE | ARCHIVE |
| 53 | EventInvestigationScreen | UNREACHABLE | ARCHIVE |
| 54 | SystemCorrelationScreen | UNREACHABLE (stub) | DELETE |
| 55 | DriftIntelligenceScreen | UNREACHABLE (stub) | DELETE |
| 56 | ControlCenterScreen | UNREACHABLE (stub) | DELETE |
| 57 | SystemIntegrityScreen | UNREACHABLE (stub) | DELETE |
| 58 | WorkflowIntelligenceScreen | UNREACHABLE (stub) | DELETE |
| 59 | EmailConfigDialog | UNREACHABLE | ARCHIVE |
| 60 | NavigationManager | UNREACHABLE | DELETE |
| 61 | LoadingDialog | UNREACHABLE (replaced) | DELETE |
| 62 | SplitButton | UNREACHABLE | DELETE |
| 63 | SkeletonRow + SkeletonTable | UNREACHABLE | DELETE |
| 64 | FIFOAllocationDialog | UNREACHABLE | ARCHIVE |
| 65 | CreditWarningDialog | UNREACHABLE | ARCHIVE |
| 66 | MixedPaymentBuilderDialog (class) | UNREACHABLE | ARCHIVE (partial) |
| 67 | TOTPSetupDialog | UNREACHABLE | ARCHIVE |
| 68 | CausalStrengthPanel | UNREACHABLE (private) | NEEDS_REVIEW |
| 69 | DecisionIntelligenceDashboard | UNREACHABLE (private) | NEEDS_REVIEW |

---

## 9. Final Outcome

| Metric | Value |
|---|---:|
| Total QWidget/QDialog subclasses | 168 |
| **REACHABLE** | 47 (44 registered + Dashboard + LoginDialog + LicenseManagerDialog) |
| **CONDITIONALLY_REACHABLE** (role/embedded) | 3 |
| **UNREACHABLE** | 19 (5 stubs + 1 broken + 2 orphans + 4 dead widgets + 4 roadmap dialogs + 1 email + 1 partial + 2 internal) |
| Internal/private widget building blocks | 99+ (KEEP — not screens) |

**Critical bug:** `analytics_workspace.py:14` is broken and will crash the "Analytics" sidebar entry. Highest priority fix.

**No files were modified.** The audit is a read-only trace. Implementation of the recommended KEEP / MERGE / ARCHIVE / DELETE actions requires a separate write-phase.
