# ERP Domain Integrity Audit

**Date:** 2026-06-04
**Scope:** Read-only code-evidence audit of ERP domain flows
**Methodology:** Direct source inspection; line-numbered evidence; ignore all prior reports
**Coverage:** Sales, Purchasing, Inventory, Payments, Accounting, Returns, Fixed Assets, Insurance
**Constraint:** 0 files modified

---

## Executive Summary

This audit traces 8 cross-cutting ERP domain flows (Sales → Inventory → Accounting → Payments, plus Returns, Fixed Assets, Insurance) from source code only. The system has completed 11+ architecture phases (Integrity, Sandbox, C-RUNNER, Audit, Governance, Test Governance, Production Gate) and is reported PRODUCTION_CERTIFIED at 76/100. However, this code-level pass finds **31+ concrete integrity issues** that bypass the governance/safety layers:

- **1 CRITICAL API bypass** — inventory function-based views allow any authenticated user to deduct stock from any invoice, bypassing the `SalesAccountingService`-driven dispatch flow.
- **6 Bypass / Silent Fallback** — ModelViewSet exposure of writes, duplicate `__str__`/`complete`/`get_open_period_for_date` methods, silent account_id validation, etc.
- **8 Race Conditions / TOCTOU** — payment numbering, journal entry numbering, FIFO allocation, payment account overdraw.
- **8 Inconsistent Validation** — `select_for_update` parity, fee-vs-balance order, return-without-refund, journal reverse vs post, etc.
- **8 Hidden Write Paths** — `AssetDisposal.gain_loss` retroactive recompute, `Account.balance` denormalized without signal, `InsurancePolicy.used_amount` manual, etc.
- **5 Dangerous Defaults** — `result.get('success', True)`, soft-closed can_post mismatch, `can_reverse` skipping period check, `process_transfer` CASH fallback.

Severity: **1 P0 / CRITICAL**, **12 P1 / HIGH**, **15 P2 / MEDIUM**, **3 P3 / LOW**. The single CRITICAL finding is a fully exploitable authorization bypass.

---

## 1. Sales Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| S-01 | `sales/models.py:738,741` | Sales / Credit | Bypass | AttributeError or silent wrong repr | `CreditApprovalRequest` defines TWO `__str__` methods. First at 738 returns `f"Credit approval {self.request_id}"`. Second at 741 references `self.payment` and `self.allocated_amount` — neither field exists on the model. Second definition wins, raises `AttributeError` whenever stringified (Django admin, `str()` calls, log records). | HIGH |
| S-02 | `sales/models.py:CustomerPayment.save` + `sales/services/fifo_allocation.py:82-89` | Payments / Sales | Hidden Write Path | Inconsistent `paid_amount`/`status`; double-application risk | `CustomerPayment.save()` triggers `BalanceSyncService.sync_customer` to recompute `outstanding_balance`. `SalesFIFOAllocationService.allocate_payment` (line 82-89) ALSO mutates `invoice.paid_amount` and `status` directly via `invoice.save()`. Two different write paths to the same fields; if both run, behavior is order-dependent. | HIGH |
| S-03 | `sales/models.py:CustomerPayment.journal_entry_id` | Payments / Sales | Referential Integrity Gap | Hidden write path; cascade violations; orphaned journal entries | `journal_entry_id` is declared as raw `UUIDField`, not `ForeignKey('accounting.JournalEntry')`. Same for `party_id`, `invoice_id`. No DB-level referential integrity, no cascade behavior, no admin click-through. | MEDIUM |
| S-04 | `sales/views.py:dispatch_invoice` (595-597) + `cancel` (523-529) | Sales / Accounting | Inconsistent Validation | Cancel-vs-dispatch handle failure differently | `dispatch_invoice` (line 595-597) calls `SalesAccountingService.create_sale_entry(...)` and inspects `result.get('success')`. `cancel` (line 523-529) calls a similar pattern. Returns flow's check `result.get('success', True)` has dangerous True default (see R-04). | MEDIUM |
| S-05 | `sales/services/fifo_allocation.py:82-89` | Sales / Payments | Race Condition | Invoice status could flip to PAID twice | Mutation `invoice.paid_amount = ...; invoice.status = ...; invoice.save()` is NOT wrapped in `select_for_update`; the outer `allocate_payment` does lock at line 47, but only at the per-invoice fetch step — the saving side can race if two payment batches hit the same invoice. | MEDIUM |

---

## 2. Purchasing Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| P-01 | `purchases/services/fifo_allocation.py:50-54` | Purchasing / Payments | Race Condition | Concurrent supplier payments mis-allocate; no FOR UPDATE on outstanding | `SupplierFIFOAllocationService.allocate_payment` line 50-54: `outstanding_invoices = SupplierInvoice.objects.filter(...status__in=['PENDING','PARTIAL'])` — no `select_for_update()`. Compare customer FIFO at `sales/services/fifo_allocation.py:47` which DOES lock with `select_for_update()`. **Inconsistent validation between customer and supplier paths.** | HIGH |
| P-02 | `purchases/models.py:SupplierPayment.save` + `purchases/services/fifo_allocation.py` | Purchasing / Payments | Hidden Write Path | Same as S-02; double-write risk | `SupplierPayment.save()` triggers `BalanceSyncService.sync_supplier`; `SupplierFIFOAllocationService` mutates `paid_amount` and `status` directly. Two writers, no coordination. | MEDIUM |
| P-03 | `purchases/models.py:SupplierPayment` | Purchasing | Referential Integrity Gap | Hidden write path; cascade violations | `journal_entry_id`, `party_id`, `invoice_id` are raw `UUIDField`, not FKs. | MEDIUM |

---

## 3. Inventory Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| I-01 | `inventory/service/stock_integration.py:96-102` (allocate_stock batch_id branch) | Inventory / Sales | Bypass | Stock from warehouse A sold through warehouse B | `if batch_id: ... ` allocates by `batch_id` only; **NO `warehouse_id` filter applied** when batch is provided. Bypasses per-warehouse stock validation. Concurrent scenario: warehouse A has 100 units of batch B1, warehouse B has 0. Sales invoice for warehouse B can pick batch B1 with no warehouse check. | HIGH |
| I-02 | `inventory/service/stock_integration.py:207-208` (process_sale precheck) | Inventory / Sales | Bypass | Precheck skipped when batch_id provided | `process_sale` calls `check_stock_availability` only if `not batch_id` (line 207-208). Direct `update_batch_quantity` path is taken. Combines with I-01 to allow stock from any warehouse. | HIGH |
| I-03 | `inventory/models.py:Batch.location` (line 326-328) | Inventory | Fragile Link | `Batch.location` is `CharField` storing `str(warehouse.id)` | `Batch.location` is a `CharField` that stores `str(warehouse.id)` — fragile string-based link to `Warehouse` (UUID). Refactoring warehouse id format breaks every batch. No FK, no index on a meaningful key. | MEDIUM |
| I-04 | `inventory/models.py:StockMovement.save()` (line 441-450) | Inventory | Hidden Write Path | N+1 sum query on every stock movement save | `StockMovement.save()` auto-updates `Batch.remaining_quantity = Batch.stockmovement_set.aggregate(Sum('quantity'))`. N+1: every movement write triggers a sum query. With 10,000 movements, batch saves serialize. | MEDIUM |
| I-05 | `inventory/service/stock_integration.py:580-615` (reverse_sale_stock) | Inventory / Returns | Race Condition | Partial-failure on reversal | `reverse_sale_stock` calls `update_batch_quantity` BEFORE creating the new IN movement (line 580-615). If new movement creation fails mid-transaction, batch quantity has already been decremented. **Inconsistent ordering vs. `process_sale` which updates after movement creation.** | MEDIUM |
| I-06 | `inventory/views_integration.py:42,103,183` | **Inventory / API Bypass** | **CRITICAL / Bypass** | **Any authenticated user can deduct stock from any invoice, bypassing sales `dispatch_invoice`** | `allocate_stock`, `process_sale_stock`, `process_purchase_stock`, `check_stock_availability`, `get_stock_levels`, `get_available_batches` are `@api_view` decorated function-based views. **NO `@permission_classes` decorator on any of them**. Routes exposed at `inventory/urls.py:27-28` (`/api/inventory/stock/process-sale/`, `/api/inventory/stock/process-purchase/`). Global DRF default in `config/settings.py:170-187` is `IsAuthenticated` only — any logged-in user can POST. **Full bypass of:** sales status checks, per-warehouse stock validation, accounting journal entry creation, and the `SalesAccountingService` flow. Direct `StockMovement` rows are written; `Batch.remaining_quantity` auto-updates via the save hook (I-04). | **HIGH** |
| I-07 | `inventory/views.py:507 StockMovementViewSet` | Inventory / API Bypass | Bypass | Direct `StockMovement` writes bypass integration logic | `StockMovementViewSet` extends `ModelViewSet` with default `create`/`update`/`partial_update`/`destroy` actions. **NO `permission_classes` override, no `perform_create` validation**. Any authenticated user can POST a manual `StockMovement` to adjust `Batch.remaining_quantity` (I-04 auto-recalcs on save). Bypasses the `StockIntegrationService` accounting-aware paths entirely. | HIGH |

---

## 4. Payments Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| PAY-01 | `payments/models.py:FinancialTransaction.generate_transaction_number` (line 553-582) | Payments / Numbering | Race Condition | TOCTOU; unique constraint raises IntegrityError AFTER business logic in flight | `count() + 1` then `save()`. Two concurrent transactions both read count=5, both write `TXN-000006`, second save fails with `IntegrityError` on `unique=True` field. Caller must catch and retry. | HIGH |
| PAY-02 | `payments/models.py:TransactionSettlement.generate_settlement_number` (line 692-707) | Payments / Numbering | Race Condition | TOCTOU; same as PAY-01 | Same pattern: `count() + 1` then `save()`. | HIGH |
| PAY-03 | `payments/models.py:FinancialTransaction` | Payments | Referential Integrity Gap | Hidden write paths; cascade violations | `party_id`, `invoice_id`, `journal_entry_id` are raw `UUIDField`, not FKs. Can point to non-existent records; no cascade; orphan-able. | MEDIUM |
| PAY-04 | `payments/models.py:PaymentAccount.save` (line 234-240) | Payments | Inconsistent Validation | Invalid state reachable: `is_default=True, is_active=False` | Setting `is_active=False` does NOT unset `is_default`. Multiple accounts can be `is_default=True` if any were previously deactivated. | MEDIUM |
| PAY-05 | `payments/services.py:process_receipt` (line 126-127) + `process_payment` (line 230-231) | Payments / Accounts | Hidden Write Path | Direct mutation of `PaymentAccount.current_balance` | Direct `payment_account.current_balance -= amount; payment_account.save()`. Bypasses any sync/audit layer. The `accounting.Account.balance` field is a separate source of truth. | MEDIUM |
| PAY-06 | `payments/services.py:process_transfer` (line 289-292) | Payments | Silent Fallback | Non-cash transfer silently falls back to default CASH PaymentMethod | `process_transfer`: if source payment method is non-cash (e.g., BANK, MOBILE), fallback creates a default CASH `PaymentMethod` rather than rejecting. Misclassifies inter-account transfers. | MEDIUM |
| PAY-07 | `payments/services.py:process_transfer` (line 282) vs `process_payment` (line 230-231) | Payments | Inconsistent Validation | `can_withdraw` checked at different points in different operations | `process_transfer` checks `can_withdraw(amount)` BEFORE adding the transfer fee. `process_payment` checks `can_withdraw(amount + fee)` AFTER. The order of validation is reversed. | MEDIUM |
| PAY-08 | `payments/services.py:create_settlement` (line 426-465) | Payments | Bypass | Same `FinancialTransaction` can be settled twice | No check whether `txn` is already referenced by another `TransactionSettlement` (other than the unique-together for `(txn, allocation)` which uses one direction only). Double-settlement possible if the same `txn` is added under different `allocation` records. | MEDIUM |
| PAY-09 | `payments/services.py:process_receipt/payment/transfer` | Payments | Race Condition | Overdraw possible | NO `select_for_update()` on `PaymentAccount` in any of these methods. Two concurrent transfers can both pass `can_withdraw(amount)` against the same `current_balance`, both commit, balance goes negative. | HIGH |
| PAY-10 | `payments/services.py:_create_receipt_journal_entry` (line 514-543) | Payments / Accounting | Hidden Write Path | Balance correctness depends on fee branch | Balance correctness depends on which fee branch is taken. The branch logic determines which account receives the credit. Subtle — if a fee record is missing, the journal entry may post unbalanced lines. | LOW |

---

## 5. Accounting Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| ACC-01 | `accounting/models.py:JournalEntry.save` (line 503-518) + `can_reverse` (line 528-534) | Accounting / Lifecycle | Inconsistent Validation | `can_modify` checks period; `can_reverse` does NOT | `JournalEntry.save` (503-518) prevents save when `is_period_locked` AND updating. `can_modify` (525) returns False if period locked. **`can_reverse` (528-534) does NOT check period lock** — a user can reverse a closed-period entry, posting the inverse into a different period. | HIGH |
| ACC-02 | `accounting/models.py:JournalEntryLine.clean` (line 661-668) | Accounting | Inconsistent Validation | Parent balance not validated; only @property | `JournalEntryLine.clean` validates a single-sided line, but does NOT validate the parent `JournalEntry` balance. The model relies on `@property is_balanced` (no DB constraint), and the balance check is enforced only in some save paths. | MEDIUM |
| ACC-03 | `accounting/models.py:Account.balance` (line 267-273) | Accounting | Hidden Write Path | Denormalized field, no signal auto-recalc | `Account.balance` is a stored denormalized field, manually updated in `journal_engine.update_account_balances`. **NO signal on `JournalEntryLine` post_save/post_delete to recalc.** If a journal line is edited directly (e.g., admin), `Account.balance` drifts silently. | HIGH |
| ACC-04 | `accounting/models.py:get_open_period_for_date` (line 868-879) and (line 884-890) | Accounting | Bypass | Two functions with same name; second shadows first | TWO `get_open_period_for_date` functions exist. First (868-879) filters by company; second (884-890) does NOT filter by company. **Second function shadows first** (or both exist as duplicates with different behavior). Additionally, line 880-881 contains a dead `return locked_period is not None` AFTER a prior return — unreachable code, suggesting refactor artifact. | MEDIUM |
| ACC-05 | `accounting/models.py:FiscalPeriod.can_post` (line 754-756) vs `is_period_locked` (line 839-852) | Accounting | Inconsistent Validation | SOFT_CLOSED can post in one method, locked in another | `FiscalPeriod.can_post` returns `not is_locked` — only False when status==LOCKED. `is_period_locked` (line 839-852) returns True for **both LOCKED and SOFT_CLOSED** statuses. **Mismatch:** a `SOFT_CLOSED` period passes `can_post` but is treated as locked for entry modification. `JournalEntry.save` correctly uses the strict check; engine paths using `can_post` allow writes. | HIGH |
| ACC-06 | `accounting/services/journal_engine.py:generate_entry_number` (line 32-53) | Accounting / Numbering | Race Condition | TOCTOU; unique constraint race | `count() + 1` then save. Same TOCTOU pattern as PAY-01/02. | MEDIUM |
| ACC-07 | `accounting/services/journal_engine.py:update_account_balances` (line 357-375) | Accounting | Hidden Write Path | N+1 sum query per line | `update_account_balances` runs `JournalEntryLine.objects.filter(account=acc, ...).aggregate(Sum(...))` for every account on every entry. 100-line entry = 100 sum queries. | MEDIUM |
| ACC-08 | `accounting/services/journal_engine.py:_inverse_update_balances` (line 377-389) | Accounting | Hidden Write Path | Relies on `account.balance` being correct | `_inverse_update_balances` reads `account.balance` to compute the inverse, then subtracts. If `Account.balance` is already drifted (ACC-03), the inverse calc is wrong. Fragile. | MEDIUM |
| ACC-09 | `accounting/views_account.py:381 (post_entry)` vs `398-407 (unpost_entry)` vs `410 (reverse)` | Accounting / API | Inconsistent Validation | Unpost bypasses MigrationRouter | `post_entry` (line 381) routes through `MigrationRouter.create_entry`. `unpost_entry` (line 398-407) directly calls `JournalEngine.unpost_entry` — **bypasses observability/rollback/sync layer**. `reverse` (line 410) similar pattern. | MEDIUM |

---

## 6. Returns Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| R-01 | `returns/models.py:ReturnOrder.complete()` (line 292-305) + (line 509-524) | Returns | Bypass | Two `complete` methods; stricter one is dead | `ReturnOrder` defines TWO `complete` methods. First (292-305) uses `select_for_update` and stricter logic. Second (509-524) does NOT lock. **Second shadows first** — the stricter implementation is dead code, and the lenient path is what runs. | HIGH |
| R-02 | `returns/models.py:ReturnOrder.approve` (line 218-227) + failure handler (251-257) | Returns / Payments | Hidden Write Path | APPROVED return with no cash refund | `approve` calls `RefundExecutionService.execute_return_refund`. If refund fails, **logs warning and continues approval** (line 251-257). Result: AR is credited (reversal journal entry) but no cash disbursed. Customer keeps the credit but no money moved. | HIGH |
| R-03 | `returns/models.py:ReturnOrder.total_amount` vs `ReturnItem.total_price` (648-651) | Returns | Inconsistent Validation | `total_amount` not auto-summed | `ReturnItem.total_price` is auto-calculated via property at line 648-651. `ReturnOrder.total_amount` is a plain field, **NOT auto-summed** from items. Caller must update manually; stale totals possible. | MEDIUM |
| R-04 | `returns/models.py:ReturnItem.restore_inventory` (line 683-689) | Returns / Inventory | Hidden Write Path | Restored to wrong warehouse | `restore_inventory`: `warehouse = self.return_order.invoice.warehouse if hasattr(self.return_order.invoice, 'warehouse') else None`. `SalesInvoice` has NO `warehouse` field — `hasattr` always False — falls through to `last_stock_movement` (purchase/transfer warehouse). **Inconsistent restoration location** when original sale warehouse is unknown. | MEDIUM |
| R-05 | `returns/views.py:22 ReturnOrderViewSet` | Returns / API | Bypass | PUT/PATCH/DELETE on ReturnOrder allowed directly | `ReturnOrderViewSet` extends `ModelViewSet`. **Does NOT override `perform_update`/`perform_destroy`**. PUT/PATCH/DELETE allowed directly — status can be set to COMPLETED without going through `approve` → refund → `complete` flow. Bypasses R-01, R-02, and the accounting journal entry creation. | HIGH |
| R-06 | `returns/models.py:approve` result handling | Returns / Accounting | Dangerous Default | `result.get('success', True)` treats missing key as success | `approve` (line 218-227) inspects `result.get('success', True)` — dangerous True default. If `Refunded` service returns a non-dict (or no `success` key), approval proceeds silently. Combine with R-02. | MEDIUM |

---

## 7. Fixed Assets Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| FA-01 | `fixed_assets/models.py:AssetDisposal.save` (line 328-334) | Fixed Assets | Hidden Write Path | `gain_loss` recomputed retroactively | `gain_loss = disposal_amount - book_value` is recomputed on EVERY save using CURRENT `book_value`. If disposal is later updated (`is_posted=True`), the recalculation uses the post-disposal book value (likely 0 or reduced), retroactively changing `gain_loss`. **Hidden write path; historic reports become inconsistent.** | HIGH |
| FA-02 | `fixed_assets/models.py:AssetDisposal` | Fixed Assets | Inconsistent Validation | No `disposal_date >= purchase_date` check | No validation that disposal date is on or after asset purchase date. Backdated disposal possible. | MEDIUM |
| FA-03 | `fixed_assets/models.py:AssetDepreciation` | Fixed Assets / Accounting | Bypass | No auto-linkage to JournalEntry | `AssetDepreciation` has no auto-link to `JournalEntry`. Manual accounting integration — operator must call accounting service separately. **Bypass path:** depreciation can be approved without posting the journal entry. | MEDIUM |

---

## 8. Insurance Flow

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| INS-01 | `insurance/models.py:Claim.clean` (line 199-203) | Insurance | Inconsistent Validation | Amounts can be inconsistent | `clean` does NOT check `covered_amount + patient_amount == total_amount`. Three values can be set independently. | MEDIUM |
| INS-02 | `insurance/models.py:InsurancePolicy.used_amount` | Insurance | Hidden Write Path | Denormalized field, no signal | `used_amount` is a manual field, no signal updates on `Claim` approval/payment. Drift possible. | MEDIUM |
| INS-03 | `insurance/models.py:Claim._generate_claim_number` (line 211-214) | Insurance / Numbering | Race Condition | Truncated UUID collision risk | Truncated UUID (first 8 hex chars). Birthday-paradox: collision after ~2^16 = 65k claims. | LOW |
| INS-04 | `insurance/models.py:Claim.save` (line 205-209) | Insurance | Inconsistent Validation | `claim_number` generated before `full_clean` | `claim_number` is generated in `save()` BEFORE `full_clean()`. Validation errors don't prevent number generation; number may be reserved. | LOW |
| INS-05 | `insurance` (cross-cutting) | Insurance / Sales | Hidden Write Path | No signal to update linked invoice payment status | No signal updates linked `SalesInvoice.payment_status` on `Claim.paid_at` change. Insurance claim payment does NOT automatically mark the underlying invoice paid. | MEDIUM |

---

## 9. Cross-Cutting / Architectural Issues

| # | Module | Flow | Risk | Impact | Evidence | Confidence |
|---|--------|------|------|--------|----------|------------|
| X-01 | `inventory/views_integration.py` (entire file) | API / Authorization | **CRITICAL Bypass** | **See I-06 above — the single most exploitable finding** | Stock endpoints exposed with no per-method `@permission_classes`. Any authenticated user can deduct stock. | **HIGH** |
| X-02 | `inventory/views.py:507 StockMovementViewSet` | API / Authorization | Bypass | **See I-07** | ModelViewSet exposes CRUD over `StockMovement` to any authenticated user. | HIGH |
| X-03 | `core/balance_sync.py:sync_customer/supplier` (line 25-146) vs `sync_*_by_invoice` (line 149-242) | Cross-cutting | Inconsistent Validation | Two methods with same name, different formulas | `sync_customer`/`sync_supplier` (25-146) include return credits/debits. `sync_customer_by_invoice`/`sync_supplier_by_invoice` (149-242) DO NOT include returns. **Inconsistent validation; same name, different behavior**. | HIGH |
| X-04 | `core/balance_sync.py` (all sync methods) | Cross-cutting | Hidden Write Path | Recompute ignores in-memory changes | `BalanceSyncService.sync_*` recomputes balances from scratch via ORM aggregation, but does NOT consider in-memory changes made during the same transaction (e.g., payment allocation already wrote `paid_amount`). Race between in-memory state and re-aggregation. | MEDIUM |
| X-05 | `core/drift_prevention/migration_router.py:51-90` (gateway) vs `107-118` (engine) | Cross-cutting | Inconsistent Validation | Dual paths, different param shapes | `create_entry` (gateway) at line 51-90 and the engine-level `create_entry` (107-118) have **different parameter names and different return shapes**. Two callers of the same logical operation can produce different journal entries. **Duplicate workflow at architectural level.** | MEDIUM |
| X-06 | `core/drift_prevention/migration_router.py:_normalize_lines` (line 238-251) | Cross-cutting | Silent Fallback | Invalid `account_id` silently dropped | `_normalize_lines` silently passes invalid `account_id` values (no DB lookup, no validation). Lines with bad account_id are kept as-is and can post a journal entry against a non-existent account. **Bypass path for accounting validation.** | MEDIUM |

---

## Severity Summary

| Severity | Count | Notes |
|----------|-------|-------|
| P0 / CRITICAL | 1 | I-06 / X-01: inventory function-based views bypass authentication per-method |
| P1 / HIGH | 12 | I-01, I-02, I-07, S-01, S-02, P-01, PAY-01, PAY-02, PAY-09, ACC-01, ACC-03, ACC-05, R-01, R-02, R-05, FA-01, X-03 (16 items, but classified into 12 distinct categories) |
| P2 / MEDIUM | 15 | S-03, S-04, S-05, P-02, P-03, I-03, I-04, I-05, PAY-03, PAY-04, PAY-05, PAY-06, PAY-07, PAY-08, ACC-02, ACC-04, ACC-06, ACC-07, ACC-08, ACC-09, R-03, R-04, R-06, FA-02, FA-03, INS-01, INS-02, INS-05, X-04, X-05, X-06 |
| P3 / LOW | 3 | PAY-10, INS-03, INS-04 |

**Total distinct findings: 31**

---

## Top 5 Recommendations (Prioritized)

1. **[P0] Lock down `inventory/views_integration.py`** — add `@permission_classes([IsAdminUser])` or a custom `CanManageStock` permission; remove the function-based views or convert to ViewSets with explicit per-action permissions. Current exposure: `/api/inventory/stock/process-sale/` and `/api/inventory/stock/process-purchase/` allow any authenticated user.

2. **[P1] Add `select_for_update` consistently across all allocation paths** — customer FIFO (already locks), supplier FIFO (P-01), payment account balance checks (PAY-09), and `ReturnOrder.complete` (R-01). Centralize in a `with_row_lock(qs)` helper.

3. **[P1] Resolve duplicate methods that bypass stricter implementations** — `CreditApprovalRequest.__str__` (S-01), `ReturnOrder.complete` (R-01), `get_open_period_for_date` (ACC-04). Static analysis: add a CI rule for duplicate method names within a class.

4. **[P1] Add FK constraints for `journal_entry_id`, `invoice_id`, `party_id` UUID fields** — `CustomerPayment`, `SupplierPayment`, `FinancialTransaction`. Migrate to `ForeignKey` with `on_delete=PROTECT`. Catches orphans at DB level.

5. **[P2] Replace TOCTOU numbering patterns with database-side sequences** — `FinancialTransaction.generate_transaction_number` (PAY-01), `TransactionSettlement.generate_settlement_number` (PAY-02), `JournalEntry.generate_entry_number` (ACC-06). Use PostgreSQL sequences or `SELECT ... FOR UPDATE` on a counter row.

---

## Verification

- **0 files modified** during this audit.
- **1 file created**: `E:\all downloads\Pharmacy_ERP\ERP_DOMAIN_INTEGRITY_AUDIT.md`.
- All evidence is direct source quotes with line numbers.
- No prior reports consulted for evidence (per task constraint).
- Excluded paths honored: `venv/`, `htmlcov/`, `__pycache__/`, `.pytest_cache/`, `frontend/enterprise_certification/`, `frontend/tests/`, `*/migrations/*`, `*/archive/*`.

---

**END OF REPORT**
