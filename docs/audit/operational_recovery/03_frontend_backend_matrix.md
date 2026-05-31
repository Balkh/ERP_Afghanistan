# 03 — Frontend↔Backend Integration Matrix

**Audit Date:** 2026-05-31
**Scope:** All 45 screens with API integration
**Methodology:** Verify each screen's API calls against backend URL configurations

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Screens audited | 45 |
| CONNECTED | 33 (73%) |
| PARTIAL | 8 (18%) |
| DISCONNECTED | 4 (9%) |
| Screens with NO API calls | 3 |
| Hardcoded URLs found | 6 |
| Backend endpoints missing | 3 |

---

## Integration Matrix

| # | Screen | API Endpoints Called | Backend Exists | Client Method | Error Handle | Status |
|---|--------|---------------------|----------------|---------------|--------------|--------|
| 1 | Dashboard | `/api/control-center/`, `/api/sales/customers/`, `/api/purchases/suppliers/` | YES | YES | PARTIAL (print only) | CONNECTED |
| 2 | ProductScreen | `GET/DELETE /api/inventory/products/` | YES | YES | YES | CONNECTED |
| 3 | CategoryScreen | `GET/DELETE /api/inventory/categories/` | YES | YES | YES | CONNECTED |
| 4 | WarehouseScreen | `GET/DELETE /api/inventory/warehouses/` | YES | YES | YES | CONNECTED |
| 5 | BatchScreen | `GET/DELETE /api/inventory/batches/` | YES | YES | YES | CONNECTED |
| 6 | SalesInvoiceScreen | `GET /api/sales/customers/`, `POST /api/sales/invoices/`, confirm, dispatch, workflows | YES | YES | YES | CONNECTED |
| 7 | CustomerScreen | `GET/POST/DELETE /api/sales/customers/` | YES | YES | YES | CONNECTED |
| 8 | PurchaseInvoiceScreen | `GET /api/purchases/suppliers/`, `POST /api/purchases/invoices/`, confirm, receive, workflows | YES | YES | YES | CONNECTED |
| 9 | SupplierScreen | `GET/POST/DELETE /api/purchases/suppliers/` | YES | YES | YES | CONNECTED |
| 10 | ReturnsScreen | `GET/POST /api/returns/return-orders/`, approve, reject, void, summary, export_csv, receipt_pdf | YES | YES | YES | CONNECTED |
| 11 | ReconciliationScreen | `GET /api/returns/reconciliation/`, fix, export_csv | YES | YES | YES | CONNECTED |
| 12 | ChartOfAccountsScreen | `GET/DELETE /api/accounting/accounts/` | YES | YES | YES | CONNECTED |
| 13 | JournalEntryScreen | `GET /api/accounting/journal-entries/`, post, unpost, reverse | YES | YES | YES | CONNECTED |
| 14 | AccountLedgerScreen | `GET /api/accounting/accounts/`, ledger | YES | YES | YES | CONNECTED |
| 15 | ReportBrowser | 13 report endpoints (trial_balance, profit_loss, etc.) | YES | YES | YES | CONNECTED |
| 16 | FinancialIntegrityScreen | `sales/customer-payments/financial_integrity/`, `fix_balances/` | **NO** | NO | YES | **DISCONNECTED** |
| 17 | FinancialAuditLogScreen | `audit/audit-trails/` | **MALFORMED** | NO | YES | **PARTIAL** |
| 18 | PaymentScreen | `GET /api/payments/transactions/` | YES | YES | YES | CONNECTED |
| 19 | BudgetingScreen | `GET /api/budgets/budgets/` | YES | YES | YES | CONNECTED |
| 20 | TaxScreen | `GET /api/tax/rates/`, returns, transactions | YES | YES | YES | CONNECTED |
| 21 | CostCentersScreen | `GET/POST/PUT /api/cost-centers/centers/` | YES | YES | YES | CONNECTED |
| 22 | CashflowScreen | `GET /api/cashflow/items/` | YES | YES | YES | CONNECTED |
| 23 | ExpenseScreen | `GET/POST /api/expenses/`, accounting accounts, payment accounts | YES | YES | YES | CONNECTED |
| 24 | CustomerPaymentWorkspace | `GET /api/sales/customers/`, payments, confirm | YES | YES | YES | CONNECTED |
| 25 | SupplierPaymentWorkspace | `GET /api/purchases/suppliers/`, payments, confirm | YES | YES | YES | CONNECTED |
| 26 | PaymentAllocationExplorer | `GET /api/sales/payments/`, `/api/purchases/payments/` | YES | YES | YES | CONNECTED |
| 27 | ReturnsExplainabilityScreen | `GET /api/returns/return-orders/` | YES | YES | YES | CONNECTED |
| 28 | JournalReversalExplorer | `GET /api/accounting/journal-entries/` | YES | YES | YES | CONNECTED |
| 29 | FinancialOperationsConsole | `GET /api/payments/transactions/`, sales payments | YES | YES | YES | CONNECTED |
| 30 | EmployeeScreen | `GET/POST/PUT/DELETE /api/hr/employees/`, departments, positions | YES | YES | YES | CONNECTED |
| 31 | AttendanceScreen | `GET /api/hr/reports/attendance-summary/` | YES | YES | YES | CONNECTED |
| 32 | LeaveScreen | `GET /api/hr/reports/leave-summary/` | YES | YES | YES | CONNECTED |
| 33 | PayrollScreen | `GET /api/payroll/cycles/`, records, `POST /api/payroll/salary-structures/` | **NO** (salary-structures) | YES | YES | **PARTIAL** |
| 34 | POSScreen | `GET /api/inventory/products/`, `POST /api/sales/invoices/` | YES | YES | YES | CONNECTED |
| 35 | BackupControlScreen | 11 backup endpoints | YES | YES | YES | CONNECTED |
| 36 | SettingsScreen | `GET/POST /api/system-config/`, companies | YES | YES | YES | CONNECTED |
| 37 | FixedAssetsScreen | `GET/POST/PUT /api/assets/assets/` | YES | YES | YES | CONNECTED |
| 38 | AuditScreen | `GET /api/audit/logs/` | YES | YES | YES | CONNECTED |
| 39 | UserManagementScreen | `GET/POST/PUT/DELETE /api/auth/users/`, roles | YES | YES | YES | CONNECTED |
| 40 | RoleManagementScreen | `GET/POST/PUT/DELETE /api/auth/roles/`, permissions | YES | YES | YES | CONNECTED |
| 41 | CompanyProfileScreen | `GET/POST/PUT /api/core/companies/` | YES | YES | YES | CONNECTED |
| 42 | EntityManagementScreen | `GET /api/entities/entities/` | YES | YES | YES | PARTIAL |
| 43 | OperationsDashboard | `/api/control-center/` endpoints | YES | YES | YES | CONNECTED |
| 44 | ObservabilityConsole | `/api/observability/v1/` endpoints | YES | YES | YES | CONNECTED |
| 45 | DecisionWorkspace | No API calls | N/A | N/A | N/A | **NO API** |

---

## DISCONNECTED Screens

### 1. FinancialIntegrityScreen (CRITICAL)
**File:** `frontend/ui/accounting/financial_integrity_screen.py`
- URL `sales/customer-payments/financial_integrity/` — malformed (missing `/api/` prefix)
- Endpoint does NOT exist in `sales/urls.py`
- Should use `/api/ops/financial-integrity/` from `config/urls.py:50`
- `fix_balances/` endpoint also doesn't exist

### 2. FinancialAuditLogScreen (HIGH)
**File:** `frontend/ui/accounting/financial_audit_log_screen.py`
- URL `audit/audit-trails/` — malformed (missing `/api/` prefix)
- Should be `/api/audit/logs/`

### 3. PayrollScreen (HIGH)
**File:** `frontend/ui/hr/payroll_screen.py`
- `salary-structures/` endpoint doesn't exist in `payroll/urls.py`
- Backend only has: cycles, records, allowances, deductions

### 4. DecisionWorkspace (MEDIUM)
**File:** `frontend/ui/causal_scoring/decision_workspace.py`
- Pure UI — no backend API calls
- Should wire to `/api/control-center/decisions/` or `/api/v1/intelligence/`

---

## Hardcoded URLs (Not Using get_endpoint())

| Screen | Hardcoded URL | Should Use |
|--------|--------------|------------|
| FinancialIntegrityScreen | `sales/customer-payments/financial_integrity/` | `get_endpoint("financial_integrity")` |
| FinancialAuditLogScreen | `audit/audit-trails/` | `get_endpoint("audit_logs")` |
| SalesInvoiceScreen | `/api/sales/invoices/{id}/confirm/` | `get_endpoint("sales_invoices")` + action |
| SalesInvoiceScreen | `/api/sales/invoices/{id}/dispatch_invoice/` | `get_endpoint("sales_invoices")` + action |
| PurchaseInvoiceScreen | `/api/purchases/invoices/{id}/confirm/` | `get_endpoint("purchase_invoices")` + action |
| PurchaseInvoiceScreen | `/api/purchases/invoices/{id}/receive/` | `get_endpoint("purchase_invoices")` + action |

---

## Missing Error Handling

| Screen | Issue |
|--------|-------|
| Dashboard | Errors only `print()` to console, no user notification |
| ProductScreen | Errors only `print()` to console |
| CategoryScreen | Delete errors show AlertDialog, but load errors only `print()` |
| WarehouseScreen | Same as CategoryScreen |
| BatchScreen | Same as CategoryScreen |
| SalesInvoiceScreen | `load_customers()` only `print()` on failure |
| PurchaseInvoiceScreen | `load_suppliers()` only `print()` on failure |
| ReturnsScreen | API errors fall through to mock data silently |

---

## Backend Endpoints With No Frontend Client

| Backend Endpoint | Frontend Coverage |
|------------------|-------------------|
| `/api/inventory/stock/allocate/` | No dedicated method |
| `/api/inventory/stock/process-sale/` | No dedicated method |
| `/api/inventory/stock/process-purchase/` | No dedicated method |
| `/api/returns/return-orders/` | No dedicated method |
| `/api/returns/reconciliation/` | No dedicated method |
| `/api/expenses/` | No dedicated method |
| `/api/tax/*` (5 ViewSets) | No dedicated methods |
| `/api/assets/*` (4 ViewSets) | No dedicated methods |
| `/api/budgets/*` (2 ViewSets) | No dedicated methods |
| `/api/cost-centers/*` (3 ViewSets) | No dedicated methods |
| `/api/entities/*` (3 ViewSets) | No dedicated methods |
| `/api/audit/*` (2 ViewSets) | No dedicated methods |
| `/api/cashflow/*` (3 ViewSets) | No dedicated methods |
| `/api/insurance/*` (3 ViewSets) | No dedicated methods |
| `/api/licensing/*` (6 endpoints) | No dedicated methods |
| `/api/payments/settlements/` | No dedicated method |
| `/api/payroll/generate/` | No dedicated method |
| `/api/payroll/approve/` | No dedicated method |
| `/api/payroll/summary/` | No dedicated method |
| `/api/payroll/reports/*` (5 reports) | No dedicated methods |
| `/api/hr/update-status/` | No dedicated method |
| `/api/hr/department-tree/` | No dedicated method |
| `/api/hr/active-employees/` | No dedicated method |
| `/api/hr/reports/*` (5 reports) | No dedicated methods |
| `/api/accounting/calculate-invoice/` | No dedicated method |
| `/api/accounting/convert-currency/` | No dedicated method |
| `/api/accounting/currencies/` | No dedicated method |
| `/api/accounting/exchange-rates/` | No dedicated method |
| `/api/accounting/calculate-mixed-payment/` | No dedicated method |
| `/api/backup/*` (11 ViewSets) | Most un-covered |
| `/api/jobs/*` (4 endpoints) | No dedicated method |
| `/api/core/companies/` | No dedicated method |
| `/api/core/system-config/` | No dedicated method |
| `/api/ops/*` (16 endpoints) | No dedicated method |
| **Total uncovered** | **~90+ endpoints** |

---

## Summary

| Category | Count |
|----------|-------|
| Fully connected screens | 33 |
| Partially connected | 8 |
| Disconnected | 4 |
| No API calls at all | 3 |
| Hardcoded URLs | 6 |
| Missing error handling | 8 screens |
| Backend endpoints without frontend client | ~90+ |
