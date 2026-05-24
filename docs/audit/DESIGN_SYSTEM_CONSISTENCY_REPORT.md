# DESIGN SYSTEM CONSISTENCY REPORT — Pharmacy ERP

## Token System Architecture

The design system is defined in `ui/constants.py` (748 lines) with:
- 105 `COLOR_*` tokens across dark/light themes
- 10 `SPACING_*` tokens
- 22 `FONT_SIZE_*` and `TEXT_*` semantic tokens
- 3 density tiers
- Dialog width governance
- State message tokens

**Runtime**: `ThemeEngine` singleton in `theme/theme_engine.py` applies theme by updating module globals in `ui.constants`.

**QSS generation**: `UIStyleBuilder` in `theme/style_builder.py` generates component stylesheets from tokens.

---

## CRITICAL FAILURE: 17 Token Interpolation Bugs

All component styling in these files uses **regular strings** (not f-strings) for `setStyleSheet()`, so `{TOKEN}` patterns are never resolved.

```python
# BROKEN — regular string, tokens are literal text
self.setStyleSheet("""
    background: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
""")

# CORRECT — f-string, tokens are resolved
self.setStyleSheet(f"""
    background: {COLOR_BG_ELEVATED};
    border: 1px solid {COLOR_BORDER};
""")
```

**Files affected** (all in `ui/components/`):
| File | Bug Location | Broken Elements |
|------|-------------|-----------------|
| `buttons.py` | Lines 209-221 | SplitButton — never gets primary color, borders, or margins |
| `dialogs.py` | Lines 91-95, 133-142, 184-191 | EnterpriseDialog — background, header, button area never styled |
| `kpi_cards.py` | Lines 78-85, 121-128, 158-164, 213-223 | KPICard, MiniMetricCard, StatusBadge — completely unstyled |
| `state_helper.py` | Lines 57-63, 104-110, 150-161, 187-193, 229-239 | All state overlays — containers and buttons never styled |
| `navigation_header.py` | Lines 42-67 | NavigationHeader — entire 26-line stylesheet broken |
| `notifications.py` | Lines 109-115, 156-167 | NotificationItem — backgrounds and colors broken |
| `loading_spinner.py` | Lines 69-75 | Loading overlay label broken |

**Impact**: ALL visual polish in these components is non-functional. The design system appears to work in `ThemeEngine` and `UIStyleBuilder` but fails at the consumer level.

---

## DUPLICATE STYLE SOURCES: Two Table Stylesheet Generators

| Source | Location | Lines | Used By |
|--------|----------|-------|---------|
| `build_table_stylesheet()` | `ui/components/tables.py` | 55-176 | DataEntryGrid (line 598-613) |
| `UIStyleBuilder.get_table_style()` | `theme/style_builder.py` | 185-270 | EnterpriseTable (line 388) |

These are nearly identical implementations. They have **diverged** — changes to one are not reflected in the other.

---

## COMPONENTS BYPASSING UIStyleBuilder

The following components build their own inline f-string stylesheets instead of using `UIStyleBuilder`:

| Component | File | Style Method |
|-----------|------|-------------|
| KPICard | `kpi_cards.py` | Inline f-string (broken) |
| MiniMetricCard | `kpi_cards.py` | Inline f-string (broken) |
| StatusBadge | `kpi_cards.py` | Inline f-string (broken) |
| StateHelper overlays | `state_helper.py` | Inline string (broken) |
| NavigationHeader | `navigation_header.py` | Inline string (broken) |
| NotificationItem | `notifications.py` | Inline string (broken) |
| LoadingOverlay label | `loading_spinner.py` | Inline string (broken) |
| DocumentActionDialog | `document_action_dialog.py` | Inline f-string |

---

## HARDCODED VALUES BYPASSING TOKENS

| File | Line | Value | Should Use |
|------|------|-------|------------|
| `dialogs.py` | 140 | `color: white;` | `COLOR_TEXT_ON_PRIMARY` or similar |
| `dialogs.py` | 121 | `header.setFixedHeight(50)` | Height token |
| `dialogs.py` | 151 | `button_area.setFixedHeight(60)` | Height token |
| `state_helper.py` | 153, 232 | `color: white;` | `COLOR_TEXT_ON_PRIMARY` |
| `notifications.py` | 118 | `layout.setContentsMargins(12, 8, 8, 8)` | `SPACING_*` tokens |
| `notifications.py` | 101, 105 | `self.setFixedHeight(50)` / `self.setFixedHeight(80)` | Height tokens |
| `notifications.py` | 164 | `rgba(255,255,255,0.2)` | `COLOR_HOVER_OVERLAY` |
| `document_action_dialog.py` | 112 | `color: white;` | `COLOR_TEXT_ON_*` |

---

## COMPLETE THEME BYPASS: financial_control_tower_screen.py

`ui/control_tower/financial_control_tower_screen.py:22-36` defines its own `COLORS` and `SPACING` dictionaries with hardcoded hex values. This file:
- Ignores `ui/constants.py` tokens
- Ignores `ThemeEngine`
- Ignores dark/light theme switching
- Will break when theme changes

---

## LEGACY/DEPRECATED FILES

| File | Status | Notes |
|------|--------|-------|
| `theme/enterprise_styling.py` | **DEPRECATED** | Marked as deprecated at line 2, retained for reference |
| `theme/theme_manager.py` | **LEGACY** | QPalette-based manager, not used by `ThemeEngine` |
| `ui/theme/theme_manager.py` | **LEGACY** | Deprecated wrapper, delegates to `theme.theme_engine` |

---

## EMPTY TOKEN: COLOR_BG_HOVER

`ui/constants.py:81`:
```python
COLOR_BG_HOVER = ""
```
This token is defined as an empty string. Any component using `{COLOR_BG_HOVER}` in stylesheets will produce invalid QSS.

---

## FORMS TOKEN USAGE

`ui/components/forms.py`:
- Line 144: Uses inline `<span style='color: {COLOR_FORM_LABEL_REQUIRED};'>` — token value IS used (f-string), but bypasses UIStyleBuilder
- No centralized form stylesheet in UIStyleBuilder
- 13 field types defined but no consistent input styling pipeline

---

## ThemeEngine Verification

| Check | Status |
|-------|--------|
| Singleton pattern | ✅ `instance()` method |
| Live theme switching | ✅ `apply_theme("dark"|"light")` |
| Signal emission | ✅ `theme_changed` signal |
| Token source | ✅ Reads from `ui.constants` |
| Widget refresh | ✅ `_refreshables` dict |
| Verify sync | ✅ `verify_sync()` method |

**ThemeEngine itself is clean**. The problem is entirely in the consumer components that fail to interpolate tokens.

---

## Consistency Summary

| Check | Status | Critical Issues |
|-------|--------|-----------------|
| ThemeEngine usage | ✅ Good | Engine itself is well-designed |
| Token compliance | ❌ **FAIL** | 17 interpolation bugs + hardcoded values |
| UIStyleBuilder adoption | ⚠️ Poor | 8 components bypass it |
| No inline styles | ❌ **FAIL** | 10+ files have hardcoded values |
| No hex colors | ❌ **FAIL** | financial_control_tower + pos + dashboard |
| Single source of truth | ⚠️ Poor | Two table style generators, two page maps |
| Consistent dialog styling | ❌ **FAIL** | Token bugs break all dialogs |
| Consistent button styling | ⚠️ Fair | SplitButton broken; 242 raw QPushButtons |
| Consistent table styling | ⚠️ Poor | Two divergent generators |
| Consistent form styling | ⚠️ Fair | Forms bypass UIStyleBuilder |
| Theme dark/light parity | ✅ Good | Both themes defined in constants.py |
