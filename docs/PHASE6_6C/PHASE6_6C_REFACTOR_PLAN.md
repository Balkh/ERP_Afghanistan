# Phase 6.6C — Refactor Plan

**Scope:** 5 target files + their downstream impact
**Method:** Top-down decomposition. Each refactor step is independent and reversible.
**Goal:** Reduce god classes, eliminate duplication, improve testability.

---

## Refactor Targets (Priority Order)

| # | Target | Current State | Refactor Goal | Effort | Risk |
|---|--------|---------------|---------------|--------|------|
| R-1 | Delete shadowed `process_*_payment` methods in `payment_operations.py` | L113, L321 | Remove 91 + 76 = 167 LOC of dead code | 15 min | ZERO |
| R-2 | Replace `eval()` in `patterns.py:77` | Uses unsafe `eval` | Use tuple directly as dict key | 5 min | ZERO |
| R-3 | Decompose `PaymentOperationsViewSet` (1111 LOC, 17 methods) | One god class | Split into 5 mixin classes | 6 hours | MEDIUM |
| R-4 | Decompose `MainWindow` (1152 LOC, 45 methods) | One god class | Extract 4 sub-controllers | 1-2 days | HIGH |
| R-5 | Decompose `PaymentEngine` (809 LOC, 10 methods) | Well-structured but large | Extract 3 helper classes | 4 hours | LOW |
| R-6 | N+1 → bulk fetch in `process_*_payment` | 101 queries per call | 3 queries per call | 6 hours | LOW |
| R-7 | `APIClient` → `AsyncAPIClient` | 667 LOC sync | 800 LOC async + refactor 21 screens | 2-3 days | HIGH |
| R-8 | Move hardcoded `setGeometry` to screen-aware | Hardcoded (100,100,1400,900) | Use `QScreen.geometry()` | 20 min | LOW |

---

## R-1: Delete shadowed method definitions (DEAD CODE)

**File:** `backend/core/api/v1/payment_operations.py`
**Dead code:**
- L113-204: `process_customer_payment` (no atomic)
- L321-397: `process_supplier_payment` (no atomic)

**Verification:** Both methods are shadowed by their L550/L684 counterparts. Confirmed by:
1. Python class-body semantics: second `def` overrides first
2. `grep -r 'customers/process-payment' frontend/` → 0 results (L113 endpoint not called)

**Refactor steps:**

1. Read L113-204, confirm no logic that L550 lacks
2. Delete L113-204 (the entire `process_customer_payment` first definition)
3. Delete L321-397 (the entire `process_supplier_payment` first definition)
4. Verify class body: only one `process_customer_payment` and `process_supplier_payment` remain
5. Run tests: `python manage.py test api.v1.payment_operations -v 2`
6. Verify URL routing: `python manage.py show_urls | grep payment`

**Effort:** 15 minutes.
**Test impact:** None (dead code had no endpoint).
**Risk:** ZERO.

---

## R-2: Replace `eval()` with tuple-as-key (SECURITY FIX)

**File:** `backend/core/operations/intelligence/patterns.py:71-77`
**Refactor steps:**

```python
# BEFORE
event_types = [e.event_type for e in events if e.source_type.value != "SIMULATION"]
patterns: Dict[str, int] = defaultdict(int)

for length in range(MIN_SEQUENCE_LENGTH, max_length + 1):
    for i in range(len(event_types) - length + 1):
        seq = tuple(event_types[i:i + length])
        patterns[str(seq)] += 1

# ...

for seq_str, count in patterns.items():
    if count >= min_support:
        types = eval(seq_str)
        ...

# AFTER
event_types = [e.event_type for e in events if e.source_type.value != "SIMULATION"]
patterns: Dict[Tuple[str, ...], int] = defaultdict(int)

for length in range(MIN_SEQUENCE_LENGTH, max_length + 1):
    for i in range(len(event_types) - length + 1):
        seq = tuple(event_types[i:i + length])
        patterns[seq] += 1

# ...

for seq, count in patterns.items():
    if count >= min_support:
        types = seq    # already a tuple
        ...
```

**Verify:**
- `patterns` is a `defaultdict` — tuple keys work the same as string keys
- `seq` is already a tuple of strings — `types = seq` is type-safe
- No external API change (returns `EventPattern` with `event_types: list[str]`)

**Tests:**
- 27 existing tests in `simulation/tests/test_intelligence/test_intelligence.py` should pass unchanged
- Add 1 new test: `test_eval_not_called` — patch `core.operations.intelligence.patterns.eval` to raise, verify no call

**Effort:** 5 minutes.
**Risk:** ZERO.

---

## R-3: Decompose `PaymentOperationsViewSet` (GOD CLASS)

**File:** `backend/core/api/v1/payment_operations.py` (1111 LOC, 17 methods)
**Current structure:** Single class with 5 logical groups:

1. **Customer operations** (4 methods): `customer_payment_workspace`, `process_customer_payment`, `allocate_customer_unallocated`, `customer_payment_trace`
2. **Supplier operations** (4 methods): same 4 for supplier
3. **Mixed payment** (3 methods): `list_payment_methods`, `list_payment_accounts`, `validate_mixed_payment`
4. **Payment processing** (4 methods): `process_customer_payment`, `process_supplier_payment`, `process_mixed_payment`, `payment_anomalies`
5. **PDF export** (2 methods): `customer_statement_pdf`, `supplier_statement_pdf`

**Refactor approach: Mixin classes**

```python
# New file: backend/core/api/v1/payment_operations_mixins/customer_mixin.py
class CustomerPaymentOperationsMixin:
    @action(detail=False, methods=['get'], url_path='customers/(?P<customer_id>[^/.]+)/payment-workspace')
    def customer_payment_workspace(self, request, customer_id=None):
        # ... 60 lines
        ...

    @action(detail=False, methods=['post'], url_path='customers/(?P<customer_id>[^/.]+)/allocate-unallocated')
    def allocate_customer_unallocated(self, request, customer_id=None):
        # ... 15 lines
        ...

    @action(detail=False, methods=['get'], url_path='customers/(?P<customer_id>[^/.]+)/payment-trace')
    def customer_payment_trace(self, request, customer_id=None):
        # ... 45 lines
        ...

# New file: backend/core/api/v1/payment_operations_mixins/supplier_mixin.py
class SupplierPaymentOperationsMixin:
    @action(detail=False, methods=['get'], url_path='suppliers/(?P<supplier_id>[^/.]+)/payment-workspace')
    def supplier_payment_workspace(self, request, supplier_id=None):
        # ... 50 lines (mirrors customer)
        ...

    # ... 3 more methods

# New file: backend/core/api/v1/payment_operations_mixins/mixed_payment_mixin.py
class MixedPaymentOperationsMixin:
    @action(detail=False, methods=['get'], url_path='payment-methods')
    def list_payment_methods(self, request):
        # ... 7 lines
        ...

    @action(detail=False, methods=['get'], url_path='payment-accounts')
    def list_payment_accounts(self, request):
        # ... 10 lines
        ...

    @action(detail=False, methods=['post'], url_path='validate-mixed-payment')
    def validate_mixed_payment(self, request):
        # ... 65 lines
        ...

# New file: backend/core/api/v1/payment_operations_mixins/payment_processing_mixin.py
class PaymentProcessingMixin:
    @action(detail=False, methods=['post'], url_path='process-customer-payment')
    @transaction.atomic
    def process_customer_payment(self, request):
        # ... 130 lines (after R-1 delete, this is the only one)
        ...

    # ... 3 more methods (process_supplier, process_mixed, payment_anomalies)

# New file: backend/core/api/v1/payment_operations_mixins/pdf_export_mixin.py
class PaymentStatementPDFMixin:
    @action(detail=False, methods=['get'], url_path='customers/(?P<customer_id>[^/.]+)/statement-pdf')
    def customer_statement_pdf(self, request, customer_id=None):
        # ... 40 lines
        ...

    @action(detail=False, methods=['get'], url_path='suppliers/(?P<supplier_id>[^/.]+)/statement-pdf')
    def supplier_statement_pdf(self, request, supplier_id=None):
        # ... 40 lines (mirrors customer)
        ...

# Refactored main file
from .payment_operations_mixins import (
    CustomerPaymentOperationsMixin,
    SupplierPaymentOperationsMixin,
    MixedPaymentOperationsMixin,
    PaymentProcessingMixin,
    PaymentStatementPDFMixin,
)

class PaymentOperationsViewSet(
    CustomerPaymentOperationsMixin,
    SupplierPaymentOperationsMixin,
    MixedPaymentOperationsMixin,
    PaymentProcessingMixin,
    PaymentStatementPDFMixin,
    viewsets.ViewSet,
):
    permission_classes = [RoleBasedPermission]
```

**Result:** 1111 LOC → 5 files of ~150-200 LOC each, plus a 15-LOC orchestrator.

**Refactor steps:**

1. Create 5 mixin files in `backend/core/api/v1/payment_operations_mixins/`
2. Move methods (preserve docstrings and decorators exactly)
3. Update imports in main file
4. Update main file to use multiple inheritance
5. Update `__init__.py` to export the mixins
6. Run `python manage.py show_urls | grep payment` — verify 17 endpoints still registered
7. Run integration tests
8. Update any direct references to `PaymentOperationsViewSet` (none expected)

**Effort:** 6 hours.
**Risk:** MEDIUM. Each mixin is independent, but the @action URL registration happens at class definition. If multiple mixins use the same URL path (they don't), the last one wins. Need to verify with `show_urls`.

**Test impact:** None. URL paths are identical.

---

## R-4: Decompose `MainWindow` (GOD CLASS — deferred)

**File:** `frontend/ui/main_window.py` (1152 LOC, 45 methods)
**Recommended decomposition:** Sub-controller pattern (mirrors Phase 6.4 refactor of SalesInvoice/PurchaseInvoice screens).

**Proposed split:**

1. **MainWindow** (150 LOC) — pure container, holds QStackedWidget + sidebar
2. **NavigationController** (200 LOC) — `_change_page`, `_go_back`, `_go_home`, `close_screen`, history management
3. **ThemeController** (150 LOC) — `on_theme_changed`, theme propagation
4. **StatusBarController** (200 LOC) — `_setup_status_bar`, time/health/connection updates
5. **StartupController** (200 LOC) — `_load_company_settings`, `_check_startup_health`, deferred work
6. **LicenseController** (100 LOC) — license signal handling (already partially extracted)

**Pattern:**

```python
class MainWindow(QMainWindow):
    def __init__(self, ...):
        # Build sub-controllers
        self._nav = NavigationController(self)
        self._theme = ThemeController(self)
        self._status = StatusBarController(self, api_client)
        self._startup = StartupController(self, api_client)
        self._license = LicenseController(self, license_validator)

        # Delegate
        self.change_page = self._nav.change_page
        self._go_back = self._nav.go_back
        self.on_theme_changed = self._theme.on_theme_changed
        # ... etc

    def _build_ui(self):
        # Pure UI assembly
        ...
```

**Risk:** HIGH. MainWindow has 21 pages, 7 timers, 4 deferred callbacks, 6 signal connections. Decomposing requires careful refactor of cross-controller interactions.

**Status:** DEFERRED. Phase 6.5 documented this as known hub. Refactor as part of Phase 7+ architectural work. Do not attempt without dedicated refactor phase.

**Effort:** 1-2 days.
**Risk:** HIGH.

---

## R-5: Decompose `PaymentEngine` (GOD CLASS — well-structured)

**File:** `backend/payments/services.py` (809 LOC, 10 methods)
**Current structure:**

| Method | LOC | Concern |
|--------|-----|---------|
| `process_receipt` | 80 | RECEIPT workflow + journal |
| `process_payment` | 80 | PAYMENT workflow + journal |
| `process_transfer` | 80 | TRANSFER workflow + journal |
| `process_refund` | 50 | REFUND (delegates to receipt/payment) |
| `create_settlement` | 80 | SETTLEMENT workflow |
| `get_account_transactions` | 70 | READ (account history) |
| `_validate_required_accounts` | 25 | HELPER (account validation) |
| `_create_receipt_journal_entry` | 90 | HELPER (journal lines) |
| `_create_payment_journal_entry` | 90 | HELPER (journal lines) |
| `_create_transfer_journal_entry` | 50 | HELPER (journal lines) |

**Proposed split:**

```python
# backend/payments/services.py (orchestrator, ~150 LOC)
class PaymentEngine:
    """Public API — delegates to helpers."""
    process_receipt = staticmethod(_process_receipt_impl)
    process_payment = staticmethod(_process_payment_impl)
    # ... etc

# backend/payments/services/journal.py (~250 LOC)
def _create_receipt_journal_entry(txn): ...
def _create_payment_journal_entry(txn): ...
def _create_transfer_journal_entry(txn): ...
def _validate_required_accounts(): ...

# backend/payments/services/settlement.py (~150 LOC)
def _create_settlement_impl(...): ...
def _link_transactions(settlement, transactions, account): ...
```

**Risk:** LOW. PaymentEngine is pure (`@staticmethod` everywhere). No state, no inheritance. Splitting is mechanical.

**Effort:** 4 hours.
**Risk:** LOW.

**Verification:**
- All 8 callers of `PaymentEngine.process_*` (via `grep -r 'PaymentEngine\.' backend/`) should still work
- Existing tests (43 accounting model tests) should pass unchanged

---

## R-6: N+1 → bulk fetch in payment processing (PERFORMANCE)

**Files:** `backend/core/api/v1/payment_operations.py:625-645, 759-779, 892-906, 931-945`
**Refactor:** See P-4, P-5, P-6, P-7 in `PHASE6_6C_PERFORMANCE_AUDIT.md`.

**Pattern (applied to all 4 sites):**

```python
# BEFORE
outstanding = FIFOAllocationService.get_outstanding_invoices(customer)
remaining = amount
for inv_data in outstanding:
    if remaining <= 0: break
    inv = SalesInvoice.objects.get(pk=inv_data['id'])   # N+1
    inv_balance = FIFOAllocationService.get_invoice_balance(inv)   # N+1
    alloc_amount = min(remaining, inv_balance)
    if alloc_amount > 0:
        PaymentAllocation.objects.create(...)
        remaining -= alloc_amount

# AFTER
with transaction.atomic():
    outstanding = list(
        SalesInvoice.objects
        .select_for_update()
        .filter(customer=customer, paid_amount__lt=F('total_amount'))
        .order_by('invoice_date')
    )
    allocations = []
    remaining = amount
    for inv in outstanding:
        if remaining <= 0: break
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
    PaymentAllocation.objects.bulk_create(allocations)
    SalesInvoice.objects.bulk_update(outstanding, ['paid_amount', 'payment_status'])
```

**Effort:** 6 hours total (1.5h × 4 sites).
**Risk:** LOW. Pure optimization, no API change.

---

## R-7: `APIClient` → `AsyncAPIClient` (GOD CLASS + SYNC IO)

**File:** `frontend/api/client.py` (667 LOC, 57 methods)
**Approach:** See P-1 in `PHASE6_6C_PERFORMANCE_AUDIT.md` for the worker pattern.

**Refactor steps:**

1. **Phase 1 (1 day):** Create `AsyncAPIClient` alongside `APIClient`. No caller changes.
2. **Phase 2 (1 day):** Convert 5 highest-frequency callers (dashboard, login, list pages).
3. **Phase 3 (0.5 day):** Convert remaining 16 screens.
4. **Phase 4 (0.5 day):** Remove `APIClient`, keep only `AsyncAPIClient`.

**Risk:** HIGH. Each call site conversion requires understanding the caller's control flow (sync return value → callback).

**Effort:** 3 days.
**Risk:** HIGH.

**Status:** DEFERRED to Phase 7+ unless blocking pilot deployment.

---

## R-8: Screen-aware window geometry (UX)

**File:** `frontend/ui/main_window.py:33-34` (and `login_screen.py:57`)
**Refactor:**

```python
# BEFORE
self.setGeometry(100, 100, 1400, 900)
self.setMinimumSize(1200, 800)

# AFTER
screen = QApplication.primaryScreen().availableGeometry()
target_w = min(1600, int(screen.width() * 0.85))
target_h = min(1000, int(screen.height() * 0.85))
self.resize(target_w, target_h)
self.move(
    (screen.width() - target_w) // 2,
    (screen.height() - target_h) // 2
)
self.setMinimumSize(1024, 700)
```

**Apply same to `login_screen.py:57`.**

**Effort:** 20 minutes.
**Risk:** LOW.

---

## Refactor Dependency Graph

```
R-1 (delete dead code)         ─┐
R-2 (replace eval)             ─┤── Zero-risk, can run in any order
R-8 (screen geometry)          ─┘

R-5 (split PaymentEngine)      ─┐
R-6 (N+1 fix)                  ─┤── Low-risk, run after R-1
R-3 (split PaymentViewSet)     ─┘

R-4 (split MainWindow)         ──── HIGH risk, deferred to Phase 7+
R-7 (AsyncAPIClient)           ──── HIGH risk, deferred to Phase 7+
```

---

## Recommended Phase 6.6C Refactor Order

1. **R-1** (15 min) — Delete dead code
2. **R-2** (5 min) — Replace `eval()`
3. **R-8** (20 min) — Screen geometry
4. **R-5** (4 hours) — Split PaymentEngine
5. **R-6** (6 hours) — N+1 fix
6. **R-3** (6 hours) — Split PaymentOperationsViewSet

**Total: ~17 hours of focused refactor work.**
**Total risk: LOW** (no high-risk items included).
**Test pass rate: unchanged** (all refactors preserve public API and behaviour).

R-4 and R-7 are deferred to Phase 7+ as documented in Phase 6.5.

---

## What is NOT a Refactor Target

| File | Why Not |
|------|---------|
| `core/operations/intelligence/patterns.py` (267 LOC) | Already well-structured. Single class, 4 methods, no god class. Only R-2 fix needed. |
| `frontend/api/endpoints.py` | Already uses `extract_list` canonical helper (Phase 3D) |
| `frontend/api/client.py` | R-7 is the proper refactor; incremental is unsafe |
| `frontend/ui/components/tables.py` | Already uses canonical widget API; Phase 3C + 3D applied |
| `frontend/utils/format.py` | Just `safe_float` and helpers; no refactor needed |

---

## Verification Checklist (after each refactor)

```bash
# 1. Run unit tests
cd backend && python manage.py test <affected_app> -v 2

# 2. Run integration tests
cd backend && python manage.py test integration -v 2

# 3. Run frontend tests
cd frontend && python -m pytest tests/ -v

# 4. Smoke test (manual)
# - Login
# - Dashboard loads
# - Each of 21 screens loads without error
# - Create one customer, one supplier, one product
# - Create one sales invoice, one purchase invoice
# - Process one customer payment, one supplier payment
# - Generate one report
# - Logout

# 5. Check URL routing
cd backend && python manage.py show_urls | wc -l
# Should be same count before and after refactor

# 6. Check API contract
curl -X GET http://localhost:8000/api/payment_operations/customers/<uuid>/payment-workspace/
# Should return same response shape
```

All checks should pass with **zero regressions** for R-1, R-2, R-3, R-5, R-6, R-8.
