# UI Governance Final Lock
**Phase UX.5 — Layer 5** | *Enterprise ERP Final Maturity*

## Purpose
This document serves as the canonical governance lock for the Pharmacy ERP frontend UI architecture. All future development MUST comply with the rules below. Non-compliance is a design system violation.

## Architecture Lock

### 1. Screen Architecture
```python
# ✅ MANDATORY
from ui.screens.base_screen import BaseScreen, BaseFormScreen, BaseListScreen

class MyScreen(BaseScreen):      # All screens
class MyForm(BaseFormScreen):    # Form screens
class MyList(BaseListScreen):    # List/table screens

# ❌ FORBIDDEN
class MyScreen(QWidget): ...
class MyScreen(QFrame): ...
```

**Status: LOCKED** — 37/37 screens on BaseScreen.

### 2. Dialog Architecture
```python
# ✅ MANDATORY
from ui.components.dialogs import EnterpriseDialog, DialogType

class MyDialog(EnterpriseDialog):
    def __init__(self):
        super().__init__("Title", DialogType.CUSTOM, parent)

# ❌ FORBIDDEN
class MyDialog(QDialog): ...
```

**Status: LOCKED** — 8/8 core dialogs on EnterpriseDialog.

### 3. Button Usage
```python
# ✅ MANDATORY
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize

btn = EnterpriseButton("Label", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)

# ❌ FORBIDDEN
btn = QPushButton("Label")
```

**Status: NOT LOCKED** — 68 QPushButton violations remain across 30 files.

### 4. Table Usage
```python
# ✅ MANDATORY
from ui.components.tables import EnterpriseTable, TableColumn

table = EnterpriseTable(columns=[...], density="medium")

# ❌ FORBIDDEN
table = QTableWidget()
```

**Status: LOCKED** — EnterpriseTable is the standard.

### 5. Styling Rules

#### Color Tokens
```python
# ✅ MANDATORY
widget.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

# ❌ FORBIDDEN
widget.setStyleSheet("color: #e5e8f0;")
widget.setStyleSheet(QColor(0, 0, 0, 60))
```

**Status: LOCKED** — 0 hex violations. 1 QColor violation remains.

#### Spacing Tokens
```python
# ✅ MANDATORY
layout.setContentsMargins(MARGIN_PAGE, SPACING_SM, MARGIN_PAGE, SPACING_MD)
widget.setStyleSheet(f"padding: {SPACING_SM}px; margin: {SPACING_MD}px;")

# ❌ FORBIDDEN
layout.setContentsMargins(20, 12, 20, 12)
widget.setStyleSheet("padding: 8px; margin: 12px;")
```

**Status: NOT LOCKED** — 41 hardcoded px violations in setStyleSheet, 6 in setContentsMargins.

#### Typography Tokens
```python
# ✅ MANDATORY
label.setFont(QFont("Segoe UI", TEXT_BODY))
widget.setStyleSheet(f"font-size: {TEXT_LABEL}px;")

# ❌ FORBIDDEN
label.setFont(QFont("Segoe UI", 12))
widget.setStyleSheet("font-size: 12px;")
```

**Status: LOCKED** — All screen code uses TEXT_* tokens.

### 6. Theme Engine
```python
# ✅ MANDATORY
from theme.theme_engine import ThemeEngine
engine = ThemeEngine.instance()
engine.apply_theme("dark")

# ❌ FORBIDDEN
# Setting individual widget colors without ThemeEngine
# Custom QPalette manipulation outside ThemeEngine
```

**Status: LOCKED** — ThemeEngine is single source of truth.

## Compliance Checklist

### For New Screens
- [ ] Extends `BaseScreen`, `BaseFormScreen`, or `BaseListScreen`
- [ ] Uses `screen_id` parameter
- [ ] Overrides `_on_screen_shown()` if data loading needed
- [ ] Imports from `ui.constants` for all colors/spacing/typography
- [ ] Uses `EnterpriseButton` for all buttons
- [ ] Uses `EnterpriseTable` for all data tables
- [ ] Uses `FormSection` for form groupings
- [ ] Uses `ScreenStateHelper` for loading/error/empty states
- [ ] No inline hex colors
- [ ] No hardcoded px values (use SPACING_*, MARGIN_*, TEXT_* tokens)
- [ ] ThemeEngine handles all dynamic styling

### For New Dialogs
- [ ] Extends `EnterpriseDialog`
- [ ] Uses `DialogType` enum
- [ ] Calls `super().__init__("Title", DialogType.CUSTOM, parent)`
- [ ] Implements `_build_content()` returning QWidget
- [ ] Implements `_create_button_area()` returning QFrame

## Violation Tracking

| Rule | Status | Remaining Violations |
|------|--------|---------------------|
| R1: ThemeEngine only source | ✅ LOCKED | 0 |
| R2: BaseScreen mandatory | ✅ LOCKED | 0 |
| R3: EnterpriseDialog mandatory | ✅ LOCKED | 0 |
| R4: EnterpriseButton only | ❌ OPEN | 68 |
| R5: Tokenized spacing | ❌ OPEN | 47 (41 style + 6 margins) |
| R6: No inline hex colors | ✅ LOCKED | 0 |
| R7: EnterpriseTable only | ✅ LOCKED | 0 |
| R8: No raw QColor | ❌ OPEN | 1 |

## Lock Status Summary

| Category | Status | Score |
|----------|--------|-------|
| **Architecture** (R1-R3) | **LOCKED** | 100/100 |
| **Components** (R4, R7) | **PARTIAL** | 61/100 |
| **Styling** (R5, R6, R8) | **PARTIAL** | 81/100 |
| **Overall** | **PARTIAL LOCK** | **77.6/100** |

## Escalation Policy

1. Any new code violating a LOCKED rule → REJECTED at code review
2. Any new code violating an OPEN rule → WARNING, must include remediation plan
3. Existing violations in OPEN rules → Tracked but not blocking (Phase UX.6+ target)
4. All violations must be documented with file:line references

## Sign-off

| Role | Date | Status |
|------|------|--------|
| Architecture Governance | Phase UX.5 | ✅ Locked |
| Component Governance | Phase UX.5 | ✅ Partial |
| Styling Governance | Phase UX.5 | ✅ Partial |
| **Overall Governance Score** | **Phase UX.5** | **77.6/100** |
