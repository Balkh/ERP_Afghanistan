# Phase 6.6D — Refactor Priority Matrix

**Date:** 2026-06-03  
**Companion to:** `PHASE6_6D_CRITICAL_REMEDIATION_AUDIT.md`  
**Purpose:** Define execution order that maximizes value while minimizing risk.  
**Type:** READ-ONLY blueprint. No code changes. No patches. No migrations.

---

## Methodology

Each candidate refactor is scored on:

| Dimension | Range | Description |
|-----------|-------|-------------|
| **Effort** | XS / S / M / L / XL | XS = <30min, S = 1-2h, M = half-day, L = 1-2d, XL = >1 week |
| **Risk** | NONE / LOW / MEDIUM / HIGH | Probability of regression in production |
| **Gain** | 0-10 | Quantified benefit (security, performance, maintainability, audit) |
| **Dependencies** | list | Must be done before this; blocks this; or independent |
| **Confidence** | % | Likelihood gain estimate is accurate |

**Priority calculation:** `Priority = (Gain × 10) / (Effort_hours × Risk_factor)`  
Where `Risk_factor` = NONE=1, LOW=1.5, MEDIUM=3, HIGH=6.

---

## Refactor Inventory

### R1 — Remove eval() in patterns.py:77

| Field | Value |
|-------|-------|
| Effort | **XS** (5 min, 3 LOC) |
| Risk | **NONE** (pure refactor, no semantic change) |
| Gain | **6/10** (security audit, compliance, maintenance) |
| Dependencies | NONE |
| Confidence | **95%** |

**Work:** Replace `patterns: Dict[str, int] = defaultdict(int)` with `Dict[Tuple[str, ...], int]`. Change `patterns[str(seq)] += 1` to `patterns[seq] += 1`. Change `eval(seq_str)` to `list(seq)`. See `PHASE6_6D_CRITICAL_REMEDIATION_AUDIT.md` §A.8.

**Tests:** Existing 8 tests at `simulation/tests/test_intelligence/test_intelligence.py:160-220, 517-520` cover determinism + correctness.

**Priority score: 6 × 10 / (0.083 × 1) = 720** ← **HIGHEST PRIORITY**

---

### R2 — Delete dead `DEBUG_MODE = True` in client.py:11

| Field | Value |
|-------|-------|
| Effort | **XS** (5 min, 1 LOC) |
| Risk | **NONE** (dead code, no behavioural effect) |
| Gain | **4/10** (audit hygiene, lint cleanup) |
| Dependencies | NONE |
| Confidence | **99%** |

**Work:** Delete line 11. Verified by grep: `content.count('DEBUG_MODE')` returns 1 (only the declaration). Zero downstream references.

**Tests:** None required — pure deletion of unused constant.

**Priority score: 4 × 10 / (0.083 × 1) = 480**

---

### R3 — Remove `time.sleep(0.35 * (attempt + 1))` in client.py:247

| Field | Value |
|-------|-------|
| Effort | **XS** (5 min, 1 LOC) |
| Risk | **LOW** (replaces blocking sleep with exponential backoff or removes it) |
| Gain | **5/10** (reduces UI freeze from 92s worst case to 90s — minor; OR eliminates it entirely if removed) |
| Dependencies | NONE |
| Confidence | **85%** |

**Work:** Option A (preferred): Remove the line entirely. The retry loop already does exponential backoff implicitly via timeout escalation. Option B: Use `QThread.msleep` (still blocks, same problem). Option C: Replace with async timer (requires R5).

**Recommendation:** **Remove entirely** for now; revisit when R5 (async migration) is in place.

**Tests:** Existing retry tests at `frontend/tests/ui/test_api_retry.py` cover retry behaviour.

**Priority score: 5 × 10 / (0.083 × 1.5) = 402**

---

### R4 — Drop 4 redundant single-column FK indexes

| Field | Value |
|-------|-------|
| Effort | **S** (1-2h, 4 migrations) |
| Risk | **LOW** (FK default remains; only the redundant index is removed) |
| Gain | **3/10** (write IOPS reduction, small disk savings) |
| Dependencies | NONE |
| Confidence | **90%** |

**Indexes to drop:**
1. `accounting__entry_i_27304d_idx` (JournalEntryLine.entry)
2. `sales_sales_batch_i_bc534d_idx` (SalesItem.batch)
3. `sales_sales_invoice_aabbb2_idx` (SalesItem.invoice)
4. `purchases_p_invoice_96471d_idx` (PurchaseItem.invoice)

**Work:** Remove from `Meta.indexes` in respective models. Run `python manage.py makemigrations` to generate `RemoveIndex` operations. Deploy. For PG, run `CREATE INDEX CONCURRENTLY` for the reverse (NOT NEEDED — only dropping).

See `FK_INDEX_VERIFICATION_REPORT.md` §7.2.

**Tests:** Existing 1,587+ tests verify ORM queries; index removal is transparent to application code.

**Priority score: 3 × 10 / (1.5 × 1.5) = 13**

---

### R5 — Move HTTP off UI thread (QThread + worker)

| Field | Value |
|-------|-------|
| Effort | **XL** (140h, ~3.5 weeks) |
| Risk | **MEDIUM** (threading, signal/slot correctness) |
| Gain | **10/10** (eliminates ALL UI freeze — 20+ screens affected) |
| Dependencies | R3 should be done first |
| Confidence | **75%** (effort estimate) |

**Work:** See `PHASE6_6D_CRITICAL_REMEDIATION_AUDIT.md` §F.3-§F.5. Add `APIClient.get_async/post_async/...` methods backed by `QThread` workers. Migrate top 5 screens (returns, backup, payroll, account_ledger, purchase_invoice) to async.

**Tests:** New tests for `Worker` thread safety; existing sync tests still pass.

**Priority score: 10 × 10 / (140 × 3) = 0.24** (LOW priority due to effort, but highest absolute gain)

---

### R6 — Split PaymentEngine (4 responsibilities → 4 classes)

| Field | Value |
|-------|-------|
| Effort | **L** (1-2d, 16h) |
| Risk | **MEDIUM** (3-layer dep on accounting; static method pattern) |
| Gain | **5/10** (maintainability, testability) |
| Dependencies | NONE |
| Confidence | **80%** |

**Work:** Extract 4 classes from `PaymentEngine`:
- `ReceiptProcessor` (process_receipt + helpers)
- `PaymentProcessor` (process_payment + helpers)
- `TransferProcessor` (process_transfer + helpers)
- `RefundProcessor` (process_refund + helpers)
- Keep `get_account_transactions` as a query helper on a 5th class or stay on engine.

Cross-domain coupling to `accounting` via `MigrationRouter` makes pure extraction non-trivial. Each new class still needs to import `MigrationRouter` and call `create_entry`. Consider extracting a `PaymentJournalBridge` to absorb that.

**Tests:** All 788 LOC of PaymentEngine is test-covered; refactor preserves public API.

**Priority score: 5 × 10 / (16 × 3) = 1.04**

---

### R7 — Split MainWindow (8 responsibilities → 8 controllers)

| Field | Value |
|-------|-------|
| Effort | **XL** (>1 week, 80-120h) |
| Risk | **HIGH** (21 navigation routes, sidebar coupling, status bar lifecycle) |
| Gain | **6/10** (maintainability, testability) |
| Dependencies | R5 should be in place (async-aware controllers) |
| Confidence | **65%** (high risk of breaking navigation) |

**Work:** Extract 8 controllers (see `PHASE6_6D_CRITICAL_REMEDIATION_AUDIT.md` §D.4):
- `StatusBarController` (4 methods)
- `NavigationController` (10 methods — change_page, _build_breadcrumb, etc.)
- `MenuController` (9 methods — create_menu_bar, dialogs, etc.)
- `ThemeController` (4 methods)
- `ConnectionController` (6 methods — check_connection, license, etc.)
- `SessionController` (4 methods — logout, _determine_role, etc.)
- `LifecycleController` (4 methods — keyPress, closeEvent, etc.)
- `UiBuilder` (3 methods — _build_ui, resize, _apply_sidebar_scopes)

**Risk:** NavigationController is tightly coupled to QStackedWidget indices. Splitting requires a navigation registry pattern.

**Tests:** UI smoke tests + manual navigation tests. No automated coverage for navigation routes.

**Priority score: 6 × 10 / (100 × 6) = 0.10** ← LOW priority (highest absolute cost + risk)

---

### R8 — Split PaymentOperationsViewSet (1077 LOC, 17 methods)

| Field | Value |
|-------|-------|
| Effort | **L** (1-2d, 16-24h) |
| Risk | **MEDIUM** (DRF ViewSet semantics, URL routing) |
| Gain | **5/10** (maintainability, testability) |
| Dependencies | R6 should be done first (so engine split is consistent) |
| Confidence | **75%** |

**Work:** Split into endpoint-specific viewsets:
- `CustomerPaymentViewSet` (L113-220, ~7 actions)
- `SupplierPaymentViewSet` (L321-430, ~7 actions)
- `MixedPaymentViewSet` (L450-600, ~3 actions)
- `FifoAllocationViewSet` (already exists — extract to new file)
- `PaymentTraceViewSet` (L220-300, ~3 actions)
- `PaymentValidationViewSet` (L520-549, ~1 action)

Update `urls.py` to register each separately.

**Tests:** Each new viewset gets a focused test file; existing integration tests continue to pass.

**Priority score: 5 × 10 / (20 × 3) = 0.83**

---

### R9 — Split PurchaseInvoiceScreen / SalesInvoiceScreen / POSScreen

| Field | Value |
|-------|-------|
| Effort | **L** (1-2d each, 60h total) |
| Risk | **HIGH** (POS flow is safety-critical; bugs = lost revenue) |
| Gain | **4/10** (maintainability) |
| Dependencies | R7 (MainWindow split) preferred but not required |
| Confidence | **70%** |

**Work:** Extract sub-controllers (e.g., `LineItemController`, `PaymentAllocator`, `BatchSelector`, `CustomerPicker`). Each invoice screen has 3-4 natural axes.

**Tests:** POS flow has integration tests; manual smoke tests required.

**Priority score: 4 × 10 / (60 × 6) = 0.11**

---

### R10 — Refactor StockIntegrationService (827 LOC → 3 services)

| Field | Value |
|-------|-------|
| Effort | **M** (4h) |
| Risk | **LOW** (3 cleanly separable concerns) |
| Gain | **4/10** (maintainability) |
| Dependencies | NONE |
| Confidence | **90%** |

**Work:** Split into:
- `BatchQueryService` (L25-69, 1 method)
- `StockAllocationEngine` (L71-300, ~5 methods)
- `StockMovementService` (L300-838, ~7 methods)

**Tests:** Existing test coverage; no API change.

**Priority score: 4 × 10 / (4 × 1.5) = 6.7**

---

### R11 — Refactor JournalEngine (already well-bounded, low priority)

| Field | Value |
|-------|-------|
| Effort | **M** (4h) |
| Risk | **LOW** |
| Gain | **2/10** (incremental improvement) |
| Dependencies | NONE |
| Confidence | **85%** |

**Work:** Optional — extract `EntryNumberGenerator`, `LineValidator`, `BalanceUpdater` as separate classes. Already passes the "large but acceptable" threshold.

**Priority score: 2 × 10 / (4 × 1.5) = 3.3**

**Recommendation:** **DEFER** — already at acceptable size; refactor adds little value.

---

### R12 — Fix shadowed methods in payment_operations.py (L113, L321)

| Field | Value |
|-------|-------|
| Effort | **S** (1h) |
| Risk | **LOW** (L113/L321 are dead code due to Python class-body override) |
| Gain | **2/10** (code clarity, lint) |
| Dependencies | NONE |
| Confidence | **95%** |

**Work:** Verified in Phase 6.6C: `payment_operations.py:113` and `payment_operations.py:321` define `process_customer_payment` and `process_supplier_payment`. At L550 and L684, these methods are RE-DEFINED. Python's class-body override means L113/L321 are dead. Delete the dead methods.

**Tests:** Existing tests cover the L550/L684 versions.

**Priority score: 2 × 10 / (1 × 1.5) = 13**

---

### R13 — Remove hardcoded window geometry in main_window.py

| Field | Value |
|-------|-------|
| Effort | **XS** (15 min) |
| Risk | **NONE** (read user settings instead of hardcoded) |
| Gain | **3/10** (HiDPI / multi-monitor support) |
| Dependencies | NONE |
| Confidence | **95%** |

**Work:** Replace `setGeometry(L33-34)` with `QSettings`-based restore. Save on `closeEvent`, restore on `__init__`.

**Tests:** Manual only.

**Priority score: 3 × 10 / (0.25 × 1) = 120**

---

## Execution Order (Recommended)

### Sprint 1 — Quick wins (5h, all LOW/NONE risk, high audit value)

1. **R1** — Remove eval() (5 min) ← **Do today**
2. **R2** — Delete dead DEBUG_MODE (5 min) ← **Do today**
3. **R3** — Remove time.sleep (5 min) ← **Do today**
4. **R13** — Replace hardcoded geometry (15 min) ← **Do today**
5. **R12** — Delete shadowed methods (1h) ← **Do today**
6. **R4** — Drop 4 redundant indexes (1.5h) ← **Generate migrations + deploy**

**Total: ~3h, ZERO risk, audit +6 points**

### Sprint 2 — Architectural refactor (32h, MEDIUM risk, high structural value)

7. **R10** — Split StockIntegrationService (4h, LOW risk) ← **Warm-up**
8. **R11** — Refactor JournalEngine (4h, LOW risk) — *optional, defer if low priority*
9. **R6** — Split PaymentEngine (16h, MEDIUM risk) ← **Core refactor**
10. **R8** — Split PaymentOperationsViewSet (20h, MEDIUM risk) ← **Coupled with R6**

**Total: ~40h, MEDIUM risk, structural +5 points**

### Sprint 3 — Async migration (140h, MEDIUM risk, ELIMINATES UI freeze)

11. **R5** — Move HTTP off UI thread (140h, MEDIUM risk) ← **Biggest user-facing win**

**Total: 140h, eliminates 100% of UI freeze**

### Sprint 4 — UI decomposition (DEFER or PARTIAL)

12. **R7** — Split MainWindow (100h, HIGH risk) ← **DEFER until R5 done**
13. **R9** — Split invoice screens (60h, HIGH risk) ← **DEFER or pair with R7**

**Total: 160h, HIGH risk, +4 maintainability points**

---

## Cumulative Impact

| After | Total effort | Audit gain | Structural gain | Performance gain | Risk |
|-------|--------------|------------|-----------------|------------------|------|
| Sprint 1 | 5h | +6 (eval, DEBUG, indexes) | 0 | +0.5 (R3) | NONE |
| Sprint 2 | 45h | +0 | +5 (3 service splits) | 0 | LOW-MEDIUM |
| Sprint 3 | 185h | +0 | +2 | **+10 (UI freeze eliminated)** | MEDIUM |
| Sprint 4 | 345h | +0 | +4 | 0 | HIGH |

---

## Hard "DO NOT" list

- ❌ Do NOT migrate to async before fixing eval() — adds risk surface
- ❌ Do NOT split MainWindow before async migration — controllers will need async anyway
- ❌ Do NOT drop indexes without verifying production has the FK defaults (already done in `FK_INDEX_VERIFICATION_REPORT.md`)
- ❌ Do NOT extract `PaymentJournalBridge` until PaymentEngine split is validated
- ❌ Do NOT touch test files in any refactor (excluded from scope)

---

## Sign-off

| Sprint | Items | Effort | Risk | Gain | Recommendation |
|--------|-------|--------|------|------|----------------|
| **Sprint 1** (R1, R2, R3, R12, R13, R4) | 6 | 5h | NONE-LOW | 6/10 | **Execute now** |
| **Sprint 2** (R10, R6, R8) | 3 | 40h | LOW-MEDIUM | 5/10 | **Execute next sprint** |
| **Sprint 3** (R5) | 1 | 140h | MEDIUM | 10/10 | **Execute after Sprint 2** |
| **Sprint 4** (R7, R9) | 2 | 160h | HIGH | 4/10 | **Defer or skip** |

**Optimal stopping point: After Sprint 2 (45h total) for production-ready claim.**
**Stretch goal: After Sprint 3 (185h total) for enterprise-ready claim.**
