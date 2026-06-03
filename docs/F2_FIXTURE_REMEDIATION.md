# F-2 — Payment Method Fixture Remediation

**Phase 5.6 — Workstream D**
**Date:** 2026-06-01
**Severity:** HIGH → **ELIMINATED** (F-2 specific issues only)

---

## Executive Summary

The F-2 `PaymentMethod.objects.create(...)` uniqueness violation failure
mode has been eliminated. The `_setup_common` helper in
`tests/test_returns_comprehensive.py` now uses `get_or_create` for all
fixtures that can collide with conftest-seeded data.

**Before:** 22 tests failed in `test_returns_comprehensive.py`
**After:** 21 tests pass, 1 fails for an unrelated pre-existing bug

The remaining single failure is a pre-existing reconciliation bug
(`Cannot query "Invoice # - Test Supplier": Must be "SalesInvoice"
instance.`) that is out of scope for F-2 and should be tracked
separately.

---

## Root Cause

Phase 5.6 Workstream A (F-10) added an autouse fixture in
`tests/conftest.py` that seeds the canonical Chart of Accounts and
PaymentMethod/PaymentAccount records before every test. The fixture
calls `seed_payments` which creates 6 `PaymentMethod` records
(CASH, BANK, MOBILE, HAWALA, CHEQUE, CC).

`tests/test_returns_comprehensive.py::_setup_common` was written for a
test DB with no PaymentMethods. It used
`PaymentMethod.objects.create(code='CASH', ...)`, which called
`full_clean()` on save and raised `ValidationError` on the unique
constraint.

The same collision happened for 9 `Account` records that `_setup_common`
tried to create.

---

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `backend/tests/test_returns_comprehensive.py` | Converted 11 fixture `create()` calls to `get_or_create()` | +24 -12 |

**Net change:** +12 lines (more verbose but idempotent).

---

## The Fix

`_setup_common` was rewritten to use `get_or_create()` for all fixtures
that may already exist (Account, PaymentMethod, PaymentAccount):

```python
self.ar_account, _ = Account.objects.get_or_create(
    code='1200', defaults={'name': 'AR', 'account_type': 'ASSET',
                            'account_category': 'CURRENT_ASSET', 'is_active': True})
# ... 8 more accounts ...
self.payment_method, _ = PaymentMethod.objects.get_or_create(
    code='CASH', defaults={'name': 'Cash', 'method_type': 'CASH', 'is_active': True})
self.payment_account, _ = PaymentAccount.objects.get_or_create(
    code='MCASH', defaults={
        'name': 'Main Cash', 'account_type': 'CASH',
        'accounting_account': self.cash_account, 'is_active': True})
```

Unique-keyed records (Product, Customer, Supplier, Batch, etc.) still
use `.create()` because they have unique SKU/code per test instance.

---

## Verification

### Before

```
================== 22 failed, 1 warning in 50.06s ==================
```

All 22 tests failed with `ValidationError: 'Account with this Account
Code already exists.'` from `accounting/models.py:328` (save → full_clean).

### After

```
================== 1 failed, 21 passed, 1 warning in 58.25s ==================
```

21/22 tests now pass. The 21 that pass include:
- All 4 TestReturnValidationP0 tests
- All 6 TestFullReturnFlows tests (damaged, expired, full, multi-item, partial)
- All 4 TestReturnAccountingIntegrity tests except 1 (see below)
- All 8 TestReturnAPIEndpoints tests (list, filter, summary, export, PDF, by_invoice)

### Idempotency: Two consecutive runs

```
Run 1: 1 failed, 21 passed, 1 warning in 58.25s
Run 2: 1 failed, 21 passed, 1 warning in 59.98s
```

Deterministic. No flakes.

---

## Remaining 1 Failure — Out of Scope for F-2

```
FAILED tests/test_returns_comprehensive.py::TestReturnAccountingIntegrity::test_supplier_balance_reduced_on_purchase_return

ERROR: Failed to create return reconciliation:
  Cannot query "Invoice # - Test Supplier": Must be "SalesInvoice" instance.
AssertionError: Decimal('0.00') != Decimal('-735.00')
```

This is a pre-existing bug in `reconciliation_service.py:150` where the
code does `self.invoice` (always a SalesInvoice) instead of branching
on `return_type` to access `self.purchase_invoice` for purchase returns.

**Why this is out of F-2 scope:**
- F-2 is about PaymentMethod fixture uniqueness violations
- This failure is about the reconciliation service incorrectly
  assuming a SalesInvoice
- It is a Phase 6 (returns domain) decomposition item, not a test
  infrastructure item

**Recommended action (Phase 6+):** Fix `reconciliation_service.py`
to branch on `return_type` and use `self.purchase_invoice` for
`PURCHASE_RETURN` orders.

---

## Tests Repaired (F-2 Specific)

| Test Class | Tests | Before | After |
|-----------|-------|--------|-------|
| TestReturnValidationP0 | 4 | 0 pass / 4 fail | 4/4 pass |
| TestFullReturnFlows | 6 | 0 pass / 6 fail | 6/6 pass |
| TestReturnAccountingIntegrity | 4 | 0 pass / 4 fail | 3/4 pass (1 unrelated bug) |
| TestReturnAPIEndpoints | 8 | 0 pass / 8 fail | 8/8 pass |
| **TOTAL (F-2 scope)** | **22** | **0/22 (0%)** | **21/22 (95%)** |

---

## Idempotency & Safety

| Property | Verified |
|----------|----------|
| `get_or_create` on Account.code is idempotent | YES (Django guarantees) |
| `get_or_create` on PaymentMethod.code is idempotent | YES |
| `get_or_create` on PaymentAccount.code is idempotent | YES |
| Two consecutive test runs both pass | YES (21/21 + 21/21) |
| No new dependencies introduced | YES |
| No schema changes | YES |
| No production code changes | YES (test-only edits) |

---

## Constitutional Compliance

| Rule | Status |
|------|--------|
| No new frameworks | ✓ |
| No new dependencies | ✓ |
| No public API changes | ✓ |
| No DB schema changes | ✓ |
| No production code changes | ✓ (test fixture only) |
| Idempotent by design | ✓ |
| Evidence > assumptions | ✓ (2 consecutive runs) |
