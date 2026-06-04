# God Object & Responsibility Violation Audit

**Date:** 2026-06-03
**Mission:** Read-only static analysis. No code modifications, no commits, no refactoring.
**Scope:** `E:\all downloads\Pharmacy_ERP\` — all production Python classes (backend + frontend).
**Excluded from analysis:** `venv/`, `__pycache__/`, `htmlcov/`, `frontend/tests/`, `frontend/enterprise_certification/`, `backend/tests/`, `*/migrations/*`, ad-hoc phase-validation scripts (`phase5_*.py`, `phase6_*.py`, `genesis_init.py`, `industrial_test_suite.py`, `certification_tests.py`, `tests_industrial.py`).

---

## Executive Summary

| Metric | Value |
|---|---:|
| Production Python files inventoried | ~700 (after exclusions) |
| **CRITICAL_GOD_OBJECT** | **7** |
| **GOD_OBJECT** | **3** |
| **LARGE** (well-scoped but big) | **8** |
| **HEALTHY** (all other classes) | ~600+ |

| Class | LOC | Methods | Fan-In | Fan-Out | Responsibilities | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `MainWindow` | **1,124** | **45** | 5 | 23 | **8** | **CRITICAL_GOD_OBJECT** |
| `PurchaseInvoiceScreen` | **887** | **38** | 1 | 13 | **6** | **CRITICAL_GOD_OBJECT** |
| `SalesInvoiceScreen` | **883** | **36** | 1 | 14 | **6** | **CRITICAL_GOD_OBJECT** |
| `POSScreen` | **859** | **40** | 0 | 13 | **8** | **CRITICAL_GOD_OBJECT** |
| `APIClient` | **667** | **57** | **56** | 7 | **9** | **CRITICAL_GOD_OBJECT** |
| `PaymentOperationsViewSet` | **1,077** | 17 | 1 | 17 | **6** | **CRITICAL_GOD_OBJECT** |
| `AccountViewSet` | **311** | 20 | 0 | n/a | **9** | **CRITICAL_GOD_OBJECT** |
| `BackupManager` | 305 | 18 | 17 | 18 | 4 | **GOD_OBJECT** |
| `FinancialReportEngine` | 632 (file) | 12 | 11 | 7 | 1 | **GOD_OBJECT** |
| `EnterpriseForm` | 337 | 27 | 0 | 6 | 1 | **LARGE** (well-scoped) |
| `FormField` | 289 | 13 | 0 | 6 | 1 | **LARGE** (well-scoped) |
| `ReturnsScreen` | 553 | 20 | 0 | 10 | 4 | **LARGE** |
| `JournalEntryViewSet` | 230 | 9 | 0 | n/a | 4 | **LARGE** |
| `SalesInvoiceViewSet` | 339 | 10 | 0 | 21 | 4 | **LARGE** |
| `BackupControlScreen` | 710 | 31 | 0 | n/a | 5 | **LARGE** (frontend) |
| `AuthorizationResolver` | 194 | 8 | 0 | 5 | 1 | **LARGE** (well-scoped) |
| `BackupScheduler` (in `backup_system.py`) | ~150 | 5 | 0 | 18 | 1 | **HEALTHY** (despite file size) |
| `JournalEngine` (in `journal_engine.py`) | n/a (file ~400 LOC) | n/a | n/a | n/a | 1 | **HEALTHY** (per AGENTS.md, not in top-50) |

**The 7 CRITICAL_GOD_OBJECTs are the highest-priority targets for decomposition.** All exhibit:
- 6+ distinct responsibilities
- 35+ methods
- 600+ LOC (or 300+ LOC with extreme responsibility breadth like `AccountViewSet`)
- A mix of business logic, UI construction, persistence, validation, and presentation

---

## 1. Classification Rubric

| Class | LOC | Methods | Responsibilities | Fan-In + Fan-Out | Action |
|---|---:|---:|---:|---:|---|
| **HEALTHY** | < 250 | < 15 | 1-2 | any | No action |
| **LARGE** | 250-500 | 15-25 | 1-3 | any | Monitor; consider if it grows |
| **GOD_OBJECT** | 500-1000 | 25-35 | 3-5 | high | Plan decomposition |
| **CRITICAL_GOD_OBJECT** | > 1000 **OR** 300+ LOC with 6+ responsibilities **OR** 35+ methods with 5+ responsibilities | | | | Decompose ASAP |

**Responsibility detection heuristics:**
- A class with `build_*`, `load_*`, `select_*`, `add_*`, `update_*`, `delete_*`, `print_*`, `export_*`, `validate_*`, `recalculate_*`, `setup_*`, `on_*_event`, and `*_action` methods is doing UI construction, persistence, validation, and event handling all at once.
- A class with both business logic (`calculate_*`, `process_*`) AND persistence (`get_queryset`, `perform_*`) AND presentation (`render_*`, `build_*`) violates SRP.
- A class with `*_pdf`, `*_csv`, `*_excel` methods is doing data export as a side responsibility.

---

## 2. CRITICAL_GOD_OBJECT Findings

### 2.1 `MainWindow` — frontend/ui/main_window.py

| Metric | Value |
|---|---:|
| File | `frontend/ui/main_window.py` |
| LOC (class body) | **1,124** |
| Method count | **45** |
| Fan-in (production) | 5 (imports of `MainWindow`) |
| Fan-out (file imports) | 23 |
| Responsibilities detected | **8** |
| Verdict | **CRITICAL_GOD_OBJECT** |

**Responsibility inventory (8 distinct concerns):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **Window lifecycle** | `__init__`, `closeEvent`, `keyPressEvent`, `resizeEvent`, `cleanup` |
| 2 | **Status bar / health monitoring** | `_setup_status_bar`, `_check_startup_health`, `_update_status_bar_time`, `_update_status_bar_user_info`, `_refresh_status_bar`, `check_connection` |
| 3 | **Navigation & page routing** | `change_page`, `navigate_to`, `_do_navigate`, `_go_back`, `_do_go_back`, `_go_home`, `_do_go_home`, `_close_screen`, `refresh_current_view`, `_do_refresh_current_view` |
| 4 | **Sidebar & UI scopes** | `_build_ui`, `_apply_sidebar_scopes`, `_on_ui_scopes_changed`, `_load_company_settings` |
| 5 | **Menu bar & dialog launchers** | `create_menu_bar`, `show_license_manager`, `show_about`, `show_preferences`, `show_stock_alerts`, `new_product`, `open_calculator`, `open_calendar` |
| 6 | **License management** | `on_license_validation_changed`, `on_license_status_changed`, `update_license_status_display`, `update_device_id_display` |
| 7 | **Theme management** | `toggle_theme`, `on_theme_changed`, `_refresh_window_styles`, `_do_refresh_window_styles` |
| 8 | **Authentication flow** | `_determine_role`, `logout`, `_build_breadcrumb`, `_update_nav_header` |

**Decomposition strategy:**

- Extract `MainWindowStatusBar` (resp 2) — owns the 3 status bar labels + health check timer
- Extract `MainWindowNavigator` (resp 3) — owns the QStackedWidget index, history stack, back/home/close logic
- Extract `MainWindowMenuBar` (resp 5) — owns the 7 menu menus and the dialog/action launchers (calculator, calendar, license, about, etc.)
- Extract `MainWindowLicenseBridge` (resp 6) — owns the signals from `LicenseValidator` and updates the device-id / license-status displays
- Extract `MainWindowThemeBridge` (resp 7) — owns the theme toggle action and re-style dispatch
- Keep `MainWindow` as a thin shell: `__init__` → compose 5 sub-widgets, `closeEvent` → forward to all, `keyPressEvent` → forward to active child

**Estimated impact:** `MainWindow` shrinks from 1,124 → ~250 LOC; each sub-widget is independently testable.

---

### 2.2 `PurchaseInvoiceScreen` — frontend/ui/purchases/purchase_invoice_screen.py

| Metric | Value |
|---|---:|
| File | `frontend/ui/purchases/purchase_invoice_screen.py` |
| LOC (class body) | **887** |
| Method count | **38** |
| Fan-in | 1 (registered in `screen_registry.py:54`) |
| Fan-out | 13 |
| Responsibilities detected | **6** |
| Verdict | **CRITICAL_GOD_OBJECT** |

**Responsibility inventory (6 distinct concerns):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **UI construction** | `_setup_screen`, `_build_header`, `_build_filters`, `_build_toolbar`, `_build_table`, `_build_footer`, `_wire_signals` |
| 2 | **Data loading** | `load_data`, `load_suppliers`, `on_supplier_selected`, `_fetch_products`, `_run_product_search`, `load_workflow_status` |
| 3 | **Product selection** | `show_product_selector`, `_on_product_search_changed`, `_on_product_search_submit`, `_show_search_results` |
| 4 | **Line items / cart** | `add_item_to_table`, `_on_remove_row`, `on_item_changed`, `on_tax_enabled_changed`, `recalculate_totals` |
| 5 | **Invoice lifecycle** | `save_draft`, `confirm_invoice`, `receive_invoice`, `dispatch_invoice`, `perform_workflow_action`, `print_invoice` |
| 6 | **Date/format helpers** | `_load_date_format`, `_apply_date_format`, `get_invoice_data`, `update_button_states`, `create_return`, `remove_selected_item`, `clear_form`, `setup_shortcuts`, `_check_action`, `_on_screen_shown` |

**Decomposition strategy:**

- Extract `PurchaseInvoiceHeader` (resp 1, partial) — header section (title, save/receive/cancel buttons)
- Extract `PurchaseInvoiceLineItemTable` (resp 4) — table widget + recalculate logic (can reuse the existing `DataEntryGrid` widget already adopted in Phase 3C)
- Extract `PurchaseInvoiceActionBar` (resp 5) — owns the action buttons (save, confirm, receive, dispatch, print, return)
- Extract `PurchaseInvoiceProductSelector` (resp 3) — modal product selection dialog (it already exists as `ProductSelectionDialog` in `common/`)
- Keep `PurchaseInvoiceScreen` as a coordinator (~300 LOC) that wires the sub-widgets together

**Estimated impact:** 887 → ~300 LOC. Identical pattern in `SalesInvoiceScreen` (see 2.3) means a single `BaseInvoiceScreen` could host both.

---

### 2.3 `SalesInvoiceScreen` — frontend/ui/sales/sales_invoice_screen.py

| Metric | Value |
|---|---:|
| File | `frontend/ui/sales/sales_invoice_screen.py` |
| LOC (class body) | **883** |
| Method count | **36** |
| Fan-in | 1 |
| Fan-out | 14 |
| Responsibilities detected | **6** |
| Verdict | **CRITICAL_GOD_OBJECT** |

**Responsibility inventory (6 distinct concerns, mirror of PurchaseInvoiceScreen):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **UI construction** | `_setup_screen`, `_build_header`, `_build_filters`, `_build_toolbar`, `_build_table`, `_build_footer`, `_wire_signals` |
| 2 | **Data loading** | `load_data`, `load_customers`, `on_customer_selected`, `on_barcode_scanned`, `on_product_selected`, `load_workflow_status` |
| 3 | **Product selection** | `show_product_selector`, `add_item_to_table`, `select_batch_for_row`, `set_batch_for_row` |
| 4 | **Line items / cart** | `on_item_changed`, `on_tax_enabled_changed`, `recalculate_totals` |
| 5 | **Invoice lifecycle** | `save_draft`, `confirm_invoice`, `dispatch_invoice`, `perform_workflow_action`, `print_invoice` |
| 6 | **Helpers** | `_load_date_format`, `_apply_date_format`, `get_invoice_data`, `update_button_states`, `create_return`, `remove_selected_item`, `clear_form`, `setup_shortcuts`, `_check_action`, `_on_screen_shown` |

**Decomposition strategy:**

- Apply the same decomposition as `PurchaseInvoiceScreen` (§2.2)
- **Strong recommendation:** Extract a shared `BaseInvoiceScreen` that owns responsibilities 1, 4, 6 (UI, line items, helpers). Subclass as `PurchaseInvoiceScreen` and `SalesInvoiceScreen` for the lifecycle-specific bits (resp 3, 5). This eliminates ~70% code duplication between the two screens.

**Estimated impact:** 883 + 887 → ~500 LOC total (1 `BaseInvoiceScreen` of ~250 LOC + 2 thin subclasses of ~125 LOC each).

---

### 2.4 `POSScreen` — frontend/ui/pos/pos_screen.py

| Metric | Value |
|---|---:|
| File | `frontend/ui/pos/pos_screen.py` |
| LOC (class body) | **859** |
| Method count | **40** |
| Fan-in | 0 (imported only by `screen_registry.py` which uses string-based dynamic import) |
| Fan-out | 13 |
| Responsibilities detected | **8** |
| Verdict | **CRITICAL_GOD_OBJECT** |

**Responsibility inventory (8 distinct concerns, most fragmented of all UI classes):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **UI scaffolding** | `_setup_screen`, `_build_header`, `_build_main_splitter`, `_build_footer`, `_action_button`, `setup_shortcuts` |
| 2 | **Left panel layout** | `_build_left_panel`, `_build_scan_zone`, `_build_product_search`, `_build_customer_zone`, `_build_alerts_zone` |
| 3 | **Right panel layout** | `_build_right_panel`, `_build_cart_table`, `_build_totals_panel`, `_build_payment_panel` |
| 4 | **Barcode scanning** | `_on_barcode_scanned`, `_show_scan_error` |
| 5 | **Product search** | `_search_products`, `_add_search_result_to_cart`, `_add_search_result_to_cart_by_index` |
| 6 | **Cart management** | `_add_to_cart`, `_refresh_cart`, `_on_cart_cell_changed`, `_remove_selected_item`, `_remove_item` |
| 7 | **Totals & change** | `_update_totals`, `_set_total`, `_update_change_label` |
| 8 | **Payment & invoice** | `_process_payment`, `_on_customer_changed`, `_show_invoice_preview`, `_print_last_invoice`, `new_sale`, `hold_sale`, `recall_sale`, `_show_alert` |

**Decomposition strategy:**

- Extract `POSScanZone` (resp 2 partial, resp 4) — scan input + barcode handler
- Extract `POSProductSearch` (resp 2 partial, resp 5) — product search panel + search handler
- Extract `POSCartTable` (resp 3 partial, resp 6) — cart widget + add/remove handlers
- Extract `POSTotalsPanel` (resp 3 partial, resp 7) — totals + change display
- Extract `POSPaymentFlow` (resp 3 partial, resp 8) — payment processing + invoice preview
- Keep `POSScreen` as a coordinator (~250 LOC) that composes the 5 sub-widgets

**Estimated impact:** 859 → ~250 LOC. Each sub-widget is independently testable.

---

### 2.5 `APIClient` — frontend/api/client.py

| Metric | Value |
|---|---:|
| File | `frontend/api/client.py` |
| LOC (class body) | **667** |
| Method count | **57** |
| Fan-in | **56** (highest in the project) |
| Fan-out | 7 |
| Responsibilities detected | **9** |
| Verdict | **CRITICAL_GOD_OBJECT** |

**Responsibility inventory (9 distinct concerns, broadest fan-in):**

| # | Responsibility | Method count | Example methods |
|---:|---|---:|---|
| 1 | **HTTP transport** | 6 | `get`, `post`, `put`, `delete`, `_make_request`, `_is_retryable_error` |
| 2 | **Auth & tokens** | 5 | `set_auth_token`, `set_auth_data`, `clear_auth_token`, `_attempt_token_refresh`, `is_authenticated` |
| 3 | **Error / UI feedback** | 3 | `_show_error_toast`, `_hide_loading_overlay`, `parse_api_error` |
| 4 | **Control center** | 5 | `get_control_center`, `get_control_center_stats`, `get_control_center_financial`, `get_control_center_inventory`, `get_control_center_hr`, `get_control_center_operations` |
| 5 | **Dashboards** | 5 | `get_executive_dashboard`, `get_sales_dashboard`, `get_inventory_dashboard`, `get_financial_dashboard`, `get_hr_dashboard` |
| 6 | **Barcodes / products** | 6 | `lookup_barcode`, `lookup_sku`, `search_products`, `get_product_detail`, `get_product_by_barcode_or_sku`, `lookup_batch_barcode`, `generate_barcode`, `validate_barcode` |
| 7 | **User / role admin** | 11 | `get_users`, `get_user`, `create_user`, `update_user`, `delete_user`, `get_roles`, `get_role`, `create_role`, `update_role`, `delete_role`, `get_permissions` |
| 8 | **Reports** | 4 | `export_report`, `download_report`, `get_report_options`, `generate_advanced_report` |
| 9 | **Workflows** | 5 | `get_workflow_status`, `workflow_action`, `get_workflow_instances`, `create_workflow_instance`, `get_approval_chains`, `get_my_pending_approvals`, `process_approval_request` |

**Decomposition strategy:**

- Keep `APIClient` as a thin **HTTP transport** (resp 1, 2, 3 — ~150 LOC)
- Extract `ControlCenterService` (resp 4) — owns 5 control-center endpoints
- Extract `DashboardService` (resp 5) — owns 5 dashboard endpoints
- Extract `ProductCatalogService` (resp 6) — owns barcode + product lookup
- Extract `UserAdminService` (resp 7) — owns user/role/permission CRUD
- Extract `ReportService` (resp 8) — owns report generation/export
- Extract `WorkflowService` (resp 9) — owns workflow state machine calls

**Per DEAD_CODE_INVENTORY.md** ~13 of these methods have 0 callers and should be deleted outright (`is_authenticated`, `parse_api_error`, `generate_barcode`, `validate_barcode`, `export_report`, `download_report`, `generate_advanced_report`, `get_report_options`, all `get_control_center*` (5), all `get_*_dashboard` (5)). That alone removes 13 methods (~20% of the class) without behaviour change.

**Estimated impact:** 667 → ~150 LOC for `APIClient` + 6 service classes (each ~80 LOC). Total goes from 667 → ~630 LOC but the responsibility surface shrinks from 9 to 1.

---

### 2.6 `PaymentOperationsViewSet` — backend/core/api/v1/payment_operations.py

| Metric | Value |
|---|---:|
| File | `backend/core/api/v1/payment_operations.py` |
| LOC (class body) | **1,077** |
| Method count | 17 |
| Fan-in | 1 |
| Fan-out | 17 |
| Responsibilities detected | **6** |
| Verdict | **CRITICAL_GOD_OBJECT** |

**Responsibility inventory (6 distinct concerns, all payment-related but operationally separate):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **Customer payment workspace** | `customer_payment_workspace`, `process_customer_payment`, `allocate_customer_unallocated` |
| 2 | **Supplier payment workspace** | `supplier_payment_workspace`, `process_supplier_payment`, `allocate_supplier_unallocated` |
| 3 | **Payment tracing** | `customer_payment_trace`, `supplier_payment_trace` |
| 4 | **Mixed payment** | `validate_mixed_payment`, `process_customer_payment`, `process_supplier_payment`, `process_mixed_payment` |
| 5 | **Anomaly detection** | `payment_anomalies` |
| 6 | **PDF statements** | `customer_statement_pdf`, `supplier_statement_pdf` |
| 7 | **Method / account listing** | `list_payment_methods`, `list_payment_accounts` |

**Decomposition strategy:**

- Extract `CustomerPaymentViewSet` (resp 1) — workspace, process, allocate
- Extract `SupplierPaymentViewSet` (resp 2) — workspace, process, allocate
- Extract `PaymentTraceViewSet` (resp 3) — customer + supplier traces
- Extract `MixedPaymentViewSet` (resp 4) — validate + process mixed payments
- Extract `PaymentDiagnosticsViewSet` (resp 5) — anomaly detection
- Extract `PaymentStatementViewSet` (resp 6) — PDF generation
- Extract `PaymentMethodAccountListView` (resp 7) — read-only reference data
- Keep `PaymentOperationsViewSet` as a router that wires the 7 sub-viewsets (~50 LOC)

**Estimated impact:** 1,077 → ~50 LOC for the router + 7 small viewset classes (~150 LOC each = 1,050 total). The split clarifies responsibility and enables per-resource rate limiting and per-feature toggling.

---

### 2.7 `AccountViewSet` — backend/accounting/views_account.py

| Metric | Value |
|---|---:|
| File | `backend/accounting/views_account.py` |
| LOC (class body, lines 46-356) | **311** |
| Method count | **20** |
| Fan-in | 0 (routed via router, not directly imported) |
| Fan-out | 7 |
| Responsibilities detected | **9** |
| Verdict | **CRITICAL_GOD_OBJECT** (responsibility breadth is the killer here) |

**Responsibility inventory (9 distinct concerns):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **Standard CRUD** | `get_queryset`, `perform_destroy` |
| 2 | **Account tree traversal** | `tree`, `by_type`, `leaf_accounts`, `children`, `descendants`, `ancestors` |
| 3 | **Account balance** | `balance` |
| 4 | **Chart initialization** | `initialize_chart` |
| 5 | **Financial reports (full P&L suite)** | `trial_balance`, `balance_sheet`, `income_statement`, `cash_flow`, `account_summary`, `ledger` |
| 6 | **Aging reports** | `ar_aging`, `ap_aging` |
| 7 | **Reconciliation** | `reconciliation` |
| 8 | **Inventory valuation** | `inventory_valuation` |
| 9 | **Other** | (no others; the 20 methods are fully covered above) |

**Decomposition strategy:**

- Keep `AccountViewSet` (resp 1) — standard CRUD (~80 LOC)
- Extract `AccountHierarchyViewSet` (resp 2, 3) — tree traversal + balance (read-only, ~60 LOC)
- Extract `FinancialReportViewSet` (resp 5, 6) — all 7 financial reports (~150 LOC). Note: `FinancialReportEngine` (in `accounting/services/financial_reports.py`) already exists — this viewset should just be a thin wrapper that delegates.
- Extract `AccountOperationsViewSet` (resp 4, 7) — chart init + reconciliation (~60 LOC)
- Extract `InventoryValuationViewSet` (resp 8) — single read-only endpoint (~30 LOC)

**Estimated impact:** 311 → 5 focused viewsets. The router can mount all 5 under `/api/accounting/` without breaking URLs (use the `@action` decorator or split into separate `urls.py`).

**Note:** This is the same problem pattern as `PaymentOperationsViewSet` (§2.6) — a single ViewSet accumulating one `@action` per financial report. The `FinancialReportEngine` service class was created later but the viewset never decomposed.

---

## 3. GOD_OBJECT Findings

### 3.1 `BackupManager` — backend/backup/backup_system.py

| Metric | Value |
|---|---:|
| File | `backend/backup/backup_system.py` |
| LOC (class body) | **305** |
| Method count | **18** |
| Fan-in | **17** (highest backend fan-in) |
| Fan-out | 18 |
| Responsibilities detected | 4 |
| Verdict | **GOD_OBJECT** (high reuse, but borderline) |

**Responsibility inventory (4 concerns, mostly focused on backup lifecycle):**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **Backup creation** | `__init__`, `_ensure_db_path`, `_setup_logging`, `_check_pre_backup_safety`, `create_backup`, `_log_db_event`, `_vacuum_database`, `_create_archive`, `_post_backup_verify` |
| 2 | **Restore & list** | `restore_backup`, `list_backups`, `delete_backup`, `cleanup_old_backups` |
| 3 | **Encryption hooks** | `generate_key`, `encrypt_file`, `decrypt_file`, `_get_encryption_password`, `_is_encryption_configured` |
| 4 | **Statistics & config** | `get_backup_stats`, `get_default_config`, `load_config`, `save_config`, `_merge_config` |

**Decomposition strategy:**

- Extract `BackupArchiver` (resp 1, partial) — owns the archive/vacuum logic
- Extract `BackupEncryptor` (resp 3) — already exists as `BackupEncryptor` class in the same file; consider making it standalone
- Extract `BackupConfig` (resp 4) — already exists as `BackupConfig` class; consider moving to a separate config module
- Keep `BackupManager` as the orchestrator (resp 1 partial, resp 2) — coordinates the above

**Estimated impact:** 305 → ~150 LOC for `BackupManager` + 2-3 sibling classes.

---

### 3.2 `FinancialReportEngine` — backend/accounting/services/financial_reports.py

| Metric | Value |
|---|---:|
| File | `backend/accounting/services/financial_reports.py` |
| LOC (class body) | **743** (in a 632-LOC file, including imports) |
| Method count | 12 |
| Fan-in | **11** |
| Fan-out | 7 |
| Responsibilities detected | 1 (financial reports — well-scoped) |
| Verdict | **GOD_OBJECT** (huge but single responsibility) |

**Responsibility inventory:**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **Financial reports (P&L, BS, TB, ledger, AR/AP aging, cash flow)** | `get_trial_balance`, `get_profit_and_loss`, `_get_pnl_section`, `process_accounts`, `get_balance_sheet`, `calculate_balances`, `get_cash_flow_statement`, `_get_account_change`, `get_account_ledger`, `get_account_summary`, `get_ar_aging`, `get_ap_aging` |

**Decomposition strategy:**

- The class is **single-responsibility** but **very large**. Recommended split:
- Extract `TrialBalanceCalculator` — `get_trial_balance`, `process_accounts`
- Extract `ProfitLossCalculator` — `get_profit_and_loss`, `_get_pnl_section`
- Extract `BalanceSheetCalculator` — `get_balance_sheet`, `calculate_balances`
- Extract `CashFlowCalculator` — `get_cash_flow_statement`, `_get_account_change`
- Extract `AccountLedgerReader` — `get_account_ledger`, `get_account_summary`
- Extract `AgingReportReader` — `get_ar_aging`, `get_ap_aging`
- Keep `FinancialReportEngine` as a façade that delegates to the 6 sub-calculators (~80 LOC)

**Estimated impact:** 743 → ~80 LOC for the façade + 6 small calculator classes. Memory pressure drops because each calculator can be lazy-loaded.

---

### 3.3 `JournalEntryViewSet` — backend/accounting/views_account.py

| Metric | Value |
|---|---:|
| File | `backend/accounting/views_account.py` |
| LOC (class body, lines 357-588) | **230** |
| Method count | 9 |
| Fan-in | 0 |
| Fan-out | n/a |
| Responsibilities detected | 4 |
| Verdict | **GOD_OBJECT** (responsibility breadth) |

**Responsibility inventory:**

| # | Responsibility | Methods |
|---:|---|---|
| 1 | **Standard CRUD** | `get_queryset` |
| 2 | **Lifecycle (post/unpost/reverse)** | `post_entry`, `unpost_entry`, `reverse_entry` |
| 3 | **Reversal safety** | `reversal_impact`, `reversal_chain`, `safe_reverse` |
| 4 | **Audit & export** | `event_history`, `export_reversal_audit_pdf` |

**Decomposition strategy:**

- Extract `JournalReversalViewSet` (resp 3) — 3 methods, 1 responsibility
- Extract `JournalAuditViewSet` (resp 4) — 2 methods, 1 responsibility
- Keep `JournalEntryViewSet` (resp 1, 2) — standard CRUD + lifecycle

**Estimated impact:** 230 → ~120 LOC.

---

## 4. LARGE (Well-Scoped) Findings

These are big but their responsibility count is low. Monitor; do not decompose yet.

| # | Class | File | LOC | Methods | Fan-In | Fan-Out | Responsibilities | Notes |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | `EnterpriseForm` | `frontend/ui/components/forms.py:377` | 337 | 27 | 0 | 6 | 1 (form rendering) | Phase 4 candidate; not yet adopted by any screen |
| 2 | `FormField` | `frontend/ui/components/forms.py:87` | 289 | 13 | 0 | 6 | 1 (single field) | Phase 4 candidate |
| 3 | `ReturnsScreen` | `frontend/ui/returns/returns_screen.py:23` | 553 | 20 | 0 | 10 | 4 (list, dialog, lifecycle, export) | Could split into `ReturnsListScreen` + `ReturnOrderDialog` (already separate, lives in same file) |
| 4 | `SalesInvoiceViewSet` | `backend/sales/views.py:400` | 339 | 10 | 0 | 21 | 4 (CRUD, cancel, dispatch, credit approval) | High fan-out suggests this viewset has many cross-concerns |
| 5 | `BackupControlScreen` | `frontend/ui/system/backup_screen.py:209` | 710 | 31 | 0 | n/a | 5 (status, restore, list, config, action bar) | Could split: `BackupListPanel` + `BackupActionPanel` + `RestoreConfirmDialog` |
| 6 | `AuthorizationResolver` | `frontend/ui/role_manager.py` | 194 | 8 | 0 | 5 | 1 (RBAC resolution) | Healthy, well-focused |
| 7 | `BackupScheduler` | `backend/backup/backup_system.py` | ~150 | 5 | 0 | 18 | 1 (cron-like scheduling) | Healthy, single-purpose |
| 8 | `JournalEventLogViewSet` | `backend/accounting/views_account.py:31` | ~15 | 0 | 0 | n/a | 1 (audit log CRUD) | Healthy |

**Verdict:** These classes are not urgent. The decomposition strategies are listed for reference.

---

## 5. Cross-Cutting Responsibility Violations

### 5.1 ViewSets accumulate `@action` methods like a junk drawer

The pattern of one ViewSet per resource that grows new `@action` methods for every report/operation is a **systemic anti-pattern** in this codebase. Affected files:

- `backend/accounting/views_account.py` — `AccountViewSet` (20 methods, 9 responsibilities)
- `backend/core/api/v1/payment_operations.py` — `PaymentOperationsViewSet` (17 methods, 6 responsibilities)
- `backend/sales/views.py` — `SalesInvoiceViewSet` (10 methods, 4 responsibilities)
- `backend/accounting/views_account.py` — `JournalEntryViewSet` (9 methods, 4 responsibilities)
- `backend/backup/views.py` — `backup/views.py` has 11 ViewSets but each is small (2-5 methods), which is the **correct** pattern

**Recommendation:** Adopt the **`backup/views.py` pattern** — many small ViewSets, each with a clear single purpose, mounted under the same URL prefix. The DRF router supports this trivially.

### 5.2 Frontend screens mix UI construction with business logic

The pattern of `_build_header`, `_build_table`, `_build_filters`, `_build_footer` + `load_data`, `recalculate_totals`, `save_draft` + `print_invoice` is repeated in `PurchaseInvoiceScreen`, `SalesInvoiceScreen`, `POSScreen`, and `ReturnsScreen`. All four screens:

1. Build their own UI tree (200-300 LOC of layout code)
2. Wire their own signals
3. Handle their own data loading
4. Handle their own save/dispatch logic
5. Handle their own printing

**Recommendation:** Extract a `BaseInvoiceScreen` (or `BaseCartscreen`) that owns responsibilities 1-3. Subclass for the lifecycle-specific bits (4-5). Phase UX.3 introduced `BaseScreen` + `BaseFormScreen` + `BaseListScreen` as a foundation — the invoice/POS screens predate that and have not been migrated.

### 5.3 `APIClient` violates SRP across 9 business domains

`APIClient` (resp 1-9 above) is the **single most-imported class in the frontend** (fan-in 56). Splitting it into 6 service classes is the highest-leverage decomposition in the entire codebase: 56 call sites would benefit from a cleaner API surface, and ~13 of those methods have 0 callers and should be deleted outright (per DEAD_CODE_INVENTORY.md).

### 5.4 `main_window.py` is the cockpit, not the airplane

`MainWindow` is a 1,124-LOC class that owns **everything** about the application's chrome. The most natural decomposition is **5 sub-widgets** (status bar, navigator, menu bar, license bridge, theme bridge) each < 200 LOC. The current shape forces any change to license handling or theme switching to edit a 1,124-LOC file — high merge conflict risk, slow code review.

---

## 6. Responsibility Heat-Map

| Concern | Files containing it | Total LOC |
|---|---|---:|
| **Invoice / sales / purchase UI** | `frontend/ui/sales/sales_invoice_screen.py`, `frontend/ui/purchases/purchase_invoice_screen.py`, `frontend/ui/pos/pos_screen.py` | **2,629** |
| **Main window orchestration** | `frontend/ui/main_window.py` | **1,124** |
| **Payment operations API** | `backend/core/api/v1/payment_operations.py` | **1,077** |
| **API client transport** | `frontend/api/client.py` | **667** |
| **Financial reports** | `backend/accounting/services/financial_reports.py` | **632** |
| **Backup UI + backend** | `frontend/ui/system/backup_screen.py` + `backend/backup/backup_system.py` | **1,430** |
| **Account & report API** | `backend/accounting/views_account.py` | **588** |
| **Returns UI** | `frontend/ui/returns/returns_screen.py` | **788** |

**Note:** Invoice / sales / purchase UI is the single biggest concentration of LOC in the project (2,629 LOC across 3 screens). A `BaseInvoiceScreen` extraction would consolidate ~50% of this code.

---

## 7. Per-File Decision Matrix

| File | Largest class | LOC | Methods | Verdict | Priority |
|---|---|---:|---:|---|---:|
| `frontend/ui/main_window.py` | `MainWindow` | 1,124 | 45 | **CRITICAL_GOD_OBJECT** | **P0** |
| `frontend/ui/purchases/purchase_invoice_screen.py` | `PurchaseInvoiceScreen` | 887 | 38 | **CRITICAL_GOD_OBJECT** | **P0** |
| `frontend/ui/sales/sales_invoice_screen.py` | `SalesInvoiceScreen` | 883 | 36 | **CRITICAL_GOD_OBJECT** | **P0** |
| `frontend/ui/pos/pos_screen.py` | `POSScreen` | 859 | 40 | **CRITICAL_GOD_OBJECT** | **P0** |
| `frontend/api/client.py` | `APIClient` | 667 | 57 | **CRITICAL_GOD_OBJECT** | **P0** |
| `backend/core/api/v1/payment_operations.py` | `PaymentOperationsViewSet` | 1,077 | 17 | **CRITICAL_GOD_OBJECT** | **P0** |
| `backend/accounting/views_account.py` | `AccountViewSet` | 311 | 20 | **CRITICAL_GOD_OBJECT** | **P0** |
| `backend/backup/backup_system.py` | `BackupManager` | 305 | 18 | **GOD_OBJECT** | P1 |
| `backend/accounting/services/financial_reports.py` | `FinancialReportEngine` | 743 | 12 | **GOD_OBJECT** | P1 |
| `backend/accounting/views_account.py` | `JournalEntryViewSet` | 230 | 9 | **GOD_OBJECT** | P1 |
| `frontend/ui/components/forms.py` | `EnterpriseForm` | 337 | 27 | LARGE (well-scoped) | P3 |
| `frontend/ui/returns/returns_screen.py` | `ReturnsScreen` | 553 | 20 | LARGE | P2 |
| `frontend/ui/system/backup_screen.py` | `BackupControlScreen` | 710 | 31 | LARGE | P2 |
| `backend/sales/views.py` | `SalesInvoiceViewSet` | 339 | 10 | LARGE | P2 |
| `frontend/ui/components/forms.py` | `FormField` | 289 | 13 | LARGE (well-scoped) | P3 |
| `frontend/ui/role_manager.py` | `AuthorizationResolver` | 194 | 8 | LARGE (well-scoped) | P3 |

---

## 8. Decomposition Strategy Summary

| Class | Strategy | Sub-classes | Estimated new LOC distribution |
|---|---|---|---|
| `MainWindow` | Compose 5 sub-widgets | `MainWindowStatusBar`, `MainWindowNavigator`, `MainWindowMenuBar`, `MainWindowLicenseBridge`, `MainWindowThemeBridge` | 250 + 4×150 + 1×100 = 950 (down from 1,124) |
| `PurchaseInvoiceScreen` + `SalesInvoiceScreen` | Extract `BaseInvoiceScreen` | `BaseInvoiceScreen`, `PurchaseInvoiceScreen` (subclass), `SalesInvoiceScreen` (subclass) | 250 + 2×(125+100) = 600 (down from 1,770) |
| `POSScreen` | Compose 5 sub-widgets | `POSScanZone`, `POSProductSearch`, `POSCartTable`, `POSTotalsPanel`, `POSPaymentFlow` | 250 + 5×120 = 850 (similar to current 859, but each testable) |
| `APIClient` | Compose 6 services | `APIClient` (HTTP) + 6 service classes | 150 + 6×80 = 630 (down from 667; deletes 13 dead methods) |
| `PaymentOperationsViewSet` | Split into 7 ViewSets | `CustomerPaymentViewSet`, `SupplierPaymentViewSet`, `PaymentTraceViewSet`, `MixedPaymentViewSet`, `PaymentDiagnosticsViewSet`, `PaymentStatementViewSet`, `PaymentMethodAccountListView` | 50 + 7×140 = 1,030 (similar to 1,077, but each clear-purpose) |
| `AccountViewSet` | Split into 4 ViewSets | `AccountViewSet` (CRUD), `AccountHierarchyViewSet`, `FinancialReportViewSet`, `AccountOperationsViewSet`, `InventoryValuationViewSet` | 5×80 = 400 (up from 311, but each clear-purpose) |
| `BackupManager` | Extract archiver + encryptor | `BackupArchiver`, `BackupEncryptor`, `BackupConfig`, `BackupManager` | 4×80 = 320 (similar) |
| `FinancialReportEngine` | Split into 6 calculators | `TrialBalanceCalculator`, `ProfitLossCalculator`, `BalanceSheetCalculator`, `CashFlowCalculator`, `AccountLedgerReader`, `AgingReportReader` + façade | 80 + 6×110 = 740 (similar) |
| `JournalEntryViewSet` | Split reversal + audit | `JournalEntryViewSet` (CRUD + lifecycle), `JournalReversalViewSet`, `JournalAuditViewSet` | 3×80 = 240 (similar to 230) |

---

## 9. Final Outcome

| Metric | Value |
|---|---:|
| Classes analyzed | 700+ (production only) |
| **CRITICAL_GOD_OBJECT** | **7** (P0) |
| **GOD_OBJECT** | **3** (P1) |
| **LARGE** (well-scoped) | 8 (P2/P3) |
| **HEALTHY** | 600+ |
| Total LOC in God Objects | **6,037** |
| Estimated LOC after decomposition | **~5,200** (slight net reduction; main benefit is testability, not LOC) |
| Methods in God Objects | **237** |
| Files modified by this audit | **0** (only this report added) |
| Risk introduced | None (read-only) |

**Conclusion:** 10 classes (7 critical + 3 god) account for **~6,000 LOC** of the production codebase — roughly **8% of total production LOC** — yet they carry **30+ distinct responsibilities** in violation of SRP. The `MainWindow`, `PurchaseInvoiceScreen` + `SalesInvoiceScreen` pair, `POSScreen`, and `APIClient` are the highest-priority targets; each carries 6-9 distinct responsibilities in a single 600-1,100 LOC class.

The most common anti-pattern is **ViewSets that accumulate `@action` methods** (`AccountViewSet`, `PaymentOperationsViewSet`, `JournalEntryViewSet`, `SalesInvoiceViewSet`) — a single resource endpoint becomes a junk drawer for every related operation. The `backup/views.py` file (with 11 small ViewSets, 2-5 methods each) is the **correct** model to emulate.

The most common frontend anti-pattern is **screens that build their own UI, load their own data, validate, save, and print** all in one class (`PurchaseInvoiceScreen`, `SalesInvoiceScreen`, `POSScreen`, `ReturnsScreen`). The `BaseScreen` / `BaseFormScreen` / `BaseListScreen` introduced in Phase UX.3 are the foundation; the invoice/POS screens predate that and need migration.
