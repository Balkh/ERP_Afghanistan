# Phase 21 — Architectural Integrity & Truth Validation Audit

**Date:** 2026-05-21
**Type:** READ-ONLY ARCHITECTURAL AUDIT
**Scope:** All Phase 21 deliverables + full system truth validation

---

## 1. CURRENT ARCHITECTURAL STATE SUMMARY

### Truth Architecture (Unchanged by Phase 21)
```
JournalEngine (SSOT) ← JournalGateway (enforcement layer)
       ↑
       ├── SalesAccountingService (calls JournalEngine directly) ⚠️
       ├── PurchaseAccountingService (calls JournalEngine directly) ⚠️
       ├── PaymentEngine (calls JournalEngine directly) ⚠️
       ├── ReturnOrder.void() (calls JournalEngine directly) ⚠️
       ├── Expense model (calls JournalEngine directly) ⚠️
       └── AssetAccountingIntegrationService (calls JournalEngine directly) ⚠️
```

### Phase 21 Additions (Validated)
| Component | Type | Mutates Financial Truth? | Delegates to JournalGateway? |
|---|---|---|---|
| PeriodClosingService | Governance | No (changes FiscalPeriod.status only) | N/A |
| ReversalSafetyService | Safety layer | No (read-only analysis) | Yes |
| Payment execution endpoints | API | No (delegates to existing models) | N/A |
| FinancialExplainability additions | Read-only | No | N/A |
| PDF generators | Read-only | No | N/A |
| Bulk depreciation endpoint | API | No (delegates to AssetLifecycleService) | N/A |

---

## 2. SSOT INTEGRITY STATUS

### ✅ CONFIRMED: JournalEngine Remains Single Source of Truth
- All journal entry creation flows through `JournalEngine.create_entry()`
- All journal entry posting flows through `JournalEngine.post_entry()`
- All journal entry reversal flows through `JournalEngine.reverse_entry()`
- Account balance updates occur ONLY in `JournalEngine.update_account_balances()` (line 375, 396)

### ✅ CONFIRMED: No Dual Financial Truth Introduced
- Phase 21 services do NOT create alternative balance computation paths
- BalanceSyncService (pre-existing) derives balance from invoices - payments (consistent with SSOT)
- FinancialTruthEngine (pre-existing) derives balance from invoices - payments (consistent with SSOT)
- No cached financial state introduced by Phase 21

### ⚠️ PRE-EXISTING: JournalGateway Not Universally Enforced
The following modules call `JournalEngine` directly, bypassing `JournalGateway`:
- `sales/views.py` (3 direct calls)
- `purchases/views.py` (3 direct calls)
- `returns/models.py` (3 direct calls)
- `payments/services.py` (3 direct calls)
- `expenses/models.py` (1 direct call)
- `fixed_assets/services/asset_accounting_service.py` (calls JournalEngine)

**Assessment:** This is a pre-existing architectural gap, NOT introduced by Phase 21. Phase 21 correctly enforces period locks within JournalGateway, but modules bypassing JournalGateway are not protected.

---

## 3. DETECTED RISKS

### RISK 1: Period Lock Bypass via Direct JournalEngine Calls [HIGH — PRE-EXISTING]
**Location:** `sales/views.py`, `purchases/views.py`, `returns/models.py`, `payments/services.py`, `expenses/models.py`

**Mechanism:** These modules call `JournalEngine.create_entry()` directly without checking `is_period_locked()`. JournalGateway has period lock enforcement (Phase 21 addition), but these modules bypass JournalGateway entirely.

**Impact:** Journal entries CAN be created in locked periods through sales dispatch, purchase receive, return void, payment processing, and expense creation.

**Not Phase 21's fault.** Phase 21 correctly added period lock enforcement to JournalGateway. The risk exists because these modules were never migrated to use JournalGateway.

### RISK 2: BalanceSyncService Directly Mutates Balance Fields [MEDIUM — PRE-EXISTING]
**Location:** `core/balance_sync.py` (lines 61, 112, 161, 208)

**Mechanism:** `BalanceSyncService.sync_customer()` and `sync_supplier()` directly set `customer.balance = new_balance` and persist it. This is a derived balance computation that overwrites the stored balance.

**Impact:** Balance mutation occurs outside JournalEngine. However, this is a reconciliation correction, not an independent truth source. The derived balance is computed from SSOT (invoices - payments).

**Assessment:** Acceptable. This is a sync operation that aligns stored balance with SSOT-derived balance. It is audited via `FinancialAuditService.log_balance_sync()`.

### RISK 3: UI Computes Invoice Totals Locally [LOW — PRE-EXISTING]
**Location:** `frontend/ui/sales/sales_invoice_screen.py`, `frontend/ui/purchases/purchase_invoice_screen.py`, `frontend/ui/pos/pos_screen.py`

**Mechanism:** UI computes subtotal, tax, discount, total, and balance using Decimal arithmetic for form display.

**Impact:** UI shows computed totals that may differ from backend-computed totals if tax/discount logic diverges. However, backend re-validates all amounts on submission.

**Assessment:** Acceptable for UX purposes. Backend is the authority. No financial truth mutation occurs in UI.

### RISK 4: No Period Validation in Sales/Purchase/Returns Screens [MEDIUM — PRE-EXISTING]
**Location:** `sales/views.py`, `purchases/views.py`, `returns/models.py`

**Mechanism:** No `is_period_locked()` checks before creating journal entries.

**Impact:** Users can dispatch sales invoices, receive purchase invoices, and void returns in locked periods.

**Assessment:** Same as Risk 1. Pre-existing gap.

---

## 4. DRIFT INDICATORS

### ✅ NO NEW ABSTRACTION LAYERS
Phase 21 introduced exactly 2 new services:
1. `PeriodClosingService` — governance layer (reads financial data, writes period status only)
2. `ReversalSafetyService` — safety layer (reads financial data, delegates to JournalGateway)

Neither introduces abstraction sprawl. Both are thin validation layers.

### ✅ NO DUPLICATED WORKFLOWS
- Payment execution endpoints use existing `FIFOAllocationService` and `SupplierFIFOAllocationService`
- No new FIFO engine created
- No new allocation logic introduced

### ✅ NO HIDDEN HELPER SERVICES
All Phase 21 code is in clearly named, purpose-specific files. No hidden financial mutation paths.

### ⚠️ PRE-EXISTING DRIFT: 6 Modules Bypass JournalGateway
As documented in Risk 1, this is a pre-existing architectural drift. Phase 21 did not worsen it.

---

## 5. SAFE AREAS (Confirmed Stable)

### ✅ Period Governance (Phase 21)
- JournalGateway enforces period locks on create/post/reverse
- PeriodClosingService validates readiness before close
- FiscalPeriodCloseLog creates immutable audit trail
- Reopen requires reason + creates audit log
- No silent override paths in Phase 21 code

### ✅ Reversal Safety (Phase 21)
- ReversalSafetyService is read-only for analysis
- Execution delegates to JournalGateway.reverse_entry()
- Period lock enforced before reversal
- Double-reversal prevention implemented
- Reversal loop detection implemented
- All reversals are atomic via @transaction.atomic

### ✅ Payment Execution (Phase 21)
- Period lock enforced on all 3 payment endpoints
- FIFO allocation uses existing single-source service
- Mixed payment validation: sum(parts) == total
- No cached allocation states
- Deterministic: same input → same allocation

### ✅ Explainability Layer (Phase 21 additions)
- `explain_journal_entry()` reads from JournalEntry + JournalEntryLine + JournalEventLog (SSOT)
- `explain_return()` reads from ReturnOrder + JournalEntry (SSOT)
- `explain_asset()` reads from FixedAsset + AssetDepreciation + JournalEntry (SSOT)
- No recomputed balances
- No precomputed financial summaries
- Fully deterministic and traceable

### ✅ PDF & Export Layer (Phase 21)
- All PDFs read directly from model fields (SSOT reads)
- No export-specific calculation logic
- No cached financial snapshot layer
- Customer/supplier statements read from customer.balance, supplier.balance (stored SSOT)
- Period closing summary reads from PeriodClosingService.check_readiness() (derived from SSOT)
- Reversal audit reads from ReversalSafetyService.analyze_impact() (derived from SSOT)

### ✅ Reconciliation Consistency (Pre-existing, verified)
- `PaymentReconciliationService` — read-only, derives from FinancialTruthEngine (SSOT)
- `AccountingReconciliationService` — read-only, compares operational data with journal entries
- Both converge on JournalEngine truth
- No dual reconciliation systems
- No cached reconciliation state

---

## 6. PHASE 22 READINESS ASSESSMENT

### Verdict: **B) FUNCTIONALLY COMPLETE BUT ARCHITECTURALLY RISKY**

### Rationale
Phase 21 is architecturally sound in its own deliverables:
- ✅ No dual truth introduced
- ✅ No hidden mutations
- ✅ No cached financial state
- ✅ No UI-side financial truth computation
- ✅ Deterministic execution preserved
- ✅ Audit trail preserved
- ✅ Period governance correct at JournalGateway level

However, the system has a pre-existing architectural risk that Phase 21 exposed but did not resolve:

**JournalGateway is not universally enforced.** Six modules (sales, purchases, returns, payments, expenses, fixed_assets) call JournalEngine directly, bypassing all JournalGateway protections including:
- Period lock enforcement
- Audit logging
- Transaction ID tracking
- Entity reference tracking

Phase 21 correctly added period lock enforcement to JournalGateway, but this protection only applies to code paths that use JournalGateway.

### Recommendation for Phase 22
**Migrate all direct JournalEngine callers to JournalGateway.** This is a surgical migration, not a redesign:
1. `sales/views.py` — replace `JournalEngine.create_entry()` with `JournalGateway.create_entry()`
2. `purchases/views.py` — same
3. `returns/models.py` — same
4. `payments/services.py` — same
5. `expenses/models.py` — same
6. `fixed_assets/services/asset_accounting_service.py` — same

This would close the period lock bypass gap and make the system fully governed.

### What NOT to Do in Phase 22
- Do NOT create a new enforcement layer
- Do NOT introduce middleware-based interception
- Do NOT add runtime JournalEngine blocking
- Do NOT refactor JournalEngine or JournalGateway

The fix is a direct substitution: `JournalEngine` → `JournalGateway` in the 6 modules listed above.

---

## AUDIT SUMMARY

| Dimension | Status | Notes |
|---|---|---|
| SSOT Integrity | ✅ INTACT | JournalEngine remains sole authority |
| Dual Truth | ✅ NONE | No alternative truth sources |
| Hidden Mutations | ✅ NONE | All mutations traceable |
| Period Governance | ⚠️ PARTIAL | Enforced at Gateway, not at direct callers |
| Reversal Safety | ✅ COMPLETE | All paths protected |
| Explainability | ✅ SAFE | Read-only, SSOT-derived |
| PDF/Export Truth | ✅ SAFE | Direct SSOT reads |
| UI Financial Logic | ⚠️ UX-ONLY | Form computation, backend re-validates |
| Reconciliation | ✅ CONSISTENT | Single-source, deterministic |
| Architectural Drift | ⚠️ PRE-EXISTING | 6 modules bypass Gateway |

**Final Classification: B — Functionally complete but architecturally risky due to pre-existing JournalGateway bypass paths.**

Phase 21 itself introduced ZERO architectural risks. The risks identified are pre-existing conditions that Phase 21's period governance work made more visible.
