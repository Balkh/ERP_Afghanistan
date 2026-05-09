# ERP Visual Identity Standard
## Unified Interactive Element System

**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-05-08

---

## CORE PRINCIPLE

> **ONE ACTION TYPE → ONE VISUAL LANGUAGE**

Every interactive element must have exactly ONE visual representation based on its semantic purpose.

---

## 1. BUTTON SYSTEM

### 1.1 Button Types

| Type | Purpose | Default | Hover | Active |
|------|---------|---------|-------|--------|
| **PRIMARY** | Main actions (Save, Submit, Confirm) | COLOR_PRIMARY | COLOR_PRIMARY_HOVER | COLOR_PRIMARY_ACTIVE |
| **SUCCESS** | Positive actions (Approve, Dispatch, Complete) | COLOR_SUCCESS | COLOR_SUCCESS_HOVER | COLOR_SUCCESS_ACTIVE |
| **DANGER** | Destructive actions (Delete, Cancel, Reject) | COLOR_DANGER | COLOR_DANGER_HOVER | COLOR_DANGER_ACTIVE |
| **INFO** | Informational actions (View, Print, Export) | COLOR_INFO | COLOR_INFO_HOVER | COLOR_INFO_ACTIVE |
| **WARNING** | Caution actions (Suspend, Hold) | COLOR_WARNING | COLOR_WARNING_HOVER | COLOR_WARNING_ACTIVE |
| **SECONDARY** | Non-primary actions (Cancel, Back, Clear) | COLOR_BG_BUTTON_SECONDARY | COLOR_TEXT_SECONDARY_LIGHT | COLOR_MUTED_LIGHT |
| **DISABLED** | Unavailable actions | COLOR_MUTED_LIGHT | - | - |

### 1.2 Button Structure

```
QPushButton {
    border: none;
    border-radius: BORDER_RADIUS_MD;
    padding: SPACING_SM SPACING_LG;
    font-weight: bold;
    min-height: BUTTON_HEIGHT_MD;
}
```

### 1.3 Interaction States

| State | Property Changes |
|-------|------------------|
| **Default** | Base color from button type |
| **Hover** | Lighter shade (HOVER variant) |
| **Pressed/Active** | Darker shade (ACTIVE variant) |
| **Disabled** | Muted gray, reduced opacity |

---

## 2. SEMANTIC COLOR PHILOSOPHY

### 2.1 Color Meanings

| Token Family | Semantic Meaning | Use Case |
|--------------|------------------|----------|
| COLOR_PRIMARY_* | Main action | Primary form submission, main workflow |
| COLOR_SUCCESS_* | Positive outcome | Approval, completion, dispatch |
| COLOR_DANGER_* | Negative outcome | Deletion, cancellation, rejection |
| COLOR_INFO_* | Neutral information | Viewing, printing, exporting |
| COLOR_WARNING_* | Caution state | Suspension, hold, pending review |
| COLOR_BG_BUTTON_SECONDARY | Alternative action | Cancel, back, secondary workflow |

### 2.2 Color Selection Rules

1. **NEVER** use random hex colors for buttons
2. **ALWAYS** use semantic token families
3. **NEVER** mix color families (e.g., don't use blue for success)
4. **CONSISTENCY** - same action always has same color across ERP

---

## 3. IMPLEMENTATION GUIDELINES

### 3.1 Correct Usage

```python
# CORRECT - Using semantic tokens
button.setStyleSheet(f"""
    QPushButton {{
        background-color: {COLOR_SUCCESS};
        color: {COLOR_TEXT_ON_PRIMARY};
    }}
    QPushButton:hover {{
        background-color: {COLOR_SUCCESS_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_SUCCESS_ACTIVE};
    }}
""")
```

### 3.2 Incorrect Usage

```python
# INCORRECT - Hardcoded hex colors
button.setStyleSheet("""
    QPushButton {
        background-color: #219653;  /* WRONG */
    }
    QPushButton:hover {
        background-color: #1e8449;  /* WRONG */
    }
""")

# INCORRECT - Using wrong semantic family
button.setStyleSheet("""
    QPushButton {
        background-color: COLOR_PRIMARY;  /* WRONG - for delete action */
    }
""")
```

---

## 4. RESOLVING REMAINING VIOLATIONS

### 4.1 sales_invoice_screen.py

Current violations use non-standard color families:

| Line | Current Hex | Should Be | Token |
|------|-------------|-----------|-------|
| 334 | #2980b9 | Primary hover | COLOR_PRIMARY_HOVER |
| 337 | #1f618d | Primary active | COLOR_PRIMARY_ACTIVE |
| 354 | #219653 | Success hover | COLOR_SUCCESS_HOVER |
| 357 | #1e8449 | Success active | COLOR_SUCCESS_ACTIVE |

**Resolution:** Update UI to use standard tokens instead of custom hex.

---

## 5. TOKENS REFERENCE

### 5.1 Button Colors

```
# Primary Actions
COLOR_PRIMARY = "#89b4fa"
COLOR_PRIMARY_HOVER = "#b4befe"
COLOR_PRIMARY_ACTIVE = "#74c7ec"
COLOR_PRIMARY_MUTED = "#45475a"

# Success Actions  
COLOR_SUCCESS = "#a6e3a1"
COLOR_SUCCESS_HOVER = "#94e3b4"
COLOR_SUCCESS_ACTIVE = "#7dd3a8"
COLOR_SUCCESS_MUTED = "#6b8f7a"

# Danger Actions
COLOR_DANGER = "#f38ba8"
COLOR_DANGER_HOVER = "#ee7596"
COLOR_DANGER_ACTIVE = "#e65f84"
COLOR_DANGER_MUTED = "#c46a82"

# Info Actions
COLOR_INFO = "#89dceb"
COLOR_INFO_HOVER = "#76c9dd"
COLOR_INFO_ACTIVE = "#63b6ce"
COLOR_INFO_MUTED = "#6a9aa8"

# Warning Actions
COLOR_WARNING = "#f9e2af"
COLOR_WARNING_HOVER = "#f5d89a"
COLOR_WARNING_ACTIVE = "#f0cd7e"
COLOR_WARNING_MUTED = "#c9b88a"

# Secondary Actions
COLOR_BG_BUTTON_SECONDARY = "#dcdde1"
COLOR_BG_BUTTON_LIGHT = "#6b7280"
```

### 5.2 Text Colors

```
COLOR_TEXT_ON_PRIMARY = "#1e1e2e"
COLOR_TEXT_DIALOG = "#2f3640"
```

---

## 6. ENFORCEMENT

### 6.1 CI Rules

1. **BUTTON COLORS** - Must use COLOR_*_HOVER and COLOR_*_ACTIVE tokens
2. **NO HARDCODED** - No #hex in button stylesheets
3. **SEMANTIC MATCH** - Button color must match action semantic
4. **STATE COMPLETE** - All buttons must have hover/active states

### 6.2 Review Checklist

- [ ] Button uses correct semantic family (primary/success/danger/info/warning/secondary)
- [ ] Hover state defined with *_HOVER token
- [ ] Active/pressed state defined with *_ACTIVE token
- [ ] No hardcoded hex colors in button stylesheet
- [ ] Text color contrasts appropriately (use COLOR_TEXT_ON_PRIMARY for light backgrounds)

---

## 7. MODULE ADOPTION

| Module | Status | Notes |
|--------|--------|-------|
| Sales | In Progress | Fixing 4 button violations |
| Purchases | - | Review needed |
| Accounting | - | Review needed |
| HR | - | Review needed |
| Inventory | - | Review needed |
| Returns | Complete | Tokens applied |

---

## 8. SUCCESS CRITERIA

- [ ] All buttons use semantic color families
- [ ] All buttons have complete interaction states (hover, active)
- [ ] No hardcoded hex colors in button styles
- [ ] Visual consistency across all ERP modules
- [ ] Zero button-related UI violations

---

*End of Visual Identity Standard*