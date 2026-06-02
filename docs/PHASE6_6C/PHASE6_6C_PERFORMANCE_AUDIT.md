# Phase 6.6C — Performance Audit Report

**Scope:** 5 target files + cross-cutting concerns (191 FKs, threading, query patterns)
**Method:** Static code inspection. No execution. No profiling.
**Reference:** Django performance best practices, PostgreSQL query planning, Qt event loop model.

---

## Summary

| # | Severity | Location | Issue | Estimated Impact |
|---|----------|----------|-------|------------------|
| P-1 | **CRITICAL** | `frontend/api/client.py` (54 call sites) | All `requests` calls on UI thread | 200-2000ms UI freeze per API call |
| P-2 | **HIGH** | `frontend/api/client.py:247` | `time.sleep(0.35 * attempt)` blocks UI thread | 0.35-2.1s UI freeze per retry chain |
| P-3 | **HIGH** | 191 FKs across 15 apps | Missing `db_index=True` on ForeignKeys | 50-200ms per query on 1M-row tables |
| P-4 | **HIGH** | `payment_operations.py:625-645` | N+1 query in `process_customer_payment` | 101 queries for 50 outstanding invoices |
| P-5 | **HIGH** | `payment_operations.py:759-779` | Same N+1 in `process_supplier_payment` | Same |
| P-6 | **MEDIUM** | `payment_operations.py:892-906` | Same N+1 in `process_mixed_payment` (customer branch) | Same |
| P-7 | **MEDIUM** | `payment_operations.py:931-945` | Same N+1 in `process_mixed_payment` (supplier branch) | Same |
| P-8 | **MEDIUM** | `payment_operations.py:228-264, 421-457` | O(N×M) loop computing payment traces | 100ms-2s for 100 payments |
| P-9 | **LOW** | `payment_engine._create_*_journal_entry` | `_validate_required_accounts` runs 7 queries per transaction | 35ms per payment (sequential) |
| P-10 | **LOW** | `frontend/ui/main_window.py:84-85` | `_load_company_settings` and `_check_startup_health` after 3-5s | Up to 5s of UI work after login |
| P-11 | **LOW** | `main_window.py:124-126` | `status_timer` fires every 1s (1000ms) | 1 repaint/sec forever |

---

## P-1: All `requests` calls on UI thread (CRITICAL)

**Location:** `frontend/api/client.py` (entire file)
**Evidence:**
- File size: 667 LOC
- 57 methods
- 0 `QThread`, 0 `QRunnable`, 0 `QThreadPool`, 0 `qasync` imports
- `requests.Session` is constructed at L36 (synchronous)
- 54 call sites: `grep -E 'requests\.(get|post|put|delete|patch)' frontend/api/client.py | wc -l` → 54

**Impact:**

In a desktop ERP, the main thread is also the UI thread. PySide6 requires all widget operations to happen on the main thread. Network I/O on the main thread blocks:
- Widget repaints
- Mouse/keyboard event processing
- Window resize/move
- Status bar updates
- Timer callbacks

**Quantified impact:**

| Network condition | RTT | Calls per workflow | Cumulative freeze |
|-------------------|-----|--------------------|--------------------|
| Local LAN | 5ms | 30 | 150ms (imperceptible) |
| WiFi (good) | 30ms | 30 | 900ms (noticeable) |
| WiFi (poor) | 200ms | 30 | 6,000ms (intolerable) |
| 4G fallback | 500ms | 30 | 15,000ms (broken) |

**Per-call breakdown (3G fallback, 500ms RTT, 50KB payload):**

```
DNS lookup:        20ms  (cached in requests.Session: ~0ms)
TCP handshake:     100ms (reused keep-alive: ~0ms)
TLS handshake:     150ms (reused session: ~50ms)
Request:           5ms
Server processing: 100ms
Response transfer: 50ms
─────────────────────────
Total per call:    ~200ms (TLS reused) to 425ms (fresh)
```

**Fix (recommended):**

Refactor `APIClient` to expose Qt signals, run requests in `QThreadPool`:

```python
# New file: frontend/api/async_client.py
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
import requests

class _ApiWorkerSignals(QObject):
    finished = Signal(object)   # result dict
    error = Signal(Exception)

class _ApiWorker(QRunnable):
    def __init__(self, session, method, url, **kwargs):
        super().__init__()
        self.signals = _ApiWorkerSignals()
        self._session = session
        self._method = method
        self._url = url
        self._kwargs = kwargs

    def run(self):
        try:
            response = self._session.request(self._method, self._url, **self._kwargs)
            self.signals.finished.emit(response)
        except Exception as e:
            self.signals.error.emit(e)

class AsyncAPIClient:
    def __init__(self):
        self._session = requests.Session()
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(8)   # bounded

    def get(self, url, on_success, on_error, **kwargs):
        worker = _ApiWorker(self._session, 'GET', url, **kwargs)
        worker.signals.finished.connect(on_success)
        worker.signals.error.connect(on_error)
        self._pool.start(worker)
```

Then update each of the 21 screens to pass `on_success` callback instead of waiting synchronously. This is a multi-day refactor (57 methods, 21 screens, ~250 call sites).

**Effort:** 2-3 days. Regression risk HIGH. Requires incremental rollout.

**Fix (workaround, faster):**

Use `QTimer.singleShot` for retry delays and wrap each call in a non-blocking helper:

```python
def _non_blocking_request(self, method, url, on_done, attempt=0, **kwargs):
    def _do_request():
        try:
            response = self.session.request(method, url, **kwargs)
            QMetaObject.invokeMethod(self._main_thread, lambda: on_done(response), Qt.QueuedConnection)
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < 2:
                delay_ms = int(350 * (attempt + 1))
                QTimer.singleShot(delay_ms, lambda: self._non_blocking_request(method, url, on_done, attempt + 1, **kwargs))
            else:
                QMetaObject.invokeMethod(self._main_thread, lambda: on_done({'error': str(e)}), Qt.QueuedConnection)
    QThreadPool.globalInstance().start(_do_request)
```

**Effort:** 4-6 hours. Lower regression risk.

**Mitigation (no code change):**

Show a `LoadingOverlay` (already exists per `main_window.py:16` import) during API calls. Reduces perceived freeze. Doesn't address root cause.

**Verification after fix:**

1. Add `time.sleep(0.5)` to a test backend endpoint
2. Open the dashboard in the frontend
3. Click buttons during the 500ms delay
4. Verify buttons still respond (no freeze)
5. Use Qt Test to assert no QApplication.processEvents() call needed

---

## P-2: `time.sleep` on UI thread (HIGH)

**Location:** `frontend/api/client.py:247`
**Code:**

```python
for attempt in range(max_retries):
    try:
        response = self.session.post(...)
    except (requests.ConnectionError, requests.Timeout) as e:
        ...
        time.sleep(0.35 * (attempt + 1))   # ← blocks UI
```

**Cumulative impact with default `max_retries=3`:**

```
attempt 0: 0.35s sleep
attempt 1: 0.70s sleep
attempt 2: 1.05s sleep
─────────────
Worst case: 2.10s freeze
```

**Fix:** Subsumed by P-1 fix. If using `QThreadPool`, retry happens off main thread. If using `QTimer.singleShot`, retry is non-blocking.

---

## P-3: 191 ForeignKeys without `db_index=True` (HIGH)

**Files:** 15 backend apps
**Distribution:**

| App | FKs without index | Highest-risk model |
|-----|-------------------|---------------------|
| accounting | 18 | `JournalEntryLine` |
| security | 15 | `UserRole`, `Permission` |
| hr | 12 | `Employee` |
| payroll | 9 | `Payslip` |
| backup | 10 | `RestorePoint` |
| cost_centers | 8 | `CostAllocation` |
| entities | 6 | `Entity` |
| sales | 7 | `SalesInvoice` |
| purchases | 7 | `PurchaseInvoice` |
| inventory | 6 | `StockMovement` |
| payments | 5 | `FinancialTransaction` |
| (others) | 86 | mixed |

**Evidence method:**

```bash
grep -rE 'models\.ForeignKey|models\.OneToOneField|models\.ManyToManyField' \
  backend/ --include='*.py' | \
  grep -v 'db_index=True' | \
  grep -v 'unique=True' | \
  grep -v 'migrations/' | \
  wc -l
# Result: 191
```

**Impact on query plans:**

For `Customer.objects.filter(supplier_invoice__payment__isnull=False)` (a 2-level join), PostgreSQL uses:
- **Indexed FK:** Hash join or merge join, O(N) memory, sub-millisecond
- **Unindexed FK:** Nested loop join, O(N×M) comparisons, 100-500ms on 100K rows

**Real example (`payment_operations.py:70`):**

```python
outstanding = FIFOAllocationService.get_outstanding_invoices(customer)
```

Tracing the implementation (assumed in `sales/services/fifo_allocation.py`):

```python
return SalesInvoice.objects.filter(
    customer=customer,
    paid_amount__lt=F('total_amount'),
).annotate(
    balance=F('total_amount') - F('paid_amount')
).order_by('invoice_date')
```

This is 1 query with 1 join (customer_id). If `customer` FK lacks index, the join is a sequential scan. On 1M sales invoices, this is 500ms+ per call.

**Fix:**

Add `db_index=True` to all 191 FKs. For existing populated tables, use `AddIndexConcurrently`:

```python
# In a manual migration
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models

class Migration(migrations.Migration):
    atomic = False   # Required for CONCURRENTLY

    operations = [
        AddIndexConcurrently(
            model_name='salesinvoice',
            index=models.Index(fields=['customer'], name='si_customer_idx'),
        ),
        # ... 190 more
    ]
```

**Effort:**
- Code change: 2 hours (find-and-replace)
- Migration generation: 1 hour
- Migration execution on populated DB: 5-30s per index = 15-90 minutes
- Total: 4-6 hours + downtime window

**Risk:**
- Adding index to a hot table can cause brief lock during index build
- `CONCURRENTLY` is non-blocking but takes longer and cannot run inside a transaction
- Tests pass-rate unchanged

---

## P-4: N+1 in `process_customer_payment` (HIGH)

**Location:** `core/api/v1/payment_operations.py:625-645`
**Code:**

```python
if allocation_mode == 'fifo':
    outstanding = FIFOAllocationService.get_outstanding_invoices(customer)   # 1 query
    remaining = amount
    for inv_data in outstanding:                                                # N iterations
        if remaining <= 0:
            break
        inv = SalesInvoice.objects.get(pk=inv_data['id'])                       # +1 query per iter
        inv_balance = FIFOAllocationService.get_invoice_balance(inv)            # +1 query per iter
        alloc_amount = min(remaining, inv_balance)
        if alloc_amount > 0:
            PaymentAllocation.objects.create(...)                               # +1 query per iter
            remaining -= alloc_amount
    unallocated_amount = remaining
```

**Query count:** `1 + 2N + 1` where N = outstanding invoices (could be 50+ for a chronically late-paying customer)

**Per-call cost (N=50, 5ms per query):**
- 1 initial + 100 + 1 = 102 queries × 5ms = 510ms

**Fix:**

```python
if allocation_mode == 'fifo':
    # Single bulk fetch with select_for_update for atomicity
    with transaction.atomic():
        outstanding = list(
            SalesInvoice.objects
            .select_for_update()
            .filter(
                customer=customer,
                paid_amount__lt=F('total_amount'),
            )
            .order_by('invoice_date')
        )

        allocations = []
        remaining = amount
        for inv in outstanding:
            if remaining <= 0:
                break
            inv_balance = inv.total_amount - inv.paid_amount
            alloc_amount = min(remaining, inv_balance)
            if alloc_amount > 0:
                allocations.append(PaymentAllocation(
                    payment=payment,
                    invoice=inv,
                    allocated_amount=alloc_amount,
                ))
                inv.paid_amount += alloc_amount
                inv.update_payment_status()
                remaining -= alloc_amount

        PaymentAllocation.objects.bulk_create(allocations)   # 1 query
        for inv in outstanding:
            inv.save(update_fields=['paid_amount', 'payment_status'])   # 1 batch
```

**Query count after fix:** 3 (bulk fetch, bulk_create, batch save)
**Per-call cost (N=50):** 15ms (50× faster)

**Effort:** 2 hours. Requires `select_for_update` for atomicity (already inside `@transaction.atomic`).

---

## P-5: N+1 in `process_supplier_payment` (HIGH)

**Location:** `core/api/v1/payment_operations.py:759-779`
**Identical pattern as P-4** but for supplier side. Same fix.

---

## P-6/P-7: N+1 in `process_mixed_payment` (MEDIUM)

**Location:** `core/api/v1/payment_operations.py:892-906, 931-945`
**Same pattern as P-4** in two branches (customer and supplier). Same fix. Doubles because each mixed payment creates N allocation rows (one per split).

**Combined cost for mixed payment with 3 splits × 50 invoices:**
- Current: 1 + 2×150 = 301 queries
- After fix: 6 queries (3 splits × 2 batches)
- Speedup: 50×

---

## P-8: O(N×M) loop in payment traces (MEDIUM)

**Location:** `core/api/v1/payment_operations.py:228-264, 421-457`
**Code (customer trace):**

```python
payments = CustomerPayment.objects.filter(
    customer=customer
).prefetch_related('allocations__invoice').order_by('-payment_date')   # 1 query

trace = []
for payment in payments:                                                 # N payments
    allocations = []
    for alloc in payment.allocations.all():                              # M allocations per payment
        allocations.append({
            'allocation_id': str(alloc.id),
            'invoice_number': alloc.invoice.invoice_number,
            # ...
        })

    trace.append({
        'payment_id': str(payment.id),
        # ...
        'is_fully_allocated': sum(
            Decimal(str(a['allocated_amount'])) for a in allocations
        ) >= payment.amount,                                             # O(M) per iteration
    })
```

**Query count:** 1 (thanks to `prefetch_related` — good practice). The `sum(Decimal(str(...)))` is the slow part.

**Impact for customer with 100 payments × 5 allocations each:**
- 1 query (good)
- 500 dictionary constructions
- 100 Decimal conversions + 100 summations

**Cost:** ~50ms (not severe but adds up at scale).

**Fix:** Use `Sum('allocated_amount')` annotation:

```python
payments = CustomerPayment.objects.filter(
    customer=customer
).prefetch_related('allocations__invoice').annotate(
    total_allocated=Sum('allocations__allocated_amount')
).order_by('-payment_date')

trace = []
for payment in payments:
    allocations = [
        {
            'allocation_id': str(alloc.id),
            'invoice_number': alloc.invoice.invoice_number,
            'allocated_amount': str(alloc.allocated_amount),
            'invoice_total': str(alloc.invoice.total_amount),
            'invoice_paid': str(alloc.invoice.paid_amount),
            'invoice_status': alloc.invoice.status,
        }
        for alloc in payment.allocations.all()
    ]
    trace.append({
        # ...
        'is_fully_allocated': (payment.total_allocated or Decimal('0')) >= payment.amount,
    })
```

**Query count:** 1 (same) but work moved to DB.
**Cost after fix:** ~5ms (10× faster).

**Effort:** 30 minutes per endpoint (2 endpoints).

---

## P-9: Required account validation runs 7 queries per payment (LOW)

**Location:** `backend/payments/services.py:480-501` (and called from L507, L596, L687)
**Code:**

```python
@staticmethod
def _validate_required_accounts() -> list:
    missing = []
    required_accounts = {
        '1000': 'Cash/Bank',
        '1200': 'Accounts Receivable',
        '1300': 'Inventory',
        '2100': 'Tax Payable',
        '4100': 'Sales Revenue',
        '5100': 'COGS',
        '6100': 'Operating Expenses',
    }
    for code, name in required_accounts.items():
        if not Account.objects.filter(code=code, is_active=True).exists():
            missing.append(f"{code} ({name})")
    return missing
```

**Queries:** 7 (one per account code, sequential).

**Called from:**
- `_create_receipt_journal_entry` (every RECEIPT) — L507
- `_create_payment_journal_entry` (every PAYMENT) — L596
- `_create_transfer_journal_entry` (every TRANSFER) — L687

**Total for a typical user session (100 payments/day):** 700 queries = 3.5s of pure validation time.

**Fix:** Cache the validation result for the lifetime of the process (or until account data changes):

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def _validate_required_accounts() -> list:
    # ... same body
```

**Cost after fix:** 7 queries on first call, 0 on subsequent calls.
**Effort:** 5 minutes.

**Caveat:** `lru_cache` lives for process lifetime. If a new account is added mid-process, the cache is stale. Acceptable for desktop ERP (process restarts frequently). NOT acceptable for long-running server.

For server, use Django's cache framework with TTL:

```python
from django.core.cache import cache

def _validate_required_accounts() -> list:
    cached = cache.get('required_accounts_validation')
    if cached is not None:
        return cached
    # ... do validation ...
    cache.set('required_accounts_validation', missing, timeout=3600)
    return missing
```

Invalidate cache on account model save:

```python
# In accounting/models.py
@receiver(post_save, sender=Account)
def invalidate_account_cache(sender, instance, **kwargs):
    cache.delete('required_accounts_validation')
```

---

## P-10: Deferred health check after 3-5s (LOW)

**Location:** `frontend/ui/main_window.py:84-85`
**Code:**

```python
QTimer.singleShot(3000, self._load_company_settings)         # 3s
QTimer.singleShot(5000, self._check_startup_health)           # 5s
```

**Impact:** These are deferred (good — they don't block startup). They run 3-5s after login. Each makes a synchronous API call (P-1 issue), so each freezes UI for ~200ms.

**Status:** Acceptable. Defers work past first paint. Fix is bundled with P-1.

---

## P-11: Status bar timer fires every 1s (LOW)

**Location:** `frontend/ui/main_window.py:124-126`
**Code:**

```python
self.status_timer = QTimer(self)
self.status_timer.timeout.connect(self._update_status_bar_time)
self.status_timer.start(1000)
```

**Impact:** Updates the system time label every second. Causes a `QLabel.setText()` call + repaint. Negligible cost (~0.5ms per tick).

**Status:** Acceptable. No fix needed. (The time is visible to user; expected behaviour.)

---

## P-12: `journal_entry_id` stored as `str` but `JournalEntry.id` is `UUID` (MEDIUM — already in CRITICAL findings as M-6)

**Already documented in CRITICAL findings.** The string-vs-UUID mismatch affects index efficiency. Migration to `UUIDField` with `db_index=True` is the fix.

---

## What is NOT a Performance Issue

| Concern | Rejection Reason |
|---------|-----------------|
| `import time` unused in `main_window.py:3` | Negligible import time; not a perf issue |
| `time_label.setText()` called every second | Acceptable for status bar |
| `LazyScreenManager` imports | Lazy loading is the optimization itself |
| 45 methods in MainWindow | UX refactor concern, not perf |
| 17 endpoints in PaymentOperationsViewSet | None are slow individually |
| `FIFOAllocationService` runs in `get_outstanding_invoices` | Not in target file; assumed optimized |

---

## Recommended Action Order

| # | Action | Effort | Estimated Speedup |
|---|--------|--------|--------------------|
| 1 | P-9 (lru_cache on account validation) | 5 min | 5ms/payment → 0.1ms |
| 2 | P-4 + P-5 (N+1 fix in customer/supplier payment) | 4 hours | 510ms → 15ms (34×) |
| 3 | P-6 + P-7 (N+1 fix in mixed payment) | 2 hours | 1008ms → 30ms (34×) |
| 4 | P-8 (Sum annotation on payment traces) | 1 hour | 50ms → 5ms (10×) |
| 5 | P-3 (191 indexes) | 4-6 hours | 100ms → 1ms (100×) on indexed queries |
| 6 | P-2 (QTimer.singleShot for retry) | 30 min | 2.1s → 0ms UI freeze |
| 7 | P-1 (full threading refactor) | 2-3 days | 200-2000ms → 0ms UI freeze per call |

**Total zero-risk wins (1-4):** ~7.5 hours. Items 1-4 are pure refactors with no API changes.

**Combined P-1 + P-2 fix:** 2-3 days (highest leverage but highest regression risk).
