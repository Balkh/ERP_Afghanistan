# PHASE 34 — TRIAGE REPORT

## Overview
- **Date**: 2026-05-21
- **Source data**: BUG_GOVERNANCE_REPORT.md (Phase 33) + live system analysis
- **Total issues analyzed**: 27 (7 Phase 33 bugs + 20 pre-existing test failures)
- **Production bugs**: 1 confirmed (BUG-001, already fixed)
- **Pre-existing test gaps**: 20 (isolated unit tests missing seed data)
- **Code quality issues found**: 4

---

## SECTION 1: PRODUCTION BUGS

### BUG-001: Export Engine Alignment Scoping
| Field | Value |
|-------|-------|
| **Classification** | Export Reliability |
| **Severity** | HIGH |
| **Status** | ✅ FIXED in Phase 33 |
| **Regression test** | ✅ Added |

### Remediation verification
- Openpyxl Excel exports now work correctly
- CSV fallback works when openpyxl is not installed
- All 236 Phase 33 + accounting tests pass

---

## SECTION 2: PRE-EXISTING TEST GAPS (20 failures)

These are NOT production bugs — they are test gaps in isolated unit tests.

### ROOT CAUSE: Missing PaymentAccount seed data
All 20 failures in `test_sales.py`, `test_sales_workflow.py`, `test_purchases.py`, `test_payment_workflow.py` have the same root cause:

```
django.core.exceptions.ValidationError: 
  No active payment account found for customer/supplier payment. 
  Cannot create financial transaction.
```

The `CustomerPayment.save()` and `SupplierPayment.save()` methods auto-create `FinancialTransaction` records via `PaymentEngine`, which requires an active `PaymentAccount`. The existing tests create payments without first creating a `PaymentAccount`.

### Affected test files:
| Test File | Failures | Root Cause |
|-----------|----------|------------|
| `tests/test_sales.py` | 6 | No PaymentAccount in test DB |
| `tests/test_sales_workflow.py` | 3 | No PaymentAccount in test DB |
| `tests/test_purchases.py` | 6 | No PaymentAccount in test DB |
| `tests/test_payment_workflow.py` | 5 | No PaymentAccount in test DB |

### Risk assessment
| Metric | Value |
|--------|-------|
| **Financial corruption risk** | NONE — these are unit tests, not production code |
| **Production impact** | NONE — production has seeded PaymentAccounts |
| **Reproducibility** | 100% — run any of these tests without PaymentAccount seed |
| **Repair complexity** | LOW — add PaymentAccount creation in setUp |

### 20 failures by sub-file:

```
tests/test_sales.py:
  CustomerPaymentModelTests.test_create_customer_payment
  CustomerPaymentModelTests.test_customer_payment_methods
  CustomerPaymentModelTests.test_customer_payment_str_representation
  CustomerPaymentModelTests.test_customer_payment_updates_customer_balance
  CustomerPaymentModelTests.test_customer_payment_updates_invoice_paid
  CustomerPaymentModelTests.test_multiple_payments_accumulate

tests/test_sales_workflow.py:
  CustomerBalanceConsistencyTests.test_customer_balance_after_payment
  CustomerBalanceConsistencyTests.test_multiple_invoices_single_customer
  CustomerBalanceConsistencyTests.test_partial_payment_balance

tests/test_purchases.py:
  SupplierPaymentModelTests.test_create_supplier_payment
  SupplierPaymentModelTests.test_multiple_supplier_payments_accumulate
  SupplierPaymentModelTests.test_supplier_payment_methods
  SupplierPaymentModelTests.test_supplier_payment_str_representation
  SupplierPaymentModelTests.test_supplier_payment_updates_invoice_paid
  SupplierPaymentModelTests.test_supplier_payment_updates_supplier_balance

tests/test_payment_workflow.py:
  CashPaymentWorkflowTests.test_cash_payment_with_invoice
  MixedPaymentWorkflowTests.test_partial_payment_multiple_methods
  PartialPaymentValidationTests.test_full_payment_updates_status
  PartialPaymentValidationTests.test_multiple_partial_payments
  PartialPaymentValidationTests.test_partial_payment_updates_invoice
```

---

## SECTION 3: CODE QUALITY ISSUES

### CQI-001: Duplicate `cancel` method on SalesInvoiceViewSet
| Field | Value |
|-------|-------|
| **File** | `backend/sales/views.py` |
| **Lines** | 319-375 AND 412-459 |
| **Type** | Method duplication |
| **Severity** | MEDIUM |

**Description**: The `cancel` action is defined twice on `SalesInvoiceViewSet`. The first definition (lines 319-375) has more detailed validation (checks PAID, PARTIAL_PAID, and logs events). The second definition (lines 412-459) has simpler validation. Django's method resolution will use the **last** definition, so the simpler version is active. The better-detailed version is shadowed.

**Risk**: If the simpler version is active, paid/partial_paid invoices could potentially be cancelled (no guard), leading to orphaned payments.

### CQI-002: PaymentAccount hard dependency
| Field | Value |
|-------|-------|
| **File** | `backend/sales/models.py`, `backend/purchases/models.py` |
| **Type** | Tight coupling |
| **Severity** | LOW |

**Description**: `CustomerPayment.save()` and `SupplierPayment.save()` require an active `PaymentAccount` to exist before they can process. If all PaymentAccounts are accidentally deactivated, no payments can be processed. No graceful degradation.

### CQI-003: Error message format inconsistency
| Field | Value |
|-------|-------|
| **Files** | Multiple view files |
| **Type** | Inconsistency |
| **Severity** | LOW |

**Description**: Some endpoints return errors as `{'error': str(e)}` while others use `APIResponse.error(message=str(e))`. This creates inconsistent API contract for frontend consumers.

### CQI-004: No rate limiting or bulk operation protection
| Field | Value |
|-------|-------|
| **Type** | Operational gap |
| **Severity** | LOW |

**Description**: No rate limiting on journal entry posting, payment creation, or export endpoints. Under high load or fat-finger scenarios, an operator could accidentally post thousands of entries.

---

## SECTION 4: WORKFLOW RISK ANALYSIS

### Workflow: Sales Lifecycle
| Status | Risk |
|--------|------|
| Draft → Confirmed | ✅ Low — simple status transition |
| Confirmed → Dispatched | ⚠️ MEDIUM — stock deduction + journal entry in atomic block |
| Dispatched → Cancelled | ⚠️ MEDIUM — stock reversal + journal reversal |
| Dispatched → Paid | ⚠️ MEDIUM — payment + journal entry |
| **CQI-001 (duplicate cancel)** | 🔴 HIGH — simpler cancel shadows detailed cancel |

### Workflow: Purchase Lifecycle
| Status | Risk |
|--------|------|
| Draft → Confirmed | ✅ Low |
| Confirmed → Received | ⚠️ MEDIUM — stock addition + journal entry |
| Received → Cancelled | ⚠️ MEDIUM — stock reversal + journal reversal |

### Workflow: Payment Lifecycle
| Status | Risk |
|--------|------|
| Payment creation | ⚠️ MEDIUM — hard dependency on PaymentAccount |
| Payment cancellation | ✅ Low — only PENDING can cancel |

### Workflow: Period Closing
| Status | Risk |
|--------|------|
| Closing | ✅ Low — full validation chain |
| Reopening | ✅ Low — full audit trail |

### Workflow: Session
| Status | Risk |
|--------|------|
| Login/Logout | ✅ Low |
| Inactive user | ✅ Low — properly rejected |

---

## SECTION 5: TRIAGE PRIORITIES

### Immediate (Layer 2):
1. 🔴 **CQI-001**: Fix duplicate `cancel` method — keep the detailed version, remove the shadowed simpler version
2. 🟡 Fix 20 pre-existing test failures by adding PaymentAccount seed data
3. 🟡 **BUG_GOVERNANCE verification**: Re-verify BUG-001 (Export) fix integrity

### Short-term (Layer 3-4):
4. 🟢 Add PaymentAccount creation in test setUp utilities
5. 🟢 UI modal/dialog cleanup audit
6. 🟢 Keyboard focus flow validation

### Medium-term (Layer 5-7):
7. 🟢 Long-session stability documentation
8. 🟢 Export stress test hardening
9. 🟢 Generate bug prevention protocol
