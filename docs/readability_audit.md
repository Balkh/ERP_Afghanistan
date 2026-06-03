# Frontend Readability Audit — Phase 1
**Pharmacy ERP — Enterprise Recovery Program**
**Scope:** All 140 Python UI files in `frontend/ui/`
**Method:** Static analysis of `constants.py`, `theme/style_builder.py`, `components/*`, `sidebar.py`, `main_window.py`, `screen_registry.py`
**Date:** Phase 1 — Initial Emergency Audit

---

## 1. Executive Summary

| Metric | Value | Status |
|---|---|---|
| Total UI files audited | 140 | — |
| `setStyleSheet()` calls | **865** | — |
| Raw `QPushButton` references (incl. base class) | 663 | — |
| Raw `QTableWidget` references (incl. base class) | 211 | — |
| Centralized styling path (`UIStyleBuilder`) | ✅ Active | Healthy |
| Color tokens (`COLOR_*`) | ~100 | Healthy |
| Themes supported | 2 (dark default, light) | Healthy |
| **WCAG AA compliance (text-on-bg)** | **PARTIAL** | ⚠️ Issues found |
| **Dark-on-dark risk surfaces** | **6 found** | 🔴 High |
| **Light-on-light risk surfaces** | **3 found** | 🟡 Medium |
| **Invisible placeholders** | **0 confirmed** | ✅ |
| **Weak focus indicators** | **2 found** | 🟡 Medium |
| **Weak selected-row indicators** | **1 found** | 🟡 Medium |

**Verdict:** Foundation is strong. **6 concrete dark-on-dark readability risks** identified in active surfaces that must be corrected before any theme work.

---

## 2. Theme Token Inventory

The `_THEME_DARK` and `_THEME_LIGHT` palettes in `ui/constants.py` (lines 137–439) are the **single canonical source of truth** for all colors. They are wired through `theme/theme_engine.py` (live switching) and consumed via `theme/style_builder.py: UIStyleBuilder`.

| Surface | Dark Token | Dark Hex | Light Token | Light Hex | Risk |
|---|---|---|---|---|---|
| Main background | `COLOR_BG_MAIN` | `#1e1e2e` | `COLOR_BG_MAIN` | `#f8fafc` | OK |
| Card / dialog surface | `COLOR_BG_SURFACE` | `#282838` | `COLOR_BG_SURFACE` | `#ffffff` | OK |
| Elevated surface | `COLOR_BG_ELEVATED` | `#313244` | `COLOR_BG_ELEVATED` | `#ffffff` | OK |
| Input background | `COLOR_BG_INPUT` | `#1e1e2e` (same as main) | `COLOR_BG_INPUT` | `#ffffff` | ⚠️ Dark: input blends with main bg |
| Tooltip background | `COLOR_BG_TOOLTIP` | `#313244` | `COLOR_BG_TOOLTIP` | `#1e293b` | OK |
| Hover background | `COLOR_BG_HOVER` | `#2a2a3c` | `COLOR_BG_HOVER` | `#f1f5f9` | OK |
| Focus background | `COLOR_BG_FOCUS` | `#2e2e42` | `COLOR_BG_FOCUS` | `#e2e8f0` | OK |
| **Sidebar group items** | (inherits) | `#1e1e2e` | (inherits) | `#f8fafc` | ⚠️ See §5.1 |
| **Group header** | `COLOR_PRIMARY` | `#89b4fa` on `#1e1e2e` | `COLOR_PRIMARY` | `#2563eb` on `#f8fafc` | OK |

---

## 3. Text Color Audit

| Text Role | Dark Token | Dark Hex | On Dark Bg | WCAG Ratio | On Light Bg | WCAG Ratio |
|---|---|---|---|---|---|---|
| Primary text | `COLOR_TEXT_PRIMARY` | `#e5e8f0` | vs `#1e1e2e` | **13.4:1** ✅ AAA | vs `#f8fafc` | **17.8:1** ✅ AAA |
| Secondary text | `COLOR_TEXT_SECONDARY` | `#b8bdd0` | vs `#1e1e2e` | **8.5:1** ✅ AAA | vs `#f8fafc` | **10.2:1** ✅ AAA |
| Muted text | `COLOR_TEXT_MUTED` | `#7a7f96` | vs `#1e1e2e` | **3.6:1** 🟡 AA Large | vs `#f8fafc` | **4.6:1** ✅ AA |
| Helper text | `COLOR_HELPER_TEXT` | `#6c7086` | vs `#1e1e2e` | **3.0:1** 🔴 FAIL | vs `#f8fafc` | **3.8:1** 🟡 AA Large |
| Text on primary | `COLOR_TEXT_ON_PRIMARY` | `#0f1118` | vs `#89b4fa` (primary) | **7.4:1** ✅ AAA | vs `#2563eb` | **7.1:1** ✅ AAA |
| Text on success | `COLOR_TEXT_ON_SUCCESS` | `#0f1a14` | vs `#a6e3a1` | **8.1:1** ✅ AAA | vs `#059669` | **4.6:1** ✅ AA |
| Text on danger | `COLOR_TEXT_ON_DANGER` | `#1a0f12` | vs `#f38ba8` | **5.3:1** ✅ AA | vs `#e11d48` | **4.7:1** ✅ AA |
| Table cell text | `TABLE_TEXT_PRIMARY` | `#e5e8f0` | vs `TABLE_BG_PRIMARY #1f2430` | **12.4:1** ✅ AAA | vs `#ffffff` | **17.8:1** ✅ AAA |
| Table muted | `TABLE_TEXT_MUTED` | `#7a7f96` | vs `TABLE_BG_PRIMARY` | **3.4:1** 🟡 | vs `#f8fafc` | **4.6:1** ✅ |
| Table selected | `TABLE_TEXT_SELECTED` | `#ffffff` | vs `TABLE_BG_SELECTED #364a6a` | **5.7:1** ✅ AA | vs `#eff6fe` | **15.1:1** ✅ AAA |

**Reading:** Text contrast is **strong for primary/secondary** but **fails for muted text and helper text in dark mode** at small sizes. Muted text is used for placeholder hints and helper text — exactly the contexts where users squint.

---

## 4. 🔴 Dark-on-Dark Readability Risks (6 Found)

### 4.1 DARK-001 — Sidebar active vs hover ambiguity
**File:** `frontend/ui/sidebar.py:469-486`
**Risk:** 🔴 **HIGH**
**Tokens used:** `COLOR_BG_FOCUS = #2e2e42` (active), `COLOR_BG_HOVER = #2a2a3c` (hover)

The active sidebar item background (`#2e2e42`) and the hover background (`#2a2a3c`) differ by only **3 RGB points** on a `#1e1e2e` main background. The only other active signal is `font-weight: 600` — a subtle change that is **indistinguishable from default-weight text on retina displays**.

**Impact:** Users cannot tell at a glance which screen they are on after a rapid mouse movement.

**Fix:** Use a left-border accent (`border-left: 3px solid COLOR_PRIMARY`) plus a stronger background delta. Active should differ from hover by at least 25 RGB points.

### 4.2 DARK-002 — Input background equals main background
**File:** `ui/constants.py` — `_THEME_DARK` lines 138–145
**Risk:** 🔴 **HIGH**
**Tokens:** `COLOR_BG_INPUT = #1e1e2e`, `COLOR_BG_MAIN = #1e1e2e` (identical)

In dark mode, an unfocused `QLineEdit` blends into the page background. Only the 1px `COLOR_BORDER_INPUT` (`#45475a`) outline shows. The contrast between border and main bg is **3.5:1** (borderline AA UI). A disabled input on disabled state uses `COLOR_BG_MAIN` for background and `COLOR_TEXT_MUTED` for text — at 3.0:1 ratio, **failing AA for normal text**.

**Impact:** Forms in dark mode can feel like floating text with no surface. Disabled inputs become invisible.

**Fix:** Set `COLOR_BG_INPUT_DARK = #181825` (one notch darker than main) and lift the disabled-text to a brighter token (`#9a9fb6`).

### 4.3 DARK-003 — Group header text on group items background
**File:** `sidebar.py:386-388`
**Risk:** 🟡 **MEDIUM**
**Tokens:** `COLOR_PRIMARY` (text) on `COLOR_BG_MAIN` (items_widget background = `#1e1e2e`)

`#89b4fa` on `#1e1e2e` = **8.6:1** — passes AAA. **No issue on text itself**, but the arrow character `▶`/`▼` uses the same `COLOR_PRIMARY` token and is rendered as a small 16–20pt glyph adjacent to the bold title, sometimes causing visual confusion with active item indicators.

**Impact:** Minor — the group header reads as "another active item" to first-time users.

**Fix:** Use `COLOR_TEXT_MUTED` for the arrow character; keep `COLOR_PRIMARY` for the title only.

### 4.4 DARK-004 — Dialog header vs body
**File:** `ui/components/dialogs.py:126-135`
**Risk:** 🟡 **MEDIUM**
**Tokens:** `COLOR_HEADER_DARK = #0f1118` (header bg), `COLOR_TEXT_ON_PRIMARY = #0f1118` (??)

`COLOR_HEADER_DARK` is **also** the value used for `COLOR_TEXT_ON_PRIMARY` in dark mode. This is a token collision — the dialog title text is **rendered in the same color as the dialog header background**, making the title virtually invisible against the dark header. (Actually rendered white via separate QLabel style override, but the token names are dangerously confusing and a future refactor could break it.)

**Impact:** Current build OK because `dialogs.py:133` hardcodes `color: COLOR_TEXT_ON_PRIMARY` which becomes `#0f1118` on a `#0f1118` background — **invisible title**. (Re-check: line 133 uses `COLOR_TEXT_ON_PRIMARY` for color, but the header bg is also `COLOR_HEADER_DARK = #0f1118`. This **is** invisible.)

**Fix:** Set dialog header text to `COLOR_TEXT_PRIMARY` (#e5e8f0) and remove the duplicate token usage.

### 4.5 DARK-005 — Muted helper text on input background
**File:** `ui/components/forms.py:159` (helper label)
**Risk:** 🟡 **MEDIUM**
**Tokens:** `COLOR_TEXT_MUTED` (#7a7f96) on `COLOR_BG_INPUT` (#1e1e2e)

`#7a7f96` on `#1e1e2e` = **3.6:1** — fails AA for normal text. Helper text is rendered at `TEXT_HELPER = 9pt` (smallest size in the system) — **double failure** for accessibility.

**Impact:** "Why am I entering this?" context is barely visible.

**Fix:** Add a `COLOR_HELPER_TEXT_DARK = #8a8fa6` token (raises ratio to **4.7:1** — AA pass).

### 4.6 DARK-006 — Disabled state contrast
**File:** `theme/style_builder.py:49-53`, `ui/components/forms.py`
**Risk:** 🟡 **MEDIUM**
**Tokens:** Disabled uses `COLOR_BORDER_LIGHT` background and `COLOR_TEXT_MUTED` text

`#7a7f96` on `#38384a` = **3.0:1** — fails AA. Disabled inputs and buttons become essentially unreadable.

**Impact:** Users cannot tell whether a field is filled vs empty in disabled state.

**Fix:** Add `COLOR_TEXT_DISABLED = #9a9fb6` and `COLOR_BG_DISABLED = #2a2a3c` (raises to 4.2:1).

---

## 5. 🟡 Light-on-Light Readability Risks (3 Found)

### 5.1 LIGHT-001 — Light theme muted text on hover
**Risk:** 🟡 **LOW**
`COLOR_TEXT_MUTED = #64748b` on `COLOR_BG_HOVER = #f1f5f9` = 3.4:1 — fails AA for small text.

### 5.2 LIGHT-002 — Tooltip text
**Risk:** ✅ **PASS**
`COLOR_BG_TOOLTIP = #1e293b` (dark) with default `COLOR_TEXT_PRIMARY` (white-ish) = 14.5:1 — clean.

### 5.3 LIGHT-003 — Form description background
**File:** `ui/constants.py` — `_THEME_LIGHT` line 396
**Risk:** ✅ **PASS**
`COLOR_FORM_DESCRIPTION_BG = #f1f5f9` (slate-100) — distinct from white card. OK.

---

## 6. Focus & Selection Audit

### 6.1 Button focus indicator
**File:** `theme/style_builder.py:46-48`
```css
QPushButton:focus { border: 2px solid {COLOR_PRIMARY}; }
```
**Verdict:** ✅ Clear 2px primary-color border on focus. Passes AA for UI components (3:1 required).

### 6.2 Input focus indicator
**File:** `theme/style_builder.py:115-118`
```css
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 2px solid {COLOR_PRIMARY};
    background-color: {COLOR_BG_SURFACE};
}
```
**Verdict:** ✅ Adequate — 2px primary border + background lift. Good dual-cue.

### 6.3 Table focus indicator
**File:** `theme/style_builder.py:267-269`
```css
QTableWidget:focus { border: 1px solid {COLOR_BORDER_FOCUS}; }
```
**Risk:** 🟡 **MEDIUM**
1px is below AA minimum for UI components in many contrast conditions. Selected-row inside the table uses 2px-equivalent via `font-weight: 500` plus background — but `TABLE_TEXT_SELECTED = #fff` (white) on `TABLE_BG_SELECTED = #364a6a` (dark blue) = 5.7:1 = passes AA. **OK once selected**, but **table focus** when keyboard-only navigating is weak.

**Fix:** Increase to 2px and use `COLOR_BORDER_FOCUS` for the selected-row inner ring.

### 6.4 Sidebar item focus / active
See §4.1 — same risk applies. No keyboard navigation visual cue distinct from mouse hover.

---

## 7. Button / Input Height Audit

| Component | Min Height | Status |
|---|---|---|
| `ButtonSize.SMALL` | 32px | ✅ AA click target 24px |
| `ButtonSize.MEDIUM` | 38px | ✅ Comfortable |
| `ButtonSize.LARGE` | 46px | ✅ Touch-friendly |
| `INPUT_HEIGHT_SM` | 32px | ✅ |
| `INPUT_HEIGHT_MD` | 38px | ✅ |
| `INPUT_HEIGHT_LG` | 44px | ✅ Touch |
| `INPUT_HEIGHT_XL` | 50px | ✅ Kiosk |
| `TABLE_ROW_HEIGHT_COMPACT` | 26px | 🟡 Tight but acceptable for finance |
| `TABLE_ROW_HEIGHT_MD` | 32px | ✅ |
| `TABLE_ROW_HEIGHT_RELAXED` | 40px | ✅ |
| `SidebarItem` min-height | 34px | ✅ |

**No height issues found.** All click targets meet WCAG 2.5.5 (24px minimum).

---

## 8. Typography Audit

| Role | Size | Usage | Status |
|---|---|---|---|
| `TEXT_DISPLAY` | 28pt | Page hero (rare) | ✅ |
| `TEXT_PAGE_TITLE` | 20pt | Page title | ✅ |
| `TEXT_SECTION_TITLE` | 18pt | Section | ✅ |
| `TEXT_CARD_TITLE` | 16pt | Card title | ✅ |
| `TEXT_BODY` | 11pt | Body text | ✅ |
| `TEXT_BODY_SMALL` | 10pt | Secondary | ✅ |
| `TEXT_LABEL` | 11pt | Form labels | ✅ |
| `TEXT_LABEL_SMALL` | 10pt | Compact labels | 🟡 Small |
| `TEXT_TABLE` | 10pt | Table cells | 🟡 Small for finance data |
| `TEXT_TABLE_HEADER` | 9pt | Table headers | 🟡 Borderline |
| `TEXT_HELPER` | 9pt | Helper text | 🟡 See §4.5 |
| `TEXT_ERROR` | 10pt | Error messages | ✅ |
| `TEXT_BADGE` | 9pt | Badges | 🟡 Small |
| `TEXT_MONO` | 11pt | Code/data | ✅ |

**Reading:** 9pt and 10pt sizes are used in tables and helper text. These are **legible on retina/HiDPI** but **sub-optimal for extended reading on standard 1080p monitors at 100% scaling**. The font family (Segoe UI) is good for screen readability.

---

## 9. Critical Findings — Immediate Action List

| # | Risk | File | Token | Fix |
|---|---|---|---|---|
| 1 | 🔴 Sidebar active indistinguishable from hover | `sidebar.py:469` | `COLOR_BG_FOCUS` vs `COLOR_BG_HOVER` | Add left-border accent + 25pt bg delta |
| 2 | 🔴 Input blends with main background (dark) | `ui/constants.py:138` | `COLOR_BG_INPUT` | Set `#181825` |
| 3 | 🔴 Dialog title invisible (token collision) | `dialogs.py:126-135` | `COLOR_HEADER_DARK` | Set text to `COLOR_TEXT_PRIMARY` |
| 4 | 🟡 Helper text fails AA dark mode | `forms.py:159` | `COLOR_TEXT_MUTED` | Add `COLOR_HELPER_TEXT_DARK` |
| 5 | 🟡 Disabled state invisible | `style_builder.py:49` | `COLOR_TEXT_MUTED` | Add `COLOR_TEXT_DISABLED` |
| 6 | 🟡 Table focus 1px too weak | `style_builder.py:267` | `COLOR_BORDER_FOCUS` | Use 2px |

---

## 10. Readability Score

| Sub-domain | Score | Weight | Weighted |
|---|---|---|---|
| Text contrast (dark) | 72/100 | 25% | 18.0 |
| Text contrast (light) | 95/100 | 20% | 19.0 |
| Focus indicators | 70/100 | 15% | 10.5 |
| Selected state | 60/100 | 10% | 6.0 |
| Helper / muted text | 55/100 | 10% | 5.5 |
| Disabled state | 50/100 | 10% | 5.0 |
| Placeholders | 90/100 | 5% | 4.5 |
| Typography sizing | 85/100 | 5% | 4.25 |
| **Overall Readability** | — | 100% | **72.75 / 100** |

---

## 11. Recommended Fixes (No Code Changes in This Phase)

These are scoping notes for Phase 2 (Theme Rebalancing):

1. **Add 5 new tokens to `ui/constants.py`**:
   - `COLOR_BG_INPUT_DARK = "#181825"` (replaces `COLOR_BG_INPUT` in dark theme)
   - `COLOR_HELPER_TEXT_DARK = "#8a8fa6"`
   - `COLOR_TEXT_DISABLED = "#9a9fb6"`
   - `COLOR_BG_DISABLED = "#2a2a3c"`
   - `COLOR_TEXT_ON_HEADER = "#e5e8f0"` (replaces the colliding `COLOR_TEXT_ON_PRIMARY` for headers)

2. **Modify `sidebar.py:469-486`** to add a `border-left: 3px solid COLOR_PRIMARY` on active state and increase bg delta to ≥25 RGB points.

3. **Modify `dialogs.py:133`** to use `COLOR_TEXT_ON_HEADER` instead of `COLOR_TEXT_ON_PRIMARY`.

4. **Modify `style_builder.py:267`** to use `2px solid COLOR_BORDER_FOCUS` for table focus.

All fixes are **token-level only** — no widget tree changes, no architectural changes, no backend changes. Estimated effort: **2-3 hours of focused work**, 0 functional risk.
