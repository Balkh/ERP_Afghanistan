# UI Architecture Governance — Design System Reference

## Phase 16 — Architecture Freeze & Governance Layer

The ERP UI is now an **architecturally frozen, governed design platform**.  
No developer may bypass the system. All UI must derive from governed primitives and centralized tokens.

---

## 1. Design Token Usage

All visual styling derives from `frontend/ui/constants.py`.

### Color Tokens
| Category | Prefix | Example |
|---|---|---|
| Background | `COLOR_BG_*` | `COLOR_BG_SURFACE`, `COLOR_BG_DIALOG` |
| Text | `COLOR_TEXT_*` | `COLOR_TEXT_PRIMARY`, `COLOR_TEXT_MUTED` |
| Border | `COLOR_BORDER_*` | `COLOR_BORDER`, `COLOR_BORDER_FOCUS` |
| Semantic | `COLOR_PRIMARY`, `COLOR_SUCCESS`, etc. | — |
| Validation | `COLOR_VALID_*`, `COLOR_INPUT_*` | `COLOR_VALID_ERROR`, `COLOR_INPUT_SUCCESS` |
| Table | `TABLE_*` | `TABLE_BG_PRIMARY`, `TABLE_HEADER_TEXT` |
| Interaction | `COLOR_FOCUS_RING`, `COLOR_HOVER_OVERLAY` | — |

**Rule:** `"#xxxxxx"` is FORBIDDEN in all production screens.  
**Exception:** `ensure_contrast()` in `tables.py` — raw fallbacks for extreme contrast correction.

### Spacing Tokens
| Token | Value | Usage |
|---|---|---|
| `SPACING_XS` | 4px | Tight spacing, label-to-input gap |
| `SPACING_SM` | 8px | Form row padding, card padding |
| `SPACING_MD` | 12px | Between form sections |
| `SPACING_LG` | 16px | Section margins |
| `SPACING_XL` | 20px | Dialog padding |
| `SPACING_XXL` | 24px | Page margins |
| `SPACING_NONE` | 0px | Explicit zero spacing |
| `SPACING_6` | 32px | Large gaps |
| `MARGIN_PAGE` | 24px | Page-level margin |
| `MARGIN_CARD` | 20px | Card-level margin |

**Rule:** `setSpacing(10)` or `padding: 15px` with raw numbers is FORBIDDEN.

### Typography Tokens
| Token | Size | Weight | Usage |
|---|---|---|---|
| `TEXT_DISPLAY` | 32pt | 700 | Page titles |
| `TEXT_PAGE_TITLE` | 20pt | 600 | Section titles |
| `TEXT_CARD_TITLE` | 16pt | 700 | Card/group titles |
| `TEXT_SECTION_TITLE` | 14pt | 700 | Form section titles |
| `TEXT_BODY` | 12pt | 400 | Body text |
| `TEXT_BODY_SMALL` | 10pt | 400 | Subtitle text |
| `TEXT_LABEL` | 12pt | 700 | Labels, buttons |
| `TEXT_LABEL_SMALL` | 10pt | 500 | Small labels |
| `TEXT_TABLE` | 11pt | 400 | Table cell text |
| `TEXT_HELPER` | 9pt | 400 | Contextual helper text |
| `TEXT_ERROR` | 10pt | 400 | Validation messages |

**Rule:** `QFont("Arial", 14)` with hardcoded font name is FORBIDDEN.  
**Official font:** `Segoe UI` only. `Consolas` / `Courier New` only for code/monospace displays.

---

## 2. Button Standards

**Only `EnterpriseButton`**. No exceptions.

| Variant | Usage |
|---|---|
| `PRIMARY` | Primary action (Save, Submit, Confirm) |
| `SECONDARY` | Secondary action (Cancel, Back, Discard) |
| `SUCCESS` | Confirm/success actions |
| `DANGER` | Destructive actions (Delete, Remove) |
| `WARNING` | Warning/caution actions |
| `GHOST` | Subtle toolbar actions, links |

**Pattern (dialogs):**
```python
btn_layout = QHBoxLayout()
btn_layout.addStretch()
cancel = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
cancel.clicked.connect(self.reject)
ok = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
ok.clicked.connect(self.accept)
btn_layout.addWidget(cancel)
btn_layout.addWidget(ok)
layout.addLayout(btn_layout)
```

**Loading state:** Always use `set_loading(True)` for async operations.  
**FORBIDDEN:** `QPushButton`, `QToolButton`, `QDialogButtonBox`, `QCommandLinkButton`.

---

## 3. Form Composition

**Only `FormSection`** for grouping form fields.  
**Only `FormField`** for individual inputs with validation.

### Section Hierarchy
- `primary=True`: Critical identity sections (thicker title, full emphasis)
- `primary=False`: Secondary/regulatory sections (softer, visually demoted)

### 2-Column Grid
```python
section = FormSection("Identity", columns=2, primary=True)
section.add_field_pair("Name*:", name_widget, "Generic Name:", generic_widget,
                       required1=True, helper1="Full product name")
section.add_full_width("Description:", text_widget,
                       helper="Optional product description")
```

### Validation UX
```python
field.set_error("This field is required")    # Red border + message
field.set_success("Valid format")            # Green border + optional message
field.clear_error()                          # Reset to normal
```

**FORBIDDEN:** `QGroupBox` with custom layout, `QFormLayout` standalone, `QMessageBox` for validation.

---

## 4. Table Standards

**Only `EnterpriseTable`** for data display.  
**Only `DataEntryGrid`** for editable line items.

### Density Tiers
| Density | Row Height | Use Case |
|---|---|---|
| `"compact"` | 26px | Financial tables, dense data |
| `"medium"` | 32px | Standard operational tables (default) |
| `"relaxed"` | 40px | Touch/kiosk interfaces |

### Stylesheet
Always use `build_table_stylesheet()` — never inline table stylesheets.

```python
table = EnterpriseTable(columns, density="medium")
table.set_data(rows)
```

**FORBIDDEN:** `QTableWidget` standalone, `QTreeWidget` for tabular data, inline `setStyleSheet()` on tables.

---

## 5. Dialog Standards

**Only `EnterpriseDialog`** (or its subclasses) for dialog windows.  
**Only `ConfirmDialog`** / `InputDialog` for standard interactions.

### Dialog Width Governance
| Constant | Value | Usage |
|---|---|---|
| `DIALOG_WIDTH_FORM_MIN` | 400px | Minimum comfortable width |
| `DIALOG_WIDTH_FORM_PREFERRED` | 520px | Default form dialog width |
| `DIALOG_WIDTH_MAX` | 720px | Maximum comfortable width |

### Dialog Pattern
```python
class MyDialog(EnterpriseDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dialog Title")
        self.setup_body()
        self.setup_footer(cancel_callback=self.reject, save_callback=self.accept)
```

**FORBIDDEN:** `QDialog` subclass without width governance, `QMessageBox` for workflow interactions.

---

## 6. Empty State Standards

**Only `StateHelper`** for loading/empty/error states.

### Pattern
```python
helper = StateHelper(layout)
helper.show_empty(
    "No invoices found",
    "Create your first invoice to get started",
    actions=[("New Invoice", self.create_invoice)]
)
helper.show_error(
    "Failed to load data",
    on_retry=self.refresh,
    actions=[("Settings", self.open_settings)]
)
helper.show_loading("Loading invoices...")
helper.hide()
```

**Standards:**
- Geometric indicator bar (3px thin line) — no emoji, no icons, no clipart
- Action suggestion buttons for primary workflow progression
- Context-aware subtitle describing what the user should do

**FORBIDDEN:** Emoji icons, static QLabel empty messages, clipart or decorative illustrations.

---

## 7. Notification Standards

**Use `NotificationManager`** for all transient notifications. Single global instance via `get_notification_manager()`.

Two API modes available:

### Simple Message Mode (Toast-style)
```python
from ui.components.notifications import show_success, show_error, show_warning, show_info

show_success(WORKFLOW_SAVED.format("Invoice #001"))
show_error("Payment processing failed")
show_warning("Batch is nearing expiry")
show_info("Background sync completed")
```

### Title+Message Mode (Notification-style)
```python
from ui.components.notifications import notify_success, notify_error, notify_warning, notify_info

notify_success("Sync Complete", "All records uploaded successfully")
notify_error("Payment Failed", "Transaction declined by processor")
```

### Global Manager Access
```python
manager = get_notification_manager()
manager.show_success("Direct access")
manager.notify_success("Title", "Message")
manager.clear_all()
```

### Adaptive Text Contrast
- Success/Error: White text on colored background (COLOR_TEXT_ON_SUCCESS / COLOR_TEXT_ON_DANGER)
- Warning: Dark text on amber background (COLOR_TEXT_ON_WARNING)
- Info: Dark text on blue background (COLOR_TEXT_ON_PRIMARY)

### Keyboard & Accessibility
- **Escape key** dismisses any notification
- **QAccessible.Alert** event on close for screen reader announcements

### Workflow Reassurance Messages
```python
from ui.components.notifications import WORKFLOW_SAVED, WORKFLOW_UPDATED, WORKFLOW_CREATED, WORKFLOW_DELETED, WORKFLOW_POSTED, WORKFLOW_PAID, WORKFLOW_CANCELLED, WORKFLOW_EXPORTED

show_success(WORKFLOW_SAVED.format("Invoice"))
show_success(WORKFLOW_UPDATED.format("Product"))
```

### Queue Management
- Max **5** visible notifications (oldest auto-evicted)
- Auto-hide: success/info 4s, warning 5s, error 8s
- `PERMANENT` duration (0) for persistent notifications

**FORBIDDEN:** `QMessageBox` for success/error feedback, `QStatusBar` for transient messages, raw `QPushButton` for notification close buttons.

---

## 8. Navigation Standards

### Sidebar
- Single instance with collapsible groups
- Active item tracking via `set_active_item(index)`
- Page navigation via `page_changed` signal
- Role-based filtering via `apply_role_filter()`

### Navigation Header
- Back/Home/Close buttons
- Breadcrumb trail for context
- Fixed height (60px)

**FORBIDDEN:** `QListWidget` for navigation, custom sidebar implementations.

---

## 9. Focus & Accessibility

- All interactive elements MUST have `setFocusPolicy(StrongFocus)`
- Focus ring via `COLOR_FOCUS_RING` + `outline: 2px solid`
- Button focus handled in `EnterpriseButton._apply_variant_style()`
- Table navigation via keyboard: Arrow keys + Enter to select

**FORBIDDEN:** Disabling focus on interactive elements, custom focus indicators.

---

## 10. Performance Governance

### FORBIDDEN
- Heavy animations (opacity, position transitions >200ms)
- Expensive repaints (frequent `setStyleSheet` calls)
- Blur effects / glassmorphism / backdrop-filter
- Excessive drop shadows
- Transparency-heavy rendering
- Animation loops in painting events

### REQUIRED
- Lightweight transitions only (fade: 500ms max, hover: 100ms)
- Low GPU usage (QPainter arc, not animated GIFs)
- Smooth keyboard navigation
- Stable scrolling under load

---

## 11. Governance Exceptions

| File | Exception | Reason |
|---|---|---|
| `tables.py` (ensure_contrast) | Raw hex fallback colors | Runs before token load; contrast correction utility |
| `printable_invoice.py` | Raw hex colors in HTML | Generates standalone HTML, not Qt UI |
| `user_management_screen.py` | Hex strings in .replace() | Migration pattern — maps old hex to COLOR_* tokens |
| `rendering/` module | BadgeRenderer kept | Backward compatibility; no new usage allowed |

---

## 12. Violation Severity Model

| Severity | Code | Meaning |
|---|---|---|
| CRITICAL | GOV-001, GOV-002 (QPushButton/QDialogButtonBox), GOV-007 | Architecture violation — must fix immediately |
| HIGH | GOV-002 (other), GOV-003, GOV-008 | Standard violation — plan to fix in current sprint |
| MEDIUM | GOV-004, GOV-005, GOV-006 | Quality violation — fix during cleanup cycles |
| LOW | Naming, minor token misuse | Improvement opportunity |

---

## 13. Running the Governance Scanner

```bash
# Full scan
python -m ui.governance.audit_scanner scan

# Full scan with report
python -m ui.governance.audit_scanner scan --save

# Generate detailed report
python -m ui.governance.audit_scanner report
```

### Running Consistency Audit
```python
from ui.governance import ConsistencyEngine
engine = ConsistencyEngine()
report = engine.run_and_report()
print(f"Consistency score: {report.overall_score:.0%}")
```
