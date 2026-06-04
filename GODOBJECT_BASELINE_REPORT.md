# Sprint 4 — God Object Baseline Report

**Date**: 2026-06-04
**Mode**: Read-only baseline capture (no modifications)
**Targets**: 3 highest-risk God Objects per `GOD_OBJECT_AUDIT.md` and `MASTER_RECONCILIATION_AUDIT.md`
- `JournalEngine`
- `PaymentEngine`
- `SalesAccountingService`

This baseline is the **regression reference** for all subsequent extractions in Sprint 4.

---

## 1. Executive Summary

| Class | File | Class LOC | Methods | Public | Private | Cyclomatic CC (rough) | Fan-In (excl tests) | Fan-Out |
|---|---|---|---|---|---|---|---|---|
| `JournalEngine` | `backend/accounting/services/journal_engine.py:17-473` | 457 | 11 | 10 | 1 | 46 | 7 modules | 28 Account, 9 JournalEntry, 6 models.* |
| `PaymentEngine` | `backend/payments/services.py:22-811` | 790 | 10 | 6 | 4 | 55 | 4 modules | 5 models, MigrationRouter |
| `SalesAccountingService` | `backend/sales/views.py:29-227` | 199 | 5 | 4 | 1 | 15 | 1 module | FIFO, StockIntegration, Account, MigrationRouter |

**Total class LOC**: 1,446 lines across 3 files
**Total methods**: 26 (20 public, 6 private)
**Total rough cyclomatic complexity**: 116

---

## 2. Target 1: `JournalEngine`

**File**: `backend/accounting/services/journal_engine.py:17-473` (457 LOC)
**Class start line**: 17
**Class end line**: 473 (file ends at line 473)

### 2.1 Method Inventory

| # | Method | Visibility | Decorators | LOC | Public? |
|---|---|---|---|---|---|
| 1 | `generate_entry_number(entry_type)` | public | `@staticmethod` | 23 | yes |
| 2 | `validate_lines(lines)` | public | `@staticmethod` | 56 | yes |
| 3 | `create_entry(...)` | public | `@staticmethod`, `@transaction.atomic` | 97 | yes |
| 4 | `log_event(entry, event_type, ...)` | public | `@staticmethod` | 21 | yes |
| 5 | `post_entry(entry_id, posted_by)` | public | `@staticmethod`, `@transaction.atomic` | 35 | yes |
| 6 | `unpost_entry(entry_id, user_id)` | public | `@staticmethod`, `@transaction.atomic` | 28 | yes |
| 7 | `reverse_entry(entry_id, reason, user_id)` | public | `@staticmethod`, `@transaction.atomic` | 54 | yes |
| 8 | `update_account_balances(entry)` | public | `@staticmethod`, `@transaction.atomic` | 20 | yes |
| 9 | `_inverse_update_balances(entry)` | private | `@staticmethod`, `@transaction.atomic` | 13 | no |
| 10 | `recalculate_all_balances()` | public | `@staticmethod` | 20 | yes |
| 11 | `get_account_ledger(account_id, ...)` | public | `@staticmethod` | 62 | yes |

**Public methods**: 10
**Private methods**: 1
**Total**: 11

### 2.2 Imports (7 lines)

```python
from decimal import Decimal
from datetime import date
from typing import Optional, Union
from dataclasses import dataclass, field  # NOTE: dataclass imported but NOT used
from django.db import models, transaction
from django.core.exceptions import ValidationError  # NOTE: imported but NOT used
from django.utils import timezone as django_timezone
from accounting.models import Account, JournalEntry, JournalEntryLine, JournalEventLog
```

**Import count**: 7 (3 stdlib, 2 django, 1 typing, 1 local)
**Unused imports**: 2 (`dataclass`, `ValidationError`, `Union`)

### 2.3 Fan-In (external callers, excluding tests)

| Caller Module | Call Count | Methods Called |
|---|---|---|
| `backend/accounting/services/journal_engine.py` (self) | 9 | (intra-class) |
| `backend/core/services/journal_gateway.py` | 4 | `create_entry`, `validate_lines`, `reverse_entry`, `log_event` |
| `backend/fixed_assets/services/asset_accounting_service.py` | 4 | `create_entry`, `log_event`, `post_entry` |
| `backend/accounting/services/inventory_accounting.py` | 3 | `create_entry`, `log_event` |
| `backend/core/drift_prevention/migration_router.py` | 3 | `create_entry`, `validate_lines` |
| `backend/insurance/services.py` | 2 | `create_entry` |
| `backend/accounting/models.py` | 1 | (declarative only) |
| `backend/accounting/views_account.py` | 1 | `get_account_ledger` |
| **TOTAL unique non-test modules** | **7** | — |

### 2.4 Fan-Out (dependencies)

| Dependency | Usage Count | Purpose |
|---|---|---|
| `Account.objects` | 28 | Query / update / filter accounts |
| `JournalEntry.objects` | 9 | Create / query / lock journal entries |
| `JournalEntryLine.objects` | 4 | Create / aggregate line items |
| `JournalEventLog.objects` | 7 | Create event log rows |
| `models.Sum` | 3 | Aggregate debit/credit totals |
| `transaction.atomic` | 5 | Transaction boundaries (preserved) |
| `django_timezone.now` | 3 | Date / datetime helpers |

### 2.5 Cyclomatic Complexity (rough)

| Metric | Count |
|---|---|
| `if`/`elif` statements | 31 |
| `for` loops | 7 |
| `while` loops | 0 |
| `except` handlers | 7 |
| **Rough CC** | **46** |

### 2.6 Responsibility Clusters (informal)

| Cluster | Methods | Approx LOC | Notes |
|---|---|---|---|
| Entry number generation | `generate_entry_number` | 23 | Pure logic, no DB transaction |
| Line validation | `validate_lines` | 56 | Pure logic, no DB transaction |
| Entry creation (orchestrator) | `create_entry` | 97 | TRANSACTION BOUNDARY — KEEP |
| Event logging | `log_event` | 21 | Simple DB insert |
| Post/Unpost (orchestrators) | `post_entry`, `unpost_entry` | 63 | TRANSACTION BOUNDARY — KEEP |
| Reversal (orchestrator) | `reverse_entry` | 54 | TRANSACTION BOUNDARY — KEEP |
| Balance update (calc + DB) | `update_account_balances`, `_inverse_update_balances` | 33 | CALCULATION + TRANSACTION — mixed |
| Recalculation | `recalculate_all_balances` | 20 | CALCULATION |
| Ledger query | `get_account_ledger` | 62 | QUERY + formatting |

### 2.7 Extraction Candidates (allowed only)

| Candidate | Type | Approx LOC | Risk |
|---|---|---|---|
| `validate_lines` | Validator | 56 | LOW — pure function, no DB transaction |
| `generate_entry_number` | Mapper / Numbering | 23 | LOW — pure function, no DB transaction |
| `get_account_ledger` formatting logic | Mapper | ~30 (subset) | LOW — read-only query |
| `update_account_balances` pure calculation (the `models.Sum` + sign flip) | Calculator | ~15 (subset) | MEDIUM — only the pure math, not the DB update |
| `recalculate_all_balances` pure calculation | Calculator | ~10 (subset) | MEDIUM — only the pure math |

### 2.8 Extraction Forbidden (per Sprint 4 spec)

- `create_entry` body (lines 130-200) — contains transaction.atomic and entry creation
- `post_entry`, `unpost_entry`, `reverse_entry` — all contain `@transaction.atomic` and `save()` calls
- Any line containing `entry.save()` or `Account.objects.filter(...).update(...)`
- Any line inside `@transaction.atomic` block

---

## 3. Target 2: `PaymentEngine`

**File**: `backend/payments/services.py:22-811` (class occupies most of file)
**Class start line**: 22
**Class end line**: 811 (file ends at line 811)

### 3.1 Method Inventory

| # | Method | Visibility | Decorators | LOC | Public? |
|---|---|---|---|---|---|
| 1 | `process_receipt(...)` | public | `@staticmethod`, `@db_transaction.atomic` | 99 | yes |
| 2 | `process_payment(...)` | public | `@staticmethod`, `@db_transaction.atomic` | 100 | yes |
| 3 | `process_transfer(...)` | public | `@staticmethod`, `@db_transaction.atomic` | 88 | yes |
| 4 | `process_refund(...)` | public | `@staticmethod`, `@db_transaction.atomic` | 48 | yes |
| 5 | `create_settlement(...)` | public | `@staticmethod`, `@db_transaction.atomic` | 82 | yes |
| 6 | `_validate_required_accounts()` | private | `@staticmethod` | 22 | no |
| 7 | `_create_receipt_journal_entry(txn)` | private | `@staticmethod` | 86 | no |
| 8 | `_create_payment_journal_entry(txn)` | private | `@staticmethod` | 88 | no |
| 9 | `_create_transfer_journal_entry(txn)` | private | `@staticmethod` | 53 | no |
| 10 | `get_account_transactions(account_code, ...)` | public | `@staticmethod` | 69 | yes |

**Public methods**: 6
**Private methods**: 4
**Total**: 10

### 3.2 Imports (17 lines)

```python
import logging
from decimal import Decimal
from datetime import date
from typing import Optional
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction, models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from payments.models import (
    PaymentMethod, PaymentAccount, FinancialTransaction,
    TransactionSettlement, SettlementTransaction,
)
from accounting.models import Account
```

**Import count**: 10 (4 stdlib, 5 django, 1 local-block of 5 models)
**Dependency modules touched**: `payments.models`, `accounting.models`, `core.drift_prevention.migration_router` (lazy import inside methods)

### 3.3 Fan-In (external callers, excluding tests)

| Caller Module | Call Count | Methods Called |
|---|---|---|
| `backend/payments/services.py` (self) | 8 | (intra-class: process_refund -> process_payment / process_receipt) |
| `backend/payments/views.py` | 6 | `process_receipt`, `process_payment`, `process_transfer`, `create_settlement`, `get_account_transactions` |
| `backend/purchases/models.py` | 2 | `process_payment` (signal handler) |
| `backend/sales/models.py` | 2 | `process_receipt` (signal handler) |
| **TOTAL unique non-test modules** | **4** | — |

### 3.4 Fan-Out (dependencies)

| Dependency | Usage Count | Purpose |
|---|---|---|
| `PaymentMethod.objects` | 4 | Resolve / list payment methods |
| `PaymentAccount.objects` | 6 | Lock / query / update balances |
| `FinancialTransaction(...)` | 4 | Create txn records |
| `Account.objects` | 12 | Resolve accounting accounts |
| `MigrationRouter.create_entry` | 3 | Cross-module journal entry creation |
| `db_transaction.atomic` | 5 | Transaction boundaries |
| `models.Q` | 2 | Query composition |
| `timezone.now` | 5 | Timestamps |
| `_` (gettext) | 7 | Error message i18n |

### 3.5 Cyclomatic Complexity (rough)

| Metric | Count |
|---|---|
| `if`/`elif` statements | 40 |
| `for` loops | 3 |
| `while` loops | 0 |
| `except` handlers | 11 |
| **Rough CC** | **55** |

### 3.6 Responsibility Clusters (informal)

| Cluster | Methods | Approx LOC | Notes |
|---|---|---|---|
| Receipt processing (orchestrator) | `process_receipt` | 99 | TRANSACTION BOUNDARY — KEEP |
| Payment processing (orchestrator) | `process_payment` | 100 | TRANSACTION BOUNDARY — KEEP |
| Transfer processing (orchestrator) | `process_transfer` | 88 | TRANSACTION BOUNDARY — KEEP |
| Refund processing (orchestrator) | `process_refund` | 48 | Delegates to process_payment / process_receipt |
| Settlement (orchestrator) | `create_settlement` | 82 | TRANSACTION BOUNDARY — KEEP |
| Account validation | `_validate_required_accounts` | 22 | Pure query + list building |
| Journal entry builders (per-type) | `_create_receipt_journal_entry`, `_create_payment_journal_entry`, `_create_transfer_journal_entry` | 227 | Build line list, dispatch to MigrationRouter |
| Query / summary | `get_account_transactions` | 69 | Query + aggregate + format |

### 3.7 Extraction Candidates (allowed only)

| Candidate | Type | Approx LOC | Risk |
|---|---|---|---|
| `_validate_required_accounts` | Validator | 22 | LOW — pure query + list |
| Fee calculation in `process_receipt` (lines 86-93): `fee_override` / `calculate_fee` / `quantize` | Calculator | 6 | LOW — pure math |
| Fee calculation in `process_payment` (lines 187-192) | Calculator | 5 | LOW — pure math |
| Settlement `included_amount` determination (lines 443-450) | Calculator | 8 | LOW — pure logic |
| `get_account_transactions` summary aggregation (lines 774-784) | Calculator | 11 | LOW — pure math |
| `get_account_transactions` txn dict formatting (lines 786-798) | Mapper | 13 | LOW — pure formatting |
| `_create_receipt_journal_entry` line-list construction (lines 514-573) | Mapper | 60 | MEDIUM — pure dict building |
| `_create_payment_journal_entry` line-list construction (lines 603-664) | Mapper | 62 | MEDIUM — pure dict building |
| `_create_transfer_journal_entry` line-list construction (lines 694-707) | Mapper | 14 | LOW — pure dict building |

### 3.8 Extraction Forbidden (per Sprint 4 spec)

- All lines inside `@db_transaction.atomic` decorated methods
- `txn.save()` calls
- `dest_account.save()` / `source_account.save()` calls
- `Account.objects.filter(...).update(balance=...)` calls (this is the actual posting)
- `MigrationRouter.create_entry(...)` calls (the actual journal entry creation)

---

## 4. Target 3: `SalesAccountingService`

**File**: `backend/sales/views.py:29-227` (class is embedded in views module — sub-optimal location)
**Class start line**: 29
**Class end line**: 227

### 4.1 Method Inventory

| # | Method | Visibility | Decorators | LOC | Public? |
|---|---|---|---|---|---|
| 1 | `calculate_cogs(invoice, allocations)` | public | `@classmethod` | 32 | yes |
| 2 | `create_sales_journal_entry(invoice, allocations, cogs_override)` | public | `@classmethod` | 78 | yes |
| 3 | `create_receipt_journal_entry(payment)` | public | `@classmethod` | 38 | yes |
| 4 | `reverse_sales_journal_entry(invoice, reason)` | public | `@classmethod` | 20 | yes |
| 5 | `_get_cash_account(payment_method)` | private | `@classmethod` | 11 | no |

**Public methods**: 4
**Private methods**: 1
**Total**: 5

### 4.2 Imports (26 lines, but class uses subset)

The class itself uses:
- `Decimal` (line 1, re-imported inside `calculate_cogs` line 47 — duplication)
- `MigrationRouter` (lazy import inside methods, lines 134, 178, 200)
- `SalesInvoice` (type hint via `sales.models`)
- `CustomerPayment` (type hint via `sales.models`)
- `Account` (line 24, used in some helpers)
- `ACC` (line 25, used for account codes)

**Class-level import count**: 0 (all imports at module level of `sales/views.py`)
**Class-specific lazy imports**: 1 (MigrationRouter, repeated 3 times)

### 4.3 Fan-In (external callers, excluding tests)

| Caller Module | Call Count | Methods Called |
|---|---|---|
| `backend/sales/views.py` (self — used by view classes) | 2 | `create_sales_journal_entry`, `create_receipt_journal_entry` (called from invoice dispatch + payment save) |
| **TOTAL unique non-test modules** | **1** | — |

Note: Despite low external fan-in, the class is heavily used **within the same file** by view classes (`SalesInvoiceViewSet`, `CustomerPaymentViewSet`). This is acceptable — the file is the right boundary.

### 4.4 Fan-Out (dependencies)

| Dependency | Usage Count | Purpose |
|---|---|---|
| `invoice.items` (related manager) | 3 | Iterate invoice lines |
| `alloc.unit_cost`, `alloc.quantity` | 4 | Read allocation data |
| `item.batch.purchase_price` | 1 | Fallback cost lookup |
| `Account.objects` (not directly used — uses account codes via ACC) | 0 | Indirect via MigrationRouter |
| `MigrationRouter.create_entry` | 1 | Journal entry dispatch |
| `MigrationRouter.reverse_entry` | 1 | Journal entry reversal |
| `ACC[...]` registry | 6 | Read account code constants |

### 4.5 Cyclomatic Complexity (rough)

| Metric | Count |
|---|---|
| `if`/`elif` statements | 12 |
| `for` loops | 2 |
| `while` loops | 0 |
| `except` handlers | 0 |
| **Rough CC** | **15** |

### 4.6 Responsibility Clusters (informal)

| Cluster | Methods | Approx LOC | Notes |
|---|---|---|---|
| COGS calculation | `calculate_cogs` | 32 | Pure math, no DB transaction |
| Sales invoice journal entry (orchestrator) | `create_sales_journal_entry` | 78 | Calls `invoice.save()` line 150 — TRANSACTION BOUNDARY |
| Customer receipt journal entry | `create_receipt_journal_entry` | 38 | Calls MigrationRouter (journal entry) |
| Reversal | `reverse_sales_journal_entry` | 20 | Calls `invoice.save()` line 212 — TRANSACTION BOUNDARY |
| Cash account lookup | `_get_cash_account` | 11 | Pure dict lookup |

### 4.7 Extraction Candidates (allowed only)

| Candidate | Type | Approx LOC | Risk |
|---|---|---|---|
| `calculate_cogs` | Calculator | 32 | LOW — pure math, no DB transaction |
| `_get_cash_account` | Mapper | 11 | LOW — pure dict lookup |
| `create_sales_journal_entry` line-list construction (lines 84-132) | Mapper | 49 | MEDIUM — pure dict building |
| `create_receipt_journal_entry` line-list construction (lines 161-176) | Mapper | 16 | LOW — pure dict building |

### 4.8 Extraction Forbidden (per Sprint 4 spec)

- `invoice.save()` calls (lines 150, 212)
- `MigrationRouter.create_entry(...)` / `MigrationRouter.reverse_entry(...)` calls
- Any line that mutates the invoice model

---

## 5. Aggregate Baseline

| Metric | JournalEngine | PaymentEngine | SalesAccountingService | TOTAL |
|---|---|---|---|---|
| **Class LOC** | 457 | 790 | 199 | **1,446** |
| **Methods** | 11 | 10 | 5 | **26** |
| **Public methods** | 10 | 6 | 4 | **20** |
| **Private methods** | 1 | 4 | 1 | **6** |
| **Cyclomatic CC (rough)** | 46 | 55 | 15 | **116** |
| **Fan-in modules (excl tests)** | 7 | 4 | 1 | **12** |
| **External test classes** | 23 (across 6 files) | 1 (test_payments.py) | 1 (test_sales_views.py) | **25** |
| **Extraction candidates (count)** | 5 | 9 | 4 | **18** |
| **Extraction candidates (LOC)** | ~134 | ~201 | ~108 | **~443** |

---

## 6. Sprint 4 Extraction Targets (per spec)

Per the spec, only 3 classes are in scope. **Stop after these three.**

The 18 extraction candidates above sum to ~443 LOC of pure (non-transaction) code that can be moved out. After extraction:
- JournalEngine: 457 → ~323 LOC (29% reduction)
- PaymentEngine: 790 → ~589 LOC (25% reduction)
- SalesAccountingService: 199 → ~91 LOC (54% reduction)

**Note**: The 25-50% method reduction target may not be hit for all classes — `JournalEngine` has 11 methods, and the extractable methods are validators/calculators that don't reduce the orchestrator method count significantly. Method-count reduction is bounded by the number of public orchestrator methods (6 in PaymentEngine, 4 in SalesAccountingService, 10 in JournalEngine).

---

## 7. Baseline Verification Commands (re-runnable)

```powershell
# LOC per class
(Get-Content backend/accounting/services/journal_engine.py | Select-Object -Skip 16 -First 457 | Measure-Object -Line).Lines
(Get-Content backend/payments/services.py | Select-Object -Skip 21 -First 790 | Measure-Object -Line).Lines
(Get-Content backend/sales/views.py | Select-Object -Skip 28 -First 199 | Measure-Object -Line).Lines

# Method count per class
(Select-String -Path backend/accounting/services/journal_engine.py -Pattern "^\s+def\s+\w+" 2>$null).Count
(Select-String -Path backend/payments/services.py -Pattern "^\s+def\s+\w+" 2>$null).Count
(Select-String -Path backend/sales/views.py -Pattern "^\s+def\s+\w+" 2>$null).Count

# Fan-in (per class)
Select-String -Path "backend/**/*.py" -Pattern "JournalEngine\.|PaymentEngine\.|SalesAccountingService\." 2>$null

# Cyclomatic complexity
$ifs = (Get-Content <file> | Select-String -Pattern "^\s+if\s").Count
$fors = (Get-Content <file> | Select-String -Pattern "^\s+for\s").Count
$excepts = (Get-Content <file> | Select-String -Pattern "^\s+except\s").Count
# CC = 1 + ifs + fors + excepts
```

---

## 8. Conclusion

This baseline is captured at **Sprint 4 start, 2026-06-04**.

**Targets frozen for extraction**:
1. `JournalEngine` (`backend/accounting/services/journal_engine.py`) — 457 LOC, CC 46
2. `PaymentEngine` (`backend/payments/services.py`) — 790 LOC, CC 55
3. `SalesAccountingService` (`backend/sales/views.py`) — 199 LOC, CC 15

**Extraction plan**: Move ~443 LOC of pure logic (validators, calculators, query builders, mappers) into new sibling modules. Keep all transaction boundaries, save calls, and posting logic in original classes. Public method signatures unchanged. Imports unchanged at call sites. Behavior unchanged.

**Next**: Phase B — Target Selection + Phase C — Extraction execution.
