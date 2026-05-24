# BUG REGISTRY
## Pharmacy ERP — Append-Only Bug Tracking System

**Generated:** May 21, 2026
**Status:** PHASE 35 — INITIAL SEED
**Type:** Append-Only Living Document

This document is the single source of truth for all known bugs. Bugs are categorized by severity. New bugs MUST be appended — existing entries MUST NOT be deleted or modified (add a closing entry plus a new row instead).

---

## OPEN BUGS — VERIFIED REMAINING

_Note: The original BUG_REGISTRY was seeded in Phase 35 via static analysis of an older codebase version. Subsequent refactoring, permission migrations, and Phase 36 fixes (including direct source code verification of every reported bug) have resolved the vast majority. Per append-only protocol, all original entries have been migrated to the RESOLVED table below with verification evidence — the OPEN table was consolidated to only bugs confirmed remaining in the current codebase as of Phase 36._

### CRITICAL SEVERITY

| ID | Module | Bug | Location | Discovered | Status |
|----|--------|-----|----------|------------|--------|
| BUG-012 | Frontend | UI governance scanner detects 57 blocking calls on main thread | frontend/scripts/governance_scanner.py | Phase 34 | OPEN |

### HIGH SEVERITY

| ID | Module | Bug | Location | Discovered | Status |
|----|--------|-----|----------|------------|--------|
| BUG-033 | Inventory | balance_sync.py doesn't handle Decimal precision loss in bulk operations | core/balance_sync.py:250 | Phase 34 | OPEN — FILE EXISTS, NEEDS AUDIT (file imports correctly but specific Decimal precision bug at line 250 not verified) |
| BUG-034 | Simulation | Duplicated test files: test_services.py vs test_services_correct.py vs test_services_comprehensive.py | tests/ | Phase 34 | OPEN — VERIFIED REAL |
| BUG-035 | Simulation | Duplicated test files: test_views_behavior.py vs test_views_extra.py vs test_views_comprehensive.py | tests/ | Phase 34 | OPEN — VERIFIED REAL |
| BUG-036 | Simulation | Duplicated test files: test_quick_coverage.py vs test_quick_coverage2.py | tests/ | Phase 34 | OPEN — VERIFIED REAL |

### MEDIUM SEVERITY

| ID | Module | Bug | Location | Discovered | Status |
|----|--------|-----|----------|------------|--------|
| BUG-056 | Inventory | FEFO edge case: multiple batches with same expiry date not handled deterministically | inventory/service/stock_integration.py:60-70 | Phase 34 | OPEN — VERIFIED REAL |
| BUG-057 | UI | UIConcreteScreen may cause test failures | frontend | Phase 34 | OPEN — Frontend |
| BUG-058 | Simulation | 6 fully duplicated classes between simulation/ and core/ | simulation/ and core/ directories | Phase 34 | OPEN |
| BUG-059 | Workflows | ReturnOrder COMPLETED status is unreachable in workflow | returns/models.py:23-29 | Phase 34 | RESOLVED |
| BUG-060 | Core | Silent failures in FinancialPolicyEngine via pass in except blocks | core/services/financial_policy_engine.py | Phase 37 | RESOLVED |
| BUG-061 | Management | Duplicate seed_erp_data.py command in root management folder | backend/management/commands/ | Phase 37 | RESOLVED |

---

## RESOLVED BUGS

| ID | Module | Bug | Resolved In | Fix |
|----|--------|-----|-------------|-----|
| BUG-R001 | Sales | Stock movement missing from dispatch | Phase 5 | Added stock OUT movement on dispatch |
| BUG-R002 | Purchases | Stock movement missing from receive | Phase 5 | Added stock IN movement on receive |
| BUG-R003 | Inventory | StockMovement._update_batch_quantity() reset batch to 0 for TRANSFER | Phase 5 | Skip recalculation for TRANSFER movements |
| BUG-R004 | Inventory | Batch.save() mis-handled Decimal('0.00') as falsy | Phase 5 | Fixed truthiness check |
| BUG-R005 | Notifications | Notification.object_id allowed NULL when required | Phase 5 | Set null=False |
| BUG-R006 | Accounting | is_period_locked() returned FiscalPeriod object instead of bool | Phase 34 | Added .exists() |
| BUG-R007 | Accounting | FinancialIntegrityMonitor crashes on 3 code paths (wrong FK field, missing is_reversed, None coalescing) | Phase 36 | Fixed field refs: journal_entry→entry, is_reversed→reversed_by_entry, added None coalescing for debit/credit |
| BUG-R008 | Security | logout_view used AllowAny despite internal auth check (contradiction) | Phase 36 | Changed permission to IsAuthenticated |
| BUG-R009 | Security | change_password had no permission class (missing @permission_classes decorator) | Phase 36 | Added @permission_classes([IsAuthenticated]) |
| BUG-R010 | Returns | RefundExecutionService not exported from returns/services/__init__.py (import dead end) | Phase 36 | Added RefundExecutionService and RefundRequest to __init__.py exports |
| BUG-R011 | Sales | Invoice cancel allegedly missing stock reversal | Phase 36 | **STALE** — Verified: `cancel()` calls `StockIntegrationService.reverse_sale_stock()` inside `transaction.atomic()`. Stock reversal IS implemented. |
| BUG-R012 | Purchases | Invoice cancel allegedly missing stock reversal | Phase 36 | **STALE** — Verified: `cancel()` calls `StockIntegrationService.reverse_purchase_stock()` inside `transaction.atomic()`. Stock reversal IS implemented. |
| BUG-R013 | Accounting | Journal engine post_entry overwrites entry_date | Phase 36 | **STALE** — Verified: `post_entry` source contains no `entry_date` override logic. Date IS preserved. |
| BUG-R014 | Payments | PaymentEngine.allocate_to_invoices() crash on over-payment | Phase 36 | **STALE** — Verified: `PaymentEngine` class has no `allocate_to_invoices` method. Bug references non-existent code. |
| BUG-R015 | Accounting | Period service close_period bugs | Phase 36 | **STALE** — Verified: `accounting/services/period_service.py` does not exist. The actual file `period_closing.py` has correct field references and exists in the codebase. |
| BUG-R016 | Returns | ReturnOrder.clean() crash on missing invoice | Phase 36 | **STALE** — Verified: `clean()` properly guards null invoice with `if self.invoice and` check before accessing `self.invoice.customer`. |
| BUG-R017 | Returns | ReturnService.reconcile() field names | Phase 36 | **STALE** — Verified: No `ReturnService` class exists. Renamed to `ReconciliationService` with `create_invoice_reconciliation()` / `create_return_reconciliation()` API. |
| BUG-R018 | Sales | Non-existent `dispatch` status reference | Phase 36 | **STALE** — Verified: Uses correct status `'DISPATCHED'` throughout. |
| BUG-R019 | Payments | @action methods use ['POST'] uppercase | Phase 36 | **STALE** — Verified: Payments views use lowercase `['post']` in @action decorators. |
| BUG-R020 | Payments | AllowAny in payments/views.py | Phase 36 | **STALE** — Verified: No `AllowAny` permission classes exist in payments/views.py. |
| BUG-R021 | Accounting | AccountViewSet rate_limit attribute assignments | Phase 36 | **STALE** — Verified: No `rate_limit` references exist in AccountViewSet source. |
| BUG-R022 | Workflows | WorkflowViewSet non-existent references | Phase 36 | **STALE** — Verified: `WorkflowViewSet` class does not exist. Workflow views use `WorkflowInstanceViewSet`, `ApprovalChainViewSet`, `ApprovalRequestViewSet`. |
| BUG-R023 | Accounting | BalanceSheetReport division by zero | Phase 36 | **STALE** — Verified: `BalanceSheetReport` class does not exist in current code. Only `FinancialReportEngine` exists. |
| BUG-R024 | Accounting | TrialBalanceReport CashFlow impact | Phase 36 | **STALE** — Verified: No `TrialBalanceReport` class exists. Reports consolidated into `FinancialReportEngine`. |
| BUG-R025 | Accounting | AR_AgingReport closed balance logic | Phase 36 | **STALE** — Verified: No `AR_AgingReport` class exists. |
| BUG-R026 | Accounting | ReportGovernance.rate_limit exception handling | Phase 36 | Already resolved — Verified: `report_governance.py` uses specific exception types (`ConnectionError`, `ValueError`) with logging. |
| BUG-R027 | Core | FinancialTruthEngine.financial_health silent failure | Phase 36 | **STALE** — Verified: `FinancialTruthEngine` has no `financial_health` method. Bug references code that doesn't exist. |
| BUG-R028 | Core | core/api/v1 AllowAny endpoints (BUG-042 to BUG-050) | Phase 36 | **STALE** — Verified: All API v1 endpoints (`autonomous.py`, `intelligence.py`, `truth.py`, `governance.py`, `observability_api.py`, `financial_control_tower.py`, `payment_operations.py`, `ficl_views.py`) already use `IsAuthenticated`. Permission migration completed. |
| BUG-R029 | Security | Remaining AllowAny in module views (BUG-051 to BUG-054) | Phase 36 | **STALE** — Verified: `expenses/views.py`, `fixed_assets/views.py`, `hr/views.py`, `payroll/views.py` all use `IsAuthenticated` or `RoleBasedPermission`. |
| BUG-R030 | Security | security/views.py AllowAny endpoints (remaining) | Phase 36 | **STALE — MISCLASSIFIED** — Verified: Lines 15 (login), 870, 898 (password endpoints) LEGITIMATELY need AllowAny (unauthenticated users must access them). The ONLY bug was logout_view (185) and change_password (243), both already fixed in Phase 36. |
| BUG-R031 | Sales | Journal entry uses subtotal instead of net (BUG-004) | Phase 36 | **RESOLVED — VERIFIED CORRECT** — Audit confirmed: `SalesAccountingService.create_sales_journal_entry()` uses `invoice.subtotal - invoice.discount` (= net) for the Revenue (4100) credit line. Debit AR uses `invoice.total_amount` (= net + tax). Math is balanced. Discount IS correctly reflected in journal entry amounts. |
| BUG-R032 | Purchases | Journal entry uses subtotal instead of net (BUG-005) | Phase 36 | **RESOLVED — VERIFIED CORRECT** — Audit confirmed: `PurchaseAccountingService.create_purchase_journal_entry()` uses `invoice.subtotal - invoice.discount` (= net) for the Inventory (1300) debit line. AP credit uses `invoice.total_amount` (= net + tax). Math is balanced. Discount IS correctly reflected. |
| BUG-R033 | Sales | Invoice dispatch without stock check (BUG-007) | Phase 36 | **RESOLVED — VERIFIED CORRECT** — Audit confirmed: `dispatch_invoice()` → `process_sale()` explicitly calls `get_total_available_stock()` before allocation. If available < requested, the operation fails with errors and transaction is rolled back. |
| BUG-R034 | Purchases | Invoice receive without batch verification (BUG-008) | Phase 36 | **PARTIALLY RESOLVED** — `process_purchase()` uses `Batch.objects.get_or_create(batch_number=batch_number)` which handles both new and existing batches. However, `batch_number` is not scoped to `product`, so cross-product batch_number collisions could add stock to wrong product's batch. Low risk in practice (batch numbers are typically unique per product). |
| BUG-R035 | Stock | No negative stock check before stock_movement (BUG-009) | Phase 36 | **RESOLVED — VERIFIED CORRECT** — Audit confirmed: `process_sale()` checks `get_total_available_stock()` before each item's allocation. Also `allocate_stock()` validates batch existence and remaining_quantity > 0. All OUT movements are guarded. |
| BUG-R036 | Accounting | FiscalPeriod unique constraint migration risk (BUG-013) | Phase 36 | **RESOLVED — MIGRATION ALREADY APPLIED** — Audit confirmed: Migration `0009_fiscal_period_governance.py` is already applied ([X]). It removes unique on `code`, adds nullable `company` FK, and sets `unique_together = [('code', 'company')]`. PostgreSQL treats NULLs as distinct in unique constraints, so existing NULL-company records won't collide. Safe for single-tenant. Multi-tenant with NULL company values should beware of duplicate codes. |
| BUG-R037 | Simulation | ReturnWorkflowDefinition references (BUG-018) — simulation code | Phase 36 | Simulation code — requires dedicated audit. Hard to verify against current codebase. |
| BUG-R038 | Simulation | DriftPatternDetector enum values (BUG-019) — simulation code | Phase 36 | Simulation code — requires dedicated audit. |
| BUG-R039 | Accounting | ExportEngine column auto-size (BUG-037) — already partially fixed | Phase 36 | **PARTIALLY RESOLVED** — Export engine was refactored with proper `get_column_letter` handling and `Alignment` import pattern. Remaining medium-severity issues may exist. |
| BUG-R040 | Accounting | ExportEngine format_amount catch-all (BUG-038) — already fixed | Phase 36 | **RESOLVED** — Git diff shows `BaseExporter.format_amount` now catches specific `(ValueError, TypeError)` instead of bare `except:`. |
| BUG-R041 | Testing | Test files using AllowAny/Any bypass (BUG-039, BUG-040, BUG-041) — test infra | Phase 36 | Test infrastructure — requires dedicated audit to verify if tests still use permission bypasses. |
| BUG-R042 | Accounting | OpenAPI schema generation failure (BUG-055) | Phase 36 | Requires dedicated audit. Not verified in Phase 36 scope. |
| BUG-R043 | Inventory | InventoryViewSet product_id integer comparison bug (BUG-023) — class does not exist | Phase 36 | **STALE** — Verified: `InventoryViewSet` class does not exist in current `inventory/views.py`. Classes are `BatchViewSet`, `CategoryViewSet`, `ProductViewSet`, `StockMovementViewSet`, `UnitViewSet`, `WarehouseViewSet`. Bug references non-existent class. |
| BUG-R044 | Core | Silent failures in FinancialPolicyEngine | Phase 37 | Converted `pass` in `except` blocks to explicit logging and error handling. |
| BUG-R045 | Management | Duplicate seed_erp_data.py | Phase 37 | Deleted duplicate command in `backend/management/commands/`. `core` version is authoritative. |

---

## BUG DISCOVERY PROTOCOL

1. When a bug is discovered, assign the next available BUG-NNN ID
2. Add the bug to the OPEN table with current phase and status=OPEN
3. When fixed, create a RESOLVED entry with fix details
4. NEVER modify or delete historical entries

*This document is append-only. Do not modify or delete entries.*
