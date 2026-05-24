# EXCLUDED DOMAINS POLICY
## Enterprise Design System CI Enforcement

**Version:** 1.0  
**Status:** Active  
**Last Updated:** 2026-05-08

---

## 1. EXCLUDED DOMAINS (STRICT DEFINITION)

The following domains MUST be excluded from all automatic enforcement:

### 1.1 DATA VISUALIZATION DOMAIN

**Files/Components:**
- Dashboards with charts
- Analytics modules
- Reporting graphs
- Intelligence/insight panels

**Rules:**
- ✅ Allow custom color palettes (mauve, pink, etc.)
- ❌ Do NOT enforce COLOR_* tokens here
- ❌ Do NOT treat as violation

**Rationale:** These colors are semantic visualization, not UI design system styling.

---

### 1.2 THEME SYSTEM DOMAIN

**Files:**
- `theme_manager.py`
- `enterprise_styling.py` core palette logic
- QPalette configurations

**Rules:**
- ❌ NEVER modify or enforce tokens here
- ✅ This is the source of truth layer
- ✅ CI must skip entirely

**Rationale:** Theme system is the foundation - modifying it would break all UI.

---

### 1.3 DOCUMENT / PRINT / EMAIL DOMAIN

**Files:**
- `printable_invoice.py`
- Email templates
- Export PDF/HTML styling

**Rules:**
- ✅ Allow inline CSS flexibility
- ✅ Skip token enforcement if compatibility required
- ✅ Only warn, never block or auto-fix

**Rationale:** Document output has specific CSS requirements.

---

### 1.4 BACKEND / BUSINESS LOGIC DOMAIN

**Files:**
- Django APIs
- Services layer
- Models.py

**Rules:**
- ❌ No UI enforcement allowed
- ✅ Any color usage is incidental and must be ignored

**Rationale:** Backend code may use colors for logging/debugging - not UI concern.

---

## 2. INCLUDED DOMAINS (ONLY VALID TARGETS)

CI ENFORCEMENT MUST ONLY APPLY TO:

- ✅ **UI Widget Layer** - PySide6 QWidget components
- ✅ **Forms** - QWidget-based screens
- ✅ **CRUD Screens** - Create/Read/Update/Delete interfaces
- ✅ **Tables and dialogs** - Data display and user prompts
- ✅ **Reusable UI components** - buttons, inputs, panels

These are valid targets for:
- COLOR_SYSTEM_ENFORCEMENT
- SPACING_SYSTEM_ENFORCEMENT
- TYPOGRAPHY_ENFORCEMENT

---

## 3. CI FILTERING LOGIC

Before reporting a violation, CI MUST:

### STEP 1: Classify file into domain
- `UI_WIDGET` → Include
- `VISUALIZATION` → Exclude
- `THEME_SYSTEM` → Exclude
- `DOCUMENT_OUTPUT` → Exclude (warning only)
- `BACKEND_LOGIC` → Exclude

### STEP 2: Apply enforcement only if
- domain == `UI_WIDGET`

### STEP 3: If domain != UI_WIDGET
- → Mark as EXCLUDED
- → Do NOT count as violation

---

## 4. IMPLEMENTATION

### File-Level Exclusions

```python
EXCLUDED_FILES = {
    "printable_invoice.py",  # DOCUMENT_OUTPUT
    "theme_manager.py",     # THEME_SYSTEM
    "enterprise_styling.py", # THEME_SYSTEM
}
```

### Pattern-Level Exclusions

- Chart color dictionaries (`color_mapping`, `chart_palette`)
- QPalette/QColor system colors
- Email template CSS
- RGBA transparency patterns

### Domain Classification

| File Pattern | Domain | Action |
|--------------|--------|--------|
| `dashboard.py` with chart data | VISUALIZATION | Exclude chart colors only |
| `theme_manager.py` | THEME_SYSTEM | Skip entire file |
| `printable_invoice.py` | DOCUMENT_OUTPUT | Warn only, no block |
| `services.py` | BACKEND_LOGIC | Skip entire file |
| `buttons.py` | UI_WIDGET | Full enforcement |

---

## 5. EXPECTED EFFECT

After applying this policy:

- ✅ Violation count becomes accurate (real UI issues only)
- ✅ False positives in dashboard/chart modules disappear
- ✅ CI cleanup focus improves
- ✅ Engineering effort shifts to real UI inconsistencies
- ✅ System stability increases

---

## 6. SUCCESS CRITERIA

- ✅ No chart-related false violations
- ✅ No theme system interference
- ✅ No email/template noise in CI reports
- ✅ Only real UI design system violations remain
- ✅ CI becomes deterministic and domain-aware

---

## 7. FINAL GOAL

Transform CI enforcement from:

**"Generic pattern-based violation scanner"**

into:

**"Domain-aware enterprise design system governance engine with precise UI-only enforcement"**

---

*End of Policy*