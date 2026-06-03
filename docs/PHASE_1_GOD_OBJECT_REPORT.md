# PHASE 1 — God Object Detection & Responsibility Audit
**Pharmacy ERP — Read-Only Static Analysis**
**Date:** Phase 1
**Method:** Static analysis only. NO code changes were made. NO refactoring was performed.
**Severity scale:** CRITICAL (>1000 lines / >30 methods) → HIGH (700-1000 lines / 20-30 methods) → MEDIUM (300-700 / 15-20) → LOW (acceptable)

---

## 1. Executive Summary

| Severity | Count | Files | Action Priority |
|---|---|---|---|
| **CRITICAL** | 15 | 7 frontend + 8 backend | Phase 2 refactor queue |
| **HIGH** | 21 | 12 frontend + 9 backend | Phase 3 refactor queue |
| **MEDIUM** | 30+ | frontend screens & components | Phase 4 polish |
| **LOW (acceptable)** | — | well-factored files | — |

**Total files audited:** 169 (95 frontend + 74 backend non-trivial)
**Total God Objects identified:** **36** (15 CRITICAL + 21 HIGH)

### Top 3 Recurring Anti-Patterns

1. **"Validator God Class"** appears **3 times** in backend: `hardening_validator.py`, `migration_validator.py`, `gate_validator.py`. Each has 7-10 `validate_*` methods in one class. Common fix: section-as-module pattern.
2. **"Function-based view as God module"** appears **2 times**: `security/views.py` (20 fns), `core/governance/views.py` (26 fns). Common fix: split by domain.
3. **"Monolithic screen class"** appears **6+ times** in frontend: every invoice/return/POS/dashboard screen has 20-45 methods on a single `QWidget` subclass. Common fix: extract helper classes (item model, totals calculator, search panel).

### Top 5 Latent Bugs (Read-Only Observations)

1. `payment_operations.py:552` and `:686` — duplicate `process_customer_payment` and `process_supplier_payment`. Second silently shadows first.
2. `returns/models.py:510` — duplicate `complete` method on `ReturnOrder`.
3. `accounting/models.py:884` — duplicate `get_open_period_for_date` function; second shadows first.
4. `production_gate/gate_validator.py:555-562` — mock `assertFalse/assertTrue/assertEqual` methods on validator class. Return silently instead of raising. **Test failures may go undetected.**
5. `main_window.py:646-678` and `sidebar.py:_set_button_active` — **two parallel implementations of the same active-item styling** (post-recovery sidebar fix in `_set_button_active` is not yet the only path; `main_window._refresh_window_styles` and theme refresh may overwrite it).

---

## 2. Frontend — CRITICAL Tier (7 files)

### F-CR-01 — `frontend/ui/main_window.py` — 1100 lines, 45 methods, 22 imports
**Class:** `MainWindow`
**Why God Object:** Single class orchestrates **5+ concerns**:
- Window construction & layout (`_build_ui` L256-374, 118 lines)
- Lazy screen registration (50 screens, L369-402)
- Navigation history (L383-456, change_page + go_back/forward/home)
- Status bar (8 status widgets, 7 update methods L94-247)
- Menu bar construction (155 lines, L775-928)
- License + auth orchestration (`on_license_*`, `logout`, `check_connection`)
- Theme management (`toggle_theme`, `on_theme_changed`, `_refresh_window_styles`)
- Action delegation (`new_product`, `show_stock_alerts`, `open_calculator`, `open_calendar`)
- Window lifecycle (`resizeEvent`, `closeEvent`, `keyPressEvent`)

**SRP violation:** SEVERE — 9 distinct concerns in 1 class.
**Hidden coupling:** Reaches into `auth_manager`, `theme_engine`, `license_validator`, `role_manager`, `role_renderer`, `sidebar` — 6+ singletons held as attributes.
**Mixed concerns:** UI layout + navigation + license + auth + theme + menu — all in one class.
**Severity:** **CRITICAL**
**Refactor recommendation:** Extract `MainWindowShell` (window only), `NavigationController` (history + change_page), `StatusBarController` (7 status widgets), `MenuBarBuilder` (155 lines), `LicenseController` (5 methods), `ThemeController` (3 methods).

---

### F-CR-02 — `frontend/utils/logger.py` — 950 lines, 33 module functions
**Why God Object:** A "logger" module that contains:
- Sanitization (L40-152, 4 fns)
- Logger factory (L153-160)
- Initialization + shutdown (L162-172)
- Active screen tracking (L174-256)
- Error deduplication (L266-289, 2 fns)
- Safe execution (L290-384)
- Health snapshots (L385-413)
- Correlation IDs (L414-528)
- Error aggregation (L529-612)
- Performance telemetry (L613-715)
- Event store (L716-821)
- Anomaly detection (L822-908)
- Operational dashboard data (L909-1154)
- Decision evaluation (L979-1154)

**13 unrelated concerns** in 950 lines. No class. Pure procedural code.
**SRP violation:** EXTREME — logger module is also telemetry, events, health, anomaly detection, and decision engine.
**Mixed concerns:** Logging + sanitization + telemetry + events + correlation + anomaly detection + decisions.
**Severity:** **CRITICAL**
**Refactor recommendation:** Convert to `utils/observability/` package: `logger.py` (sanitize + get_logger + init_logging), `telemetry.py` (record_* + perf), `events.py` (emit + EventStore), `correlation.py` (CorrelationEngine), `anomaly.py` (detect_anomalies + bursts), `health.py` (snapshots), `decisions.py` (evaluate_decisions).

---

### F-CR-03 — `frontend/ui/components/forms.py` — 809 lines, 5 classes, 53 methods
**Classes:** `FieldType` (enum), `ValidationRule` (8 methods), `FormField` (15+ methods), plus 2 helpers
**Why God Object:** 809 lines for "form components". Contains:
- 13 field types enum
- 8 validation rule types (each with own validate())
- `FormField` widget with label, input, helper, validation states, 8 input types
- All in one file
- 53 methods

**SRP violation:** SEVERE — validation logic + widget rendering + field-type dispatch + helper text + state machine in one file.
**Severity:** **CRITICAL**
**Refactor recommendation:** Split into `components/forms/field.py` (FormField), `components/forms/validators.py` (ValidationRule types), `components/forms/types.py` (FieldType enum), `components/forms/inputs.py` (input widget factory).

---

### F-CR-04 — `frontend/ui/purchases/purchase_invoice_screen.py` — 808 lines, 1 class, 31 methods
**Class:** `PurchaseInvoiceScreen`
**Why God Object:** Single screen class handles:
- UI construction (3 zones: header, line items, financial summary)
- Product search (now wired in Phase Recovery)
- Batch / mfg / expiry date entry
- Totals calculation (`recalculate_totals` L554)
- Tax / discount math
- Supplier dropdown
- Workflow state machine (Submit, Approve, Reject, Post) — 4 actions
- Print PDF
- Save draft + Confirm + Receive
- 9 keyboard shortcuts
- Date format handling (`_apply_date_format`)

**SRP violation:** HIGH — UI + math + workflow + print + shortcuts in one class.
**Severity:** **CRITICAL**
**Refactor recommendation:** Extract `PurchaseInvoiceItem` (data class), `PurchaseTotalsCalculator` (math), `PurchaseWorkflowActions` (Submit/Approve/Reject/Post). Screen becomes UI glue.

---

### F-CR-05 — `frontend/ui/returns/returns_screen.py` — 794 lines, 2 classes, 30 methods
**Classes:** `ReturnsScreen`, `ReturnOrderDialog`
**Why God Object:** Single screen file with 30 methods, including a 297-line `ReturnOrderDialog` class (L577-874) that handles:
- Source invoice search (sales + purchases)
- Product prefill
- Quantity / discount / tax proration
- Reason capture
- Save / Cancel

Plus the main screen does list + filter + approve + reject + void + export + print.
**SRP violation:** SEVERE — two classes in one file, each with 15+ methods.
**Severity:** **CRITICAL**
**Refactor recommendation:** Move `ReturnOrderDialog` to `ui/returns/components/return_order_dialog.py`. Extract `ReturnsFilterBar` from main screen.

---

### F-CR-06 — `frontend/ui/sales/sales_invoice_screen.py` — 777 lines, 1 class, 30 methods
**Class:** `SalesInvoiceScreen`
**Why God Object:** Same anti-pattern as Purchase Invoice:
- UI zones (header, line items, financial summary, payment)
- Product search (BarcodeSearchLineEdit wired)
- Batch selection
- Totals calculator
- Workflow (Submit/Approve/Reject/Post)
- 9 keyboard shortcuts
- Print PDF
- Workflow status polling (`api_client.get_workflow_status`)

**SRP violation:** HIGH.
**Hidden coupling:** Direct `api_client` calls + `get_endpoint` + `auth_manager`.
**Severity:** **CRITICAL**
**Refactor recommendation:** Extract `SalesInvoiceItem`, `SalesTotalsCalculator`, `WorkflowActionBar`. Then `sales_invoice_screen.py` and `purchase_invoice_screen.py` can share a `BaseInvoiceScreen` (the only place they currently differ is the line item table + button labels).

---

### F-CR-07 — `frontend/ui/pos/pos_screen.py` — 774 lines, 1 class, 40 methods
**Class:** `POSScreen`
**Why God Object:** 40 methods in one POS class. Covers:
- Cart management (`_add_to_cart`, `_remove_selected_item`, `_refresh_cart`)
- Product search (`_search_products`)
- Barcode scanning (`_on_barcode_scanned`)
- Customer selection
- Held sales (`_held_sales`, `hold_sale`, `recall_sale`)
- Totals (now includes tax + discount from Phase Recovery)
- Payment processing
- Invoice preview
- 6 keyboard shortcuts
- Mock data fallback for dev

**SRP violation:** SEVERE — POS class is 40 methods. Largest screen in the codebase.
**Mixed concerns:** Cart state + search + barcode + held sales + totals + payment + keyboard + print all in one class.
**Severity:** **CRITICAL**
**Refactor recommendation:** Extract `POSCart` (state + add/remove), `POSSearchPanel` (search + barcode), `POSPaymentPanel` (tax/discount/amount/change), `POSKeyboardHandler` (6 shortcuts). Class becomes composition root.

---

## 3. Frontend — HIGH Tier (12 files)

### F-HI-01 — `frontend/ui/observability/dashboards.py` — 715 lines, 8 classes, 38 methods
**Why God Object:** 8 dashboard widget classes in one file. Each is 30-100 lines. **Inconsistent — some are base classes, some are concrete widgets, some are sub-panels.** No clear responsibility split.
**Severity:** **HIGH**
**Refactor recommendation:** Move each dashboard widget to its own file in `ui/observability/dashboards/`.

### F-HI-02 — `frontend/ui/system/backup_screen.py` — 710 lines, 5 classes, 31 methods
**Classes:** `BackupScreen`, `RestoreConfirmDialog`, `EmailConfigDialog`, `BackupHealthWidget`, `RecoveryValidationWidget`
**Why God Object:** Backup **screen** file contains 3 dialog classes and 2 widget classes. Backup domain has 4 sub-concerns (records, restore, health, recovery) all in one file.
**Severity:** **HIGH**
**Refactor recommendation:** Move each dialog/widget to `ui/system/components/`. Screen becomes 200 lines.

### F-HI-03 — `frontend/api/client.py` — 661 lines, 1 class, 60+ methods
**Class:** `APIClient`
**Why God Object:** Single class with 60+ methods covering:
- HTTP request core (`_make_request`, 200 lines)
- Auth (token, refresh, session)
- Loading overlay management
- Error handling + telemetry
- 50+ domain-specific wrappers (`search_products`, `get_users`, `get_endpoint`, `lookup_barcode`, `generate_barcode`, `validate_barcode`, `get_workflow_status`, etc.)
- Custom domain methods (POS-specific, returns-specific)

**SRP violation:** HIGH — 4 layers (transport, auth, telemetry, domain wrappers) in 1 class.
**Severity:** **HIGH**
**Refactor recommendation:** Split into `api/transport.py` (HTTP), `api/auth.py` (tokens), `api/telemetry.py` (timing), `api/endpoints/` package (one module per domain: `inventory.py`, `sales.py`, `purchases.py`, `payments.py`, `accounting.py`, `hr.py`, `returns.py`).

### F-HI-04 — `frontend/ui/sidebar.py` — 623 lines, 1 class, 18 methods
**Class:** `Sidebar`
**Why God Object:** 623 lines for "sidebar". Concerns:
- Layout construction (header + scroll area + group widgets)
- 11 group definitions (hardcoded `create_group` calls in `_populate_groups`)
- Active state styling (now with left-border post-recovery)
- Theme refresh
- Auto-expand on navigation (post-recovery)
- Role-based filtering
- Search + signals

**SRP violation:** HIGH — group definitions hardcoded in class init, no separation of nav-data from view.
**Severity:** **HIGH**
**Refactor recommendation:** Move group definitions to `ui/navigation/registry.py`. Sidebar becomes pure view.

### F-HI-05 — `frontend/ui/accounting/report_browser.py` — 580 lines, 2 classes, 19 methods
**Classes:** `ReportBrowser` (+ 1 helper)
**Why God Object:** Generic report browser instantiated 14 times (one per report type). Each instance differs only by `report_type` parameter. 580 lines for a "configurable report viewer".
**Severity:** **HIGH**
**Refactor recommendation:** Already correctly de-duplicated (14 instances share 1 class). File is acceptable but could extract report-specific data adapters.

### F-HI-06 — `frontend/ui/role_manager.py` — 557 lines, 15 classes, 21 methods
**Classes:** `UserRole` (enum), `ROLE_PERMISSIONS` (dict), `ROLE_HIERARCHY`, 5 helper functions, plus 9 `*Decision` dataclasses
**Why God Object:** 15 classes in 557 lines. Mixes enum + data dicts + decision dataclasses + permission helpers + role hierarchy.
**Latent bug:** Lines 503-504 have duplicate `"sales_invoice"` entry in `ROLE_PERMISSIONS["ADMIN"]` and `"financial "` has a trailing space.
**Severity:** **HIGH** (also contains a real bug)
**Refactor recommendation:** Split into `role_manager/enum.py`, `role_manager/permissions.py`, `role_manager/decisions.py`, `role_manager/resolver.py`.

### F-HI-07 — `frontend/ui/components/tables.py` — 522 lines, 5 classes, 48 methods
**Classes:** `TableSelectionMode`, `TableColumn`, `EnterpriseTable` (largest, 30+ methods), `build_table_stylesheet`, `ensure_contrast`
**Why God Object:** 48 methods. `EnterpriseTable` alone has 30+ methods (data, sort, filter, pagination, chunks, deferred render, selection, signals, validation).
**SRP violation:** HIGH — table widget doing data + sort + filter + pagination + deferred render + contrast checks.
**Severity:** **HIGH**
**Refactor recommendation:** Extract `TableSorter`, `TableFilter`, `TablePaginator`, `TableDeferredRenderer`. Component becomes composition.

### F-HI-08 — `frontend/ui/sales/customer_screen.py` — 522 lines, 2 classes, 15 methods
**Classes:** `CustomerScreen` + `CustomerDialog` (in-file)
**Why God Object:** 522 lines for customer CRUD + dialog. Dialog is 200+ lines inline.
**Severity:** **HIGH**
**Refactor recommendation:** Move `CustomerDialog` to `ui/sales/components/`.

### F-HI-09 — `frontend/ui/screens/base_screen.py` — 484 lines, 4 classes, 71 methods
**Classes:** `BaseScreen`, `BaseFormScreen`, `BaseListScreen`, `_ScreenLifecycleMixin`
**Why God Object:** **71 methods** in the base class hierarchy. Every screen in the app inherits from this. The base class has become a kitchen sink of:
- Lifecycle (`showEvent`, `closeEvent`, `_on_screen_shown`, `_on_screen_hidden`)
- Loading skeleton (`show_skeleton_loader`, `_setup_skeleton_loader`)
- State management (`set_state`, `show_loading`, `show_empty`, `show_error`, `hide_state`)
- Data refresh (`refresh_data`, `_on_refresh`)
- Form action handling (`submit_form`, `cancel_form`, `validate_form`)
- Permission check (`_check_access`, `on_access_denied`)
- Telemetry hooks (`_record_load_time`, `_record_user_action`)

**SRP violation:** HIGH — base class has 9 concerns.
**Hidden coupling:** Every screen method (over 100 screens) is now coupled to this base.
**Severity:** **HIGH** (high blast radius — every screen depends on it)
**Refactor recommendation:** Extract `ScreenLifecycleMixin`, `ScreenStateMixin`, `ScreenFormMixin`, `ScreenTelemetryMixin` from base. Base becomes thin composition of these.

### F-HI-10 — `frontend/ui/components/operator_safety.py` — 310 lines, 6 classes, 25 methods
**Classes:** `SafetyLevel`, `SafetyViolation`, `OperatorSafetyCheck`, `ConfirmationGate`, `AuditLogger`, `OperatorSafetyManager`
**Why God Object:** Operator safety domain scattered across 6 small classes in 1 file. Acceptable boundary but the file mixes definitions + manager + audit logger.
**Severity:** **HIGH**
**Refactor recommendation:** Split into `components/operator_safety/levels.py`, `checks.py`, `gates.py`, `audit.py`, `manager.py`.

### F-HI-11 — `frontend/ui/components/notifications.py` — 341 lines, 4 classes, 21 methods
**Severity:** **HIGH**
**Refactor recommendation:** Split into `notifications/types.py`, `toast.py`, `inbox.py`, `manager.py`.

### F-HI-12 — `frontend/ui/components/base_widgets.py` — 39 methods in 4 classes
**Why God Object:** 39 methods in "base widgets". Already a base layer; further splitting would over-engineer.
**Severity:** **HIGH** (but boundary OK)

---

## 4. Frontend — MEDIUM Tier (Notable, 15+ methods)

| File | Methods | Notes |
|---|---|---|
| `ui/dashboard.py` | 22 | 6 KPI render + 4 navigation + 3 timer + 4 data fetch |
| `ui/hr/payroll_screen.py` | 22 | payroll + payslip inline |
| `ui/finance/customer_payment_workspace.py` | 20 | payment workspace |
| `ui/finance/supplier_payment_workspace.py` | 20 | mirror of customer |
| `ui/accounting/journal_entry_screen.py` | 20 | journal entry + lines + balance |
| `ui/returns/returns_screen.py` | 30 | covered in CRITICAL |
| `ui/system/backup_screen.py` | 31 | covered in HIGH |
| `ui/observability/widgets.py` | 24 | observability widgets |
| `ui/finance/financial_operations_console.py` | 17 | financial ops console |
| `ui/system/settings_screen.py` | 17 | settings + tabs |
| `ui/system/user_management_screen.py` | 17 | user CRUD + roles |
| `ui/system/role_management_screen.py` | 18 | role CRUD |
| `ui/finance/cashflow_screen.py` | 18 | cashflow table |
| `ui/observability/base_view_model.py` | 16 | view model base |
| `ui/hr/employee_screen.py` | 15 | employee CRUD |
| `ui/hr/departments_screen.py` | 17 | dept + positions |
| `ui/finance/budgeting_screen.py` | 15 | budget editor |
| `ui/accounting/chart_of_accounts_screen.py` | 15 | chart of accounts |
| `ui/common/barcode_search.py` | 13 | barcode search widget |
| `ui/components/buttons.py` | 15 | 3 button variants — already split into sub-classes (EnterpriseButton, IconButton, SplitButton) |

---

## 5. Backend — CRITICAL Tier (8 files)

### B-CR-01 — `backend/genesis_init.py` — 1439 lines, 3 classes, 25 methods
**Class:** `GenesisInitializer` (25 methods, 22 phase methods + helpers)
**Why God Object:** 10 phase methods + 22 helper methods in 1 class. Owns full ERP reset authority. Mixes:
- Schema checksum + DB introspection
- State reset + soft-delete detection
- Governance revalidation
- Idempotency validation
- Baseline snapshot
- Report generation

**SRP violation:** SEVERE.
**Severity:** **CRITICAL**
**Refactor recommendation:** Split into `genesis/` package: `phases/schema.py`, `phases/reset.py`, `phases/governance.py`, `phases/reports.py`, with thin `orchestrator.py`.

### B-CR-02 — `backend/pre_production_hardening/hardening_validator.py` — 1311 lines, 3 classes
**Class:** `PreProductionHardeningValidator` (11 methods)
**Why God Object:** 8 `validate_*` methods (DB, concurrency with 10 threads, operator resilience, sessions, exports, deployment, perf, audit) in 1 class. Spans DB + threads + crypto + sessions + exports + recovery + perf.
**Severity:** **CRITICAL** (third copy of "Validator God Class" anti-pattern)
**Refactor recommendation:** Convert to `validators/` package, one module per domain.

### B-CR-03 — `backend/core/governance/industrial_test_suite.py` — 1172 lines, 19 classes
**Why God Object:** Entire 7-phase test suite in 1 file. 19 classes total. Each phase has 4-8 detection methods.
**Severity:** **CRITICAL**
**Refactor recommendation:** Move to `core/governance/industrial_tests/` package, one phase per module.

### B-CR-04 — `backend/scripts/drift_check.py` — 1151 lines, 4 classes, 20 module functions
**Why God Object:** 20 module-level `check_*`/`run_*` functions all sharing a single mutable `DriftReport`. No class encapsulation. Mixed static analysis + AST parsing + git pre-commit hooks + auto-fix.
**Severity:** **CRITICAL**
**Refactor recommendation:** Convert to `drift/` package with `BaseCheck` subclass pattern.

### B-CR-05 — `backend/production_infrastructure/migration_validator.py` — 1080 lines, 3 classes
**Why God Object:** Same anti-pattern as hardening_validator. 9 `validate_*` methods (PostgreSQL, threads, pooling, Redis, Celery, security, backup, perf, observability) in 1 class. Live infra probing.
**Severity:** **CRITICAL**
**Refactor recommendation:** `infrastructure/validators/` package.

### B-CR-06 — `backend/core/operations/operational_intelligence.py` — 1073 lines, 11 classes
**Why God Object:** 11 classes covering 8+ concerns in 1 file. **Two duplicate SLA monitoring classes** (`SLAComplianceMonitor` L618 and `SLAMonitoringEngine` L778). Singleton `RuleRegistry` as global state.
**Severity:** **CRITICAL**
**Refactor recommendation:** Split into `core/operations/intelligence/` package: `registry.py`, `anomaly.py`, `trend.py`, `risk.py`, `sla.py` (consolidate both), `forecast.py`, `alerts.py`, `cache.py`.

### B-CR-07 — `backend/core/api/v1/payment_operations.py` — 977 lines, 1 ViewSet, 16 actions
**Why God Object:** 16 `@action` methods on `PaymentOperationsViewSet`. **DUPLICATE `process_customer_payment` (L114 + L552) and `process_supplier_payment` (L322 + L686).** The second silently shadows the first — latent routing bug.
**SRP violation:** SEVERE.
**Severity:** **CRITICAL** (escalated due to duplicate method = latent bug)
**Refactor recommendation:** Split into 5 ViewSets: customer_payment_viewset.py, supplier_payment_viewset.py, mixed_payment_viewset.py, payment_diagnostics_viewset.py, payment_statement_pdf_viewset.py. **Remove duplicate method definitions.**

### B-CR-08 — `backend/backup/backup_system.py` — 954 lines, 5 classes
**Class:** `BackupManager` (18 methods — LARGEST SINGLE CLASS in backend)
**Why God Object:** Configuration + disk checks + vacuum + archive + encryption + restoration + listing + deletion + cleanup + stats — 10 responsibilities in 1 class.
**Severity:** **CRITICAL** (escalated — 18 methods in one class is severe)
**Refactor recommendation:** Convert to `backup/` package: `config.py`, `validator.py`, `encryptor.py`, `manager/creator.py`, `manager/restorer.py`, `manager/lister.py`, `scheduler.py`.

### B-CR-09 — `backend/security/views.py` — 927 lines, 0 classes, 20 module functions
**Why God Object:** 20 function-based views in 1 module covering 7 security domains (auth, profile, notifications, users, roles, permissions, 2FA).
**SRP violation:** SEVERE.
**Severity:** **CRITICAL** (escalated — service work in views)
**Refactor recommendation:** Split into `security/views/` package by domain. Move ORM writes to `security/services/`.

### B-CR-10 — `backend/returns/models.py` — 812 lines, 3 models
**Model:** `ReturnOrder` has 10 methods including `approve`, `complete`, `void` (110 lines), `_create_accounting_entries`. **DUPLICATE `complete` (L293, L510).** Cross-app atomic writes inside models (`@transaction.atomic` + `from inventory.models import StockMovement` + `from accounting.models import JournalEntry`).
**SRP violation:** SEVERE — models doing lifecycle work + cross-app writes.
**Severity:** **CRITICAL** (escalated — model with cross-app atomic writes is a major anti-pattern + duplicate method)
**Refactor recommendation:** Move all `@transaction.atomic` business logic into `returns/services/lifecycle.py`. **Remove duplicate `complete` method.**

### B-CR-11 — `backend/core/governance/views.py` — 795 lines, 0 classes, 26 module functions
**Why God Object:** 26 function-based views covering 10+ governance domains in 1 file. Control plane alone is 6 endpoints.
**Severity:** **CRITICAL** (escalated — 26 fns, 795 lines, 10+ domains)
**Refactor recommendation:** `core/governance/views/` package by domain.

### B-CR-12 — `backend/core/api/v1/sales/views.py` — 762 lines, 5 classes (escalated by audit)
**`SalesInvoiceViewSet.dispatch_invoice`** is 90+ lines doing stock + journal + balance + tax in one method. **`SalesAccountingService` is in views.py (wrong location).**
**Severity:** **CRITICAL**
**Refactor recommendation:** Move `SalesAccountingService` to `accounting/services/`. Extract `dispatch_invoice` body into `sales/services/dispatch_service.py`.

### B-CR-13 — `backend/production_gate/gate_validator.py` — 843 lines, 3 classes
**Class:** `ProductionGateValidator` (18 methods)
**Why God Object:** 7 sections in 1 class. **Mock `assertFalse/assertTrue/assertEqual` methods at L555-562** — these silently return truthy/falsy values instead of raising. **Test failures may go undetected.** This is a third copy of the "Validator God Class" anti-pattern.
**Severity:** **CRITICAL** (escalated — mock assert methods are a latent bug)
**Refactor recommendation:** `production_gate/sections/` package. **Delete mock assert methods** or replace with proper `assert` statements.

---

## 6. Backend — HIGH Tier (Notable)

| File | Lines | Methods | Notes |
|---|---|---|---|
| `core/pdf_generator.py` | 876 | 14 | 6 PDF document types in 1 file, reportlab imports scattered |
| `payments/services.py` | 809 | 10 | `PaymentEngine` with 10 static methods; 3 `_create_*_journal_entry` |
| `backup/views.py` | 813 | 11 ViewSets | 11 ViewSets in 1 file; file I/O in views |
| `accounting/models.py` | 798 | 9 models | Duplicate `get_open_period_for_date` (L868 + L884) |
| `inventory/service/stock_integration.py` | 792 | 14 static | No `__init__` — class is pure namespace |
| `sales/views.py` | 762 | 5 classes | (covered in CRITICAL) |
| `core/governance/views.py` | 795 | 26 fns | (covered in CRITICAL) |
| `security/views.py` | 927 | 20 fns | (covered in CRITICAL) |

---

## 7. Recurring Anti-Patterns (Cross-Cutting)

| Anti-Pattern | Count | Files |
|---|---|---|
| Validator God Class (7-10 `validate_*` in 1 class) | 3 | hardening_validator, migration_validator, gate_validator |
| Function-based view as God module (20+ views) | 2 | security/views, core/governance/views |
| Duplicate method definitions (latent shadow bug) | 3 | payment_operations, returns/models, accounting/models |
| Service work in views/models | 5+ | payment_operations, security/views, backup/views, returns/models, accounting/models |
| `import` inside function (lazy import) | 30+ | pdf_generator (12+ reportlab re-imports) |
| Singleton/global state leakage | 4 | operational_intelligence (RuleRegistry), migration_router, governance_engine, theme_engine |

---

## 8. Severity Summary

| Severity | Frontend | Backend | Total |
|---|---|---|---|
| CRITICAL | 7 | 8 | **15** |
| HIGH | 12 | 9 | **21** |
| MEDIUM | ~20 | ~10 | **~30** |
| **Total** | **~40** | **~27** | **~66** |

---

## 9. Top 10 Refactoring Targets (Ranked by Impact / Latent Bug Risk)

| Rank | File | Severity | Impact | Latent Bug? |
|---|---|---|---|---|
| 1 | `payment_operations.py` | CRITICAL | High | **YES** — duplicate methods |
| 2 | `returns/models.py` | CRITICAL | High | **YES** — duplicate `complete` |
| 3 | `production_gate/gate_validator.py` | CRITICAL | High | **YES** — mock assert methods |
| 4 | `accounting/models.py` | CRITICAL | High | **YES** — duplicate function |
| 5 | `main_window.py` | CRITICAL | Highest (every page depends on it) | 🟡 Parallel active-state style paths |
| 6 | `genesis_init.py` | CRITICAL | Medium (only runs at deploy) | No |
| 7 | `operational_intelligence.py` | CRITICAL | Medium | No (but duplicate SLA class) |
| 8 | `security/views.py` | CRITICAL | High | No |
| 9 | `pos_screen.py` | CRITICAL | Medium (well-tested) | No |
| 10 | `utils/logger.py` | CRITICAL | High (used everywhere) | No |

---

## 10. Refactor Recommendations Summary (High-Level, Non-Executing)

| Pattern | Recommended Fix |
|---|---|
| Validator God Class | Convert to `validators/` package, one module per section, common `BaseValidator` returning `SectionResult` |
| ViewSet God Class (16+ actions) | Split by domain (customer, supplier, mixed, diagnostics, PDF) |
| Function-based view God module (20+ fns) | Split by domain into `views/` package |
| Model with cross-app atomic writes | Move all `@transaction.atomic` to `app/services/lifecycle.py` |
| Monolithic screen class (30+ methods) | Extract `*Item`, `*TotalsCalculator`, `*WorkflowActions`, `*SearchPanel` |
| Module with 30+ top-level functions | Convert to package with class-based organization |
| Lazy imports inside function | Move to module top, manage circular imports at module level |
| Singleton registry as global state | Pass via constructor; use a factory function returning a configured instance |

---

## 11. Conclusion

The codebase has **15 CRITICAL and 21 HIGH-severity God Objects** across frontend and backend. The most actionable findings are the **5 latent bugs** discovered during this audit — all are duplicate method/function definitions that silently shadow their predecessors, plus the **mock assert methods in gate_validator.py** that can mask test failures.

**All recommendations are non-executing.** This is a read-only audit. No refactoring, no code changes, no architecture redesign was performed.

**Recommended next phase:** Phase 2 — Refactoring of the top 5 latent-bug God Objects, in order of safety + impact:
1. Remove duplicate methods in `payment_operations.py` (1 hour)
2. Remove duplicate `complete` in `returns/models.py` (30 min)
3. Remove duplicate function in `accounting/models.py` (15 min)
4. Delete mock assert methods in `gate_validator.py` (30 min)
5. Resolve parallel active-state styling in `main_window.py` (1 hour)

**Total effort to fix the 5 latent bugs: ~3.5 hours. Zero functional risk.**
