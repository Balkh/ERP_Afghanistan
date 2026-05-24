# TECHNICAL DEBT REGISTRY
## Pharmacy ERP — Real Technical Debt (Not Theoretical Cleanup)

**Generated:** May 21, 2026
**Status:** PHASE 35 — INITIAL SEED
**Type:** Append-Only Living Document

This document catalogs genuine technical debt — code that works today but WILL cause problems without remediation. Items are ranked by real operational impact, not by code aesthetics.

---

## EXECUTIVE SUMMARY

| Category | Count | Est. Effort | Priority |
|----------|-------|-------------|----------|
| CRITICAL | 0 | 0 hours | — ALL RESOLVED |
| HIGH — Functional Impairment | 3 | 11 hours | SHORT-TERM |
| MEDIUM — Operational Degradation | 0 | 0 hours | — ALL RESOLVED |
| LOW — Code Quality | 1 | 1 hour | LONG-TERM |
| **TOTAL** | **4** | **~12 hours** | |

_Note: Phase 37/38 audit verified that 24 of 28 debt items were already resolved or verified correct by prior refactoring. Remaining items below._

---

## CRITICAL DEBT (Phase 36 — All 6 Resolved/Stale)

_Phase 36 audit verified: All 6 original critical items are resolved or stale. TD-004 was fully traced and confirmed correct — discount IS reflected in journal entry amounts._

### TD-001: FinancialIntegrityMonitor Has 3 Crash Bugs ✅ RESOLVED (Phase 36)
- **Location:** `core/operations/financial.py:88-92,118,146-148`
- **Status:** ✅ **RESOLVED** — Fixed in Phase 36 (wrong FK field `journal_entry`→`entry`, non-existent `is_reversed`→`reversed_by_entry`, added None coalescing for debit/credit)

### TD-002: Period Closing Service Has 2 Non-Existent References
- **Location:** `accounting/services/period_service.py:45,50`
- **Status:** ❌ **STALE — File does not exist.** The file `accounting/services/period_service.py` was never created; the actual file is `period_closing.py` which has correct field references. No action needed.

### TD-003: Invoice Cancel Does NOT Reverse Stock Movements
- **Location:** `sales/views.py:420-449`, `purchases/views.py:339-363`
- **Status:** ❌ **STALE — Already implemented.** Verified: `SalesInvoiceViewSet.cancel()` calls `StockIntegrationService.reverse_sale_stock()` and `PurchaseInvoiceViewSet.cancel()` calls `StockIntegrationService.reverse_purchase_stock()`, both inside `transaction.atomic()`.

### TD-004: Journal Entries Use Subtotal Instead of Net (Discount Ignored) ✅ RESOLVED — VERIFIED CORRECT (Phase 36)
- **Location:** `sales/views.py:79`, `purchases/views.py:85`
- **Status:** ✅ **RESOLVED — VERIFIED CORRECT** — Full code-path trace completed in Phase 36:
  - **Sales**: `SalesInvoiceViewSet.dispatch()` → `MigrationRouter.create_entry(module='sales', operation='create_entry')` → `JournalGateway.create_entry()` which calls `SalesAccountingService.create_sales_journal_entry()`. The Revenue (4100) credit line uses `invoice.subtotal - invoice.discount` (= net amount). The AR debit uses `invoice.total_amount` (= net + tax). Math is balanced. **Discount IS correctly reflected.**
  - **Purchases**: `PurchaseInvoiceViewSet.receive()` → `MigrationRouter.create_entry(module='purchases', operation='create_entry')` → `JournalGateway.create_entry()` which calls `PurchaseAccountingService.create_purchase_journal_entry()`. The Inventory (1300) debit line uses `invoice.subtotal - invoice.discount` (= net amount). The AP credit uses `invoice.total_amount` (= net + tax). Math is balanced. **Discount IS correctly reflected.**

### TD-005: Returns Module Has 4+ Crash Bugs ✅ RESOLVED (Phase 36)
- **Location:** `returns/models.py:78`, `returns/services.py:120`, `returns/views.py`
- **Status:** ✅ **RESOLVED — All verified-fixed.** `ReturnOrder.clean()` properly guards null invoice. `ReturnService` does not exist (renamed to `ReconciliationService` with different API). `RefundExecutionService` export fixed in Phase 36.

### TD-006: Journal Engine post_entry Overwrites Original Date
- **Location:** `accounting/services/journal_engine.py:237,270`
- **Status:** ❌ **STALE — Not in current code.** Verified: `post_entry()` source contains no `entry_date` override logic. The date is preserved as passed to `create_entry()`.

---

## HIGH DEBT (Phase 36/37 — 7 Resolved/Stale, 3 Remaining)

### TD-007: 12 Core API V1 Endpoints Use AllowAny ❌ STALE — Already Fixed
- **Status:** ❌ **STALE** — Verified: All API v1 endpoints (`autonomous.py`, `intelligence.py`, `truth.py`, `governance.py`, `observability_api.py`, `financial_control_tower.py`, `payment_operations.py`, `ficl_views.py`, `core/operations/views.py`, `expenses/views.py`, `fixed_assets/views.py`, `hr/views.py`) already use `IsAuthenticated`. Permission migration completed in prior phases.

### TD-008: AllowAny Endpoints in Security Views ✅ RESOLVED (Phase 36)
- **Status:** ✅ **RESOLVED** — `logout_view` changed to `IsAuthenticated`, `change_password` received missing `@permission_classes([IsAuthenticated])`. Remaining AllowAny endpoints (login, password-reset) legitimately need open access for unauthenticated users.

### TD-009: Invoice Dispatch Without Stock Check ✅ VERIFIED CORRECT (Phase 37)
- **Location:** `sales/views.py:298-310`
- **Status:** ✅ **VERIFIED CORRECT** — Full code-path trace completed in Phase 37: `dispatch_invoice()` → `StockIntegrationService.process_sale()` explicitly calls `get_total_available_stock(product, warehouse)` before allocation. If `available < quantity`, the operation fails with errors and the `transaction.atomic()` block rolls back. Stock check IS enforced on every dispatch.

### TD-010: No Negative Stock Prevention ❌ STALE — Infrastructure Exists
- **Status:** ❌ **STALE** — `StockIntegrationService` already has `get_available_batches()` and `get_total_available_stock()` methods that check quantity before OUT movements. The original bug referenced `inventory/views.py:180-200` but the stock movement creation is handled through `StockIntegrationService`, not inventory views.

### TD-011: PaymentEngine Allocation Crash ❌ STALE — Non-Existent Method
- **Status:** ❌ **STALE** — `PaymentEngine` class has no `allocate_to_invoices()` method. Bug references code that doesn't exist in current codebase.

### TD-012: Workflow ViewSet References Non-Existent Functions ❌ STALE — Non-Existent Class
- **Status:** ❌ **STALE** — `WorkflowViewSet` class does not exist. Workflow views use `WorkflowInstanceViewSet`, `ApprovalChainViewSet`, `ApprovalRequestViewSet`.

### TD-013: Duplicated Test Files (6 Files) 🔴 REMAINS OPEN — Detailed Audit (Phase 37)
- **Locations:** `tests/test_services.py`, `tests/test_services_correct.py`, `tests/test_services_comprehensive.py`, `tests/test_views_behavior.py`, `tests/test_views_extra.py`, `tests/test_views_comprehensive.py`, `tests/test_quick_coverage.py`, `tests/test_quick_coverage2.py`
- **Status:** 🔴 **REMAINS OPEN** — Phase 37 audit verified all 8 files exist with overlapping scope:
  - **`test_services.py`** (~220 lines): Tests `AccountHierarchyService` (tree, balances, ancestors/descendants) + `ReportExporter` (CSV/text for all 7 report types). Two test classes, ~25 test methods.
  - **`test_services_correct.py`** (~160 lines): Method-existence checks only — uses `hasattr()` on `JournalEngine`, `InvoiceCalculator`, `TaxCalculator`, `DiscountCalculator`, `CurrencyConverter`, `ReportExporter`. 6 test classes, ~40 `def test_*_exists` methods. Zero functional assertions.
  - **`test_services_comprehensive.py`** (~350 lines): Full functional tests for `JournalEngine` (create/post/unpost/reverse/ledger), `ReportExporter` (direct `_export_*_csv` calls), `InvoiceCalculator`, `TaxCalculator`, `DiscountCalculator`, `CurrencyConverter`. 6 test classes, ~30 test methods. Duplicates scope of the other two service test files.
  - **`test_views_behavior.py`** (~100 lines): Basic CRUD tests for Account, JournalEntry, Customer, Product, Report, Dashboard views. Uses `self.assertIn(response.status_code, [200, 403, 404])` pattern. 5 test classes, ~10 test methods.
  - **`test_views_extra.py`** (~200 lines): Extended CRUD tests for Accounting (bulk, export), Sales (dispatch, cancel, PDF, statement, reports), Purchases (receive, cancel, statement, reports), Inventory (detail, update, warehouse, adjustment, transfer, valuation), Payments (create, reconcile), HR (employee, department, attendance, leave), Payroll (salary, payroll run, payslip). 6+ test classes, ~30 test methods.
  - **`test_views_comprehensive.py`** (~200 lines): Additional CRUD tests for Accounting (detail, update, post, filter), Sales (customer CRUD, invoice create), Purchases (supplier CRUD, invoice create), Inventory (product CRUD, pagination, warehouse, batch, stock movements), Payments (methods, accounts, transactions), HR/Payroll (employee, department, attendance, payroll list), Reports (inventory, sales, purchase), Filters (search). 8+ test classes, ~30 test methods. Significant overlap with `test_views_extra.py`.
  - **`test_quick_coverage.py`** (~120 lines): Lightweight service method existence + model creation + basic API + lifecycle + validation + security import tests. 6 test classes, ~15 test methods. Designed as quick coverage boosters.
  - **`test_quick_coverage2.py`** (~160 lines): Functional service tests — creates actual entries, posts them, verifies trial balance and P&L outputs. Tests inventory batch operations, account balance changes, reversal impact. 3 test classes, ~10 test methods.
  - **Overlap summary**: 3 files test the same services (services.py, services_correct.py, services_comprehensive.py). 3 files test the same views (views_behavior.py, views_extra.py, views_comprehensive.py). 2 files are quick coverage boosters (quick_coverage.py, quick_coverage2.py) but overlap with both services and views.
  - **Consolidation strategy**: Merge `test_services_correct.py` method-existence checks into `test_services_comprehensive.py` (delete `test_services_correct.py`). Merge `test_views_behavior.py` and `test_views_extra.py` into `test_views_comprehensive.py` (delete `test_views_behavior.py` and `test_views_extra.py`). Merge `test_quick_coverage2.py` into `test_quick_coverage.py` (delete `test_quick_coverage2.py`). Target: 8 files → 4 files (~3h savings).

### TD-014: FiscalPeriod Unique Constraint Migration Risk ✅ RESOLVED — SAFE (Phase 37)
- **Status:** ✅ **RESOLVED — SAFE** — Verified in Phase 37: Migration `0009_fiscal_period_governance.py` is **already applied** (confirmed via `MigrationRecorder`). PostgreSQL `unique_together` treats NULLs as distinct in unique constraints, so existing single-tenant records (NULL company) won't collide. Safe for single-tenant. Multi-tenant with NULL company values is a theoretical edge case, not a real blocker.

### TD-015: Simulation Has 6+ Duplicated Classes 🔴 REMAINS OPEN — Detailed Audit (Phase 37)
- **Locations:** `backend/simulation/predictive/warnings/*.py`, `backend/simulation/predictive/trends/*.py`, `backend/simulation/predictive/safety/*.py`, `backend/simulation/predictive/probability/*.py`
- **Status:** 🔴 **REMAINS OPEN** — Phase 37 audit confirmed 11+ duplicated classes found via source inspection:
  - `predictive/warnings/engine.py:EarlyWarningEngine` ↔ `predictive/warnings/early_warning_engine.py:EarlyWarningEngine`
  - `predictive/warnings/deduplicator.py:WarningDeduplicator` ↔ `predictive/warnings/warning_deduplicator.py:WarningDeduplicator`
  - `predictive/warnings/classifier.py:WarningSeverityClassifier` ↔ `predictive/warnings/warning_severity_classifier.py:WarningSeverityClassifier`
  - `predictive/warnings/retention.py:WarningRetentionManager` ↔ `predictive/warnings/warning_retention_manager.py:WarningRetentionManager`
  - `predictive/trends/velocity.py:DriftVelocityTracker` ↔ `predictive/trends/drift_velocity_tracker.py:DriftVelocityTracker`
  - `predictive/trends/analyzer.py:DriftTrendAnalyzer` ↔ `predictive/trends/drift_trend_analyzer.py:DriftTrendAnalyzer`
  - `predictive/trends/forecast.py:DriftForecastWindow` ↔ `predictive/trends/drift_forecast_window.py:DriftForecastWindowGenerator`
  - `predictive/safety/memory_guard.py:PredictiveMemoryGuard` ↔ `predictive/safety/predictive_memory_guard.py:PredictiveMemoryGuard`
  - `predictive/safety/isolation.py:PredictionFailureIsolation` ↔ `predictive/safety/prediction_failure_isolation.py:PredictionFailureIsolation`
  - `predictive/safety/performance.py:PredictivePerformanceMonitor` ↔ `predictive/safety/predictive_performance_monitor.py:PredictivePerformanceMonitor`
  - `predictive/probability/weights.py:ProbabilityWeightRegistry` ↔ `predictive/probability/probability_weight_registry.py:ProbabilityWeightRegistry`
  - Also: `digital_twin/integrity/matrix.py:IntegrityMatrix` ↔ `digital_twin/pipeline/digital_twin.py:IntegrityMatrix`, `digital_twin/integrity/replay_validator.py:ReplayValidator` ↔ `replay/validation/replay_validator.py:ReplayValidator`
  - **Impact**: 11+ duplicated classes across the simulation `predictive/` subdirectory. Each pair has a short-name file (e.g., `engine.py`) and a descriptive-name file (e.g., `early_warning_engine.py`). Likely created during code reorganization where files were renamed but originals were not deleted. Active code imports from descriptive names; short-name files appear orphaned. Est. fix: 4 hours (requires verifying each pair for import safety before deletion).
  - **Note**: Original estimate of "6 duplicated classes" was an undercount. Actual count is 11+.

### TD-016: UI Has 57 Blocking Calls on Main Thread 🔴 REMAINS OPEN — Frontend
- **Locations:** `frontend/ui/` — various screens using synchronous QTableWidget operations
- **Status:** 🔴 **REMAINS OPEN** — Frontend issue, outside backend audit scope. Original scan detected 57 blocking synchronous calls on the main Qt thread, causing UI freeze during data operations. Fix requires converting synchronous API calls to async or moving data loading to background threads. BUG_REGISTRY.md references this as BUG-012. Est. fix: 4 hours.

---

## MEDIUM DEBT (Phase 36/38 — 7 Resolved/Stale, 0 Remaining)

### TD-017: Report Governance Rate Limit Doesn't Handle ConnectionError ✅ Resolved
- **Status:** ✅ **RESOLVED** — Already fixed. `report_governance.py` uses specific exception types (`ConnectionError`, `ValueError`) with proper logging, not bare `except:`.

### TD-018: FinancialTruthEngine Silently Swallows Exceptions ❌ Stale
- **Status:** ❌ **STALE** — `FinancialTruthEngine` has no `financial_health()` method. The class exposes `get_customer_balance`, `get_supplier_balance`, etc. Bug references non-existent code.

### TD-019: Decimal Precision Loss in Bulk Operations ❌ STALE — Line 250 Does Not Exist
- **Location:** `core/balance_sync.py:250`
- **Status:** ❌ **STALE** — Verified in Phase 37: Current `balance_sync.py` is only ~160 lines. The reported line 250 does not exist. The file uses `Decimal('0.00')` throughout with proper aggregation via `.aggregate(total=Sum(...)) or Decimal('0.00')`. No Decimal precision bug found in current code. The file was likely truncated during prior refactoring.

### TD-020: FEFO Non-Deterministic for Same-Expiry Batches ✅ RESOLVED — Applied (Phase 38)
- **Location:** `inventory/service/stock_integration.py:62`
- **Status:** ✅ **RESOLVED — Applied (Phase 38)** — All 6 sort sites patched:
  - `stock_integration.py:62` — FEFO sort: `order_by('expiry_date', 'manufacturing_date', 'id')`
  - `stock_integration.py:65` — FIFO sort: `order_by('manufacturing_date', 'expiry_date', 'id')`
  - `stock_integration.py` (process_transfer) — FEFO: `order_by('expiry_date', 'id')`
  - `inventory/views.py:403` — FIFO batch list: `order_by('manufacturing_date', 'id')`
  - `inventory/views.py:420` — FEFO batch list: `order_by('expiry_date', 'id')`
  - `inventory/service/transfer_service.py:68` — Transfer batch selection: `order_by('expiry_date', 'id')`
  - **Fix**: Added `'id'` as tertiary sort key at all 6 sites, ensuring deterministic ordering even when batches share identical expiry/manufacturing dates.

### TD-021: ReturnOrder COMPLETED Status Unreachable ✅ RESOLVED — Signal Handler Applied (Phase 38)
- **Location:** `returns/models.py:23-29`
- **Status:** ✅ **RESOLVED — Signal Handler Applied (Phase 38)**
  - Added `ReturnOrder.complete()` model method — transitions APPROVED → COMPLETED with validation, supports optional `completed_by` param for audit trail
  - Created `returns/signals.py` with `post_save` signal handler `auto_complete_return_order` — after any ReturnOrder save where status=APPROVED and approved_by is set, auto-transitions to COMPLETED using `update()` to avoid recursive signal firing
  - Updated `returns/apps.py` `ReturnsConfig.ready()` to import signals module
  - **Design rationale**: All post-approval processing (inventory restore, accounting entries, reconciliation creation, refund execution) happens inside `approve()` before the final save. By the time the signal fires, all heavy lifting is done. Non-blocking failures (e.g., refund errors) are already logged as warnings in approve() — completing the return doesn't mask them, as they're recorded in logs and notes.

### TD-022: FiscalPeriodCloseLog.save_log() Not Implemented ❌ Stale
- **Status:** ❌ **STALE** — Referenced from `period_service.py` which does not exist. The `FiscalPeriodCloseLog` model exists but was never referenced by any current code.

### TD-023: BalanceSheet Division by Zero Risk ❌ Stale
- **Status:** ❌ **STALE** — `BalanceSheetReport` class does not exist. Reports consolidated into `FinancialReportEngine`. Bug references non-existent class.

### TD-024: Account Type Discrepancy ✅ RESOLVED — CONSISTENT (Phase 37)
- **Location:** Accounting model migrations
- **Status:** ✅ **RESOLVED — CONSISTENT** — Verified in Phase 37: Migration `0003_fix_account_category_null` already exists and handles the account_category null consistency. The model field definitions (`account_type`: CharField, not-null with choices; `account_category`: CharField, null-allowed with choices) are consistent across all 9 applied migrations. No discrepancy found.

---

## LOW DEBT (Phase 36/37 — 2 Resolved, 1 Remaining, 1 Superseded)

### TD-025: Orphaned Helper Functions in Backup System ✅ Partially Resolved
- **Status:** ✅ **PARTIALLY RESOLVED** — Git diff shows bare `except:` clauses in `backup/backup_system.py:277,666,721` have been replaced with specific exception types (`ImportError`, `KeyError`, `AttributeError`, `OSError`, `json.JSONDecodeError`, `ValueError`, `TypeError`). Remaining bare handlers may exist.

### TD-026: Export Engine Catch-All Exception Handling ✅ Resolved
- **Status:** ✅ **RESOLVED** — Git diff shows `BaseExporter.format_amount` exception handling was already updated to catch specific types (`ValueError`, `TypeError`) instead of bare `except:`. Also fixed `Alignment` import pattern and `openpyxl.utils.get_column_letter` reference.

### TD-027: 8+ Duplicated Test Files Need Consolidation ✅ SUPERSEDED BY TD-013 (Phase 37)
- **Location:** `tests/*.py`
- **Status:** ✅ **SUPERSEDED** — Same scope as TD-013 (duplicated test files). Phase 37 audit confirmed both track the same 8 files. TD-013 has the authoritative audit evidence with consolidation strategy. TD-027 was the original seed entry; superseded by TD-013's more detailed analysis. 0 hours — covered by TD-013's 3h estimate.

### TD-028: UI Governance Scanner Has 2 Non-Existent References 🔴 Remains Open — Frontend
- **Location:** frontend governance scanner
- **Status:** 🔴 **REMAINS OPEN** — Frontend issue, outside backend audit scope. The governance scanner at `frontend/scripts/governance_scanner.py` references screen names that no longer exist in `main_window.py`'s screen registry, producing false positives. Fix: Update scanner's screen reference list or auto-generate from current code. Est. fix: 1 hour.

---

## DEBT MANAGEMENT POLICY

- New debt items MUST be appended with next available TD-NNN ID
- When debt is resolved, update status to RESOLVED with date and fix description
- NEVER delete historical debt entries
- Debt classification (Critical/High/Medium/Low) MUST include impact justification

*This document is append-only. Do not modify or delete existing entries.*
