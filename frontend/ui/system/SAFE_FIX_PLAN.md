# Phase 6 — System UI/UX Safe Fix Plan

**Target**: `frontend/ui/system/` (21 files, 117 issues)
**Strategy**: Fix one batch at a time. Each batch is self-contained with no external dependencies. All changes are surgical — zero architecture changes, zero new features, zero behaviour changes beyond restoring intended behaviour.

---

## Batch 0 — Settings Screen Crash (P0)

### 0.1 `settings_screen.py:25-31` — Missing `_setup_ui()` call
**Fix**: Add `self._setup_ui()` call immediately before `self._load_settings()` in `__init__`.

```python
# Before
self._load_settings()

# After
self._setup_ui()
self._load_settings()
```

### 0.2 `settings_screen.py:277` — Name-mangled unused variable
**Fix**: Remove the line (variable is never read).
```python
# Remove:
__currency_ok = self._save_company_currency()
```

### 0.3 `settings_screen.py:353-362` — on_show() AttributeError
**Fix**: Resolved automatically by 0.1 — `_setup_ui()` creates all referenced widgets.

**Validate**: Navigate to Settings screen → should render full UI without crash.

---

## Batch 1 — Audit Screen Crashes (P0)

### 1.1 `audit_screen.py:60,109` — `datetime.date.addDays()` crash
**Fix**: Replace `datetime.now().date()` with `QDate.currentDate()`.
```python
# Line 60 — Before
self.from_date.setDate(datetime.now().date().addDays(-7))
# After
self.from_date.setDate(QDate.currentDate().addDays(-7))

# Line 65 — Before
self.to_date.setDate(datetime.now().date())
# After
self.to_date.setDate(QDate.currentDate())

# Line 109 — Before
self.from_date.setDate(datetime.now().date().addDays(-7))
# After
self.from_date.setDate(QDate.currentDate().addDays(-7))

# Line 114 — Before
self.to_date.setDate(datetime.now().date())
# After
self.to_date.setDate(QDate.currentDate())
```

### 1.2 `audit_screen.py:114` — Undefined `self.status_label`
**Fix**: Either add `status_label` to `_setup_ui()` or replace the line with a StateHelper call.
```python
# Option A: Add to _setup_ui() before the header layout
self.status_label = QLabel()
self.status_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")

# Option B: Replace with StateHelper
self.state_helper.show_loading(self.content_area)  # content_area must exist
```
Recommended: **Option A** (minimal, preserves existing loading-text behaviour).

### 1.3 `audit_screen.py:191` — `on_show()` never called by BaseScreen
**Fix**: Rename `on_show` to `_on_screen_shown` (BaseScreen lifecycle hook).
```python
# Before
def on_show(self):
# After
def _on_screen_shown(self):
```

### 1.4 `audit_screen.py:87` — Export button unconnected
**Fix**: Add click handler.
```python
# Add after export_btn definition:
self.export_btn.clicked.connect(self._export_csv)
```

**Validate**: Navigate to Audit screen → filters load with valid dates, no crash, data table populates, Export button works.

---

## Batch 2 — Fixed Assets OOB Column (P0)

### 2.1 `fixed_assets_screen.py:218` — Column index 8 on 8-column table
**Fix**: Change column index from 8 to 7, or add the column first.
```python
# Before
self.assets_table.setColumnCount(7)
# After
self.assets_table.setColumnCount(8)
headers = ["Asset Code", "Name", "Category", "Purchase Date", "Cost", "Depreciation", "Book Value", "Status"]
```

Then ensure headers include an "Actions" column (or reduce the setCellWidget index).

**Better fix**: Since the 7 declared headers map to columns 0-6, and the View button is designed for column 8 (index 7), add column 7:
```python
# In _setup_ui(), change to:
self.assets_table.setColumnCount(8)
self.assets_table.setHorizontalHeaderLabels([
    "Asset Code", "Name", "Category", "Purchase Date",
    "Cost", "Depreciation", "Book Value", "Actions"
])
```
The `setCellWidget(row, 8, btn)` on the old line 218 becomes `setCellWidget(row, 7, btn)` — but since we're now at 8 columns, index 7 is valid.

**Validate**: Assets table renders View button in every row.

---

## Batch 3 — AlertDialog Arg-Order Bugs (BUG, 15 occurrences)

### 3.1 `licensing_screen.py:139,143,145`
Fix every `AlertDialog.info/warning/error(self, title, msg)` → `AlertDialog.info/warning/error(title, msg, self)`.

**Pattern for all 15 occurrences**:
```python
# Before (WRONG — parent as first arg)
AlertDialog.info(self, "Success", msg)
AlertDialog.warning(self, "Error", msg)
AlertDialog.error(self, "Error", str(e))

# After (CORRECT — parent as last arg)
AlertDialog.info("Success", msg, self)
AlertDialog.warning("Error", msg, self)
AlertDialog.error("Error", str(e), self)
```

### 3.2 `licensing_screen.py`
- L139: `AlertDialog.info(self, "Success", msg)`
- L143: `AlertDialog.warning(self, "Error", msg)`
- L145: `AlertDialog.warning(self, "Error", str(e))`

### 3.3 `role_management_screen.py:262-265`
```python
# Before
ConfirmDialog.confirm(self, "Delete Role", message)
# After
ConfirmDialog.confirm("Delete Role", message, self)
```

### 3.4 `company_profile_screen.py` (10 occurrences)
- L136: `AlertDialog.warning(self, "Error", msg)`
- L168: `AlertDialog.info(self, "Success", msg)`
- L169: `AlertDialog.warning(self, "Error", msg)`
- L171: `AlertDialog.error(self, "Error", str(e))`
- L176: `AlertDialog.warning(self, "Error", msg)`
- L192: `AlertDialog.warning(self, "Error", msg)`
- L195: `AlertDialog.warning(self, "Error", msg)`
- L207: `AlertDialog.info(self, "Success", msg)`
- L209: `AlertDialog.warning(self, "Error", msg)`
- L211: `AlertDialog.error(self, "Error", str(e))`

### 3.5 `invoice_template_manager.py` (2 occurrences)
- L204: `AlertDialog.info(self, "Success", msg)`
- L207: `AlertDialog.error(self, "Error", str(e))`

**Validate**: Trigger each dialog path → correct title and message displayed, dialog modal to correct parent.

---

## Batch 4 — Backup State Badge (BUG)

### 4.1 `backup_screen.py:548` — Wrong layout index
**Fix**: Change `itemAt(3)` to `itemAt(2)`.
```python
# Before
existing = self.layout().itemAt(3)
# After
existing = self.layout().itemAt(2)
```

**Validate**: Restore state transitions visibly update the badge.

---

## Batch 5 — Intelligence Hub Risk Colors (P1)

### 5.1 `intelligence_hub_screen.py:256` — COLOR_DANGER for both CRITICAL and HIGH
**Fix**: Use `COLOR_WARNING` for HIGH risk level.
```python
# Before
color = COLOR_DANGER
# After
color = COLOR_DANGER if risk_level == "CRITICAL" else COLOR_WARNING
```
Or restructure the if-chain:
```python
if risk_level == "CRITICAL":
    color = COLOR_DANGER
elif risk_level == "HIGH":
    color = COLOR_WARNING
elif risk_level == "MEDIUM":
    color = COLOR_INFO
```
(Keep existing MEDIUM and LOW colour assignments.)

**Validate**: CRITICAL items render in red, HIGH items in orange/warning colour.

---

## Batch 6 — Dead Buttons (P1)

### 6.1 `fixed_assets_screen.py:99` — dispose_btn unconnected
**Fix**: Add click handler.
```python
self.dispose_btn.clicked.connect(self._dispose_asset)
```
Add stub method if one doesn't exist:
```python
def _dispose_asset(self):
    AlertDialog.info("Dispose Asset", "Disposal workflow coming soon.", self)
```

### 6.2 `audit_screen.py:87` — Export button unconnected
Already covered in Batch 1.4.

**Validate**: Dispose and Export buttons produce user feedback when clicked.

---

## Batch 7 — Dead Code Duplication (P2)

### 7.1 `backup_screen.py:29-129` — 3 duplicated widget classes
**Strategy**: Replace private class definitions with imports from `backup_widgets.py`.

```python
# Remove lines 29-129 entirely (3 class definitions)
# Add to imports section at top:
from .backup_widgets import StatusIndicator, WarningBanner, RestoreStateBadge
```

Then rename all usages:
- `_StatusIndicator(` → `StatusIndicator(`
- `_WarningBanner(` → `WarningBanner(`
- `_RestoreStateBadge(` → `RestoreStateBadge(`

### 7.2 `user_management_screen.py:244-463` — UserDialog duplication
**Strategy**: Remove inline `UserDialog` class, import from `user_dialog.py`.

```python
# Remove lines 244-463 entirely
# Add to imports:
from .user_dialog import UserDialog
```
Ensure `user_dialog.py:UserDialog` has the same API. If not, reconcile.

**Validate**: Backup screen widgets render identically. User dialog opens and functions identically.

---

## Batch 8 — Orphaned Files (P2)

### 8.1 `backup_helpers.py`
**Strategy**: Remove unused imports (`EnterpriseButton`, `ButtonVariant`, `ButtonSize`). Keep the file as it may be used by test files or planned features. If confirmed dead (nothing imports it), delete.

### 8.2 `user_dialog.py`
**Strategy**: After Batch 7.2, it becomes the canonical definition. No action needed beyond ensuring it's imported by `user_management_screen.py`.

**Validate**: `grep -r "from.*backup_helpers\|import.*backup_helpers" frontend/` returns nothing → dead.

---

## Batch 9 — BaseScreen Inheritance (P2, 5 screens)

### 9.1 `control_center_screen.py`
### 9.2 `integrity_screen.py`
### 9.3 `drift_intelligence_screen.py`
### 9.4 `workflow_intelligence_screen.py`
### 9.5 `correlation_screen.py`

All 5 follow the same pattern — inherit `QWidget`, hardcode `font-size: 20px` in header stylesheet, assign unused `_api_client`.

**Pattern fix per file**:
```python
# Before
class ControlCenterScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._api_client = APIClient()
        self._setup_ui()

    def _build_header(self):
        header = QLabel("Title")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a1a2e;")

# After
from ui.screens.base_screen import BaseScreen

class ControlCenterScreen(BaseScreen):
    screen_id = "control_center"

    def __init__(self, parent=None):
        self._api_client = APIClient()
        super().__init__(parent, screen_id=self.screen_id)
        self._setup_ui()

    def _build_header(self):
        header = QLabel("Title")
        header.setStyleSheet(f"font-size: {TEXT_PAGE_TITLE}pt; font-weight: {FONT_WEIGHT_BOLD}; color: {COLOR_TEXT_PRIMARY};")
```

**Detailed changes per file**:

| Before | After |
|--------|-------|
| Import `QWidget` from PySide6 | No change needed (BaseScreen extends QWidget anyway) |
| Import `QFont` from PySide6.QtGui | Add `BaseScreen` import from `ui.screens.base_screen` |
| Import `SPACING_*`, `MARGIN_*` but not `FONT_WEIGHT_BOLD` | Add `FONT_WEIGHT_BOLD` to import if not present |
| `class Foo(QWidget)` | `class Foo(BaseScreen)` |
| `super().__init__(parent)` | With `screen_id` kwarg |
| Remove unused `Qt` import | Optional |
| Stylesheet `'font-size: 20px; font-weight: bold'` | `f'font-size: {TEXT_PAGE_TITLE}pt; font-weight: {FONT_WEIGHT_BOLD}'` |

**Validate**: Each screen loads in the sidebar without error, header renders with correct semantic styling, theme switching (if applicable) works.

---

## Batch 10 — Unused Imports (P2, 13+ occurrences)

**Files with unused imports**:
| File | Unused Import |
|------|---------------|
| `licensing_screen.py:1` | `QFormLayout` |
| `licensing_screen.py:1` | `QHBoxLayout` |
| `settings_screen.py:5` | `QGroupBox` |
| `settings_screen.py:6` | `QFormLayout` |
| `user_dialog.py:4` | `QGroupBox` |
| `control_center_screen.py:2` | `Qt` |
| `integrity_screen.py:2` | `Qt` |
| `drift_intelligence_screen.py:2` | `Qt` |
| `workflow_intelligence_screen.py:2` | `Qt` |
| `correlation_screen.py:2` | `Qt` |
| `audit_screen.py:5` | `Qt` |
| `audit_screen.py:10` | `BORDER_RADIUS_MD` |
| `control_center_screen.py:3` | `TEXT_PAGE_TITLE` |

**Fix**: Remove each unused import from the import statement.

**Validate**: `python -c "import ast; ast.parse(open('file').read())"` for each file → no syntax errors.

---

## Batch 11 — Hardcoded Font-Weight in Stylesheets (P2, 14 occurrences)

Replace `'font-weight: bold'` or `'font-weight: 700'` with `f'font-weight: {FONT_WEIGHT_BOLD}'` in all stylesheet strings.

**Files**:
- `intelligence_hub_screen.py:49`
- `audit_screen.py:31,42`
- `analytics_workspace.py:33`
- `analytics_workspace.py:224` (if exists)
- `invoice_template_manager.py:42,174,175`
- 5 screens from Batch 9 (already covered)

**Fix pattern**:
```python
# Before
setStyleSheet("font-weight: bold; color: #333;")
# After
setStyleSheet(f"font-weight: {FONT_WEIGHT_BOLD}; color: {COLOR_TEXT_PRIMARY};")
```

---

## Batch 12 — Hardcoded Spacing Values (P2, 9 occurrences)

| File | Line | Value | Token |
|------|------|-------|-------|
| `user_management_screen.py` | 410 | `addSpacing(15)` | `SPACING_LG` (or nearest) |
| `user_dialog.py` | 197 | `addSpacing(15)` | `SPACING_LG` |
| `restore_confirm_dialog.py` | 63 | `setFixedHeight(60)` | — (custom height) |
| `company_profile_screen.py` | 72 | `setMaximumHeight(80)` | — (custom height) |
| `audit_screen.py` | 46,49 | `setMinimumWidth(150)` | — (custom width) |
| `audit_screen.py` | 56,61,66 | `setMinimumHeight(30)` | `INPUT_HEIGHT_MD` |

**Fix**: Where a matching token exists, replace. Where no token exists (custom heights), add a comment or leave as-is.

---

## Batch 13 — Spacing Arithmetic (P2, 6 occurrences)

| File | Lines | Expression | Fix |
|------|-------|------------|-----|
| `user_management_screen.py` | 37,71,97 | `SPACING_MD + SPACING_XS` (12+4=16) | `SPACING_LG` |
| `user_management_screen.py` | 356,357,413 | `SPACING_XL + SPACING_SM` (24+8=32) | `SPACING_XXL` |
| `entity_management_screen.py` | 22 | `SPACING_LG` for margins | `MARGIN_PAGE` |
| `fixed_assets_screen.py` | 32,73,74 | `SPACING_MD + SPACING_XS` | `SPACING_LG` |
| `intelligence_hub_screen.py` | 125 | `SPACING_LG + SPACING_XS` (16+4=20) | `SPACING_XL` |
| `intelligence_hub_screen.py` | 142 | `SPACING_MD + SPACING_XS` (12+4=16) | `SPACING_LG` |

**Validate**: Visual spacing identical before and after (SPACING tokens are the exact same numeric values).

---

## Batch 14 — Raw QTableWidget → EnterpriseTable (P2, 5 occurrences)

### 14.1 `user_management_screen.py:184-203` — `populate_table()` uses raw QTableWidget API
**Fix**: Replace with `self.table.set_data(data)` where data is a list of dicts.

### 14.2 `fixed_assets_screen.py` — `assets_table` and `depreciation_table`
- L137: `categories_table = QTableWidget()` → migrate to EnterpriseTable
- L177: `depreciation_table = QTableWidget()` → migrate to EnterpriseTable
- L190: `setRowCount(0)` → `clear_all_rows()`
- L206-207: `insertRow() + setItem()` → `set_data()`

### 14.3 `audit_screen.py:115` — `self.table.setRowCount(0)` → `self.table.set_data([])`

---

## Batch 15 — Missing StateHelper (P2, 4 occurrences)

| File | Line | Issue | Fix |
|------|------|-------|-----|
| `intelligence_hub_screen.py` | 113 | Raw `QLabel("Loading...")` | `self.state_helper.show_loading(content_area)` |
| `entity_management_screen.py` | 124 | AlertDialog for errors | `self.state_helper.show_error(message)` then reload |
| `entity_management_screen.py` | 79 | `print()` for API error | `self.state_helper.show_error(message)` |
| `fixed_assets_screen.py` | 228 | No loading/error/empty states | Add StateHelper instance and use in load_data |

Each file needs `from ui.components.state_helper import StateHelper` added if not present.

---

## Batch 16 — Unused `_api_client` (P2, 5 screens)

**Files**: `control_center_screen.py`, `integrity_screen.py`, `drift_intelligence_screen.py`, `workflow_intelligence_screen.py`, `correlation_screen.py`

These 5 screens assign `self._api_client = APIClient()` in `__init__` but never use it.

**Fix**: Either remove the assignment, or keep it for future use with a `# noqa` comment. If keeping, at minimum use `_ = APIClient()` to signal intentional disuse.

---

## Batch 17 — Miscellaneous (P2)

### 17.1 `intelligence_hub_screen.py:42,358` — Duplicate UIStyleBuilder import
**Fix**: Remove local imports from `_setup_ui()` and `_refresh_overview_dashboard()`.

### 17.2 `intelligence_hub_screen.py:159` — Fragile stylesheet copy
```python
# Before
anomaly_box.setStyleSheet(status_box.styleSheet())
# After
anomaly_box.setStyleSheet("background: transparent; border: none; padding: 8px;")
```

### 17.3 `analytics_workspace.py:23` — `_init_api_client` before super()
**Fix**: Move API client init after `super().__init__()` is called.

### 17.4 `analytics_workspace.py:24` — Missing `screen_id`
**Fix**: Add `screen_id="analytics_workspace"` to `super().__init__()`.

### 17.5 `audit_screen.py:166` — `print()` instead of logging
**Fix**: Replace with `logger.info(...)` or `logger.debug(...)`.

### 17.6 `audit_screen.py:126` — Hardcoded API URL
**Fix**: Replace `/api/audit/logs/` with `get_endpoint("audit_logs")` or a constant.

### 17.7 `restore_confirm_dialog.py:43` — Checksum truncation adds `...` for short values
**Fix**: Only append `...` when `len(value) > 32`.

### 17.8 `invoice_template_manager.py:153` — Wrong API response key
**Fix**: Change `response.get('id')` to `response.get('data', {}).get('id')`.

### 17.9 `fixed_assets_screen.py:157,160` — Hardcoded depreciation/book values
**Fix**: Derive from dynamic source or mark with `# TODO: compute dynamically`.

### 17.10 `fixed_assets_screen.py:139,143,179,183` — Duplicate `setAlternatingRowColors`
**Fix**: Remove the second call in each pair.

---

## Execution Order

| Batch | Risk | Files Touched | Dependencies |
|-------|------|---------------|-------------|
| 0 | P0 | 1 | None |
| 1 | P0 | 1 | None |
| 2 | P0 | 1 | None |
| 3 | BUG | 4 | None |
| 4 | BUG | 1 | None |
| 5 | P1 | 1 | None |
| 6 | P1 | 2 | None |
| 7 | P2 | 2 | None |
| 8 | P2 | 2 | None |
| 9 | P2 | 5 | None |
| 10-17 | P2 | ~15 | None |

Each batch is independent. Fix and test one at a time.
