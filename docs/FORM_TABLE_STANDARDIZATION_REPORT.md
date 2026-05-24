# Table & Form Standardization Report — Phase UX.2 Layer 4

**Generated:** 2026-05-24

---

## Table Standardization

| Metric | Status |
|---|---|
| `EnterpriseTable` used in active screens | **38 import sites** — primary table component |
| `build_table_stylesheet()` direct calls (legacy bypass) | **0** — all redirected to `UIStyleBuilder.get_table_style()` |
| `EnterpriseTable` style source | `UIStyleBuilder.get_table_style()` — single canonical QSS |
| `DataEntryGrid` style source | `UIStyleBuilder.get_table_style()` — now consistent with EnterpriseTable |
| Raw `QTableWidget` in legacy screens | 15 orphaned screens archived (Layer 1 cleanup) |
| Pagination | `PaginationWidget` with `EnterpriseButton` nav buttons |

## Form Standardization

| Metric | Status |
|---|---|
| `EnterpriseForm` / `FormSection` used | Available in `ui/components/forms.py` |
| Screen-level BaseScreen/BaseFormScreen usage | 23 of ~55 screens use BaseScreen — 32 use raw QWidget |
| Filter bars | **No standardized component** — 12+ inline implementations |
| Tab order | Set by each screen individually — no automated audit |
| Save/cancel patterns | Inconsistent across screens — some use inline buttons, others EnterpriseButton |

## Recommendations for Phase UX.3

1. **Create FilterBar component** — Consolidate 12+ inline filter bar implementations into a single reusable `FilterBar` or `SearchBar` component
2. **BaseFormScreen migration** — Convert remaining 32 raw QWidget screens to BaseScreen/BaseFormScreen
3. **Form Save/Canel pattern** — Define canonical save/cancel button pattern using EnterpriseButton
