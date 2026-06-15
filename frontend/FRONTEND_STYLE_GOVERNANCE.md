# 🎨 Frontend Style Governance Rules
**Effective:** 2026-06-16  
**Applies to:** All files in `frontend/ui/`, `frontend/theme/`, `frontend/utils/`

---

## ✅ Mandatory Rules

### Rule 1: Font Size Units — Always use `pt`
```python
# ✅ CORRECT
font-size: {TEXT_BODY}pt;
self.label.setStyleSheet(f"font-size: {TEXT_BODY}pt;")

# ❌ WRONG
font-size: {TEXT_BODY}px;   # px renders smaller on HiDPI displays
font-size: 10px;            # hardcoded value
```
**Exception:** HTML output files (`printable_invoice.py`) may use `px` since they render in a browser.

### Rule 2: Colors — Always use `COLOR_*` tokens
```python
# ✅ CORRECT
color: {COLOR_TEXT_ON_PRIMARY};
background-color: {COLOR_BG_SURFACE};

# ❌ WRONG
color: white;
color: #ffffff;
background-color: #282838;
```

### Rule 3: Border Radius — Always include `px` suffix
```python
# ✅ CORRECT
border-radius: {BORDER_RADIUS_MD}px;

# ❌ WRONG
border-radius: {BORDER_RADIUS_MD};   # Qt silently ignores without px
```

### Rule 4: Use `UIStyleBuilder` for common patterns
```python
from theme.style_builder import UIStyleBuilder

# ✅ CORRECT — centralized, theme-aware
self.loading_label.setStyleSheet(UIStyleBuilder.get_state_label_style("loading"))
self.table.setStyleSheet(UIStyleBuilder.get_table_style())
self.input.setStyleSheet(UIStyleBuilder.get_input_style())

# ❌ WRONG — inline f-string
self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt;")
```

### Rule 5: Spacing — Always use `SPACING_*` tokens
```python
# ✅ CORRECT
padding: {SPACING_MD}px;
margin: {SPACING_LG}px;

# ❌ WRONG
padding: 12px;
margin: 16px;
```

---

## Available `UIStyleBuilder` Methods

| Method | Use Case |
|--------|----------|
| `get_button_style(variant)` | All buttons (primary, secondary, success, danger, warning, ghost) |
| `get_input_style(state)` | All input fields (default, error, success, warning) |
| `get_table_style()` | All QTableWidget instances |
| `get_tab_style()` | QTabWidget |
| `get_card_style()` | Card/section containers |
| `get_label_style(role)` | Labels (title, section, body, muted, label, error, success, helper) |
| `get_form_section_style(primary)` | QGroupBox form sections |
| `get_state_label_style(state)` | Loading/empty/error state labels |
| `get_page_header_style()` | Page title headers |
| `get_toolbar_style()` | Toolbar containers |
| `get_subtitle_style()` | Dialog/form subtitles |
| `get_divider_style()` | Section dividers |
| `get_global_style()` | Global QComboBox, QMenu, QListView |
| `get_status_indicator_style(color)` | Status indicator cards |
| `get_warning_banner_style(level)` | Warning/error banners |
| `get_badge_style(color)` | State badges |

---

## Pre-commit Checks

The `pre_commit_enforcer.py` script should check for:
1. No `color: white` or `color: black` in QSS
2. No `font-size: Npx` where N is a digit (should be `pt`)
3. No hex colors (#XXXXXX) outside `constants.py` and `theme_engine.py`
4. No `border-radius: {BORDER_RADIUS_*};` without `px` suffix
