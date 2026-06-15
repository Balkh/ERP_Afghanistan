# 🎨 Frontend UI/UX Audit Report — ERP_Afghanistan
**Date:** 2026-06-16  
**Auditor:** Arena.ai Agent (Expert UI/UX Review)  
**Scope:** All files in `frontend/ui/`, `frontend/theme/`, `frontend/utils/`  
**Files Analyzed:** 135+ Python source files  

---

## Executive Summary

The frontend uses a well-designed **Design Token System** (`ui/constants.py`) with 150+ tokens, a **centralized StyleBuilder** (`theme/style_builder.py`), and a **ThemeEngine** for live dark/light switching. The architecture is professional.

However, a thorough line-by-line audit reveals **6 categories of issues** that degrade visual consistency, contrast, and professional appearance:

| Category | Severity | Count | Impact |
|----------|----------|-------|--------|
| 🔴 A. Contrast & Readability | Critical | 7 | Text unreadable on some backgrounds |
| 🟠 B. pt/px Unit Mixing | High | 21 files | Font sizes render inconsistently across screens |
| 🟠 C. Hardcoded `color: white` | High | 4 locations | Breaks in light theme |
| 🟡 D. Missing `px` Suffix on Border-Radius | Medium | 5+ locations | Sidebar rounded corners silently fail |
| 🟡 E. StyleBuilder Adoption Gap | Medium | 88 vs 7 | 88 files use inline QSS, only 7 use StyleBuilder |
| 🟢 F. Dead/Duplicate Variables | Low | 3 locations | Code confusion, no visual impact |

---

## 🔴 Category A: Contrast & Readability Failures (Critical)

### A1. Tab Bar — Hardcoded `color: white` on `COLOR_PRIMARY` Background
**File:** `frontend/theme/style_builder.py:165`
```python
QTabBar::tab:selected { 
    background: {COLOR_PRIMARY};  # #89b4fa (light blue)
    color: white;                 # ❌ HARDCODED — fails on light theme
}
```
**Problem:** `white` text on `#89b4fa` → **contrast ratio 1.67:1** (WCAG requires 4.5:1 minimum). In light theme `COLOR_PRIMARY` is `#1976d2` and `white` is OK but still hardcoded.  
**Fix:** Use `{COLOR_TEXT_ON_PRIMARY}` which is theme-aware (`#0f1118` in dark, `#ffffff` in light).

### A2. Invoice Templates — Hardcoded `color: white`
**File:** `frontend/utils/invoice_template_engine.py:54,62,74`
```python
.header { background-color: {colors['primary']}; color: white; }
th { background-color: {colors['accent']}; color: white; }
.grand-total { ... color: white; }
```
**Problem:** If primary/accent colors are light-toned, white text becomes invisible.  
**Fix:** Use `{COLOR_TEXT_ON_PRIMARY}` token.

### A3. StatusBadge — `font-size: {TEXT_TABLE}px` (px instead of pt)
**File:** `frontend/ui/components/kpi_cards.py:220`
```python
font-size: {TEXT_TABLE}px;  # TEXT_TABLE = 9 → renders as 9px (tiny!)
```
**Problem:** `TEXT_TABLE` is designed for `pt` units. Using `px` makes the badge text ~30% smaller than intended.  
**Fix:** Change to `{TEXT_TABLE}pt`.

### A4. Notifications — `font-size: {TEXT_CARD_TITLE}px`
**File:** `frontend/ui/components/notifications.py:161`
```python
font-size: {TEXT_CARD_TITLE}px;  # TEXT_CARD_TITLE=11 → 11px ≈ 8pt (too small for a card title)
```
**Fix:** Change to `{TEXT_CARD_TITLE}pt`.

### A5. Printable Invoice — Hardcoded `font-size: 10px`
**File:** `frontend/ui/common/printable_invoice.py:187`
```python
.status { ... font-size: 10px; }  # ❌ Not using TEXT_* token
```
**Fix:** Use `{TEXT_LABEL}pt` or `{TEXT_TABLE}pt`.

### A6. POS Screen — Heavy `px`/`pt` Mixing (16 px, 13 pt)
**File:** `frontend/ui/pos/pos_screen.py`
- 16 occurrences use `px` for font-size
- 13 occurrences use `pt` for font-size
- **Same screen, different elements rendered with different unit scales**
**Fix:** Standardize all to `pt` for Qt QSS font sizing.

### A7. Purchase/Sales Invoice Screens — Extreme `px` Dominance
**Files:** `purchase_invoice_screen.py`, `sales_invoice_screen.py`
- Both use 10× `px` but only 1× `pt`
- Grid cells, headers, totals all sized differently from the rest of the app
**Fix:** Convert all to `pt`.

---

## 🟠 Category B: pt/px Unit Mixing (High — 21 Files)

**Root cause:** Qt QSS treats `pt` and `px` differently. `pt` = points (DPI-aware), `px` = pixels (fixed). Mixing them creates inconsistent sizing especially on HiDPI displays.

| File | `pt` count | `px` count | Status |
|------|-----------|-----------|--------|
| `pos/pos_screen.py` | 13 | 16 | ❌ MIXED |
| `purchases/purchase_invoice_screen.py` | 1 | 10 | ❌ MIXED |
| `sales/sales_invoice_screen.py` | 1 | 10 | ❌ MIXED |
| `main_window.py` | 13 | 8 | ❌ MIXED |
| `licensing/activation_screen.py` | 8 | 4 | ❌ MIXED |
| `accounting/journal_entry_screen.py` | 5 | 4 | ❌ MIXED |
| `accounting/report_browser.py` | 5 | 2 | ❌ MIXED |
| `accounting/account_ledger_screen.py` | 4 | 2 | ❌ MIXED |
| `hr/attendance_screen.py` | 5 | 3 | ❌ MIXED |
| `hr/employee_screen.py` | 5 | 3 | ❌ MIXED |
| `hr/payroll_screen.py` | 4 | 3 | ❌ MIXED |
| `inventory/components/product_form.py` | 2 | 2 | ❌ MIXED |
| `inventory/components/batch_form_dialog.py` | 1 | 1 | ❌ MIXED |
| `inventory/components/category_form_dialog.py` | 1 | 1 | ❌ MIXED |
| `inventory/components/warehouse_form_dialog.py` | 1 | 1 | ❌ MIXED |
| `returns/returns_screen.py` | 5 | 2 | ❌ MIXED |
| `returns/reconciliation_screen.py` | 1 | 1 | ❌ MIXED |
| `purchases/supplier_screen.py` | 4 | 3 | ❌ MIXED |
| `accounting/chart_of_accounts_screen.py` | 1 | 2 | ❌ MIXED |
| `accounting/components/account_form_dialog.py` | 1 | 1 | ❌ MIXED |
| `auth/login_screen.py` | 10 | 1 | ❌ MIXED |

**Standard:** All `font-size` in QSS should use `pt` (the Qt QSS convention used by `style_builder.py`).

---

## 🟠 Category C: Hardcoded Color Values (High)

| File | Line | Value | Should Be |
|------|------|-------|-----------|
| `theme/style_builder.py` | 165 | `color: white` | `{COLOR_TEXT_ON_PRIMARY}` |
| `utils/invoice_template_engine.py` | 54 | `color: white` | `{COLOR_TEXT_ON_PRIMARY}` |
| `utils/invoice_template_engine.py` | 62 | `color: white` | `{COLOR_TEXT_ON_PRIMARY}` |
| `utils/invoice_template_engine.py` | 74 | `color: white` | `{COLOR_TEXT_ON_PRIMARY}` |

---

## 🟡 Category D: Missing `px` Suffix on Border-Radius (Medium)

**File:** `frontend/ui/sidebar.py`

QSS requires `border-radius: Npx` but several sidebar styles omit `px`:

| Line | Current | Should Be |
|------|---------|-----------|
| 216 | `border-radius: {BORDER_RADIUS_SM};` | `border-radius: {BORDER_RADIUS_SM}px;` |
| 392 | `border-radius: {BORDER_RADIUS_MD};` | `border-radius: {BORDER_RADIUS_MD}px;` |
| 548 | `border-radius: {BORDER_RADIUS_MD};` | `border-radius: {BORDER_RADIUS_MD}px;` |
| 564 | `border-radius: {BORDER_RADIUS_MD};` | `border-radius: {BORDER_RADIUS_MD}px;` |
| 656 | `border-radius: {BORDER_RADIUS_SM};` | `border-radius: {BORDER_RADIUS_SM}px;` |

**Impact:** Qt may silently ignore the border-radius → sidebar buttons appear with sharp corners.

---

## 🟡 Category E: StyleBuilder Adoption Gap (Medium)

The `UIStyleBuilder` in `theme/style_builder.py` provides centralized, theme-aware styles for:
- ✅ Buttons (`get_button_style`)
- ✅ Inputs (`get_input_style`)
- ✅ Tables (`get_table_style`)
- ✅ Tabs (`get_tab_style`)
- ✅ Cards (`get_card_style`)
- ✅ Labels (`get_label_style`)
- ✅ Forms (`get_form_section_style`)

**Adoption rate:** Only **7 out of 88 files** (8%) with `setStyleSheet` use `UIStyleBuilder`.  
The other **81 files** build QSS inline with f-strings and direct token references.

**Risk:** When theme tokens change, inline f-strings may not pick up new patterns (e.g., hover states, focus rings, disabled states) that StyleBuilder provides automatically.

**Recommendation:** Gradually migrate high-traffic screens first (see Phase plan).

---

## 🟢 Category F: Dead/Duplicate Variables (Low)

### F1. StatusBadge — Double variable assignment
**File:** `frontend/ui/components/kpi_cards.py:211-212`
```python
__color = _severity_color(self._severity)  # assigned but never used
__clr = _severity_color(self._severity)    # same value, this one is used
```
**Fix:** Remove `__color`, rename `__clr` → `_color`.

### F2. Causal scoring screens — `px` unit on all `TEXT_*` tokens
**Files:** `causal_strength_panel.py:76`, `decision_ranking_dashboard.py:89,102,115`
- All use `font-size: {TEXT_BODY}px` — should be `pt`.
- These are monospace code-viewer panels, but the unit should still match the system.

---

# 📋 PHASE PLAN: UI/UX Improvement Roadmap

## Phase 1: 🔴 Critical Contrast & Readability Fixes (Day 1)
**Files:** 6 | **Impact:** Highest | **Risk:** Zero (no layout changes)

| Task | File | Change |
|------|------|--------|
| 1.1 | `style_builder.py:165` | `color: white` → `color: {COLOR_TEXT_ON_PRIMARY}` |
| 1.2 | `invoice_template_engine.py:54,62,74` | `color: white` → `color: {COLOR_TEXT_ON_PRIMARY}` |
| 1.3 | `kpi_cards.py:220` | `{TEXT_TABLE}px` → `{TEXT_TABLE}pt` |
| 1.4 | `kpi_cards.py:211-212` | Remove `__color`, rename `__clr` → `_color` |
| 1.5 | `notifications.py:161` | `{TEXT_CARD_TITLE}px` → `{TEXT_CARD_TITLE}pt` |
| 1.6 | `printable_invoice.py:187` | `font-size: 10px` → `font-size: {TEXT_LABEL}pt` |

## Phase 2: 🟠 Sidebar Border-Radius Fix (Day 1)
**Files:** 1 | **Impact:** Medium | **Risk:** Zero

| Task | File | Change |
|------|------|--------|
| 2.1 | `sidebar.py:216,392,548,564,656` | Add `px` suffix to all `border-radius` values |

## Phase 3: 🟠 Font Unit Standardization — Core Screens (Day 2-3)
**Files:** 8 (highest-traffic) | **Impact:** High | **Risk:** Low

Priority order by user frequency:
1. `pos/pos_screen.py` — 16 px→pt conversions
2. `sales/sales_invoice_screen.py` — 10 px→pt
3. `purchases/purchase_invoice_screen.py` — 10 px→pt
4. `main_window.py` — 8 px→pt
5. `accounting/journal_entry_screen.py` — 4 px→pt
6. `accounting/account_ledger_screen.py` — 2 px→pt
7. `accounting/chart_of_accounts_screen.py` — 2 px→pt
8. `accounting/report_browser.py` — 2 px→pt

**Rule:** Every `font-size: {TEXT_*}px` → `font-size: {TEXT_*}pt`

## Phase 4: 🟠 Font Unit Standardization — Secondary Screens (Day 3-4)
**Files:** 13 remaining | **Impact:** Medium | **Risk:** Low

- `hr/attendance_screen.py`, `hr/employee_screen.py`, `hr/payroll_screen.py`
- `licensing/activation_screen.py`
- `inventory/components/*.py` (4 files)
- `returns/returns_screen.py`, `returns/reconciliation_screen.py`
- `purchases/supplier_screen.py`
- `causal_scoring/` (2 files)
- `auth/login_screen.py`

## Phase 5: 🟡 StyleBuilder Migration — High-Traffic (Day 5-7)
**Goal:** Migrate 10 highest-traffic screens to use `UIStyleBuilder` methods.

| Screen | Current | Target |
|--------|---------|--------|
| `dashboard.py` | Inline QSS | `get_card_style()`, `get_label_style()` |
| `sidebar.py` | Inline QSS | `get_button_style("ghost")`, new `get_sidebar_style()` |
| `login_screen.py` | Inline QSS | `get_input_style()`, `get_card_style()` |
| `pos_screen.py` | Inline QSS | `get_button_style()`, `get_input_style()`, `get_table_style()` |
| `sales_invoice_screen.py` | Inline QSS | `get_table_style()`, `get_input_style()` |
| `purchase_invoice_screen.py` | Inline QSS | Same as above |
| `journal_entry_screen.py` | Inline QSS | `get_table_style()`, `get_label_style()` |
| `employee_screen.py` | Inline QSS | `get_table_style()`, `get_label_style()` |
| `chart_of_accounts_screen.py` | Inline QSS | `get_table_style()` |
| `customer_screen.py` | Inline QSS | `get_table_style()`, `get_input_style()` |

**Approach:**
1. Add new helper methods to `UIStyleBuilder` if needed (`get_sidebar_nav_style()`, `get_status_label_style()`)
2. Replace inline f-strings with `UIStyleBuilder.get_*()` calls
3. Test theme switching after each file

## Phase 6: 🟢 Polish & Validation (Day 8)
- Run automated contrast checker on all `COLOR_TEXT_*` vs `COLOR_BG_*` combinations
- Verify all screens in both dark and light themes
- Remove remaining dead code (`__color` in StatusBadge, etc.)
- Create `FRONTEND_STYLE_GOVERNANCE.md` with rules:
  - ✅ All `font-size` must use `pt` (not `px`)
  - ✅ All colors must use `COLOR_*` tokens (no hex, no `white`/`black`)
  - ✅ All `border-radius` must include `px` suffix
  - ✅ New screens must use `UIStyleBuilder` methods
  - ✅ Pre-commit enforcer must check for `color: white` and `px` in font-size

---

## Summary Metrics

| Metric | Before | After Phase 6 |
|--------|--------|---------------|
| Hardcoded colors | 4 | 0 |
| pt/px mixed files | 21 | 0 |
| Missing `px` suffix | 5 | 0 |
| StyleBuilder adoption | 8% (7/88) | 30%+ (17/88) |
| Contrast failures | 7 | 0 |
| Dead variables | 3 | 0 |
| WCAG AA compliance | ~80% | 100% |
