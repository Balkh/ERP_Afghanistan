# FRONTEND ARCHITECTURE MAP

## 1. Module Hierarchy

```
frontend/
├── main.py                          # Application entry point (login → MainWindow)
├── api/
│   ├── client.py                    # APIClient (QObject, signals, auth, CRUD)
│   └── endpoints.py                 # Central endpoint registry (70+ endpoints)
├── ui/
│   ├── main_window.py               # MainWindow (QMainWindow, QStackedWidget, lazy screens)
│   ├── sidebar.py                   # Sidebar (collapsible groups, role-filtered nav)
│   ├── dashboard.py                 # Dashboard (KPI cards, role-aware, alerts)
│   ├── role_manager.py              # UserRole enum, AuthorizationResolver, ROLE_PERMISSIONS
│   ├── role_renderer.py             # RoleRenderer (scope-based UI filtering)
│   ├── constants.py                 # COLOR_* tokens, SPACING_* tokens, typography roles
│   ├── navigation/
│   │   └── navigation_manager.py    # NavigationManager (QObject, history stacks) — standalone
│   ├── screens/
│   │   └── base_screen.py           # BaseScreen, BaseFormScreen, BaseListScreen
│   ├── components/
│   │   ├── buttons.py               # EnterpriseButton, ButtonVariant, ButtonSize
│   │   ├── tables.py                # EnterpriseTable, TableColumn, build_table_stylesheet
│   │   ├── dialogs.py               # EnterpriseDialog, BaseDialog
│   │   ├── forms.py                 # FormSection, FormField
│   │   ├── state_helper.py          # ScreenStateHelper (loading/empty/error)
│   │   ├── kpi_cards.py             # KPICard, MiniMetricCard, StatusBadge
│   │   ├── notifications.py         # show_error, show_success, show_warning
│   │   ├── loading_spinner.py       # LoadingOverlay
│   │   └── navigation_header.py     # NavigationHeader (back/home/close)
│   ├── accounting/                  # 14 screen files + 5 component files
│   ├── sales/                       # 5 files (invoice, customer, dialogs)
│   ├── purchases/                   # 3 files (invoice, supplier)
│   ├── inventory/                   # 6 files (product, category, warehouse, batch)
│   ├── returns/                     # 2 files (returns, reconciliation)
│   ├── hr/                          # 8 files (employee, attendance, leave, payroll)
│   ├── payroll/                     # 1 file (report_screens.py)
│   ├── finance/                     # 15 files (payments, expenses, budgeting, etc.)
│   ├── pos/                         # 1 file (pos_screen.py)
│   ├── system/                      # 21 files (settings, backup, audit, etc.)
│   ├── control_tower/               # 6 files (operations, health, workflow)
│   ├── observability/               # 9 files (console, dashboards, replay)
│   ├── governance/                  # 7 files (approval, scanner, registry)
│   ├── licensing/                   # 5 files (activation, dialogs, status)
│   ├── autonomous/                  # 5 files (decisions, forecast, warnings)
│   ├── investigation/               # 2 files (anomaly, event)
│   ├── causal_scoring/              # 5 files (engine, workspace, ranking)
│   ├── truth/                       # 1 file (event_store)
│   ├── theme/
│   │   ├── theme_engine.py          # CANONICAL ThemeEngine (singleton, signals)
│   │   ├── theme_manager.py         # DEPRECATED — redirects to ThemeEngine
│   │   ├── style_builder.py         # UIStyleBuilder (global stylesheet)
│   │   └── enterprise_styling.py    # Enterprise styling utilities
│   ├── common/
│   │   ├── barcode_scanner.py       # BarcodeScannerInput widget
│   │   ├── batch_selection.py       # BatchSelectionDialog
│   │   └── printable_invoice.py     # PrintableInvoiceDialog
│   ├── utils/
│   │   └── lazy_loader.py           # LazyScreenManager (deferred widget creation)
│   └── base/
│       └── base_widgets.py          # Base widget classes
├── security/                        # auth_manager, session_store, tamper_detection
├── theme/                           # Legacy theme at top level
├── utils/                           # logger, cache, print_engine, etc.
└── runtime/                         # orchestrator, timer_registry, auto_healer
```

## 2. Screen Registration Matrix

| Index | Screen Class | Module | Sidebar Group | Lazy? | API Endpoint Used |
|-------|-------------|--------|---------------|-------|-------------------|
| 0 | Dashboard | ui.dashboard | Dashboard (always) | No | /api/control-center/ |
| 1 | ProductScreen | ui.inventory.product_screen | Inventory | Yes | /api/inventory/products/ |
| 2 | CategoryScreen | ui.inventory.category_screen | Inventory | Yes | /api/inventory/categories/ |
| 3 | WarehouseScreen | ui.inventory.warehouse_screen | Inventory | Yes | /api/inventory/warehouses/ |
| 4 | BatchScreen | ui.inventory.batch_screen | Inventory | Yes | /api/inventory/batches/ |
| 5 | SalesInvoiceScreen | ui.sales.sales_invoice_screen | Sales | Yes | /api/sales/invoices/ |
| 6 | PurchaseInvoiceScreen | ui.purchases.purchase_invoice_screen | Purchases | Yes | /api/purchases/invoices/ |
| 7 | CustomerScreen | ui.sales.customer_screen | Sales | Yes | /api/sales/customers/ |
| 8 | SupplierScreen | ui.purchases.supplier_screen | Purchases | Yes | /api/purchases/suppliers/ |
| 9 | ReturnsScreen | ui.returns.returns_screen | Returns | Yes | /api/returns/return-orders/ |
| 10 | POSScreen | ui.pos.pos_screen | Sales | Yes | /api/sales/invoices/ |
| 10 | ChartOfAccountsScreen | ui.accounting.chart_of_accounts_screen | Accounting | Yes | /api/accounting/accounts/ |
| 11 | JournalEntryScreen | ui.accounting.journal_entry_screen | Accounting | Yes | /api/accounting/journal-entries/ |
| 12 | AccountLedgerScreen | ui.accounting.account_ledger_screen | Accounting | Yes | /api/accounting/accounts/ledger/ |
| 13 | ReportBrowser(TB) | ui.accounting.report_browser | Reports | Yes | /api/accounting/accounts/trial_balance/ |
| 14 | ReportBrowser(P&L) | ui.accounting.report_browser | Reports | Yes | /api/accounting/accounts/profit_loss/ |
| 15 | ReportBrowser(BS) | ui.accounting.report_browser | Reports | Yes | /api/accounting/accounts/balance_sheet/ |
| 16 | ReportBrowser(AR) | ui.accounting.report_browser | Reports | Yes | /api/accounting/accounts/ar_aging/ |
| 17 | ReportBrowser(AP) | ui.accounting.report_browser | Reports | Yes | /api/accounting/accounts/ap_aging/ |
| 18 | PaymentScreen | ui.finance.payment_screen | Finance | Yes | /api/payments/transactions/ |
| 19 | BudgetingScreen | ui.finance.budgeting_screen | Finance | Yes | /api/budgets/budgets/ |
| 20 | TaxScreen | ui.finance.tax_screen | Finance | Yes | /api/tax/categories/ |
| 21 | CostCentersScreen | ui.finance.cost_centers_screen | Finance | Yes | /api/cost-centers/centers/ |
| 22 | CashflowScreen | ui.finance.cashflow_screen | Finance | Yes | /api/cashflow/items/ |
| 23 | EmployeeScreen | ui.hr.employee_screen | HR | Yes | /api/hr/employees/ |
| 24 | AttendanceScreen | ui.hr.attendance_screen | HR | Yes | /api/hr/reports/attendance-summary/ |
| 25 | LeaveScreen | ui.hr.leave_screen | HR | Yes | /api/hr/reports/leave-summary/ |
| 26 | PayrollScreen | ui.hr.payroll_screen | HR | Yes | /api/payroll/records/ |
| 27 | BackupControlScreen | ui.system.backup_screen | System | Yes | /api/backup/records/ |
| 28 | SettingsScreen | ui.system.settings_screen | System (Settings) | Yes | N/A (local config) |
| 29 | FixedAssetsScreen | ui.system.fixed_assets_screen | System | Yes | /api/assets/assets/ |
| 30 | AuditScreen | ui.system.audit_screen | System | Yes | /api/audit/logs/ |
| 31 | UserManagementScreen | ui.system.user_management_screen | System | Yes | /api/auth/users/ |
| 32 | IntelligenceHubScreen | ui.system.intelligence_hub_screen | System | Yes | /api/control-center/intelligence/ |
| 33 | InvoiceTemplateManager | ui.system.invoice_template_manager | System | Yes | N/A (local templates) |
| 34 | CompanyProfileScreen / ExpenseScreen | ui.system.company_profile_screen / ui.finance.expense_screen | System / Finance | Yes | /api/companies/config/ / /api/expenses/ |
| 35 | EntityManagementScreen | ui.system.entity_management_screen | System | Yes | /api/entities/ |
| 36 | LicensingScreen | ui.system.licensing_screen | System | Yes | /api/licensing/ |
| 38 | OperationsDashboard | ui.control_tower.operations_dashboard | System | Yes | /api/control-center/ |
| 39 | ObservabilityConsole | ui.observability.observability_console | System | Yes | /api/observability/ |
| 40-42 | AnalyticsWorkspace | ui.system.analytics_workspace | System | Yes | /api/analytics/ |
| 43-45 | OperationsDashboard (dup) | ui.control_tower.operations_dashboard | System | Yes | /api/control-center/ |
| 46-47 | DecisionWorkspace | ui.causal_scoring.decision_workspace | System | Yes | /api/decisions/ |
| 48 | RoleManagementScreen | ui.system.role_management_screen | System | Yes | /api/auth/roles/ |
| 48-56 | ReportBrowser (HR/Payroll) | ui.accounting.report_browser | Reports | Yes | /api/hr/reports/* /api/payroll/reports/* |
| 57 | ReconciliationScreen | ui.returns.reconciliation_screen | Returns | Yes | /api/returns/reconciliation/ |
| 58 | FinancialIntegrityScreen | ui.accounting.financial_integrity_screen | Accounting | Yes | /api/accounting/integrity/ |
| 59 | FinancialAuditLogScreen | ui.accounting.financial_audit_log_screen | Accounting | Yes | /api/accounting/audit-log/ |
| 60 | CustomerPaymentWorkspace | ui.finance.customer_payment_workspace | Finance | Yes | /api/payments/ |
| 61 | SupplierPaymentWorkspace | ui.finance.supplier_payment_workspace | Finance | Yes | /api/payments/ |
| 62 | PaymentAllocationExplorer | ui.finance.payment_allocation_explorer | Finance | Yes | /api/payments/ |
| 63 | ReturnsExplainabilityScreen | ui.finance.returns_explainability | Finance | Yes | /api/returns/ |
| 64 | JournalReversalExplorer | ui.finance.journal_reversal_explorer | Finance | Yes | /api/accounting/journal-entries/ |
| 65 | FinancialOperationsConsole | ui.finance.financial_operations_console | Finance | Yes | /api/control-center/ |

## 3. Dependency Graph

```
main.py
├── security.auth_manager
│   └── api.client (APIClient)
├── ui.main_window (MainWindow)
│   ├── ui.sidebar (Sidebar)
│   │   ├── ui.role_manager (UserRole, ROLE_PERMISSIONS)
│   │   ├── ui.constants (COLOR_*, SPACING_*, TEXT_*)
│   │   └── theme.theme_engine (ThemeEngine)
│   ├── ui.dashboard (Dashboard)
│   │   ├── ui.components.kpi_cards
│   │   ├── ui.components.buttons
│   │   └── ui.constants
│   ├── ui.components (buttons, tables, dialogs, forms, state_helper, etc.)
│   │   └── ui.constants
│   ├── ui.utils.lazy_loader (LazyScreenManager)
│   ├── ui.navigation.navigation_header
│   └── ALL screen modules (lazy-loaded)
├── ui.role_renderer
├── theme.theme_engine (singleton)
└── runtime.timer_registry
```

## 4. Shared Component Map

| Component | Used By | Notes |
|-----------|---------|-------|
| EnterpriseButton | Dashboard, ReturnsScreen, ReconciliationScreen, all BaseScreens | Canonical button component |
| EnterpriseTable | ReturnsScreen, ReconciliationScreen, many screens | Canonical table component |
| KPICard | Dashboard | KPI metric display |
| StatusBadge | Dashboard, accounting screens | Status indicators |
| LoadingOverlay | MainWindow (global) | Modal loading overlay |
| NavigationHeader | MainWindow | Back/home/close breadcrumb nav |
| ScreenStateHelper | BaseScreen-derived screens | Loading/empty/error states |
| FormSection | Accounting, HR screens | Standardized form grouping |
| APIClient | ALL screens | Central HTTP client (singleton pattern) |

## 5. Theme System Architecture

```
ThemeEngine (theme.theme_engine) ← SINGLE SOURCE OF TRUTH
├── theme_changed signal → MainWindow, Sidebar, Dashboard
├── refresh_widget_tree() → recursive style refresh
├── apply_theme(name) → set_active_theme() in constants
└── toggle() → light/dark switch

ThemeManager (ui.theme.theme_manager) ← DEPRECATED
└── All methods redirect to ThemeEngine

ui.constants
├── set_active_theme() → updates COLOR_* globals
├── _THEME_DARK dict (100+ tokens)
├── _THEME_LIGHT dict (100+ tokens)
├── SPACING_* tokens
├── TEXT_* semantic roles
└── BORDER_RADIUS_*, BUTTON_HEIGHT_*, INPUT_HEIGHT_* tokens

style_builder.UIStyleBuilder
└── get_global_style() → QSS stylesheet for all widgets
```

## 6. Ownership Map

| Module | Owner/Domain | Responsibility |
|--------|-------------|----------------|
| accounting/ | Financial Accounting | Chart of Accounts, JE, Ledger, Reports |
| sales/ | Sales Operations | Invoices, Customers, FIFO Allocation |
| purchases/ | Procurement | Invoices, Suppliers |
| inventory/ | Warehouse Operations | Products, Categories, Batches, Warehouses |
| returns/ | Returns Management | Return Orders, Reconciliation |
| hr/ | Human Resources | Employees, Attendance, Leave, Payroll |
| finance/ | Financial Operations | Payments, Expenses, Budget, Tax, Cashflow |
| pos/ | Point of Sale | Checkout, Barcode Scanning, Cart |
| system/ | System Administration | Settings, Backup, Audit, Users, Roles |
| control_tower/ | Operations Intelligence | Dashboard, Health, Workflow |
| observability/ | Monitoring | Console, Replay, Dashboards |
| governance/ | Governance | Approval, Scanner, Registry |
| autonomous/ | Autonomous Intelligence | Decisions, Forecast, Anomalies |
| investigation/ | Investigation | Anomaly, Event investigation |
| causal_scoring/ | Decision Intelligence | Causal Analysis, Rankings |
| licensing/ | License Management | Activation, Validation, Status |
