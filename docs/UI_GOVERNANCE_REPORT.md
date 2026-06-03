# UI Governance & Design System Audit — Phase 2
**Pharmacy ERP — Read-Only Audit**
**Date:** 2026-06-01
**Scope:** 140 Python files in `frontend/ui/` (excluding `__pycache__` and `backups/`)
**Method:** Static analysis only. NO code was modified. NO new widgets, tokens, or designs were created.

---

## 1. Executive Summary

| Pillar | Score | Status |
|---|---|---|
| **Color Tokenization** | **100%** | ✅ Perfect — 0 hex violations in stylesheet code |
| **Font-size Tokenization** | **97%** | 🟡 7 files bypass TEXT_* tokens |
| **Border-radius Tokenization** | **99%** | ✅ 1 violation |
| **Spacing Tokenization** | **88%** | 🟡 ~30 inline CSS values bypass SPACING_* |
| **Border-width Tokenization** | **0%** | 🔴 No BORDER_WIDTH_* token category exists |
| **Widget Dimensioning** | **30%** | 🔴 ~190 setFixed*/setMin*/setMax*/resize calls |
| **Font Family Tokenization** | **0%** | 🔴 ~100 QFont("Segoe UI", ...) calls |
| **Button Component Compliance** | **100%** | ✅ 0 raw QPushButton |
| **Table Component Compliance** | **68%** | 🟡 21 raw QTableWidget |
| **Form Component Compliance** | **0%** | 🔴 124 raw QLineEdit, 86 raw QComboBox |
| **Dialog Component Compliance** | **97%** | ✅ 1 of 38 dialogs on QWidget |
| **Screen Component Compliance** | **98%** | ✅ 3 of 178 screens off BaseScreen |
| **Navigation Component Compliance** | **100%** | ✅ Single Sidebar, single NavigationHeader |
| **State Helper Compliance** | **0%** | 🔴 StateHelper defined, 0 uses; 15 _show_loading overrides |

**Overall Design System Adoption: ~72%** (based on weighted styling touchpoints).

---

## 2. Top 10 Governance Findings (Ranked by Severity)

| # | Finding | Severity | Files Affected | Effort |
|---|---|---|---|---|
| 1 | **StateHelper defined but never used; 15 files have `_show_loading` overrides** | 🔴 HIGH | 15 | LOW |
| 2 | **DataEntryGrid defined but never used; 6 line-item tables use raw QTableWidget** | 🔴 HIGH | 6 | MEDIUM |
| 3 | **124 raw QLineEdit, 86 raw QComboBox bypass FormField** | 🔴 HIGH | ~60 | HIGH |
| 4 | **Border width has no BORDER_WIDTH_* token; ~160 hardcoded `1px/2px` borders** | 🟡 MEDIUM | ~40 | MEDIUM |
| 5 | **QFont family "Segoe UI" hardcoded ~100 times; no FONT_FAMILY token** | 🟡 MEDIUM | ~40 | LOW |
| 6 | **Widget dimensions (setFixed*/setMin*) hardcoded ~190 times; INPUT_HEIGHT_*/BUTTON_HEIGHT_* exist but rarely used** | 🟡 MEDIUM | ~50 | MEDIUM |
| 7 | **`_safe_float` exact duplicate in 9 files** | 🟡 MEDIUM | 9 | LOW |
| 8 | **Class name collision: `MetricCard` vs `KPICard`** | 🟡 MEDIUM | 2 components | LOW |
| 9 | **Class name collision: `SectionHeader` defined in 2 modules with different bases** | 🟡 MEDIUM | 2 components | LOW |
| 10 | **Dead code: `base_widgets.py` (4 unused classes), `licensing/dialogs.py` (12 unused fns), `BaseFormScreen`, `BaseListScreen`** | 🟡 MEDIUM | 4 files | LOW (delete) |

---

## 3. Strengths (What's Already Working)

### 3.1 Color System — 100% Compliant
- 0 hex literals in any `setStyleSheet()` call outside of `ui/constants.py` and `theme/style_builder.py`
- 100% of color values flow through `COLOR_*` tokens
- The 2 false positives in `audit_scanner.py` and `operator_safety.py` are scanner exclusion lists / invoice number strings, not actual colors
- Two-theme (dark/light) support works seamlessly

### 3.2 Button System — 100% Compliant
- **0 raw `QPushButton` instantiations** in screens or dialogs
- All 0 violations of the previous 68 (per UX.5 design system enforcement work)
- `EnterpriseButton` (6 variants), `IconButton`, `SplitButton` are the only entry points

### 3.3 Dialog Migration — 97% Complete
- 37 of 38 dialog classes extend `EnterpriseDialog` (per Phase UX.4)
- Only 1 straggler: `LicenseDetailsDialog(QWidget)` in `licensing/license_status_screen.py:285`

### 3.4 Screen Migration — 98% Complete
- 55+ direct `BaseScreen` subclasses
- Only 2 of 178 classes extend `QWidget` directly (both in `licensing/`)

### 3.5 Navigation — 100% Compliant
- Single `Sidebar` (in `ui/sidebar.py`)
- Single `NavigationHeader` (in `ui/components/navigation_header.py`)
- No duplicate navigation widgets

### 3.6 EnterpriseTable — 68% Compliant
- 45 `EnterpriseTable` instantiations
- 21 raw `QTableWidget` instantiations
- All raw uses are line-item entry tables (which should be `DataEntryGrid`) or display tables in dialogs

---

## 4. Weaknesses (Top 5)

### 4.1 Form Widget Bypass — 0% Compliance
- **124 raw `QLineEdit`** across 39 files — should be `FormField` from `components/forms.py`
- **86 raw `QComboBox`** across 44 files — should be `FormField` (SELECT variant)
- **52 raw `QGroupBox`** across 30 files — should be `FormSection`
- **40 raw `QTextEdit`** across 24 files
- **20 raw `QDateEdit`** across 13 files

The `FormField` system in `components/forms.py` provides:
- Label + input + helper text + validation in one widget
- 4 validation states (default, error, warning, success)
- Required-field indicator
- Token-driven styling

**Most-affected files:**
- `purchases/supplier_screen.py` — 25 raw form widgets
- `sales/customer_screen.py` — 19 raw form widgets
- `pos/pos_screen.py` — 12 raw form widgets

### 4.2 StateHelper Not Wired
- `StateHelper` in `components/state_helper.py` provides `show_loading()`, `show_empty()`, `show_error()`
- **Used in 0 files**
- 15 finance screens define local `_show_loading(show=True)` overrides
- Many screens define manual `self.loading_label = QLabel("Loading...")`

### 4.3 DataEntryGrid Not Adopted
- `DataEntryGrid` in `components/tables.py` (also exported in `components/__init__.py:18`) is purpose-built for line-item entry
- **Used in 0 files**
- 6 line-item tables use raw `QTableWidget`:
  - `sales/sales_invoice_screen.py` (line items)
  - `purchases/purchase_invoice_screen.py` (line items)
  - `returns/returns_screen.py` (return items)
  - `accounting/components/journal_entry_form.py` (journal lines)
  - `pos/pos_screen.py` (cart + search results)

### 4.4 Border-width Token Category Missing
- `border: 1px solid {COLOR_*}` appears 160+ times
- `border: 2px solid {COLOR_*}` appears ~30 times
- `BORDER_WIDTH_THIN` and `BORDER_WIDTH_THICK` tokens do NOT exist
- This is a **missing token category**, not developer error
- Developers used a working pattern (color tokenized) but the width is not

### 4.5 Widget Dimensions Ungoverned
- 33 `setFixedWidth/Height(N)` calls
- ~150 `setMinimum/Maximum Width/Height(N)` calls
- 9 `resize(N, N)` calls
- **Available tokens not used:**
  - `BUTTON_HEIGHT_SM/MD/LG/XL` (32/38/46/50) — exist
  - `INPUT_HEIGHT_SM/MD/LG/XL` (32/38/44/50) — exist
  - `DIALOG_WIDTH_MIN/PREFERRED/MAX/FORM_MIN/FORM_PREFERRED/WIDE` — exist
  - `BUTTON_AREA_HEIGHT` — does NOT exist (60 used 9 times in dialogs)

---

## 5. Dead Code Inventory

| Component | File | Severity | Action |
|---|---|---|---|
| `BaseWidget` (4 base classes) | `components/base_widgets.py` | HIGH | Delete (244 lines unused) |
| `licensing/dialogs.py` (12 helper fns) | `licensing/dialogs.py` | HIGH | Delete (126 lines unused) |
| `DocumentActionDialog` | `components/document_action_dialog.py` | LOW | Delete (no callers) |
| `LoadingOverlay` (wrapper) | `observability/widgets.py:289` | LOW | Delete (deprecated) |
| `BaseFormScreen` | `screens/base_screen.py:289` | MEDIUM | Delete or populate (0 subclasses) |
| `BaseListScreen` | `screens/base_screen.py:377` | MEDIUM | Delete or populate (0 subclasses) |
| `StateHelper` | `components/state_helper.py` | HIGH | Adopt (15 files need this) |
| `DataEntryGrid` | `components/tables.py` | MEDIUM | Adopt (6 files need this) |
| `PaginationWidget` | `components/tables.py` | MEDIUM | Adopt (0 callers) |

---

## 6. Class-Name Collisions

### 6.1 `LoadingOverlay`
- `components/loading_spinner.py` — primary implementation
- `observability/widgets.py:289` — deprecated wrapper
- **Verdict:** Delete wrapper, keep primary

### 6.2 `SectionHeader`
- `components/kpi_cards.py:231` — `SectionHeader(QLabel)` — title-only
- `observability/widgets.py:309` — `SectionHeader(QFrame)` — title + optional action
- **Verdict:** Real namespace conflict if both imported. Pick one or rename.

### 6.3 `MetricCard` vs `KPICard`
- `components/kpi_cards.py:51` — `KPICard(QFrame)` — `severity` string param
- `observability/widgets.py:154` — `MetricCard(QFrame)` — `color` hex param
- Different APIs, different consumers
- **Verdict:** Consolidate to single primitive; pick `severity` or `color` API.

### 6.4 `StatusIndicator` vs `_StatusIndicator`
- `observability/widgets.py:16` — public
- `system/backup_screen.py:29` — private, local duplicate
- **Verdict:** Use the public one in backup_screen.

---

## 7. Duplicate-Pair Detection (Method Signature Overlap)

| Group | Files | Shared Methods | Severity |
|---|---|---|---|
| **A** Inventory CRUD | product, category, warehouse, batch | 13/13 shared | HIGH |
| **B** Sales/Purchase Invoice | sales_invoice + purchase_invoice | 22/24 shared | HIGH |
| **C** Customer/Supplier CRUD | customer_screen + supplier_screen | 12/14 shared | HIGH |
| **D** Customer/Supplier Payment Workspace | customer_payment + supplier_payment | 19/20 shared | HIGH |
| **E** HR CRUD | employee + departments | 9/15 shared | MEDIUM |
| **F** User/Role Management | user_management + role_management | 9/16 shared | MEDIUM |
| **G** Finance Explorer Screens | 10+ files | 6 shared | HIGH |
| **H** Attendance/Leave/Payroll | 3 files | 5/6-8 shared | LOW |
| **I** `_parse_response` (HR/Payroll) | 4 files | exact dup | LOW |
| **J** `_safe_float` | 9 files | exact dup | LOW |
| **K** `_combo_style` | 4 files | exact dup | LOW |
| **L** `_build_content`/`_create_button_area` | 34 files | same lifecycle | MEDIUM |

---

## 8. Top 10 Most-Duplicated Patterns

| # | Pattern | Count | Severity |
|---|---|---|---|
| 1 | `QLineEdit(` raw | **124** | HIGH |
| 2 | `QComboBox(` raw | **86** | HIGH |
| 3 | `QGroupBox(` raw | **52** | MEDIUM |
| 4 | `QTextEdit(` raw | **40** | MEDIUM |
| 5 | `QDateEdit(` raw | **20** | MEDIUM |
| 6 | `QCheckBox(` raw | **19** | MEDIUM |
| 7 | `QTableWidget(` raw (line-item) | **21** | HIGH |
| 8 | Custom `_show_loading` overrides | **15** | MEDIUM |
| 9 | `_build_content` + `_create_button_area` | **34+34** | MEDIUM |
| 10 | `_safe_float` exact dup | **9** | LOW |

---

## 9. Token Category Gaps (Missing Design Tokens)

The following token categories would unlock significant cleanup if added to `ui/constants.py`:

| Missing Token | Replaces | Frequency |
|---|---|---|
| `BORDER_WIDTH_THIN = 1` | `border: 1px solid ...` | 160+ |
| `BORDER_WIDTH_THICK = 2` | `border: 2px solid ...` | ~30 |
| `BUTTON_AREA_HEIGHT = 60` | `setFixedHeight(60)` in 9 dialogs | 9 |
| `INPUT_FIELD_HEIGHT_COMPACT = 30` | `setMinimumHeight(30)` in 15+ screens | 15+ |
| `DIALOG_WIDTH_COMPACT = 400` | `setMinimumWidth(400)` | 1+ |
| `DIALOG_WIDTH_MEDIUM = 500` | `setMinimumWidth(500)` | 4+ |
| `DIALOG_WIDTH_LARGE = 700` | `setMinimumWidth(700)` | 2+ |
| `DIALOG_WIDTH_XLARGE = 850` | `setMinimumWidth(850)` | 2+ |
| `FONT_FAMILY_PRIMARY = "Segoe UI"` | `QFont("Segoe UI", ...)` | ~100 |
| `FONT_FAMILY_MONO = "Consolas"` | `QFont("Consolas", ...)` | ~5 |
| `QT_MAX_SIZE = 16777215` | `setMaximumHeight(16777215)` | 5 (sidebar) |

**Note:** Adding tokens is the work of Phase 3 (which the user has forbidden in this Phase 2 audit-only mandate).

---

## 10. Compliance by Component

| Component | Compliance | Notes |
|---|---|---|
| Buttons | **100%** | All migrated to EnterpriseButton/IconButton |
| Dialogs | **97%** | 37/38 on EnterpriseDialog |
| Screens | **98%** | 176/178 on BaseScreen (2 licensing stragglers) |
| Tables (display) | **68%** | 45/66 use EnterpriseTable; 21 raw |
| Tables (entry) | **0%** | DataEntryGrid defined, 0 callers |
| Forms | **0%** | FormField defined, 0 callers; 360 raw widgets |
| State | **0%** | StateHelper defined, 0 callers; 15 local overrides |
| Navigation | **100%** | Single Sidebar, single NavigationHeader |
| Color tokens | **100%** | All hex values via COLOR_* |
| Font-size tokens | **97%** | 7 files use literal int |
| Border-radius tokens | **99%** | 1 file uses literal int |
| Spacing tokens | **88%** | ~30 inline CSS values |
| Border-width tokens | **0%** | Token category missing |
| Font family | **0%** | Token category missing |
| Widget dimensions | **30%** | Most use setFixed*/setMin* literally |

---

## 11. Audit Conclusion

**The design system foundation is strong (97-100% on 5 of 14 components), but the **form** and **state** systems are completely bypassed (0% compliance) despite being fully implemented.**

The 4 high-severity gaps that need immediate attention (without adding new tokens):
1. **StateHelper** — implemented, never wired; 15 files reimplement
2. **DataEntryGrid** — implemented, never used; 6 line-item tables use raw QTableWidget
3. **FormField / FormSection** — implemented, 360 raw form widgets bypass it
4. **21 raw QTableWidget** — should be EnterpriseTable or DataEntryGrid

**Recommended Phase 3 work (governance enforcement, not new design):**
1. Add `BORDER_WIDTH_*` and `FONT_FAMILY_*` token categories (the only genuinely missing tokens)
2. Adopt StateHelper in 15 finance screens
3. Adopt DataEntryGrid in 6 line-item tables
4. Adopt FormField in the top 10 worst offenders (the 10 files with 4+ raw form widgets each)
5. Delete 4 dead-code files (zero functional risk)
6. Resolve 4 class-name collisions (rename or consolidate)

**Total estimated effort:** ~25-30 hours of focused governance work. Zero functional risk to existing flows.
