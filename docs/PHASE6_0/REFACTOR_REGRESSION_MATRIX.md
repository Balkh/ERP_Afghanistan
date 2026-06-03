# WS-F: Refactor Regression Protection Matrix

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Purpose:** Document the regression protection for each top refactor candidate — what tests, workflows, reports, signals, and accounting flows must be verified.

---

## 1. Protection Layers

| Layer | Tool | Coverage |
|-------|------|----------|
| Unit tests | pytest (1587+ tests) | All services, all engines, all major models |
| Integration tests | pytest integration suite | Journal engine, payment engine, stock engine |
| Accounting invariants | `InvariantRegistry` (6 invariants) | FOREIGN_KEYS, JOURNAL_ENTRY, STOCK, AR_AP, AUDIT_TRAIL, ACCOUNTING_EQUATION |
| API contract | `ContractGuard` (4 contracts) | response_format, error_format, endpoint_naming, pagination_signature |
| Smoke tests | `phase5_7/5_8/5_9` | End-to-end workflows with 3.2M+ rows |
| UI smoke | EnterpriseDialog/BaseScreen lifecycle | Dialog open/close, form submit/cancel |

---

## 2. Top 20 Refactor Candidates — Protection Matrix

Headers: # | File | Class/Method | Affected Tests | Affected Workflows | Affected Reports | Affected Signals | Affected Accounting | Required Verification

| # | File | Target | Tests | Workflows | Reports | Signals | Accounting | Verification |
|---|------|--------|-------|-----------|---------|---------|------------|--------------|
| 1 | `sales/services.py` | `InvoiceService.create_invoice` | test_sales_flow, test_journal_engine | Sales → Dispatch → Journal | Trial Balance, P&L, AR Aging | invoice_created | SALE journal entry (Dr AR, Cr Revenue, Cr Tax) | Run sales workflow + assert journal balanced |
| 2 | `accounting/services/journal_engine.py` | `JournalEngine.create_entry` | test_accounting_model (43), test_journal_engine | All postings | Trial Balance, P&L, BS, Cash Flow | journal_posted | All journal entries | Run invariant check + balance equation |
| 3 | `payments/services.py` | `PaymentEngine.process_receipt` | test_payment_engine, test_financial_cert | Customer payment | AR Aging, Cash Flow | receipt_posted | RECEIPT journal entry | Run payment + assert balance |
| 4 | `inventory/services/stock_engine.py` | `StockEngine.record_movement` | test_inventory, test_stock_engine | All stock movements | Stock reports, valuation | movement_posted | Stock valuation consistency | Run stock movement + assert invariant |
| 5 | `purchases/services.py` | `PurchaseService.receive_invoice` | test_purchases, test_journal_engine | Purchase receive | AP Aging, Inventory valuation | purchase_received | PURCHASE journal entry (Dr Inv, Cr AP) | Run purchase + assert balance |
| 6 | `returns/services.py` | `ReturnService.process_return` | test_returns, test_void_reversal | Returns | Returns report, AR/AP reversal | return_processed | Reversal journal entry | Run return + assert balance |
| 7 | `accounting/services/financial_reports.py` | `FinancialReports.trial_balance` | test_financial_reports | All postings | Trial Balance | report_generated | Sum of all entries by account | Compare TB before/after refactor |
| 8 | `accounting/services/financial_reports.py` | `FinancialReports.profit_loss` | test_financial_reports | All postings | P&L | report_generated | Revenue - Expense | Compare P&L before/after refactor |
| 9 | `accounting/services/financial_reports.py` | `FinancialReports.balance_sheet` | test_financial_reports | All postings | Balance Sheet | report_generated | Assets = Liab + Equity | Compare BS before/after refactor |
| 10 | `hr/services/reports.py` | `HRReportsService.generate` | test_hr, test_payroll | HR reports | HR reports | report_generated | - | Compare HR report before/after refactor |
| 11 | `payroll/services/reports.py` | `PayrollReportsService.generate` | test_payroll | Payroll | Payroll reports | report_generated | PAYROLL journal entry | Compare payroll + assert balance |
| 12 | `frontend/ui/sales/sales_invoice_screen.py` | `SalesInvoiceScreen class` | frontend/tests/ui | Sales UI | - | form signals | - | Run UI smoke (open/close/submit/cancel) |
| 13 | `frontend/ui/purchases/purchase_invoice_screen.py` | `PurchaseInvoiceScreen class` | frontend/tests/ui | Purchase UI | - | form signals | - | Run UI smoke |
| 14 | `frontend/ui/accounting/journal_entry_form.py` | `JournalEntryForm class` | frontend/tests/ui | Journal UI | - | form signals | - | Run UI smoke + DataEntryGrid |
| 15 | `frontend/ui/accounting/chart_of_accounts_screen.py` | `ChartOfAccountsScreen class` | frontend/tests/ui | CoA UI | - | form signals | - | Run UI smoke |
| 16 | `frontend/ui/inventory/product_form.py` | `ProductFormDialog class` | frontend/tests/ui | Product UI | - | form signals | - | Run UI smoke + EnterpriseDialog |
| 17 | `frontend/ui/finance/customer_payment_workspace.py` | `CustomerPaymentWorkspace class` | frontend/tests/ui | Customer payment UI | - | form signals | - | Run UI smoke + StateHelper |
| 18 | `frontend/ui/finance/supplier_payment_workspace.py` | `SupplierPaymentWorkspace class` | frontend/tests/ui | Supplier payment UI | - | form signals | - | Run UI smoke + StateHelper |
| 19 | `frontend/ui/finance/financial_operations_console.py` | `FinancialOperationsConsole class` | frontend/tests/ui | Finance console UI | - | form signals | - | Run UI smoke |
| 20 | `frontend/ui/accounting/report_browser.py` | `ReportBrowser class` | frontend/tests/ui | Report browser UI | - | form signals | - | Run UI smoke for all 14 report types |

---

## 3. Cross-Cutting Protections

### 3.1 Accounting Invariants
Every refactor touching accounting, payments, or inventory MUST preserve the 6 invariants from `InvariantRegistry`:
1. **FOREIGN_KEYS** — every FK resolves
2. **JOURNAL_ENTRY** — every journal entry is balanced (sum of debits = sum of credits)
3. **STOCK** — sum of stock movements = product batch remaining quantity
4. **AR_AP** — sum of customer invoices - payments = AR balance
5. **AUDIT_TRAIL** — every financial action has a corresponding audit log
6. **ACCOUNTING_EQUATION** — Assets = Liabilities + Equity (verified on every BS generation)

### 3.2 API Contract
- Response format: `{success, data, meta}`
- Error format: `{success, error, meta}`
- Endpoint naming: kebab-case with version prefix
- Pagination: `{count, next, previous, results}`

### 3.3 UI Lifecycle
- `BaseScreen.showEvent` must trigger data load exactly once
- `EnterpriseDialog.showEvent` must initialize form exactly once
- `DataEntryGrid.cell_value_changed` must propagate to presenter exactly once

---

## 4. Verification Protocol

For each refactor:
1. **Snapshot** the production state (pg_dump, run pytest baseline).
2. **Refactor** with the extraction map.
3. **Unit test** — pytest with all 1587+ tests must pass.
4. **Invariant test** — run `InvariantRegistry.check_all()` — all 6 must pass.
5. **Contract test** — run `ContractGuard.verify_all()` — all 4 must pass.
6. **Smoke test** — re-run phase5_7/5_8/5_9 (or relevant subset).
7. **Diff check** — compare financial reports (TB, P&L, BS) before/after — must be identical.
8. **UI smoke** — open/close all refactored screens — no lifecycle errors.

---

## 5. Conclusion

- Every refactor candidate has at least one protection layer.
- Critical paths (accounting, payments, stock) have 3+ protection layers.
- The verification protocol requires 8 explicit checks before any refactor is considered complete.
- **No refactor proceeds without green protection evidence.**
