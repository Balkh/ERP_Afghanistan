# BUG PREVENTION PROTOCOL — Phase 34

## Purpose
Reduce future bug creation probability close to zero by establishing mandatory rules for any future code changes.

---

## SECTION 1: SAFE MUTATION RULES

### 1.1 Transaction Boundaries
- **Rule**: Every `transaction.atomic()` block MUST raise exceptions on failure — never use `return Response(error)` inside the block.
- **Rationale**: `transaction.atomic()` only rolls back on unhandled exceptions. A normal return commits partial state.
- **Enforcement**: When adding workflow logic inside `with transaction.atomic():`, all error paths MUST `raise ValidationError(...)` not `return Response(...)`.
- **Example (WRONG)**:
  ```python
  with transaction.atomic():
      result = service.call()
      if not result.success:
          return Response({'error': 'failed'})  # COMMITS partial state!
  ```
- **Example (CORRECT)**:
  ```python
  try:
      with transaction.atomic():
          result = service.call()
          if not result.success:
              raise ValidationError({'error': 'failed'})
  except ValidationError as e:
      return Response(e.message_dict, status=400)
  ```

### 1.2 Catch-All Exception Safety
- **Rule**: Never use bare `except Exception:` inside `@transaction.atomic` blocks without re-raising.
- **Rationale**: Catching all exceptions and returning normally defeats atomic rollback protection.
- **Enforcement**: All `except Exception` in transactional code MUST either re-raise (`raise`) or be placed OUTSIDE the atomic block.
- **Exception**: Top-level API view error handlers (outside atomic blocks) may catch and return HTTP responses.

### 1.3 Idempotency Guards Must Be Locked
- **Rule**: Any idempotency check (query-then-act) MUST use `select_for_update()` on the guard row.
- **Rationale**: Without a row-level lock, two concurrent requests can both pass the check before either commits.
- **Enforcement**: Always use `Model.objects.select_for_update().filter(...)` for concurrency-sensitive idempotency checks.

---

## SECTION 2: OPERATIONAL VALIDATION RULES

### 2.1 Every Fix Must Include
1. **Root-cause validation** — Identify the actual failure mechanism, not the symptom
2. **Deterministic reproduction** — Can be reproduced without race conditions
3. **Rollback safety** — Verify the fix does not create partial-commit paths
4. **Regression test** — At least one test that covers the fixed scenario
5. **Logging validation** — Error paths must produce actionable log output

### 2.2 Forbidden Fix Patterns
❌ Speculative fixes ("this might also be a problem")
❌ Broad rewrites of working code
❌ Cleanup refactors mixed with bug fixes (separate commits)
❌ Hidden behavior changes (e.g., changing error handling without API contract notice)

---

## SECTION 3: ACCOUNTING INTEGRITY RULES

### 3.1 Journal Entry Creation
- Every financial transaction (receipt, payment, transfer) MUST create a journal entry
- Journal entry failure MUST roll back the entire transaction
- **Never** silently ignore journal entry failures — this creates ghost money movements without accounting records

### 3.2 Payment Engine Integrity
- `PaymentEngine.process_receipt()`, `process_payment()`, `process_transfer()` — if journal entry creation fails, the method MUST raise, not return success
- The caller is responsible for catching the exception and returning an appropriate API response

### 3.3 Account Balance Synchronization
- Customer/Supplier balance updates MUST be atomic with the related invoice/payment operations
- Use `select_for_update()` when reading and writing balance-related rows
- Never use aggregate-recalculate patterns without row-level locking

---

## SECTION 4: UI STABILITY RULES

### 4.1 Form Data Collection
- Every form dialog's `save()` method MUST have a corresponding `get_entry_data()` method that collects all form fields into a structured dict
- Never reference undefined methods in event handlers

### 4.2 API Error Feedback
- All API calls from UI MUST handle error responses and display user-visible messages
- Silent failures (empty dropdowns, frozen dialogs) are unacceptable

### 4.3 Modal Lifecycle
- Each dialog/modal MUST clean up its state when closed (rejected or accepted)
- Avoid stacking multiple instances of the same dialog type

---

## SECTION 5: WORKFLOW MODIFICATION CONSTRAINTS

### 5.1 Sales Lifecycle
- `DRAFT → CONFIRMED → DISPATCHED → PAID → CANCELLED`
- Each transition has specific guards. Never add new transitions without auditing all existing guards.
- Stock reversal and journal reversal MUST be in the same atomic block as status changes.

### 5.2 Purchase Lifecycle
- `DRAFT → CONFIRMED → RECEIVED → PAID → CANCELLED`
- Same atomicity rules as sales lifecycle

### 5.3 Return Lifecycle
- `PENDING → APPROVED → REFUNDED → VOID`
- Refund failures MUST NOT leave the return in APPROVED state without compensatory action

### 5.4 Period Closing
- Period status transitions (OPEN → SOFT_CLOSED → CLOSED → LOCKED → REOPENED) MUST use `select_for_update()` on the period row
- Never force-close a period without explicitly documenting the bypassed checks

---

## SECTION 6: ARCHITECTURE CONTAINMENT RULES

### 6.1 No New Engine Classes
- The existing JournalEngine, PaymentEngine, StockIntegrationService, CreditPolicyEngine, FinancialTruthEngine are the complete set of core engines
- New business logic MUST be implemented as standalone functions or thin service methods, not new Engine classes

### 6.2 No Orchestration Layers
- Business workflows are coordinated by the ViewSet actions (dispatch, cancel, receive, etc.)
- Adding intermediate orchestration layers creates hidden coupling and makes error handling ambiguous

### 6.3 Single Source of Truth (SSOT)
- `FinancialTruthEngine` is the sole authority for financial balances
- `JournalEngine` is the sole authority for journal entry creation
- Never cache or duplicate financial truth in other modules

### 6.4 test Infrastructure
- Tests that create payments (CustomerPayment, SupplierPayment) MUST set up PaymentAccount and PaymentMethod infrastructure first
- Use `TransactionBaseTestCase` for tests that need the full accounting chart
- Use `BaseTestCase` for tests that need payment infrastructure
- Avoid raw `APITestCase` for tests that trigger financial model saves

---

## SECTION 7: REGRESSION PREVENTION CHECKLIST

Before submitting any code change, verify:

- [ ] All existing tests pass
- [ ] No new unbounded data structures introduced (bounded collections only)
- [ ] No bare `except Exception` inside `transaction.atomic()` without re-raise
- [ ] All error paths inside atomic blocks raise exceptions (not return Response)
- [ ] Idempotency guards use `select_for_update()`
- [ ] Journal entry failures propagate (not silently swallowed)
- [ ] New API endpoints return standardized format (APIResponse)
- [ ] No architectural complexity added (no new engines, no new orchestration)
- [ ] No cleanup/fix mixed in the same commit
- [ ] Test setUp creates all required infrastructure (accounts, payment methods)

---

## SECTION 8: ENFORCEMENT

1. The lead engineer MUST review all commits against this protocol
2. Any violation of Sections 6.1-6.3 (Architecture Containment) requires immediate rollback
3. Violations of Sections 1.1-1.3 (Transaction Safety) must be fixed before merge
4. Violations of Section 7 (Regression Checklist) should be flagged for follow-up
5. This protocol must be read and acknowledged before any production code change
