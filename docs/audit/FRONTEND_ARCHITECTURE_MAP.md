# FRONTEND ARCHITECTURE MAP — Pharmacy ERP

## Module Hierarchy

```
frontend/
├── main.py                          # Application entry, ThemeEngine init, Auth gateway
├── api/                             # Backend API client layer (12 files)
│   ├── client.py                    #   Core APIClient (QObject) — HTTP, auth, retry, signals
│   ├── endpoints.py                 #   URL registry (90+ endpoints) + extract_list() helper
│   ├── autonomous_client.py         #   Typed client for /api/v1/autonomous/
│   ├── control_center_service.py    #   Resilient dashboard fetcher (own requests.Session)
│   ├── correlation_service.py       #   Cross-module event chain builder
│   ├── document_action_service.py   #   WhatsApp / print / share (client-side only)
│   ├── drift_intelligence_service.py#   In-memory trend analysis (no API calls)
│   ├── governance_client.py         #   Typed client for /api/v1/governance/
│   ├── integrity_service.py         #   Frontend-side cross-module consistency checks
│   ├── intelligence_client.py       #   Typed client for /api/v1/intelligence/
│   ├── observability_client.py      #   Typed client for /api/v1/observability/
│   └── truth_client.py              #   Typed client for /api/v1/truth/
│
├── ui/                              # All UI screens, components, navigation
│   ├── main_window.py               #   QMainWindow — lazy screen manager, sidebar, nav history
│   ├── sidebar.py                   #   260px fixed sidebar, 12 collapsible groups, 66 items
│   ├── constants.py                 #   Design tokens: 105 COLOR_*, spacing, typography, density
│   ├── dashboard.py                 #   Dashboard (index 0, always visible)
│   ├── screens/
│   │   ├── base_screen.py           #   BaseScreen, BaseFormScreen, BaseListScreen
│   ├── components/                  #   12 core reusable components
│   │   ├── buttons.py               #   EnterpriseButton + IconButton + SplitButton
│   │   ├── tables.py                #   EnterpriseTable + DataEntryGrid + TableColumn
│   │   ├── forms.py                 #   FormField (13 types) + ValidationRule
│   │   ├── dialogs.py               #   EnterpriseDialog + ConfirmDialog + AlertDialog
│   │   ├── kpi_cards.py             #   KPICard + MiniMetricCard + StatusBadge
│   │   ├── state_helper.py          #   StateHelper (loading/empty/error overlays)
│   │   ├── navigation_header.py     #   NavigationHeader (back/home/close + breadcrumb)
│   │   ├── notifications.py         #   NotificationItem + toast helpers
│   │   ├── loading_spinner.py       #   LoadingSpinner + LoadingOverlay
│   │   ├── document_action_dialog.py#   Print/PDF/WhatsApp dialog
│   │   └── base_widgets.py          #   BaseWidget + BaseContainerWidget
│   ├── accounting/                  #   12 files: dashboard, COA, journal, ledger, reports
│   ├── sales/                       #   4 files: invoice, customer, credit, allocation
│   ├── purchases/                   #   2 files: invoice, supplier
│   ├── inventory/                   #   8 files: product, category, warehouse, batch
│   ├── returns/                     #   2 files: returns, reconciliation
│   ├── finance/                     #   13 files: payments, expenses, budgets, tax, etc.
│   ├── hr/                          #   5 files: employee, attendance, leave, payroll, reports
│   ├── payroll/                     #   1 file: report_screens.py
│   ├── system/                      #   18 files: settings, users, roles, backup, audit, etc.
│   ├── pos/                         #   1 file: pos_screen.py
│   ├── auth/                        #   2 files: login, totp_setup
│   ├── autonomous/                  #   4 files (ALL orphaned)
│   ├── investigation/               #   2 files (ALL orphaned)
│   ├── governance/                  #   6 files (mostly orphaned)
│   ├── licensing/                   #   4 files (partially orphaned)
│   ├── control_tower/               #   6 files (partially orphaned)
│   ├── observability/               #   6 files (observability_console.py active)
│   ├── causal_scoring/              #   5 files (decision_workspace.py active)
│   ├── truth/                       #   1 file: event_store_screen.py (orphaned)
│   ├── common/                      #   5 utility dialogs
│   ├── navigation/                  #   1 file: navigation_manager.py (orphaned)
│   └── base/                        #   EMPTY directory (__init__.py only)
│
├── theme/                           # Theme system
│   ├── theme_engine.py              #   ThemeEngine singleton — canonical theme manager
│   ├── style_builder.py             #   UIStyleBuilder — centralized QSS generation
│   ├── enterprise_styling.py        #   DEPRECATED
│   └── theme_manager.py             #   Legacy QPalette manager (not used)
│
├── security/                        # Auth, session, tamper detection
│   ├── auth_manager.py              #   AuthManager (session restore, ui_scopes)
│   ├── session_store.py             #   Session persistence
│   ├── tamper_detector.py           #   File integrity checking
│   └── encrypted_config.py          #   Encrypted config
│
├── utils/                           # Logging, caching, printing, device
│   ├── logger.py                    #   Structured logging, correlation IDs, burst detection
│   ├── cache.py                     #   @cached decorator, TTL-based
│   ├── print_engine.py              #   Thermal / label / invoice printing
│   ├── offline_queue.py             #   Offline transaction queue with replay
│   ├── company_config.py            #   Company identity config fetcher
│   └── ...
│
├── i18n/                            # Internationalization (stub)
├── runtime/                         # Timer registry, auto-healer
├── config/                          # Production config
├── tests/                           # UI test suite (21 test files)
└── docs/                            # Design system docs
```

## Dependency Graph

```
main.py
  ├── ThemeEngine (theme/theme_engine.py)
  │     └── ui/constants.py (COLOR_*, SPACING_*, FONT_* tokens)
  ├── UIStyleBuilder (theme/style_builder.py)
  │     └── ui/constants.py
  ├── APIClient (api/client.py)
  │     ├── endpoints.py
  │     └── requests (HTTP)
  ├── AuthManager (security/auth_manager.py)
  ├── RoleRenderer (ui/role_renderer.py)
  │     └── role_manager.py
  └── MainWindow (ui/main_window.py)
        ├── Sidebar (ui/sidebar.py)
        ├── LazyScreenManager (ui/utils/lazy_loader.py)
        ├── NavigationHeader (ui/components/navigation_header.py)
        ├── LoadingOverlay (ui/components/loading_spinner.py)
        └── 66 Screen Widgets (lazy-loaded)
              └── BaseScreen (ui/screens/base_screen.py)
                    ├── StateHelper (ui/components/state_helper.py)
                    ├── EnterpriseTable (ui/components/tables.py)
                    ├── EnterpriseButton (ui/components/buttons.py)
                    └── FormField (ui/components/forms.py)
```

## Ownership Map

| Owner | Files | Responsibility |
|-------|-------|----------------|
| `main_window.py` | MainWindow | Screen registration, navigation orchestration, auth scoping |
| `sidebar.py` | Sidebar | Navigation menu, collapsible groups, role filtering |
| `constants.py` | All | Canonical design tokens (colors, spacing, typography, density) |
| `theme_engine.py` | ThemeEngine | Live theme switching dark/light |
| `style_builder.py` | UIStyleBuilder | Centralized QSS generation for all components |
| `base_screen.py` | BaseScreen/BaseFormScreen/BaseListScreen | Screen lifecycle, state machine, caching |
| `components/buttons.py` | EnterpriseButton | All button variants and sizes |
| `components/tables.py` | EnterpriseTable, DataEntryGrid | All tabular data display |
| `components/forms.py` | FormField | All form input types |
| `components/dialogs.py` | EnterpriseDialog | All dialog types |
| `components/kpi_cards.py` | KPICard, MiniMetricCard | KPI/metric display |
| `components/state_helper.py` | StateHelper | Loading/empty/error state overlays |
| `components/notifications.py` | NotificationItem | Toast notifications |
| `api/client.py` | APIClient | All HTTP communication, auth, retry |
| `api/endpoints.py` | Endpoint registry | Centralized URL constants |

## Shared Component Map

| Component | Used By | Count |
|-----------|---------|-------|
| EnterpriseButton | 40+ screens | Primary action button |
| EnterpriseTable | 25+ screens | Tabular data |
| FormField | 30+ screens | Form inputs |
| EnterpriseDialog | 20+ screens | Modal dialogs |
| StateHelper | 30+ screens | Loading/empty/error |
| KPICard | Dashboard, finance screens | Metric display |
| NavigationHeader | All screens (except dashboard) | Breadcrumb |
| LoadingOverlay | MainWindow | Global loading |
| NotificationItem | All screens | Toast messages |

## Screen Registration Matrix

```
Index  Screen Class                    Module                  Registered   Sidebar   BaseScreen
────── ────────────────────────────── ──────────────────────── ──────────── ────────  ─────────
  0    Dashboard                       ui.dashboard              ✅          ✅       ❌ (QWidget)
  1    ProductScreen                   ui.inventory.product_screen ✅          ✅       ✅
  2    CategoryScreen                  ui.inventory.category_screen  ✅       ✅       ✅
  3    WarehouseScreen                 ui.inventory.warehouse_screen ✅      ✅       ✅
  4    BatchScreen                     ui.inventory.batch_screen ✅         ✅       ✅
  5    SalesInvoiceScreen              ui.sales.sales_invoice_screen ✅    ✅       ❌ (QWidget)
  6    PurchaseInvoiceScreen           ui.purchases.purchase_invoice ✅    ✅       ❌ (QWidget)
  7    CustomerScreen                  ui.sales.customer_screen   ✅          ✅       ✅
  8    SupplierScreen                  ui.purchases.supplier_screen ✅        ✅       ✅
  9    ReturnsScreen                   ui.returns.returns_screen  ✅          ✅       ✅
 10    ChartOfAccountsScreen           ui.accounting.chart_of_accounts ✅    ✅       ❌ (QFrame)
 11    JournalEntryScreen              ui.accounting.journal_entry_screen ✅ ✅       ❌ (QFrame)
 12    AccountLedgerScreen             ui.accounting.account_ledger ✅       ✅       ❌ (QFrame)
 13-17 ReportBrowser (5 report types)  ui.accounting.report_browser ✅      ✅       ❌ (QWidget)
 18    PaymentScreen                   ui.finance.payment_screen  ✅          ✅       ❌ (QWidget)
 19    BudgetingScreen                 ui.finance.budgeting_screen ✅        ✅       ✅
 20    TaxScreen                       ui.finance.tax_screen      ✅          ✅       ✅
 21    CostCentersScreen               ui.finance.cost_centers_screen ✅     ✅       ✅
 22    CashflowScreen                  ui.finance.cashflow_screen ✅         ✅       ✅
 23    EmployeeScreen                  ui.hr.employee_screen      ✅          ✅       ✅
 24    AttendanceScreen                ui.hr.attendance_screen    ✅          ✅       ✅
 25    LeaveScreen                     ui.hr.leave_screen         ✅          ✅       ✅
 26    PayrollScreen                   ui.hr.payroll_screen       ✅          ✅       ✅
 27    BackupControlScreen             ui.system.backup_screen    ✅          ✅       ✅
 28    SettingsScreen                  ui.system.settings_screen  ✅          ✅       ✅
 29    FixedAssetsScreen               ui.system.fixed_assets_screen ✅      ✅       ✅
 30    AuditScreen                     ui.system.audit_screen     ✅          ✅       ✅
 31    UserManagementScreen            ui.system.user_management  ✅          ✅       ✅
 32    IntelligenceHubScreen           ui.system.intelligence_hub ✅          ✅       ✅
 33    InvoiceTemplateManager          ui.system.invoice_template ✅          ✅       ✅
 34    ExpenseScreen                   ui.finance.expense_screen  ✅          ✅       ✅
 35    EntityManagementScreen          ui.system.entity_management ✅         ✅       ✅
 36    LicensingScreen                 ui.system.licensing_screen ✅          ✅       ✅
 37    POSScreen                       ui.pos.pos_screen          ✅          ✅       ❌ (QWidget)
 38    OperationsDashboard             ui.control_tower.operations ✅        ✅       ❌ (QWidget)
 39    ObservabilityConsole            ui.observability.observability ✅     ✅       ❌ (QWidget)
 40    AnalyticsWorkspace              ui.system.analytics_workspace ✅      ❌       ❌ (QWidget)
 41-46 [unused]                        —                          —           —        —
 47    DecisionWorkspace               ui.causal_scoring.decision ✅         ✅       ❌ (QWidget)
 48    RoleManagementScreen            ui.system.role_management  ✅          ✅       ✅
 49-56 ReportBrowser (8 HR/Payroll)    ui.accounting.report_browser ✅      ✅       ❌ (QWidget)
 57    ReconciliationScreen            ui.returns.reconciliation  ✅          ✅       ✅
 58    FinancialIntegrityScreen        ui.accounting.financial_integrity ✅ ✅       ❌ (QWidget)
 59    FinancialAuditLogScreen         ui.accounting.financial_audit_log ✅  ✅       ❌ (QWidget)
 60    CustomerPaymentWorkspace        ui.finance.customer_payment ✅        ✅       ❌ (QWidget)
 61    SupplierPaymentWorkspace        ui.finance.supplier_payment ✅        ✅       ❌ (QWidget)
 62    PaymentAllocationExplorer       ui.finance.payment_allocation ✅      ✅       ❌ (QWidget)
 63    ReturnsExplainabilityScreen     ui.finance.returns_explainability ✅  ✅       ❌ (QWidget)
 64    JournalReversalExplorer         ui.finance.journal_reversal ✅        ✅       ❌ (QWidget)
 65    FinancialOperationsConsole      ui.finance.financial_operations ✅    ✅       ❌ (QWidget)
 66    CompanyProfileScreen            ui.system.company_profile ✅          ✅       ✅
```

## Screen Base Class Compliance

| Base Class | Count | Status |
|------------|-------|--------|
| BaseScreen (compliant) | 27 | ✅ |
| QWidget (violation) | 24 | ❌ |
| QFrame (violation) | 4 | ❌ |
| **Total registered screens** | **55** | — |

## Key Architecture Issues

1. **Dual URL management**: `client.py` has hardcoded endpoint strings in methods; `endpoints.py` has centralized registry — not fully synchronized
2. **Two HTTP sessions**: `APIClient` (with auth) and `ControlCenterService` (separate session, no auth)
3. **Two navigation systems**: `MainWindow.change_page()` is active; `NavigationManager` exists but is never wired
4. **Two page_map dictionaries**: One for breadcrumb, one for `navigate_to()` — with 13 off-by-one errors and 19 missing entries
5. **29 orphan screen files**: Exist on disk but never registered in MainWindow
6. **17 critical token interpolation bugs**: Component stylesheets use `{TOKEN}` in non-f-strings — silently broken
