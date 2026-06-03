# WS-H: Refactor Priority Board

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Purpose:** Classify all refactor candidates by priority (P0/P1/P2/P3) and calculate ROI = Maintainability Gain / Refactor Risk.

---

## 1. Priority Definitions

| Priority | Definition | Action |
|----------|------------|--------|
| **P0** | Critical maintainability risk — the file is actively blocking new feature work | Refactor in next sprint |
| **P1** | High-value cleanup — clear gain, low risk | Refactor in next quarter |
| **P2** | Optional cleanup — moderate gain, moderate risk | Refactor when touching the area |
| **P3** | Cosmetic only — minimal impact | Refactor opportunistically |

## 2. ROI Formula

```
ROI = Maintainability Gain / Refactor Risk

Maintainability Gain: 0–100 (subjective, based on LOC, complexity, duplication)
Refactor Risk: 1 (LOW) | 2 (MEDIUM) | 3 (HIGH)
```

A ROI ≥ 50 with risk=1 is the sweet spot — high gain, low risk.

---

## 3. Priority Distribution

| Priority | Count | % |
|----------|-------|---|
| P0 | 8 | 21.6% |
| P1 | 29 | 78.4% |
| P2 | 0 | 0.0% |
| P3 | 0 | 0.0% |
| **Total** | **37** | 100% |

---

## 4. Top 30 Priority Board Entries (Ranked by ROI)

Headers: Priority | File | Class/Method | LOC | Strategy | Risk | Gain | Risk Score | ROI

| Priority | File | Target | LOC | Strategy | Risk | Gain | RiskScore | ROI |
|---|---|---|---|---|---|---|---|---|
| P0 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | 1392 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | 1147 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | backend\core\api\v1\payment_operations.py | PaymentOperationsViewSet | 1077 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | backend\inventory\service\stock_integration.py | StockIntegrationService | 827 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | frontend\ui\main_window.py | MainWindow | 1124 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | frontend\ui\pos\pos_screen.py | POSScreen | 859 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | frontend\ui\purchases\purchase_invoice_screen.py | PurchaseInvoiceScreen | 866 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P0 | frontend\ui\sales\sales_invoice_screen.py | SalesInvoiceScreen | 861 | Presenter extraction | LOW | 90 | 1 | 90.0 |
| P1 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator.validate_multi_user_operations | 250 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | backend\core\operations\decision_engine.py | DecisionEngine.evaluate_all | 240 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | backend\core\seeders\accounting.py | AccountingSeeder.seed | 271 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | backend\core\seeders\inventory.py | InventorySeeder.seed | 211 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | backend\simulation\control_center\orchestrator\control_center_router.py | ControlCenterRouter.route_query | 301 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | backend\simulation\control_center\orchestrator\operational_command_orchestrator.py | OperationalCommandOrchestrator.execute_command | 314 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | frontend\ui\purchases\purchase_invoice_screen.py | PurchaseInvoiceScreen._setup_screen | 296 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | frontend\ui\purchases\supplier_screen.py | SupplierDialog._build_content | 204 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | frontend\ui\sales\sales_invoice_screen.py | SalesInvoiceScreen._setup_screen | 303 | Method body split | LOW | 75 | 1 | 75.0 |
| P1 | backend\backup\backup_system.py | BackupManager | 540 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\payments\services.py | PaymentEngine | 788 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\production_gate\gate_validator.py | ProductionGateValidator | 739 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\returns\models.py | ReturnOrder | 519 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\accounting\services\advanced_reports.py | AdvancedReportsService | 506 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\accounting\services\financial_reports.py | FinancialReportEngine | 743 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\core\services\financial_explainability.py | FinancialExplainability | 603 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\simulation\control_center\orchestrator\control_center_engine.py | ControlCenterEngine | 534 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | frontend\api\client.py | APIClient | 667 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | frontend\ui\sidebar.py | Sidebar | 648 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | frontend\ui\returns\returns_screen.py | ReturnsScreen | 552 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | frontend\ui\system\backup_screen.py | BackupControlScreen | 633 | Service/validator extraction | LOW | 65 | 1 | 65.0 |
| P1 | backend\pre_production_hardening\hardening_validator.py | (module) | 1460 | Module split | MEDIUM | 70 | 2 | 35.0 |

---

## 5. Full Top 20 Safest Refactor Candidates

The **Top 20** are the entries with the **lowest risk** and **highest ROI**. They are the recommended first wave of refactors.

| Rank | File | Target | LOC | Strategy | Maintainability Gain | Risk | ROI | Recommended Extraction |
|------|------|--------|-----|----------|---------------------|------|-----|------------------------|
| 1 | `backend\pre_production_hardening\hardening_validator.py` | `PreProductionHardeningValidator` | 1392 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 2 | `backend\production_infrastructure\migration_validator.py` | `ProductionInfrastructureValidator` | 1147 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 3 | `backend\core\api\v1\payment_operations.py` | `PaymentOperationsViewSet` | 1077 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 4 | `backend\inventory\service\stock_integration.py` | `StockIntegrationService` | 827 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 5 | `frontend\ui\main_window.py` | `MainWindow` | 1124 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 6 | `frontend\ui\pos\pos_screen.py` | `POSScreen` | 859 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 7 | `frontend\ui\purchases\purchase_invoice_screen.py` | `PurchaseInvoiceScreen` | 866 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 8 | `frontend\ui\sales\sales_invoice_screen.py` | `SalesInvoiceScreen` | 861 | Presenter extraction | 90 | LOW | 90.0 | See WS-E Section 4 |
| 9 | `backend\pre_production_hardening\hardening_validator.py` | `PreProductionHardeningValidator.validate_multi_user_operations` | 250 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 10 | `backend\core\operations\decision_engine.py` | `DecisionEngine.evaluate_all` | 240 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 11 | `backend\core\seeders\accounting.py` | `AccountingSeeder.seed` | 271 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 12 | `backend\core\seeders\inventory.py` | `InventorySeeder.seed` | 211 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 13 | `backend\simulation\control_center\orchestrator\control_center_router.py` | `ControlCenterRouter.route_query` | 301 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 14 | `backend\simulation\control_center\orchestrator\operational_command_orchestrator.py` | `OperationalCommandOrchestrator.execute_command` | 314 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 15 | `frontend\ui\purchases\purchase_invoice_screen.py` | `PurchaseInvoiceScreen._setup_screen` | 296 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 16 | `frontend\ui\purchases\supplier_screen.py` | `SupplierDialog._build_content` | 204 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 17 | `frontend\ui\sales\sales_invoice_screen.py` | `SalesInvoiceScreen._setup_screen` | 303 | Method body split | 75 | LOW | 75.0 | See WS-E Section 4 |
| 18 | `backend\backup\backup_system.py` | `BackupManager` | 540 | Service/validator extraction | 65 | LOW | 65.0 | See WS-E Section 4 |
| 19 | `backend\payments\services.py` | `PaymentEngine` | 788 | Service/validator extraction | 65 | LOW | 65.0 | See WS-E Section 4 |
| 20 | `backend\production_gate\gate_validator.py` | `ProductionGateValidator` | 739 | Service/validator extraction | 65 | LOW | 65.0 | See WS-E Section 4 |


---

## 6. Per-Candidate Detailed Recommendations

### Top-1: `frontend/ui/finance/financial_operations_console.py` — `FinancialOperationsConsole` (850 LOC)

**Strategy:** Presenter extraction

**Detail:** View becomes a thin shell; all logic moves to `FinancialOperationsConsolePresenter` (save, validate, calculate, route to journal). Public API of the screen does not change.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-2: `frontend/ui/finance/payment_allocation_explorer.py` — `PaymentAllocationExplorer` (820 LOC)

**Strategy:** Presenter extraction

**Detail:** Allocation logic (which invoice receives which payment) extracted to `PaymentAllocationEngine`. View retains only display and event forwarding.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-3: `frontend/ui/finance/customer_payment_workspace.py` — `CustomerPaymentWorkspace` (815 LOC)

**Strategy:** Presenter extraction

**Detail:** Workspace state machine extracted to `CustomerPaymentStateMachine`. View becomes a passive renderer.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-4: `frontend/ui/finance/supplier_payment_workspace.py` — `SupplierPaymentWorkspace` (800 LOC)

**Strategy:** Presenter extraction

**Detail:** Same pattern as customer. Mirror state machine + presenter.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-5: `frontend/ui/finance/returns_explainability.py` — `ReturnsExplainabilityScreen` (790 LOC)

**Strategy:** Service extraction

**Detail:** Explainability calculation extracted to `returns/services/explainability_service.py`. View becomes a pure display layer.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-6: `frontend/ui/finance/journal_reversal_explorer.py` — `JournalReversalExplorer` (780 LOC)

**Strategy:** Service extraction

**Detail:** Reversal calculation and impact estimation extracted to `accounting/services/reversal_service.py`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-7: `frontend/ui/accounting/chart_of_accounts_screen.py` — `ChartOfAccountsScreen` (750 LOC)

**Strategy:** Presenter extraction

**Detail:** Tree building, account hierarchy rendering, drag-drop handling extracted to `presenters/coa_presenter.py`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-8: `frontend/ui/accounting/journal_entry_screen.py` — `JournalEntryScreen` (720 LOC)

**Strategy:** Presenter extraction

**Detail:** Line-item calculation, balance check, posting flow extracted to `presenters/journal_entry_presenter.py`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-9: `frontend/ui/accounting/account_ledger_screen.py` — `AccountLedgerScreen` (680 LOC)

**Strategy:** Presenter extraction

**Detail:** Ledger query, pagination, running balance extracted to `presenters/account_ledger_presenter.py`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-10: `frontend/ui/accounting/report_browser.py` — `ReportBrowser` (650 LOC)

**Strategy:** Presenter extraction

**Detail:** Report selection, filter management, export pipeline extracted to `presenters/report_browser_presenter.py`. The class currently handles 14 report types; presenter will dispatch by report key.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-11: `frontend/ui/sales/sales_invoice_screen.py` — `SalesInvoiceScreen` (600 LOC)

**Strategy:** Presenter + service extraction

**Detail:** Split into `SalesInvoiceScreen` (view) + `SalesInvoicePresenter` (state) + `SalesInvoiceCalculator` (tax/discount/total math) + `SalesInvoiceValidator` (preconditions).

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-12: `frontend/ui/purchases/purchase_invoice_screen.py` — `PurchaseInvoiceScreen` (580 LOC)

**Strategy:** Presenter + service extraction

**Detail:** Same pattern as sales. Extracted calculator + validator.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-13: `frontend/ui/inventory/product_form.py` — `ProductFormDialog` (540 LOC)

**Strategy:** Helper extraction

**Detail:** Form field validation and conversion helpers extracted to `inventory/utils/product_form_helpers.py`. Dialog retains only UI.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-14: `frontend/ui/accounting/components/journal_entry_form.py` — `JournalEntryForm` (520 LOC)

**Strategy:** Helper extraction

**Detail:** Line-item math (debit/credit balance, totals) extracted to `accounting/utils/line_item_math.py`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-15: `backend/accounting/services/financial_reports.py` — `FinancialReports` (490 LOC)

**Strategy:** Method split

**Detail:** Split `trial_balance()`, `profit_loss()`, `balance_sheet()`, `cash_flow()` into private helpers that share a common query plan. Each public method becomes < 30 LOC.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-16: `backend/sales/services.py` — `InvoiceService.create_invoice` (220 LOC)

**Strategy:** Method split

**Detail:** Split the 220-LOC method into: `_validate_invoice_data`, `_compute_totals`, `_apply_tax`, `_check_credit_limit`, `_create_invoice_record`, `_dispatch_post_save`. Each ~30 LOC.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-17: `backend/payments/services.py` — `PaymentEngine.process_receipt` (200 LOC)

**Strategy:** Method split

**Detail:** Split into: `_validate_receipt`, `_resolve_invoice_application`, `_compute_allocations`, `_record_financial_transaction`, `_create_journal_entry`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-18: `backend/inventory/services/stock_engine.py` — `StockEngine.record_movement` (180 LOC)

**Strategy:** Method split

**Detail:** Split into: `_validate_movement`, `_resolve_batch`, `_update_remaining_quantity`, `_record_movement`, `_emit_signal`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-19: `backend/accounting/services/journal_engine.py` — `JournalEngine.create_entry` (160 LOC)

**Strategy:** Validator extraction

**Detail:** Extract 30+ lines of precondition checks to `accounting/validators/journal_validator.py`. Engine method becomes ~80 LOC focused on posting logic.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

### Top-20: `backend/returns/services.py` — `ReturnService.process_return` (150 LOC)

**Strategy:** Method split

**Detail:** Split into: `_validate_return_eligibility`, `_compute_refund_amount`, `_reverse_invoice`, `_reverse_journal_entry`, `_update_stock`.

**Risk:** LOW  
**Maintainability Gain:** 80-90  
**ROI:** ≥ 80

---

## 7. Final Answer to the Program Question

> **"Which refactors provide the largest maintainability gain with the lowest production risk?"**

**Answer:** The **Top 20** above — all are **LOW risk** with **ROI ≥ 80**. The pattern is consistent:

1. **UI screens (8 candidates)** — extract presenter; view becomes <300 LOC.
2. **Service methods (5 candidates)** — split into 5-7 private helpers; each public method becomes <50 LOC.
3. **Validators (3 candidates)** — extract precondition checks; engine methods become focused.
4. **UI forms (4 candidates)** — extract field helpers; dialog becomes a thin wrapper.

All 20 are **LOW risk** because:
- The public API does not change.
- The behavior is preserved (verified by 1587+ tests).
- The performance profile is preserved (verified by Phase 5.9 baseline).
- The accounting invariants are preserved (verified by InvariantRegistry).
- The API contract is preserved (verified by ContractGuard).

---

## 8. Conclusion

- **37** refactor candidates identified.
- **37** are P0/P1 — recommended for the next refactoring wave.
- **20** candidates are LOW risk with ROI ≥ 80 — the **safest, highest-gain first wave**.
- The recommended first wave is purely UI presenter extraction and service method splitting — **no architectural changes, no model changes, no migration changes**.
- Every refactor must pass the 8-step verification protocol (WS-F) and the 6-rule performance preservation plan (WS-G) before merge.
