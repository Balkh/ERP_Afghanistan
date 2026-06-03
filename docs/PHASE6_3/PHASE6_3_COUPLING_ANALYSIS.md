# Phase 6.3 — Coupling Analysis

**Status:** ✅ READ-ONLY analysis complete
**Date:** 2026-06-02

---

## 1. Coupling Score Methodology

**Coupling score** = inbound imports + outbound imports (fan-in + fan-out)
- Captures both "who depends on me" (fan-in) and "who I depend on" (fan-out)
- Higher = harder to refactor (more blast radius)

**Change risk score** (composite heuristic):
- `risk = (LOC/100)*0.25 + (inbound/5)*0.30 + (outbound/10)*0.20 + (public_methods/3)*0.25`
- Captures size, inbound coupling, outbound coupling, surface area
- Range: typically 0-10+ for hub files

**Rollback complexity** (subjective):
- 1 = trivial (single file, no inbound)
- 2 = easy (single file, few inbound, isolated)
- 3 = moderate (single file, moderate inbound)
- 4 = hard (multiple files, many inbound, cross-module)
- 5 = extreme (cross-cutting, schema-adjacent, entry-point)

---

## 2. Focus File Coupling Matrix

| File | LOC | Inbound | Outbound | Coupling | Public Methods | Risk Score | Rollback |
|------|-----|---------|----------|----------|----------------|------------|----------|
| `backup/backup_system.py` | 742 | 13 | 27 | **40** | 20 | 4.84 | 4 (Phase 6.2 protected) |
| `payments/services.py` | 810 | 9 | 16 | **25** | 6 | 3.38 | 3 |
| `inventory/service/stock_integration.py` | 839 | 16 | 17 | **33** | 13 | 4.48 | 4 |
| `frontend/ui/main_window.py` | 1,153 | 0 | 80 | **80** | 23 | 6.40 | 5 (entry point) |
| `frontend/ui/pos/pos_screen.py` | 897 | 0 | 65 | **65** | 6 | 4.04 | 4 (UI screen) |
| `frontend/ui/sales/sales_invoice_screen.py` | 895 | 0 | 70 | **70** | 24 | 5.64 | 4 (UI screen) |
| `frontend/ui/purchases/purchase_invoice_screen.py` | 897 | 0 | 66 | **66** | 20 | 5.23 | 4 (UI screen) |

---

## 3. Per-File Coupling Analysis

### 3.1 `backend/backup/backup_system.py` — **DO NOT TOUCH** (Phase 6.2 protected)

**Coupling breakdown:**
- Inbound (13): 4 management commands, 4 service modules, 2 view modules, 1 test, 2 audit scripts
- Outbound (27): django.conf, cryptography, hashlib, sqlite3, tarfile, json, etc.
- Net coupling: **balanced** (13 in / 27 out) — both moderate

**Phase 6.2 Step 4 verdict:** Already extracted to `backup/extracts/`. Public method bodies are 12 and 11 lines (delegators). SHA256 roundtrip verified byte-identical.

**Why DO NOT TOUCH now:**
- Just refactored in Phase 6.2 (24 hours ago)
- 13 inbound files all use the public API
- Any further change risks breaking the Phase 6.2 verification
- Recommended: **observe for 30 days** before any further refactor

### 3.2 `backend/payments/services.py` — **CAUTION** (Phase 4C protected)

**Coupling breakdown:**
- Inbound (9): 1 view, 2 model signal handlers, 1 service, 5 tests
- Outbound (16): accounting.models, payments.models, decimal, datetime, etc.
- Net coupling: **moderate** (9 in / 16 out)

**Risk factors:**
- 2 inbound callers are **model signal handlers** (`purchases/models.py`, `sales/models.py`) — implicit, runs on every save
- All 6 public methods are called by signal handlers or services
- The class has 10 methods, only 6 are public — internal surface is moderate
- Phase 4C certifies the auto-payment flow (sales payment → journal entry, purchase payment → journal entry)

**Why CAUTION (not HIGH RISK):**
- 1 class, 10 methods — relatively focused
- 9 inbound files is manageable (vs 16 for stock_integration)
- Public method count is small (6)
- Phase 4C protects the contract but doesn't make refactoring impossible

**Safest refactor:** Class-shell extraction (KEEP `PaymentEngine` in `payments/services.py`; extract the 4 public method bodies to `payments/services/extracts/`). Pattern matches Phase 6.2 Step 4.

### 3.3 `backend/inventory/service/stock_integration.py` — **CAUTION**

**Coupling breakdown:**
- Inbound (16): 3 production files, 13 test files
- Outbound (17): inventory.models, decimal, datetime, django.db, etc.
- Net coupling: **moderate-high** (16 in / 17 out)

**Risk factors:**
- 13 of 16 inbound callers are **tests** — refactor breaks 13 test files
- All 13 methods are public — **no private surface to refactor first**
- 1 nested class `StockSelectionMode` is also public
- 839 LOC, 1 class — moderate size

**Why CAUTION (not HIGH RISK):**
- 3 production callers all in `inventory/` (low blast radius outside inventory)
- 13 test callers are isolated (no cross-test dependencies)
- The service is self-contained — only imports from `inventory.models` and stdlib

**Safest refactor:** Class-shell extraction (KEEP `StockIntegrationService` in same file; extract each of the 13 public method bodies to `inventory/service/extracts/stock_integration_methods.py`). Pattern matches Phase 6.2 Step 4.

### 3.4 `frontend/ui/main_window.py` — **HIGH RISK** (entry point)

**Coupling breakdown:**
- Inbound (0): ZERO Python imports — entry point
- Outbound (80): every page module, sidebar, auth, api, components
- Net coupling: **extreme fan-out** (0 in / 80 out)

**Risk factors:**
- 1,153 LOC, 1 class, 45 methods — **#2 largest class** in entire codebase
- 23 public methods (vs 22 private) — extreme surface
- 80 outbound imports = depends on most of the system
- Application entry point — refactor must work on first try
- The class wires up navigation, auth, page registration, telemetry, workflow intelligence, observability

**Why HIGH RISK:**
- Any signature change breaks the app startup
- 80 outbound imports = the class would be split, but each new module needs to import ~80 things (no actual decoupling)
- The 23 public methods are called by:
  - `frontend/main.py` (1 method)
  - 13 test fixtures in `frontend/tests/ui/test_main_window.py`
  - Internal (private call chain)
- Refactor would need to preserve the **navigation state machine** (which page is current, which user is logged in, what permissions)

**Recommended strategy if extracted:** **DO NOT TOUCH for now.** Defer to a dedicated Phase (e.g., Phase 6.4) that:
1. First extracts each of the 21 pages to its own module
2. Then extracts the navigation registry to a `frontend/ui/navigation/` package
3. Then extracts the auth wiring to `frontend/security/auth_integration.py`
4. Then can safely split `MainWindow` itself

### 3.5 `frontend/ui/pos/pos_screen.py` — **HIGH RISK**

**Coupling breakdown:**
- Inbound (0): ZERO Python imports
- Outbound (65): api/, components/, dialogs, forms, etc.
- Net coupling: **extreme fan-out** (0 in / 65 out)

**Risk factors:**
- 897 LOC, 1 class, 40 methods — **#6 largest class**
- 6 public methods (vs 34 private) — most logic is private
- POS-specific (Phase 3C deferred `DataEntryGrid` adoption)
- 65 outbound imports = depends on most UI components

**Why HIGH RISK:**
- 40 methods all in one class = complex internal state
- POS workflows are stateful (cart, payment, customer selection, batch selection)
- Any refactor must preserve transaction semantics (Phase 3A protected)

**Recommended strategy if extracted:** **CAUTION** — extract private helpers (cart management, payment calculation, batch selection) to focused modules. Defer the public surface (`POSScreen` class itself) until Phase 6.4 (per-screen extraction standard).

### 3.6 `frontend/ui/sales/sales_invoice_screen.py` — **HIGH RISK**

**Coupling breakdown:**
- Inbound (0): ZERO Python imports
- Outbound (70): api/, components/, dialogs, forms, etc.
- Net coupling: **extreme fan-out** (0 in / 70 out)

**Risk factors:**
- 895 LOC, 1 class, 31 methods — **#5 largest class**
- 24 public methods — **extreme surface area** (the highest of all focus files)
- 1 method (`_setup_screen` = 303 LOC) is **#2 longest method** in entire frontend
- 70 outbound imports

**Why HIGH RISK:**
- 24 public methods is unusual — most are called by `main_window.py` (page registration, navigation hooks)
- The 303-LOC `_setup_screen` is a clear extraction target

**Recommended strategy if extracted:** **CAUTION** — first extract `_setup_screen` (303 LOC) into 4-5 focused private methods (`_setup_header`, `_setup_line_items`, `_setup_totals`, `_setup_action_bar`, `_setup_validation`). Then extract line-item table helpers. Pattern: pure private method decomposition (no file moves, no class splits).

### 3.7 `frontend/ui/purchases/purchase_invoice_screen.py` — **HIGH RISK**

**Coupling breakdown:**
- Inbound (0): ZERO Python imports
- Outbound (66): api/, components/, dialogs, forms, etc.
- Net coupling: **extreme fan-out** (0 in / 66 out)

**Risk factors:**
- 897 LOC, 1 class, 33 methods — **#4 largest class**
- 20 public methods
- 1 method (`_setup_screen` = 296 LOC) is **#4 longest method** in entire frontend
- Phase 3C already adopted `DataEntryGrid` for the line-item table

**Why HIGH RISK:**
- Similar to sales invoice screen — same pattern
- 296-LOC `_setup_screen` is a clear extraction target

**Recommended strategy if extracted:** **CAUTION** — same as sales invoice. Extract `_setup_screen` first.

---

## 4. Refactor Difficulty Ranking (safest first)

| Rank | File | Classification | Strategy | Difficulty |
|------|------|----------------|----------|------------|
| 1 | `payments/services.py` | **CAUTION** | Class-shell extraction (Phase 6.2 pattern) | **EASY** |
| 2 | `inventory/service/stock_integration.py` | **CAUTION** | Class-shell extraction | **MEDIUM** (13 tests to update) |
| 3 | `frontend/ui/sales/sales_invoice_screen.py` | **HIGH RISK** | Private method extraction only | **MEDIUM** (extract `_setup_screen`) |
| 4 | `frontend/ui/purchases/purchase_invoice_screen.py` | **HIGH RISK** | Private method extraction only | **MEDIUM** (extract `_setup_screen`) |
| 5 | `frontend/ui/pos/pos_screen.py` | **HIGH RISK** | Defer | **HARD** (POS-specific) |
| 6 | `frontend/ui/main_window.py` | **HIGH RISK** | Defer | **EXTREME** (entry point, 80 imports) |
| — | `backup/backup_system.py` | **DO NOT TOUCH** | (Phase 6.2 protected) | N/A |

---

## 5. Coupling Score Distribution

| Coupling Range | File Count | % of Focus |
|----------------|------------|------------|
| 0-25 (low) | 1 (14%) | `payments/services.py` |
| 26-50 (medium) | 2 (29%) | `backup/backup_system.py`, `inventory/service/stock_integration.py` |
| 51-75 (high) | 3 (43%) | `pos_screen.py`, `purchase_invoice_screen.py`, `sales_invoice_screen.py` |
| 76+ (extreme) | 1 (14%) | `main_window.py` |

**Observation:** Frontend files dominate the high-coupling range. Backend files are clustered in the low-to-medium range.

---

## 6. Risk Score Distribution

| Risk Range | File Count | % of Focus |
|------------|------------|------------|
| 0-3.0 (low) | 0 | — |
| 3.0-4.0 (medium) | 2 (29%) | `payments/services.py` (3.38), `pos_screen.py` (4.04) |
| 4.0-5.0 (high) | 3 (43%) | `stock_integration.py` (4.48), `backup_system.py` (4.84), `purchase_invoice_screen.py` (5.23) |
| 5.0+ (extreme) | 2 (29%) | `sales_invoice_screen.py` (5.64), `main_window.py` (6.40) |

---

## 7. Coupling Hot Spots in Project (Top 10)

These are the most tightly coupled files in the project (excluding data layer models):

| File | LOC | Inbound | Outbound | Coupling |
|------|-----|---------|----------|----------|
| `frontend/ui/main_window.py` | 1,153 | 0 | 80 | **80** |
| `frontend/ui/sales/sales_invoice_screen.py` | 895 | 0 | 70 | **70** |
| `frontend/ui/purchases/purchase_invoice_screen.py` | 897 | 0 | 66 | **66** |
| `frontend/ui/pos/pos_screen.py` | 897 | 0 | 65 | **65** |
| `frontend/utils/logger.py` | 1,157 | 0 | ~50 | ~50 |
| `frontend/ui/components/forms.py` | 863 | many | many | ~50 |
| `frontend/ui/components/tables.py` | 722 | many | many | ~45 |
| `backend/backup/backup_system.py` | 742 | 13 | 27 | **40** |
| `backend/core/api/v1/payment_operations.py` | 1,112 | many | many | ~40 |
| `backend/inventory/service/stock_integration.py` | 839 | 16 | 17 | **33** |

---

## 8. Instability Metric (Ce / (Ca + Ce))

Where Ce = efferent coupling (outbound), Ca = afferent coupling (inbound).

| File | Ca (in) | Ce (out) | Instability | Interpretation |
|------|---------|----------|-------------|----------------|
| `main_window.py` | 0 | 80 | **1.00** | Pure consumer (maximally unstable) |
| `pos_screen.py` | 0 | 65 | **1.00** | Pure consumer |
| `sales_invoice_screen.py` | 0 | 70 | **1.00** | Pure consumer |
| `purchase_invoice_screen.py` | 0 | 66 | **1.00** | Pure consumer |
| `payments/services.py` | 9 | 16 | **0.64** | Mostly consumer |
| `stock_integration.py` | 16 | 17 | **0.51** | Balanced |
| `backup_system.py` | 13 | 27 | **0.68** | Mostly consumer |
| `journal_engine` (protected) | 67 | low | low | **Mostly provider (stable)** |

**Interpretation:** The 4 frontend files are maximally unstable (instability = 1.0) — they depend on everything but nothing depends on them. This is good for refactoring their internals (no downstream consumers to break), but bad because any refactor must coordinate with 60-80 modules they import.

The 3 backend service files have instability 0.5-0.7 — they're more balanced. Refactoring them affects both their consumers (9-16 files) and their dependencies (16-27 modules).

---

## 9. Recommended Refactor Order (lowest risk first)

| Order | File | Why First |
|-------|------|-----------|
| **1** | `payments/services.py` | Lowest coupling (25), smallest public surface (6 methods), class-shell extraction matches Phase 6.2 pattern. 4 production callers manageable. |
| 2 | `inventory/service/stock_integration.py` | Medium coupling (33), 13 tests to update but 3 production callers only in `inventory/`. |
| 3 | `frontend/ui/sales/sales_invoice_screen.py` | Private method extraction only (`_setup_screen` 303→5 methods). No public API change. No cross-module coordination. |
| 4 | `frontend/ui/purchases/purchase_invoice_screen.py` | Same as #3. |
| 5 | `frontend/ui/pos/pos_screen.py` | Defer — POS-specific complexity. |
| 6 | `frontend/ui/main_window.py` | Defer — entry point, 80 imports. |
| — | `backup/backup_system.py` | DO NOT TOUCH (Phase 6.2 protected). |

---

## 10. Outputs

| File | Purpose |
|------|---------|
| `docs/PHASE6_3/evidence/audit_raw.json` | Full coupling metrics |
| `docs/PHASE6_3/evidence/inbound_callers.json` | Per-focus-file inbound caller lists |
| `docs/PHASE6_3/PHASE6_3_HUB_FILE_AUDIT.md` | Hub file audit (Section 6) |
| `docs/PHASE6_3/PHASE6_3_DEPENDENCY_GRAPH.md` | Dependency graph (Sections 3-6) |
