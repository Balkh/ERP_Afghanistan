# ENDPOINT-SCREEN COVERAGE REPORT — Pharmacy ERP

## Coverage Summary

| Classification | Count | Percentage |
|----------------|-------|------------|
| FULL_UI_COVERAGE | 25 | 71% |
| PARTIAL_UI_COVERAGE | 7 | 20% |
| NO_UI_COVERAGE | 3 | 9% |
| **Total backend modules** | **35** | **100%** |

---

## FULL_UI_COVERAGE (25 modules)

| Module | Endpoints | Frontend Screens |
|--------|-----------|-----------------|
| Auth/Security | 15+ | login_screen, totp_setup_dialog, user_management_screen, role_management_screen |
| Inventory | 11+ | product_screen, category_screen, warehouse_screen, batch_screen, POS |
| Sales | 4+ | customer_screen, sales_invoice_screen, fifo_allocation_dialog, customer_payment_workspace |
| Purchases | 4+ | supplier_screen, purchase_invoice_screen, supplier_payment_workspace |
| Returns | 2+ | returns_screen, reconciliation_screen |
| Accounting | 12+ | chart_of_accounts, journal_entry, account_ledger, report_browser, financial_integrity, financial_audit_log |
| Payments | 5+ | payment_screen, customer_payment_workspace, supplier_payment_workspace, payment_allocation_explorer, financial_operations_console |
| Expenses | 1+ | expense_screen |
| Licensing | 3 | licensing_screen, activation_screen, license_status_screen |
| Backup | 11+ | backup_screen, email_config_dialog |
| HR | 12+ | employee_screen, attendance_screen, leave_screen, payroll_screen, report_screens |
| Payroll | 9+ | payroll_screen, report_screens |
| Fixed Assets | 4 | fixed_assets_screen |
| Budgeting | 2 | budgeting_screen |
| Tax | 5 | tax_screen |
| Cost Centers | 3 | cost_centers_screen |
| Entities | 3 | entity_management_screen |
| Audit | 2 | audit_screen |
| Cashflow | 3 | cashflow_screen |
| Core | 6+ | settings_screen, company_profile_screen, invoice_template_manager |
| Observability v1 | 11 | observability_console (9 tabs) |
| v1 Governance | 8+ | approval_screen + typed GovernanceAPIClient |
| v1 Truth | 14 | event_store_screen + typed TruthAPIClient |
| v1 Observability | 13 | typed ObservabilityAPIClient + console |
| v1 Intelligence | 12 | typed IntelligenceAPIClient + investigation screens |
| Fin Control Tower | 4 | financial_control_tower_screen |

---

## PARTIAL_UI_COVERAGE (7 modules)

### 1. Workflows (`/api/workflows/`)
- **Backend**: 7+ endpoints (instances, chains, requests, status, action, pending, approve)
- **Frontend**: workflow_intelligence_screen, approval_screen, workflow_execution_screen
- **Gap**: Chains, requests, and action endpoints lack dedicated sidebar screen; some consumed through governance API instead
- **Severity**: MEDIUM — functional but workflows not first-class in navigation

### 2. Ops/Health (`/api/ops/`, `/api/health/`)
- **Backend**: 20+ endpoints (health, integrity, alerts, bad-requests, slow-requests, scalability, guardrails, etc.)
- **Frontend**: Health check used in main_window, control_center_screen aggregates some data
- **Gap**: Individual ops endpoints (bad-requests, slow-requests, guardrails, sampling, stability, scalability) have NO direct UI consumer
- **Severity**: LOW — aggregated by control center, but granular debug UIs missing

### 3. Control Center (`/api/control-center/`)
- **Backend**: 10+ endpoints (main, stats, health, financial, inventory, ops, hr, intelligence, signals, decisions, jobs)
- **Frontend**: Dashboard aggregates some, control_center_screen exists
- **Gap**: Signals, decisions, and jobs sub-endpoints lack dedicated detailed workspace UIs
- **Severity**: LOW — main dashboard covers the essentials

### 4. v1 Autonomous (`/api/v1/autonomous/`)
- **Backend**: 8 endpoints (insights, risk-summary, decision-options, forecast, anomaly-warnings, report, recommendations)
- **Frontend**: 4 screens exist (master_dashboard, forecast_dashboard, decision_options_screen, anomaly_warning_center) but NO direct typed API client or confirmed API calls
- **Gap**: Screens appear to be speculative — no active API consumption
- **Severity**: HIGH — screens exist but appear disconnected from backend

### 5. v1 Financial Intelligence (`/api/v1/financial-intelligence/`)
- **Backend**: 18 comprehensive endpoints (anomalies, reconciliation, credit-risk, cashflow, explain, trace, health)
- **Frontend**: Related screens (financial_integrity, financial_operations_console) do NOT directly consume FICL API
- **Gap**: Rich backend module with zero direct UI consumption
- **Severity**: MEDIUM — related screens exist but don't leverage the API

### 6. v1 Payment Operations (`/api/v1/payment-operations/`)
- **Backend**: Full CRUD ViewSet
- **Frontend**: Customer/supplier payment workspaces still use older `/api/payments/` and `/api/sales/` endpoints
- **Gap**: New API not yet consumed by any screen
- **Severity**: LOW — old API still functional

### 7. Status Bar / Connection Health
- **Backend**: `/api/health/` endpoint
- **Frontend**: main_window status bar shows connection status, periodic check every 30s
- **Gap**: No health detail view, no retry/error detail in status bar
- **Severity**: LOW — functional but could be richer

---

## NO_UI_COVERAGE (3 modules)

### 1. Jobs (`/api/jobs/`) — ⚠️ NEEDS SCREEN
- **Backend endpoints**: `jobs/`, `scheduled/`, `job/<int>/`, `job/<int>/action/`, `stats/`, `run-scheduled/`
- **Frontend screens**: NONE
- **Impact**: Background job management (scheduled tasks, job monitoring, retry) has zero UI
- **Priority**: HIGH — users cannot monitor or manage background jobs

### 2. Insurance (`/api/insurance/`) — ⚠️ NEEDS SCREEN
- **Backend endpoints**: `providers/`, `policies/`, `claims/`
- **Frontend screens**: NONE
- **Impact**: Insurance module (providers, policies, claims management) invisible to users
- **Priority**: MEDIUM — depends on whether insurance is an active requirement

### 3. Integration (`/api/integration/`)
- **Backend endpoints**: NONE (empty urlpatterns — placeholder module)
- **Frontend screens**: NONE
- **Impact**: Placeholder module, no real functionality
- **Priority**: LOW — not a real module yet

---

## API UNUSED — Endpoints Not Consumed by Any Screen

Even within modules marked FULL_UI_COVERAGE, individual endpoints are not consumed:

| Endpoint | Module | Reason |
|----------|--------|--------|
| `POST /api/sales/payments/fix_balances/` | Sales | Auto-fix tool, no UI entry point |
| `GET /api/sales/invoices/pending_credit_approvals/` | Sales | Credit approval workflow UI missing |
| `POST /api/sales/invoices/approve_credit/` | Sales | No approve/reject action in invoice screen |
| `GET /api/accounting/accounts/{pk}/descendants/` | Accounting | Hierarchy navigation not exposed |
| `GET /api/accounting/accounts/{pk}/ancestors/` | Accounting | Hierarchy navigation not exposed |
| `POST /api/accounting/journal-entries/{pk}/safe_reverse/` | Accounting | Reversal UI exists but safe_reverse flow not connected |
| `POST /api/accounting/fiscal-periods/{pk}/close/` | Accounting | Period close not exposed in UI |
| `POST /api/accounting/fiscal-periods/{pk}/lock/` | Accounting | Period lock not exposed in UI |
| `GET /api/inventory/batches/fifo_order/` | Inventory | FIFO/FEFO order viewing not exposed |
| `GET /api/inventory/batches/fefo_order/` | Inventory | FIFO/FEFO order viewing not exposed |
| `POST /api/inventory/stock/allocate/` | Inventory | Manual stock allocation not exposed |
| `POST /api/budgets/budgets/{pk}/approve/` | Budgeting | Budget approval workflow not exposed |
| `POST /api/budgets/budgets/{pk}/lock/` | Budgeting | Budget lock not exposed |
| `POST /api/budgets/budgets/{pk}/reject/` | Budgeting | Budget reject not exposed |
| `POST /api/budgets/lines/{pk}/transfer/` | Budgeting | Budget line transfer not exposed |
| `POST /api/tax/rates/{pk}/activate/` | Tax | Tax rate activate/deactivate not exposed |
| `POST /api/payroll/generate/` | Payroll | Payroll generate not in UI |
| `POST /api/payroll/approve/` | Payroll | Payroll approve not in UI |
| `POST /api/assets/assets/{pk}/activate/` | Fixed Assets | Asset lifecycle actions not exposed |
| `POST /api/assets/assets/{pk}/decommission/` | Fixed Assets | Asset lifecycle actions not exposed |
| `POST /api/assets/assets/{pk}/impair/` | Fixed Assets | Asset impairment not exposed |
| `POST /api/assets/assets/run_depreciation/` | Fixed Assets | Bulk depreciation run not exposed |

---

## CRITICAL FINDING: 17 Token Interpolation Bugs

Component files use `setStyleSheet("""...{COLOR_*}...""")` with **regular strings** (not f-strings). The tokens are never resolved, appearing as literal text in QSS. Qt silently ignores invalid properties.

| File | Lines | Broken Tokens |
|------|-------|---------------|
| `ui/components/buttons.py` | 209-221 | COLOR_PRIMARY, COLOR_TEXT_ON_PRIMARY, SPACING_SM, BORDER_RADIUS_SM |
| `ui/components/dialogs.py` | 91-95, 133-142, 184-191 | COLOR_BG_DIALOG, COLOR_HEADER_DARK, COLOR_BG_MAIN, COLOR_FORM_FOOTER_BORDER |
| `ui/components/kpi_cards.py` | 78-85, 121-128, 158-164, 213-223 | COLOR_BG_ELEVATED, COLOR_BORDER, BORDER_RADIUS, all colors |
| `ui/components/state_helper.py` | 57-63, 104-110, 150-161, 187-193, 229-239 | COLOR_BG_SURFACE, COLOR_BORDER, COLOR_PRIMARY, COLOR_DANGER |
| `ui/components/navigation_header.py` | 42-67 | 10+ tokens including COLOR_TEXT_PRIMARY, COLOR_BORDER, COLOR_BG_ELEVATED |
| `ui/components/notifications.py` | 109-115, 156-167 | bg_color, text_color, COLOR tokens |
| `ui/components/loading_spinner.py` | 69-75 | COLOR_PRIMARY, TEXT_BODY |

**Impact**: ALL KPICard styling, ALL Dialog backgrounds, ALL StateHelper overlays, ALL NotificationItem badges, and NavigationHeader styling are completely broken. Colors never render as intended.

---

## LAYER VIOLATION: 21 Registered Screens Bypass BaseScreen

Per AGENTS.md: "ALL new screens MUST inherit from BaseScreen."

| Screen | File | Current Base |
|--------|------|-------------|
| Dashboard | `ui/dashboard.py` | QWidget |
| SalesInvoiceScreen | `ui/sales/sales_invoice_screen.py` | QWidget |
| PurchaseInvoiceScreen | `ui/purchases/purchase_invoice_screen.py` | QWidget |
| POSScreen | `ui/pos/pos_screen.py` | QWidget |
| ChartOfAccountsScreen | `ui/accounting/chart_of_accounts_screen.py` | QFrame |
| JournalEntryScreen | `ui/accounting/journal_entry_screen.py` | QFrame |
| AccountLedgerScreen | `ui/accounting/account_ledger_screen.py` | QFrame |
| ReportBrowser | `ui/accounting/report_browser.py` | QWidget |
| FinancialIntegrityScreen | `ui/accounting/financial_integrity_screen.py` | QWidget |
| FinancialAuditLogScreen | `ui/accounting/financial_audit_log_screen.py` | QWidget |
| PaymentScreen | `ui/finance/payment_screen.py` | QWidget |
| CustomerPaymentWorkspace | `ui/finance/customer_payment_workspace.py` | QWidget |
| SupplierPaymentWorkspace | `ui/finance/supplier_payment_workspace.py` | QWidget |
| PaymentAllocationExplorer | `ui/finance/payment_allocation_explorer.py` | QWidget |
| ReturnsExplainabilityScreen | `ui/finance/returns_explainability.py` | QWidget |
| JournalReversalExplorer | `ui/finance/journal_reversal_explorer.py` | QWidget |
| FinancialOperationsConsole | `ui/finance/financial_operations_console.py` | QWidget |
| OperationsDashboard | `ui/control_tower/operations_dashboard.py` | QWidget |
| ObservabilityConsole | `ui/observability/observability_console.py` | QWidget |
| DecisionWorkspace | `ui/causal_scoring/decision_workspace.py` | QWidget |
| AnalyticsWorkspace | `ui/system/analytics_workspace.py` | QWidget |

These screens miss: lifecycle hooks (show/hide events), state machine (loading/ready/error/empty), auto-refresh, data caching, navigation_requested signal.
