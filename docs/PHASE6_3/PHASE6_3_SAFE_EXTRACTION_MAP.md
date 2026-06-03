# Phase 6.3 — Safe Extraction Map

**Status:** ✅ READ-ONLY analysis complete
**Date:** 2026-06-02
**Purpose:** For each focus file, identify the safest extraction targets and recommend the extraction strategy.

---

## 1. Extraction Strategy Decision Tree

```
┌────────────────────────────────────────────────────────┐
│ Is the file recently refactored (Phase 6.2)?           │
│ YES → DO NOT TOUCH (observe for 30 days)              │
│ NO  ↓                                                  │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Is the file a data-layer models.py?                   │
│ YES → DO NOT TOUCH (data layer is sacred)             │
│ NO  ↓                                                  │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Is the file an entry point (main.py, app.py)?         │
│ YES → DO NOT TOUCH (entry point)                      │
│ NO  ↓                                                  │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Are there ≥1 giant public method bodies (>80 LOC)?    │
│ YES → Class-shell extraction (KEEP class, EXTRACT     │
│       method bodies to a sibling module)              │
│       Pattern: Phase 6.2 Step 4                       │
│ NO  ↓                                                  │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Are there ≥1 giant private methods (>200 LOC)?        │
│ YES → Private method decomposition                    │
│       (split one method into 3-5 focused methods)     │
│       Pattern: Phase 6.2 Step 3                       │
│ NO  ↓                                                  │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Otherwise → SAFECAUTION (defer to next wave)          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Per-File Extraction Map

### 2.1 `backend/backup/backup_system.py` — **DO NOT TOUCH**

**Status:** Phase 6.2 Step 4 refactored (2026-06-02, 24 hours ago)
**Recommendation:** Observe for 30 days, then re-evaluate.

**Already extracted:**
- `create_backup` body → `backup/extracts/create_backup_workflow.py` (173 LOC)
- `restore_backup` body → `backup/extracts/restore_backup_workflow.py` (141 LOC)

**Remaining potential extraction targets (NOT recommended now):**
| Target | LOC | Why Defer |
|--------|-----|-----------|
| `_create_archive` | 19 | Small, focused, no extraction needed |
| `_post_backup_verify` | 11 | Small, focused |
| `_check_pre_backup_safety` | 24 | Small, focused |
| `BackupValidator` (entire class) | 73 | All 4 methods are static and small |
| `BackupEncryptor` (entire class) | 62 | All 3 methods are static and small |
| `BackupConfig` (entire class) | 90 | All 4 methods are small |
| `BackupScheduler` (entire class) | 96 | Only 4 methods, well-bounded |

**Verdict:** No further extraction needed. The file is now a 742-LOC orchestrator with thin delegators for the 2 giant public methods. Remaining private methods are all <30 LOC.

---

### 2.2 `backend/payments/services.py` — **CAUTION** (RECOMMENDED for next wave)

**Status:** Not refactored. Phase 4C protected logic.
**Recommendation:** **Class-shell extraction** (Phase 6.2 Step 4 pattern). KEEP `PaymentEngine` in `payments/services.py`; extract the 4 public method bodies to `payments/services/extracts/`.

**Extraction targets:**
| Method | LOC | Strategy |
|--------|-----|----------|
| `process_receipt` | ~150 | Extract to `payments/services/extracts/process_receipt.py` |
| `process_payment` | ~150 | Extract to `payments/services/extracts/process_payment.py` |
| `process_transfer` | ~80 | Extract to `payments/services/extracts/process_transfer.py` |
| `process_refund` | ~80 | Extract to `payments/services/extracts/process_refund.py` |

**Refactored class would become:**
```python
class PaymentEngine:
    def process_receipt(self, *args, **kwargs):
        from payments.services.extracts.process_receipt import run
        return run(self, *args, **kwargs)
    # ... etc
```

**Estimated reduction:** 810 LOC → ~150 LOC main file (-82%)

**Risk mitigation:**
- Keep all 9 inbound import sites working (signature unchanged)
- All state via `self.config`, `self.accounting_engine`, etc. (unchanged)
- All logging, side effects, transactions preserved byte-identical
- Pattern matches Phase 6.2 Step 4 (proven safe)

**Tests to verify:**
- `tests/test_payments.py` (4 uses of `PaymentEngine`)
- `tests/test_financial_hardening.py` (4 uses)
- `tests/test_coverage_final.py`, `test_integration_comprehensive.py`, `test_more_coverage.py` (1 use each)

---

### 2.3 `backend/inventory/service/stock_integration.py` — **CAUTION**

**Status:** Not refactored.
**Recommendation:** **Class-shell extraction** (Phase 6.2 Step 4 pattern). KEEP `StockIntegrationService`; extract each of the 13 public method bodies to `inventory/service/extracts/`.

**Extraction targets (13 methods, all public):**
| Method | LOC | Strategy |
|--------|-----|----------|
| TBD (need to read file) | varies | Extract to `inventory/service/extracts/method_*.py` |

**Refactored class would become:**
```python
class StockIntegrationService:
    def method_1(self, *args, **kwargs):
        from inventory.service.extracts.method_1 import run
        return run(self, *args, **kwargs)
    # ... 12 more
```

**Risk mitigation:**
- All 13 methods are public — every signature is part of the contract
- 3 production callers (all in `inventory/`)
- 13 test callers — need to verify each test still passes
- Pattern matches Phase 6.2 Step 4

**Concerns:**
- 13 methods is a lot to extract at once
- Recommended: extract 3-4 per release (Wave #1: 4 methods, Wave #2: 4, Wave #3: 5)
- Or extract all 13 in one wave if tests are comprehensive

---

### 2.4 `frontend/ui/main_window.py` — **DO NOT TOUCH** (defer to Phase 6.4)

**Status:** Entry point. Refactoring would touch every page.
**Recommendation:** **Defer to Phase 6.4** (separate "per-screen extraction standard" phase).

**Why defer:**
- 1,124-LOC class, 45 methods, 23 public
- 80 outbound imports = touches most of the system
- Entry point — refactor must work on first try
- The class wires up 21 different pages, auth, sidebar, telemetry, observability

**Pre-requisites for safe refactor:**
1. Each of the 21 pages extracted to its own `screen.py` (Phase 6.4)
2. Navigation registry extracted to `frontend/ui/navigation/` package
3. Auth wiring extracted to `frontend/security/auth_integration.py`
4. Telemetry hooks already isolated (Phase UX.5)
5. Workflow intelligence hooks already isolated (Phase UX.5)

**After pre-requisites, the refactor would:**
- Extract each `setup_page_X` method to a focused module
- Extract the navigation state machine to a NavigationController class
- Extract the auth wiring to a separate module
- The MainWindow class would become a 200-LOC shell that wires the controllers together

**Estimated reduction:** 1,153 LOC → ~250 LOC main file (-78%)

**Estimated time:** Phase 6.4 = 3-4 weeks of work (21 pages to extract individually first).

---

### 2.5 `frontend/ui/pos/pos_screen.py` — **HIGH RISK** (CAUTION strategy)

**Status:** Not refactored. POS-specific.
**Recommendation:** **CAUTION** — extract private helpers to focused methods. Defer class-shell extraction until per-screen standard is established.

**Extraction targets (40 methods, 6 public):**
- 34 private methods, most <20 LOC each
- 1 large public method: `__init__` (~50 LOC)
- Several medium private methods related to cart, payment, batch selection

**Recommended approach:**
1. Decompose large private methods (>30 LOC) into smaller focused methods
2. Group related private methods into a `_CartManager`, `_PaymentCalculator`, `_BatchSelector` nested class (or extract to a separate module)
3. **Do NOT** extract the public surface (`POSScreen` class itself)

**Estimated reduction:** 897 LOC → ~700 LOC (-22%)

**Risk mitigation:**
- No public API change
- POS transaction semantics preserved
- Phase 3A protected payment flow preserved

---

### 2.6 `frontend/ui/sales/sales_invoice_screen.py` — **HIGH RISK** (CAUTION strategy)

**Status:** Not refactored.
**Recommendation:** **CAUTION** — extract `_setup_screen` (303 LOC) into 4-5 focused private methods. This is the **#2 longest method** in the entire frontend.

**Extraction targets:**
| Target | Current LOC | New Method | Target LOC |
|--------|-------------|------------|------------|
| `_setup_screen` | 303 | `_setup_header` | ~60 |
| | | `_setup_line_items` | ~80 |
| | | `_setup_totals` | ~50 |
| | | `_setup_action_bar` | ~50 |
| | | `_setup_validation` | ~60 |
| Other private methods (29) | ~590 | (unchanged) | ~590 |

**Refactored `_setup_screen` would become:**
```python
def _setup_screen(self):
    self._setup_header()
    self._setup_line_items()
    self._setup_totals()
    self._setup_action_bar()
    self._setup_validation()
```

**Estimated reduction:** 895 LOC → ~830 LOC (-7%) — but **cyclomatic complexity** drops dramatically.

**Risk mitigation:**
- No public API change
- All 24 public methods untouched
- Pure private method decomposition (no file moves, no class splits)
- Pattern matches Phase 6.2 Step 3 (workflow section extraction)

**Why this is the safest frontend refactor:**
- Single method decomposition
- No cross-module coordination
- No test changes needed (private methods not tested directly)
- Reversible in 5 minutes

---

### 2.7 `frontend/ui/purchases/purchase_invoice_screen.py` — **HIGH RISK** (CAUTION strategy)

**Status:** Not refactored. Phase 3C already adopted `DataEntryGrid`.
**Recommendation:** **CAUTION** — same as sales_invoice_screen. Extract `_setup_screen` (296 LOC) into 4-5 focused private methods.

**Extraction targets:**
| Target | Current LOC | New Method | Target LOC |
|--------|-------------|------------|------------|
| `_setup_screen` | 296 | `_setup_header` | ~60 |
| | | `_setup_line_items` | ~70 |
| | | `_setup_totals` | ~50 |
| | | `_setup_action_bar` | ~50 |
| | | `_setup_validation` | ~60 |
| Other private methods (31) | ~600 | (unchanged) | ~600 |

**Estimated reduction:** 897 LOC → ~830 LOC (-7%)

**Risk mitigation:** Same as sales_invoice_screen.

---

## 3. Recommended Refactor Sequence (next wave)

| Order | File | Strategy | Est. Reduction | Risk |
|-------|------|----------|----------------|------|
| **1** | `frontend/ui/sales/sales_invoice_screen.py` | Private method extraction (`_setup_screen` 303→5) | 895→830 | LOW (private only) |
| **2** | `frontend/ui/purchases/purchase_invoice_screen.py` | Private method extraction (`_setup_screen` 296→5) | 897→830 | LOW (private only) |
| **3** | `payments/services.py` | Class-shell extraction (4 method bodies) | 810→150 | MEDIUM (9 callers) |
| **4** | `inventory/service/stock_integration.py` | Class-shell extraction (13 method bodies, in waves of 4-4-5) | 839→150 | MEDIUM (16 callers, 13 tests) |
| 5 | `frontend/ui/pos/pos_screen.py` | Defer until per-screen standard | (TBD) | HIGH (POS-specific) |
| 6 | `frontend/ui/main_window.py` | Defer to Phase 6.4 | (TBD) | EXTREME (entry point) |
| — | `backup/backup_system.py` | **DO NOT TOUCH** | — | N/A (Phase 6.2) |

**Why this order:**
1. Sales invoice `_setup_screen` extraction is the **lowest-risk** refactor possible (private method decomposition, no API change, no cross-module coordination)
2. Purchase invoice `_setup_screen` extraction is identical pattern (parallel refactor)
3. Payments class-shell extraction is a proven pattern (Phase 6.2 Step 4) with manageable blast radius
4. Stock integration is more complex (13 methods, 13 tests) but follows the same pattern

---

## 4. Extraction Risk Matrix

| File | Strategy | LOC Reduction | API Change | Test Impact | Rollback Time |
|------|----------|---------------|------------|-------------|---------------|
| `sales_invoice_screen.py` | Private method extract | -7% (60 LOC) | NONE | None (private) | 5 min |
| `purchase_invoice_screen.py` | Private method extract | -7% (60 LOC) | NONE | None (private) | 5 min |
| `payments/services.py` | Class-shell extract | -82% (660 LOC) | NONE | 5 test files | 10 min |
| `stock_integration.py` | Class-shell extract | -82% (690 LOC) | NONE | 13 test files | 15 min |
| `pos_screen.py` | Defer | — | — | — | — |
| `main_window.py` | Defer (Phase 6.4) | — | — | — | — |
| `backup/backup_system.py` | DO NOT TOUCH | — | — | — | — |

---

## 5. Pre-Refactor Checklist (per file)

For each file to be refactored:
- [ ] Create evidence backup (`docs/PHASE6_3/evidence/<file>_BEFORE.py`)
- [ ] Document public API surface (signatures, return types, side effects)
- [ ] Document inbound callers (file path + what they import)
- [ ] Document outbound dependencies (what the file imports)
- [ ] Run full test suite to capture baseline
- [ ] Identify private methods to extract (only if safe)
- [ ] Create refactor plan with method-by-method extraction order
- [ ] Identify rollback command (cp evidence / rm -rf extracts/)
- [ ] Identify verification commands (test suite + smoke test)
- [ ] Identify a "Reviewer 2" to spot-check the refactor (we have 1, document)

---

## 6. Outputs

| File | Purpose |
|------|---------|
| `docs/PHASE6_3/evidence/inbound_callers.json` | Inbound caller analysis |
| `docs/PHASE6_3/PHASE6_3_HUB_FILE_AUDIT.md` | Hub file audit (Section 6 — per-file metrics) |
| `docs/PHASE6_3/PHASE6_3_COUPLING_ANALYSIS.md` | Coupling analysis (Section 4 — refactor difficulty ranking) |
