# LAYOUT & SPACE UTILIZATION REPORT — Pharmacy ERP

## Sidebar Layout

- **Fixed width**: 260px
- **Brand area**: 80px high, primary-color background
- **Scrollable area**: Entire sidebar scrollable
- **Bottom frame**: 60px with Logout button
- **Groups**: 12 collapsible groups, all collapsed by default
- **Items per group**: 1-12 items

### Space Analysis

| Group | Items | Expanded Height (approx) | Category |
|-------|-------|--------------------------|----------|
| Dashboard | 1 (always visible) | 40px | ✅ Good |
| Inventory | 4 | 220px | ✅ Good |
| Sales | 3 | 180px | ✅ Good |
| Purchases | 2 | 140px | ✅ Good |
| Returns | 2 | 140px | ✅ Good |
| Accounting | 5 | 260px | ✅ Good |
| Reports | 5 | 260px | ✅ Good |
| Finance | **12** | **580px** | ⚠️ **Overcrowded** |
| HR | 4 | 220px | ✅ Good |
| HR Reports | 4 | 220px | ✅ Good |
| Payroll Reports | 4 | 220px | ✅ Good |
| System | **13** | **620px** | ⚠️ **Overcrowded** |

**Finance group (12 items)** and **System group (13 items)** are overcrowded. Finance mixes transaction screens (Payments, Expenses), planning screens (Budgeting, Tax, Cost Centers, Cash Flow), and advanced operation screens (Customer Payments, Supplier Payments, Allocation Explorer, Returns Explainability, Journal Reversals, Operations Console). Users must scroll and visually scan through 12 entries.

**Recommendation**: Split Finance into subgroups:
- **Transactions**: Payments, Expenses, Customer Payments, Supplier Payments
- **Planning**: Budgeting, Tax, Cost Centers, Cash Flow
- **Advanced**: Allocation Explorer, Returns Explainability, Journal Reversals, Operations Console

---

## Dashboard Layout

- **Location**: `ui/dashboard.py`
- **State**: Direct QWidget inheritance (not BaseScreen)
- **Structure**: KPI cards in grid layout, potential charts
- **Issue**: Not using BaseScreen lifecycle — no loading/error states, no auto-refresh

---

## Dialog Sizing

| Dialog | Width | Height | Notes |
|--------|-------|--------|-------|
| EnterpriseDialog | DIALOG_WIDTH_PREFERRED (580) | **400px (hardcoded)** | Not responsive |
| ConfirmDialog | 580 | auto | ✅ Good |
| AccountFormDialog | DIALOG_WIDTH_PREFERRED | auto | ✅ Good |
| JournalEntryForm | DIALOG_WIDTH_WIDE (900) | auto | ✅ Good |
| ProductSelectionDialog | 800 | 600 | ✅ Good |

**Issue**: `EnterpriseDialog` hardcodes height to 400px at `dialogs.py:88`. For dynamic content, this should be auto-sized or use a height token.

---

## Component Spacing

| Token | Value | Usage |
|-------|-------|-------|
| SPACING_XS | 4px | Micro spacing |
| SPACING_SM | 8px | Tight spacing |
| SPACING_MD | 12px | Standard spacing |
| SPACING_LG | 16px | Section spacing |
| SPACING_XL | 20px | Panel spacing |
| SPACING_XXL | 24px | Large section spacing |

**Issue**: `notifications.py` uses hardcoded margins `(12, 8, 8, 8)` instead of spacing tokens. `dialogs.py` uses hardcoded heights `50px` and `60px`.

---

## Density Tiers

| Tier | Spacing | Row Height | Input Height | KPI Height | Margin |
|------|---------|------------|-------------|------------|--------|
| COMFORTABLE | 20px | 40px | 44px | 120px | 32px |
| STANDARD | 12px | 32px | 38px | 90px | 25px |
| COMPACT | 8px | 26px | 32px | 60px | 16px |

Density tiers are well-defined in `constants.py` but not consistently applied across screens. Screens that bypass BaseScreen (21 screens) don't use density-aware patterns.

---

## Table Layout

| Feature | Status |
|---------|--------|
| Column width management | ✅ Configurable via TableColumn.width |
| Sort indicators | ✅ Via sortable flag |
| Selection modes | ✅ Single/Multi/Extended/None |
| Pagination | ✅ Built into EnterpriseTable |
| Empty state | ⚠️ Parameter exists but never displayed |
| Loading state | ❌ Not built-in |

**Issue**: `EnterpriseTable` has `empty_state_text` parameter (line 253) but `_refresh_display()` never checks it. Empty tables show as blank white space.

---

## Screen Composition Analysis

### Good Layout Examples
- **ChartOfAccountsScreen**: Tree view + detail panel — good use of split layout
- **JournalEntryScreen**: Header form + line-item grid — standard ERP pattern
- **SalesInvoiceScreen**: Customer info + line items + totals — expected layout

### Layout Issues

| Issue | Locations | Severity |
|-------|-----------|----------|
| KPI cards not rendering accent colors | kpi_cards.py (token bug) | CRITICAL |
| Dialog header colors not rendering | dialogs.py (token bug) | HIGH |
| NavigationHeader completely unstyled | navigation_header.py (token bug) | HIGH |
| Notification badges not styled | notifications.py (token bug) | HIGH |
| Loading overlay label color broken | loading_spinner.py (token bug) | MEDIUM |
| Finance group has 12 items — excessive | sidebar.py | MEDIUM |
| System group has 13 items — excessive | sidebar.py | MEDIUM |

---

## Summary

| Aspect | Rating | Issues |
|--------|--------|--------|
| Sidebar organization | ⚠️ FAIR | Finance (12) and System (13) overcrowded |
| Dialog sizing | ⚠️ FAIR | Hardcoded heights, not responsive |
| Component spacing | ❌ POOR | Token bugs break all spacing |
| Table utilization | ✅ GOOD | Well-implemented but missing empty state |
| Density system | ✅ GOOD | Well-defined but not universally applied |
| Dashboard layout | ⚠️ FAIR | Not using BaseScreen, no lifecycle |
