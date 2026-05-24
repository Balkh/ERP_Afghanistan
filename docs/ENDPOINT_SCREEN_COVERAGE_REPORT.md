# ENDPOINT ↔ SCREEN COVERAGE REPORT

## Classification Legend
- ✅ **FULLY_CONNECTED** — Screen exists, API consumed, workflow complete
- ⚠️ **PARTIALLY_CONNECTED** — Screen exists but missing some API actions
- ❌ **UI_MISSING** — Backend endpoint exists with no frontend screen
- 🔌 **API_UNUSED** — Frontend has endpoint defined but no screen consumes it
- 🔧 **BROKEN_FLOW** — Screen exists but workflow has gaps
- 🗑️ **LEGACY** — Deprecated/removed endpoint or screen

---

## 1. INVENTORY MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/inventory/products/` | products | ProductScreen (idx 1) | ✅ FULLY_CONNECTED | CRUD, search, pagination |
| `/api/inventory/categories/` | categories | CategoryScreen (idx 2) | ✅ FULLY_CONNECTED | CRUD |
| `/api/inventory/warehouses/` | warehouses | WarehouseScreen (idx 3) | ✅ FULLY_CONNECTED | CRUD |
| `/api/inventory/batches/` | batches | BatchScreen (idx 4) | ✅ FULLY_CONNECTED | CRUD, expiry tracking |
| `/api/inventory/stock-movements/` | stock_movements | — | ❌ UI_MISSING | No dedicated screen |
| `/api/inventory/products/by_barcode/` | — | POS / BarcodeScannerInput | ✅ FULLY_CONNECTED | Via APIClient.lookup_barcode |
| `/api/inventory/products/by_sku/` | — | POS / SalesInvoice | ✅ FULLY_CONNECTED | Via APIClient.lookup_sku |
| `/api/inventory/products/generate_barcode/` | — | — | 🔌 API_UNUSED | Defined but not consumed in UI |
| `/api/inventory/products/validate_barcode/` | — | — | 🔌 API_UNUSED | Defined but not consumed in UI |

## 2. SALES MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/sales/customers/` | customers | CustomerScreen (idx 7) | ✅ FULLY_CONNECTED | CRUD, balance lookup |
| `/api/sales/customers/{id}/balance/` | customer_balance | CustomerScreen | ✅ FULLY_CONNECTED | Balance display |
| `/api/sales/invoices/` | sales_invoices | SalesInvoiceScreen (idx 5) | ✅ FULLY_CONNECTED | Create, view, dispatch, payment |
| `/api/sales/items/` | sales_items | — | ❌ UI_MISSING | No dedicated line-item screen |
| `/api/sales/payments/` | sales_payments | PaymentScreen | ⚠️ PARTIALLY_CONNECTED | Payment processing via invoice flow |

## 3. PURCHASES MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/purchases/suppliers/` | suppliers | SupplierScreen (idx 8) | ✅ FULLY_CONNECTED | CRUD, balance lookup |
| `/api/purchases/suppliers/{id}/balance/` | supplier_balance | SupplierScreen | ✅ FULLY_CONNECTED | Balance display |
| `/api/purchases/invoices/` | purchase_invoices | PurchaseInvoiceScreen (idx 6) | ✅ FULLY_CONNECTED | CRUD, receive, payment |
| `/api/purchases/items/` | purchase_items | — | ❌ UI_MISSING | No dedicated line-item screen |
| `/api/purchases/payments/` | purchase_payments | PaymentScreen | ⚠️ PARTIALLY_CONNECTED | Payment via invoice flow |

## 4. RETURNS MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/returns/return-orders/` | return-orders | ReturnsScreen (idx 9) | ✅ FULLY_CONNECTED | CRUD, approve, reject, void |
| `/api/returns/return-orders/{id}/approve/` | — | ReturnsScreen | ✅ FULLY_CONNECTED | Approval workflow |
| `/api/returns/return-orders/{id}/reject/` | — | ReturnsScreen | ✅ FULLY_CONNECTED | Rejection workflow |
| `/api/returns/return-orders/{id}/void/` | — | ReturnsScreen | ✅ FULLY_CONNECTED | Void workflow |
| `/api/returns/return-orders/summary/` | — | ReturnsScreen | ✅ FULLY_CONNECTED | Summary stats |
| `/api/returns/return-orders/export_csv/` | — | ReturnsScreen | ✅ FULLY_CONNECTED | CSV export |
| `/api/returns/return-orders/{id}/receipt_pdf/` | — | ReturnsScreen | ✅ FULLY_CONNECTED | PDF receipt |
| `/api/returns/reconciliation/` | reconciliation | ReconciliationScreen (idx 57) | ✅ FULLY_CONNECTED | CRUD, fix mismatch |
| `/api/returns/reconciliation/{id}/fix/` | — | ReconciliationScreen | ✅ FULLY_CONNECTED | Fix workflow |
| `/api/returns/reconciliation/export_csv/` | — | ReconciliationScreen | ✅ FULLY_CONNECTED | CSV export |

## 5. ACCOUNTING MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/accounting/accounts/` | accounts | ChartOfAccountsScreen (idx 10) | ✅ FULLY_CONNECTED | CRUD, hierarchy |
| `/api/accounting/accounts/leaf_accounts/` | leaf_accounts | ChartOfAccountsScreen | ✅ FULLY_CONNECTED | Leaf account filtering |
| `/api/accounting/accounts/trial_balance/` | trial_balance | ReportBrowser (idx 13) | ✅ FULLY_CONNECTED | Report + export |
| `/api/accounting/accounts/profit_loss/` | profit_loss | ReportBrowser (idx 14) | ✅ FULLY_CONNECTED | Report + export |
| `/api/accounting/accounts/balance_sheet/` | balance_sheet | ReportBrowser (idx 15) | ✅ FULLY_CONNECTED | Report + export |
| `/api/accounting/accounts/ar_aging/` | ar_aging | ReportBrowser (idx 16) | ✅ FULLY_CONNECTED | Report + export |
| `/api/accounting/accounts/ap_aging/` | ap_aging | ReportBrowser (idx 17) | ✅ FULLY_CONNECTED | Report + export |
| `/api/accounting/accounts/ledger/` | ledger | AccountLedgerScreen (idx 12) | ✅ FULLY_CONNECTED | Account detail view |
| `/api/accounting/journal-entries/` | journal_entries | JournalEntryScreen (idx 11) | ✅ FULLY_CONNECTED | CRUD, post, reverse |
| `/api/accounting/report-options/` | — | ReportBrowser | ✅ FULLY_CONNECTED | Available report types |
| `/api/accounting/export/` | — | All report screens | ✅ FULLY_CONNECTED | CSV/XLSX/PDF export |
| `/api/accounting/reports/` | — | ReportBrowser | ✅ FULLY_CONNECTED | Advanced report generation |
| `/api/accounting/journal-entries/{id}/reverse_entry/` | — | JournalEntryScreen | ✅ FULLY_CONNECTED | Reversal workflow |
| `/api/accounting/journal-entries/{id}/reversal_impact/` | — | JournalReversalExplorer | ✅ FULLY_CONNECTED | Impact analysis |
| `/api/accounting/journal-entries/{id}/reversal_chain/` | — | JournalReversalExplorer | ✅ FULLY_CONNECTED | Chain visualization |

## 6. FINANCE MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/payments/transactions/` | payments | PaymentScreen (idx 18) | ✅ FULLY_CONNECTED | Transaction listing |
| `/api/payments/methods/` | payment_methods | PaymentScreen | ✅ FULLY_CONNECTED | Method selection |
| `/api/payments/accounts/` | payment_accounts | PaymentScreen | ✅ FULLY_CONNECTED | Account selection |
| `/api/payments/settlements/` | settlements | — | ❌ UI_MISSING | No dedicated settlement screen |
| `/api/budgets/budgets/` | budgets | BudgetingScreen (idx 19) | ✅ FULLY_CONNECTED | Budget management |
| `/api/budgets/lines/` | budget_lines | BudgetingScreen | ⚠️ PARTIALLY_CONNECTED | Via budget detail |
| `/api/tax/categories/` | tax_categories | TaxScreen (idx 20) | ✅ FULLY_CONNECTED | Tax category management |
| `/api/tax/rates/` | tax_rates | TaxScreen | ✅ FULLY_CONNECTED | Rate management |
| `/api/tax/returns/` | tax_returns | TaxScreen | ⚠️ PARTIALLY_CONNECTED | Return filing |
| `/api/tax/transactions/` | tax_transactions | — | ❌ UI_MISSING | No dedicated screen |
| `/api/cost-centers/centers/` | cost_centers | CostCentersScreen (idx 21) | ✅ FULLY_CONNECTED | CRUD |
| `/api/cashflow/items/` | cashflow, cashflow_items | CashflowScreen (idx 22) | ✅ FULLY_CONNECTED | Cash flow items |
| `/api/cashflow/forecasts/` | cashflow_forecasts | CashflowScreen | ⚠️ PARTIALLY_CONNECTED | Forecast view |
| `/api/cashflow/scenarios/` | cashflow_scenarios | — | ❌ UI_MISSING | No scenario UI |
| `/api/expenses/` | — | ExpenseScreen (idx 34) | ✅ FULLY_CONNECTED | Expense management |

## 7. HR & PAYROLL MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/hr/employees/` | employees | EmployeeScreen (idx 23) | ✅ FULLY_CONNECTED | CRUD |
| `/api/hr/departments/` | departments | EmployeeScreen | ✅ FULLY_CONNECTED | Department selection |
| `/api/hr/positions/` | positions | EmployeeScreen | ✅ FULLY_CONNECTED | Position management |
| `/api/hr/reports/attendance-summary/` | attendance | AttendanceScreen (idx 24) | ✅ FULLY_CONNECTED | Attendance tracking |
| `/api/hr/reports/leave-summary/` | leave | LeaveScreen (idx 25) | ✅ FULLY_CONNECTED | Leave management |
| `/api/payroll/records/` | payroll_records | PayrollScreen (idx 26) | ✅ FULLY_CONNECTED | Payroll processing |
| `/api/payroll/cycles/` | payroll_cycles | PayrollScreen | ✅ FULLY_CONNECTED | Cycle management |
| `/api/payroll/allowances/` | allowances | PayrollScreen | ✅ FULLY_CONNECTED | Allowance management |
| `/api/payroll/deductions/` | deductions | PayrollScreen | ✅ FULLY_CONNECTED | Deduction management |

## 8. SYSTEM & OPERATIONS MODULE

| Endpoint | Key | Screen | Status | Notes |
|----------|-----|--------|--------|-------|
| `/api/auth/users/` | — | UserManagementScreen (idx 31) | ✅ FULLY_CONNECTED | CRUD |
| `/api/auth/roles/` | — | RoleManagementScreen (idx 48) | ✅ FULLY_CONNECTED | CRUD |
| `/api/auth/login/` | login | main.py (login dialog) | ✅ FULLY_CONNECTED | Authentication |
| `/api/auth/notifications/` | notifications | — | 🔧 BROKEN_FLOW | Endpoint defined, no notification center screen |
| `/api/auth/notifications/unread-count/` | notifications_unread | — | 🔧 BROKEN_FLOW | No UI consumption |
| `/api/backup/records/` | backup_records | BackupControlScreen (idx 27) | ✅ FULLY_CONNECTED | Backup management |
| `/api/backup/restore-points/` | restore_points | BackupControlScreen | ✅ FULLY_CONNECTED | Restore points |
| `/api/audit/logs/` | audit_logs | AuditScreen (idx 30) | ✅ FULLY_CONNECTED | Audit log viewer |
| `/api/assets/assets/` | assets | FixedAssetsScreen (idx 29) | ✅ FULLY_CONNECTED | Asset management |
| `/api/control-center/` | control_center | Dashboard / OperationsDashboard | ✅ FULLY_CONNECTED | Central dashboard |
| `/api/control-center/intelligence/` | intelligence | IntelligenceHubScreen (idx 32) | ✅ FULLY_CONNECTED | Intelligence display |
| `/api/control-center/health/` | control_health | MainWindow status bar | ✅ FULLY_CONNECTED | Health monitoring |
| `/api/health/` | health | MainWindow | ✅ FULLY_CONNECTED | Backend health check |
| `/api/observability/` | — | ObservabilityConsole (idx 39) | ✅ FULLY_CONNECTED | Observability |

## 9. MISSING UI (ENDPOINTS WITH NO FRONTEND SCREEN)

| Endpoint | Suggested Screen | Priority |
|----------|-----------------|----------|
| `/api/inventory/stock-movements/` | Stock Movement History Screen | MEDIUM |
| `/api/payments/settlements/` | Settlement Management Screen | LOW |
| `/api/tax/transactions/` | Tax Transaction Viewer | LOW |
| `/api/cashflow/scenarios/` | Cashflow Scenario Planner | LOW |
| `/api/auth/notifications/` | Notification Center Screen | MEDIUM |
| `/api/sales/items/` | Sales Line Item Report | LOW |
| `/api/purchases/items/` | Purchase Line Item Report | LOW |
| `/api/settlements/` | Settlement Screen | LOW |

## 10. UNUSED API ENDPOINTS IN FRONTEND

| Endpoint Key | Status |
|-------------|--------|
| `generate_barcode` | Defined in endpoints.py, not consumed in any screen |
| `validate_barcode` | Defined in endpoints.py, not consumed in any screen |

## SUMMARY

| Classification | Count |
|---------------|-------|
| ✅ FULLY_CONNECTED | 55 |
| ⚠️ PARTIALLY_CONNECTED | 6 |
| ❌ UI_MISSING | 8 |
| 🔌 API_UNUSED | 2 |
| 🔧 BROKEN_FLOW | 2 |
| **Total Endpoints** | **73** |
