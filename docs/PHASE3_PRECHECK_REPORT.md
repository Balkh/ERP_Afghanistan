# PHASE 3 — PRECHECK REPORT

**Project:** Pharmacy ERP — Frontend Debt Reduction Program
**Phase:** 3A (Dead Code) + 3B (StateHelper) + 3C (DataEntryGrid) + 3D (Utilities)
**Status:** APPROVED FOR EXECUTION
**Constraint:** Zero-redesign, surgical refactoring of existing approved architecture.

---

## 1. Files Affected

### Phase 3A — Dead Code Purge (4 candidates)

| File / Symbol | Action | Lines Removed | Lines Added | Files Touched |
|---|---|---|---|---|
| `frontend/ui/components/base_widgets.py` (244 lines, 4 classes) | DELETE | 244 | 0 | + 1 broken-test cleanup |
| `frontend/ui/licensing/dialogs.py` (126 lines, 12 functions) | DELETE | 126 | 0 | 0 |
| `frontend/ui/components/document_action_dialog.py` (132 lines, 1 class) | DELETE | 132 | 0 | 0 |
| `frontend/ui/observability/widgets.py` — `LoadingOverlay` shim (lines 289-306) | DELETE (18 lines) | 18 | 0 | 0 |

**Phase 3A total:** 520 lines deleted, 0 lines added, 4 files affected.

### Phase 3B — StateHelper Adoption (15 screens)

| Screen | File | Pattern | Local Lines Removed | Estimated |
|---|---|---|---|---|
| BudgetingScreen | `finance/budgeting_screen.py` | Pattern C (tabs) | 3 methods + 3 widgets | ~50 |
| CashflowScreen | `finance/cashflow_screen.py` | Pattern C (tabs) | 3 methods + 2 widgets | ~45 |
| CostCentersScreen | `finance/cost_centers_screen.py` | Pattern A (table) | 3 methods + 3 widgets | ~50 |
| ExpenseScreen | `finance/expense_screen.py` | Pattern A (table) | 3 methods + 3 widgets | ~50 |
| PaymentScreen | `finance/payment_screen.py` | Pattern A (table) | 3 methods + 2 widgets | ~45 |
| TaxScreen | `finance/tax_screen.py` | Pattern C (tabs) | 3 methods + 3 widgets | ~45 |
| CustomerPaymentWorkspace | `finance/customer_payment_workspace.py` | Pattern B (workspace) | 3 methods + widgets | ~50 |
| SupplierPaymentWorkspace | `finance/supplier_payment_workspace.py` | Pattern B (workspace) | 3 methods + widgets | ~50 |
| PaymentAllocationExplorer | `finance/payment_allocation_explorer.py` | Pattern B (workspace) | 3 methods + widgets | ~50 |
| JournalReversalExplorer | `finance/journal_reversal_explorer.py` | Pattern B (workspace) | 3 methods + widgets | ~50 |
| FinancialOperationsConsole | `finance/financial_operations_console.py` | Pattern B (workspace) | 3 methods + widgets | ~50 |
| ReturnsExplainability | `finance/returns_explainability.py` | Pattern B (workspace) | 3 methods + widgets | ~50 |
| ReconciliationScreen | `returns/reconciliation_screen.py` | Pattern D (inline) | inline toggles | ~30 |
| ChartOfAccountsScreen | `accounting/chart_of_accounts_screen.py` | Pattern D (inline) | inline toggles | ~30 |
| BackupScreen | `system/backup_screen.py` | Pattern E (status_label) | status messages | ~25 |

**Phase 3B total (estimated):** ~670 lines removed, ~480 lines added (StateHelper call sites +1 line each call).

### Phase 3C — DataEntryGrid Adoption (3-5 line-item tables)

| Screen | File | Complexity | Decision |
|---|---|---|---|
| Returns (`ReturnOrderDialog`) | `returns/returns_screen.py` | LOW | **MIGRATE** — text-only cells, 1 editable col |
| Purchase Invoice | `purchases/purchase_invoice_screen.py` | MEDIUM | **MIGRATE** — text-only, standard add/remove |
| Mixed Payment Builder | `finance/mixed_payment_builder.py` | HIGH | **MIGRATE** — pure widget-grid, fix closure bug |
| Journal Entry Form | `accounting/components/journal_entry_form.py` | HIGH | **MIGRATE** — pure widget-grid, fix `indexAt` bug |
| Sales Invoice | `sales/sales_invoice_screen.py` | HIGH | **DEFER** — too many POS-style specific features (cell widget, hidden col, smart-add) |
| POS Cart | `pos/pos_screen.py` | HIGH | **DEFER** — too many POS-specific features (hold/recall, prescription flags) |

**Phase 3C decision:** Migrate the 4 lower-complexity candidates that fit DataEntryGrid's text-only model with widget-cell support. Defer Sales Invoice and POS Cart to a future wave (out of scope).

**Phase 3C scope expansion — DataEntryGrid widget-cell API (mandatory prerequisite):**
- Add `set_cell_widget(row, col, widget) -> None`
- Add `cell_widget(row, col) -> QWidget`
- Add `cell_value_changed = Signal(int, int, object)` for per-cell value updates
- Add `set_row_data(row, dict)`, `get_row_data(row) -> dict` for rich row state
- Add `row_added = Signal(int)`, `row_removed = Signal(int)` for parent reactions

**Phase 3C total (estimated):** ~600 lines removed, ~580 lines added (DataEntryGrid instantiation + helper methods).

### Phase 3D — Duplicate Utility Extraction (3 helpers, 17 definitions)

| Helper | Definitions | Call Sites | New Shared Location | Status |
|---|---|---|---|---|
| `_safe_float` | 9 | 38 | NEW: `frontend/utils/format.py::safe_float()` | SAFE — byte-for-byte identical |
| `_parse_response` | 4 | 4 | REUSE: `frontend/api/endpoints.py::extract_list` (with `isinstance(x, dict)` filter added) | SAFE — already canonical exists |
| `_combo_style` | 4 | 6 | NEW: `frontend/ui/components/styles.py::combo_stylesheet()` | SAFE — fix latent `f`-prefix bug in `payment_allocation_explorer` |

**Phase 3D total (estimated):** ~120 lines removed, ~50 lines added (2 new files: `utils/format.py` + `ui/components/styles.py`, 1 small extension to `extract_list`).

---

## 2. Estimated Risk

| Phase | Risk | Justification |
|---|---|---|
| 3A | **LOW** | All 4 candidates verified at 0 production callers + 0 external subclasses. The only "external" references are: 1 script skip-list, 1 broken test (symbols don't exist), 1 historical doc, 0 callers of `LoadingOverlay` shim. Deletion has no runtime path impact. |
| 3B | **LOW-MEDIUM** | StateHelper is read-only (only mutates a supplied layout). All 15 candidate screens have local state patterns that match StateHelper's contract (loading/empty/error). Risk is visual: StateHelper uses `COLOR_BG_SURFACE` (themed) — local labels currently use whatever `setStyleSheet` they had. We must preserve current visual by passing equivalent `message` strings. |
| 3C | **MEDIUM** | DataEntryGrid is text-only today. We must add widget-cell support BEFORE migration of mixed_payment_builder / journal_entry_form. Two latent bugs in the original code (closure-capture in `mixed_payment_builder._remove_split_row`, sender/indexAt in `journal_entry_form._remove_line_at`) MUST be fixed during migration. |
| 3D | **LOW** | All `_safe_float` definitions are byte-for-byte identical. `extract_list` is already in use by 12 files. `_combo_style` consolidation silently fixes an `f`-prefix bug in `payment_allocation_explorer`. No semantic change for any caller. |

---

## 3. Dependency Impact

| Phase | New Imports Added | Imports Removed |
|---|---|---|
| 3A | none | `from ui.components.base_widgets import ...` (broken test); `from ui.licensing.dialogs import ...` (none) |
| 3B | `from ui.components.state_helper import StateHelper` (15 sites) | none |
| 3C | `from ui.components.tables import DataEntryGrid` (4 sites) | none (QTableWidget instantiations replaced) |
| 3D | `from utils.format import safe_float` (9 sites), `from ui.components.styles import combo_stylesheet` (4 sites), `from api.endpoints import extract_list` (4 sites) | none |

**No new module-level dependencies on PySide6** beyond what the screens already use.
**No backend, API, schema, or test changes.**

---

## 4. Runtime Impact

| Phase | Performance | Memory | UI Threading |
|---|---|---|---|
| 3A | NEGATIVE — fewer imports at startup | NEGATIVE — ~520 lines of bytecode not loaded | none |
| 3B | NEUTRAL — same number of widgets created on demand | NEUTRAL — same | NEUTRAL — StateHelper is synchronous (no I/O) |
| 3C | NEUTRAL — same widget count, more API surface | NEUTRAL | NEUTRAL — DataEntryGrid is synchronous |
| 3D | POSITIVE — 1 fewer call to `ui.components.*` for `_combo_style` (now free function), `extract_list` already used widely | NEUTRAL | NEUTRAL |

**Total expected startup speedup:** negligible (~520 lines bytecode removed + ~190 lines consolidated).

---

## 5. UI Impact

| Phase | Visual | Functional | Behavioral |
|---|---|---|---|
| 3A | none | none | none — code paths removed have no callers |
| 3B | POTENTIALLY POSITIVE — StateHelper provides standardized `COLOR_BG_SURFACE` containers with `BORDER_RADIUS_LG` borders and themed indicator bars. Local labels were flat `QLabel`s with no container framing. | NONE — same content (loading/empty/error messages) | NONE — same call signatures |
| 3C | POSITIVE for Returns + Purchase — DataEntryGrid applies canonical `UIStyleBuilder.get_table_style()`. The current screens use their own inline table styles (tokenized but slightly different). | NONE — same row operations | NONE — same add/remove logic |
| 3D | POSITIVE for `payment_allocation_explorer` — its dropdowns currently render unstyled (missing `f`-prefix bug). After consolidation they get the canonical themed style. | NONE | NONE — slight delta: mixed_payment_builder dropdowns gain 2px height (28→30px) and primary selection background. |

**No layout, no workflow, no business logic, no user-visible workflow change.**

---

## 6. Rollback Strategy

| Phase | Rollback |
|---|---|
| 3A | `git checkout frontend/ui/components/base_widgets.py frontend/ui/licensing/dialogs.py frontend/ui/components/document_action_dialog.py` and remove the 18-line shim from `frontend/ui/observability/widgets.py`. |
| 3B | `git checkout frontend/ui/finance/*.py frontend/ui/returns/reconciliation_screen.py frontend/ui/accounting/chart_of_accounts_screen.py frontend/ui/system/backup_screen.py`. All changes are local to `_show_*` methods — restoring them restores the original behavior. |
| 3C | `git checkout frontend/ui/components/tables.py frontend/ui/returns/returns_screen.py frontend/ui/purchases/purchase_invoice_screen.py frontend/ui/finance/mixed_payment_builder.py frontend/ui/accounting/components/journal_entry_form.py`. The widget-cell API additions to DataEntryGrid are additive — they don't break any existing call site that doesn't use them. |
| 3D | `git checkout frontend/utils/format.py frontend/ui/components/styles.py frontend/api/endpoints.py` and all 17 files that import the new helpers. The new files are isolated modules — removing them has no cascade. |

**Single-commit rollback is possible per phase. No cross-phase coupling.**

---

## 7. Success Criteria

- **3A**: 520 lines removed, 0 callers broken, 0 test failures, 0 import errors.
- **3B**: 15 screens migrated, ~670 lines of duplicate logic eliminated, 0 visual regressions, 0 workflow changes.
- **3C**: 4 line-item tables migrated, widget-cell API added, 2 latent bugs fixed, 0 functional regressions.
- **3D**: 3 helpers consolidated, 1 latent `f`-prefix bug fixed, 1 latent pagination bug fixed, 48 call sites updated, 0 behavioral changes for any caller.
- **Global**: 0 new architecture, 0 new components, 0 new patterns, 0 new design tokens, 0 backend changes, 0 API changes, 0 test changes, 0 business behavior changes.

---

## 8. Execution Order

1. **Phase 3A** — Delete 4 dead code candidates, fix broken test import.
2. **Phase 3B** — Migrate 15 screens to StateHelper.
3. **Phase 3C** — Add DataEntryGrid widget-cell API, then migrate 4 line-item tables.
4. **Phase 3D** — Extract 3 utility duplicates.

---

**APPROVAL:** This precheck reflects the constraints of "Surgical Refactoring Directive (Zero-Rewrite Edition)". No new components, no new tokens, no new architecture. Existing approved components are being adopted; dead code is being removed; exact-duplicate utilities are being consolidated.

Proceed to execution.
