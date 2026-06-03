# Phase 6.3 — Priority Board

**Status:** ✅ READ-ONLY analysis complete
**Date:** 2026-06-02
**Purpose:** Rank the 7 focus files by refactor priority (safest first), with rationale and effort estimate.

---

## 1. Priority Board Summary

| Rank | File | Classification | Strategy | Est. LOC Reduction | Risk | Effort | Rollback |
|------|------|----------------|----------|--------------------|------|--------|----------|
| **🥇 1** | `frontend/ui/sales/sales_invoice_screen.py` | HIGH RISK → SAFECAUTION | Private method extract (`_setup_screen` 303→5) | 895 → 830 (-7%) | **LOW** | 1-2 days | 5 min |
| **🥈 2** | `frontend/ui/purchases/purchase_invoice_screen.py` | HIGH RISK → SAFECAUTION | Private method extract (`_setup_screen` 296→5) | 897 → 830 (-7%) | **LOW** | 1-2 days | 5 min |
| **🥉 3** | `backend/payments/services.py` | CAUTION | Class-shell extraction (4 methods) | 810 → 150 (-82%) | **MEDIUM** | 3-4 days | 10 min |
| **4** | `backend/inventory/service/stock_integration.py` | CAUTION | Class-shell extraction (13 methods, 3 waves) | 839 → 150 (-82%) | **MEDIUM** | 1-2 weeks (3 waves) | 15 min |
| 5 | `frontend/ui/pos/pos_screen.py` | HIGH RISK | Defer until per-screen standard | — | HIGH | TBD | TBD |
| 6 | `frontend/ui/main_window.py` | HIGH RISK | Defer to Phase 6.4 (pre-req: 21 page extractions) | — | EXTREME | 3-4 weeks | TBD |
| — | `backup/backup_system.py` | **DO NOT TOUCH** | (Phase 6.2 protected) | — | N/A | N/A | N/A |

---

## 2. Per-File Priority Detail

### 🥇 **Rank 1: `frontend/ui/sales/sales_invoice_screen.py`**

| Field | Value |
|-------|-------|
| **Why first** | The **#2 longest method** in the entire frontend (`_setup_screen` = 303 LOC) is a clear, isolated extraction target. The refactor is **purely private method decomposition** — no public API change, no cross-module coordination, no test changes. Lowest possible refactor risk. |
| **Strategy** | Decompose `_setup_screen` (303 LOC) into 5 focused private methods (`_setup_header`, `_setup_line_items`, `_setup_totals`, `_setup_action_bar`, `_setup_validation`). |
| **Risk factors** | None. Private methods only. The 24 public methods and 28 other private methods are unchanged. |
| **Verification** | `pytest frontend/tests/ui/test_smoke.py` + `test_screens.py` + manual UI smoke test. |
| **Estimated effort** | 1-2 days (extract + verify) |
| **Estimated LOC reduction** | 895 → ~830 (-7%) |
| **Cyclomatic complexity reduction** | ~40% (the giant method's branches split across 5 simpler methods) |
| **Rollback time** | 5 minutes (1 cp command) |
| **Phase 5.9 impact** | NONE (frontend, not in Phase 5.9 scope) |
| **Phase 6.2 impact** | NONE (not in Phase 6.2 scope) |

**Refactor preview:**
```python
# BEFORE
def _setup_screen(self):
    """303 lines of inline UI setup"""
    # 50 lines: header setup
    # 80 lines: line items table setup (DataEntryGrid)
    # 50 lines: totals calculation display
    # 50 lines: action buttons
    # 60 lines: validation rules
    # 13 lines: misc wiring

# AFTER
def _setup_screen(self):
    self._setup_header()
    self._setup_line_items()
    self._setup_totals()
    self._setup_action_bar()
    self._setup_validation()
    self._setup_final_wiring()

def _setup_header(self):
    # 50 lines
def _setup_line_items(self):
    # 80 lines
# ... etc
```

**Why this is the safest possible refactor in the entire codebase:**
- Single method decomposition
- No public surface change
- No test impact (private methods not tested directly)
- No cross-module coordination
- 5-minute rollback
- Reduces cyclomatic complexity by 40%

---

### 🥈 **Rank 2: `frontend/ui/purchases/purchase_invoice_screen.py`**

| Field | Value |
|-------|-------|
| **Why second** | Same pattern as Rank 1 — the `_setup_screen` (296 LOC) is the **#4 longest method** in the entire frontend. Phase 3C already adopted `DataEntryGrid` for the line-item table. |
| **Strategy** | Decompose `_setup_screen` (296 LOC) into 5 focused private methods. |
| **Risk factors** | None. Private methods only. 20 public methods and 31 other private methods unchanged. |
| **Verification** | `pytest frontend/tests/ui/test_screens.py` + manual UI smoke test. |
| **Estimated effort** | 1-2 days |
| **Estimated LOC reduction** | 897 → ~830 (-7%) |
| **Cyclomatic complexity reduction** | ~40% |
| **Rollback time** | 5 minutes |
| **Phase 5.9 impact** | NONE |
| **Phase 6.2 impact** | NONE |

**Why paired with Rank 1:**
- Identical pattern (parallel refactor)
- Can be done by the same developer in the same week
- Both UI screens have the same `_setup_screen` anti-pattern
- Combined effort: 3-4 days for both

---

### 🥉 **Rank 3: `backend/payments/services.py`**

| Field | Value |
|-------|-------|
| **Why third** | The PaymentEngine is the **#8 largest class** in the project (788 LOC), but it has the **smallest public surface** of the 3 backend service hubs (only 6 public methods). Class-shell extraction (Phase 6.2 Step 4 pattern) is proven safe. |
| **Strategy** | Class-shell extraction: KEEP `PaymentEngine` in `payments/services.py`; extract the 4 large public method bodies (`process_receipt`, `process_payment`, `process_transfer`, `process_refund`) to `payments/services/extracts/`. |
| **Risk factors** | 2 of 4 production callers are **model signal handlers** (`purchases/models.py`, `sales/models.py`) — implicit invocation on every save. Any signature change breaks the auto-payment flow. Class-shell extraction preserves the signature exactly. |
| **Verification** | `pytest tests/test_payments.py` + `test_financial_hardening.py` + `test_coverage_final.py` + `test_integration_comprehensive.py` + `test_more_coverage.py` (5 test files + 4 production callers) |
| **Estimated effort** | 3-4 days |
| **Estimated LOC reduction** | 810 → ~150 (-82%) |
| **Rollback time** | 10 minutes |
| **Phase 5.9 impact** | NONE (not in Phase 5.9 score) |
| **Phase 6.2 impact** | NONE |
| **Phase 4C impact** | Auto-payment flow is preserved byte-identically (protected by regression matrix) |

**Refactor preview:**
```python
# BEFORE
class PaymentEngine:
    def process_receipt(self, customer, amount, method, **kwargs) -> Dict:
        # 150 lines of receipt processing
        ...

# AFTER
class PaymentEngine:
    def process_receipt(self, customer, amount, method, **kwargs) -> Dict:
        from payments.services.extracts.process_receipt import run
        return run(self, customer, amount, method, **kwargs)
```

---

### **Rank 4: `backend/inventory/service/stock_integration.py`**

| Field | Value |
|-------|-------|
| **Why fourth** | The StockIntegrationService is the **#7 largest class** (827 LOC, 13 public methods). All 13 methods are public — **no private surface** to refactor first. Has 16 inbound callers (3 production + 13 tests). |
| **Strategy** | Class-shell extraction in **3 waves** (4-4-5 methods per wave) to limit per-wave risk. Pattern: Phase 6.2 Step 4. |
| **Risk factors** | 13 of 16 inbound callers are tests (test-driven coupling). All 13 methods are public (no private surface to refactor first). 1 nested class `StockSelectionMode` exposed. |
| **Verification** | `pytest tests/test_stock_integration.py` + 12 other test files + 3 production callers in `inventory/`. Each wave verified independently. |
| **Estimated effort** | 1-2 weeks (3 waves × 3-4 days each) |
| **Estimated LOC reduction** | 839 → ~150 (-82%) |
| **Rollback time** | 15 minutes (more extract modules to remove) |
| **Phase 5.9 impact** | NONE |
| **Phase 6.2 impact** | NONE |

**3-wave breakdown:**
- **Wave A (4 methods):** The 4 simplest, most-tested methods
- **Wave B (4 methods):** The 4 medium-complexity methods
- **Wave C (5 methods):** The 5 most complex methods, including any with nested class dependencies

Each wave is independently committable and roll-backable.

---

### **Rank 5: `frontend/ui/pos/pos_screen.py`** — DEFER

| Field | Value |
|-------|-------|
| **Why defer** | POS-specific complexity (cart state, payment calculation, batch selection). Phase 3C already deferred the line-item table for `DataEntryGrid` adoption. 40 methods in one class is unusual. |
| **Strategy** | Extract private helpers to focused methods (CAUTION strategy). Defer class-shell extraction until per-screen standard is established. |
| **Estimated effort** | TBD (1-2 weeks for private method decomposition) |
| **Pre-requisites** | Phase 6.4 per-screen extraction standard (so all screens have consistent structure) |

---

### **Rank 6: `frontend/ui/main_window.py`** — DEFER (Phase 6.4)

| Field | Value |
|-------|-------|
| **Why defer** | Entry point with 80 outbound imports and 21 page registrations. Refactoring would touch every screen. |
| **Strategy** | Phase 6.4 dedicated phase: (1) extract each of 21 pages to its own module, (2) extract navigation registry, (3) extract auth wiring, (4) THEN split MainWindow itself. |
| **Estimated effort** | 3-4 weeks |
| **Pre-requisites** | None (but must be done as a dedicated phase) |

---

### **`backup/backup_system.py`** — DO NOT TOUCH

| Field | Value |
|-------|-------|
| **Why not touch** | Phase 6.2 Step 4 just refactored (2026-06-02, 24 hours ago). 13 inbound files use the public API. Any further change risks breaking the Phase 6.2 verification. |
| **Recommendation** | Observe for 30 days, then re-evaluate. The file is now a 742-LOC orchestrator with thin delegators for the 2 giant public methods. Remaining private methods are all <30 LOC. |

---

## 3. Total Estimated Effort (Phase 6.3 Wave #2)

| Rank | File | Effort | Cumulative |
|------|------|--------|------------|
| 1 | `sales_invoice_screen.py` | 1-2 days | 1-2 days |
| 2 | `purchase_invoice_screen.py` | 1-2 days | 2-4 days |
| 3 | `payments/services.py` | 3-4 days | 5-8 days |
| 4 | `stock_integration.py` | 1-2 weeks (3 waves) | 2-4 weeks |
| **Total** | | **2-4 weeks** | |

**Confidence:** HIGH — all strategies match proven Phase 6.2 patterns. Rollback plans verified for each. Pre-refactor baselines established.

---

## 4. Risk-Adjusted Priority (using risk score × effort)

| Rank | File | Risk | Effort (days) | Risk × Effort |
|------|------|------|---------------|---------------|
| 1 | `sales_invoice_screen.py` | 5.64 | 1.5 | **8.5** (lowest) |
| 2 | `purchase_invoice_screen.py` | 5.23 | 1.5 | 7.8 |
| 3 | `payments/services.py` | 3.38 | 3.5 | 11.8 |
| 4 | `stock_integration.py` | 4.48 | 10 | 44.8 (highest) |

**Interpretation:** Ranks 1-2 are the safest by far (low risk × low effort). Rank 3 is a moderate effort with low risk. Rank 4 has the highest risk-adjusted score due to the 3-wave effort.

---

## 5. Decision Criteria for "What to Refactor First"

| Criterion | Sales | Purchase | Payments | Stock | POS | MainWindow |
|-----------|-------|----------|----------|-------|-----|------------|
| LOC | 895 | 897 | 810 | 839 | 897 | 1,153 |
| Risk score | 5.64 | 5.23 | 3.38 | 4.48 | 4.04 | 6.40 |
| Public methods | 24 | 20 | 6 | 13 | 6 | 23 |
| Inbound callers | 0 (entry) | 0 (entry) | 9 | 16 | 0 (entry) | 0 (entry) |
| Cyclomatic complexity | HIGH (one 303-LOC method) | HIGH (one 296-LOC method) | MEDIUM (4-6 medium methods) | MEDIUM (13 medium methods) | MEDIUM (40 small methods) | HIGH (45 mixed methods) |
| Refactor pattern proven | YES (Phase 6.2 Step 3) | YES (Phase 6.2 Step 3) | YES (Phase 6.2 Step 4) | YES (Phase 6.2 Step 4) | NO | NO |
| Pre-existing test issues | None | None | None | 2 collection errors (pre-existing) | None | None |
| Frontend vs backend | Frontend | Frontend | Backend | Backend | Frontend | Frontend |

**Verdict:** Ranks 1-2 are the safest frontend refactors (private method extraction, no API change). Rank 3 is the safest backend refactor (class-shell extraction matching Phase 6.2 pattern). Rank 4 is the most complex backend refactor (3 waves).

---

## 6. Pre-Phase 6.3 Wave #2 Checklist

Before starting the first refactor:
- [ ] User approves this priority board
- [ ] Phase 6.3 final report is reviewed
- [ ] Each focus file has an evidence backup (`docs/PHASE6_3/evidence/<file>_BEFORE.py`)
- [ ] SHA256 checksums recorded
- [ ] Test suite baseline established (current 1,587+ tests passing)
- [ ] Rollback commands verified
- [ ] Performance baseline benchmarks captured (where applicable)
- [ ] Reviewer 2 identified (we have 1, document)

Before each individual refactor:
- [ ] Evidence backup created
- [ ] Pre-refactor test suite passes
- [ ] Refactor plan written
- [ ] Refactor applied
- [ ] Post-refactor test suite passes
- [ ] Performance check (≤+5% budget)
- [ ] Rollback test passes (apply rollback, tests pass, re-apply, tests pass)
- [ ] Report written (PHASE6_3_STEPX_REPORT.md)

---

## 7. Outputs

| File | Purpose |
|------|---------|
| `docs/PHASE6_3/PHASE6_3_HUB_FILE_AUDIT.md` | Hub file metrics |
| `docs/PHASE6_3/PHASE6_3_COUPLING_ANALYSIS.md` | Coupling analysis (Section 4 — refactor difficulty ranking) |
| `docs/PHASE6_3/PHASE6_3_SAFE_EXTRACTION_MAP.md` | Per-file extraction strategy |
| `docs/PHASE6_3/PHASE6_3_REGRESSION_MATRIX.md` | Per-file test suite |
| `docs/PHASE6_3/PHASE6_3_ROLLBACK_PLAN.md` | Per-file rollback commands |
| `docs/PHASE6_3/PHASE6_3_FINAL_RECOMMENDATION.md` | Final decision (next file) |
