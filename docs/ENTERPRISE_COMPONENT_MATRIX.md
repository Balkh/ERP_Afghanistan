# Enterprise Component Matrix — Phase UX.2 Layer 2

**Generated:** 2026-05-24  
**Authority:** Single source of truth for all enterprise UI primitives

---

## Official Component Registry

Every enterprise UI surface MUST use these components. No exceptions.

| Category | Component | File | Line | Inheritance | Variants | Style Authority |
|---|---|---|---|---|---|---|
| **Button** | `EnterpriseButton` | `ui/components/buttons.py` | 30 | `QPushButton` | PRIMARY, SECONDARY, SUCCESS, DANGER, WARNING, GHOST | `UIStyleBuilder.get_button_style()` |
| **Icon Button** | `IconButton` | `ui/components/buttons.py` | 162 | `EnterpriseButton` | Same as EnterpriseButton | `UIStyleBuilder.get_button_style()` |
| **Split Button** | `SplitButton` | `ui/components/buttons.py` | 191 | `QPushButton` | PRIMARY (dropdown) | Inline QSS |
| **Table** | `EnterpriseTable` | `ui/components/tables.py` | 225 | `QTableWidget` | Sorted, filtered, paginated, selectable | `UIStyleBuilder.get_table_style()` |
| **Editable Grid** | `DataEntryGrid` | `ui/components/tables.py` | 474 | `QTableWidget` | Lightweight line-item grid | `UIStyleBuilder.get_table_style()` |
| **Pagination** | `PaginationWidget` | `ui/components/tables.py` | 390 | `QWidget` | Page nav + page size | Inline |
| **Table Column** | `TableColumn` | `ui/components/tables.py` | 33 | NamedTuple | key, title, width, align, format | N/A |
| **Dialog Base** | `EnterpriseDialog` | `ui/components/dialogs.py` | 42 | `QDialog` | CONFIRM, ALERT, INPUT, CUSTOM | `UIStyleBuilder` constants via f-strings |
| **Confirm Dialog** | `ConfirmDialog` | `ui/components/dialogs.py` | 214 | `EnterpriseDialog` | Yes/No buttons | Delegates to EnterpriseDialog |
| **Alert Dialog** | `AlertDialog` | `ui/components/dialogs.py` | 254 | `EnterpriseDialog` | OK button | Delegates to EnterpriseDialog |
| **Loading Dialog** | `LoadingDialog` | `ui/components/dialogs.py` | 295 | `EnterpriseDialog` | Spinner + message | Delegates to EnterpriseDialog |
| **Notify (singleton)** | `NotificationManager` | `ui/components/notifications.py` | 189 | `QWidget` | INFO, SUCCESS, WARNING, ERROR | `_NOTIFICATION_STYLES` dict |
| **Notification Item** | `NotificationItem` | `ui/components/notifications.py` | 61 | `QWidget` | Title+message or message-only | `_NOTIFICATION_STYLES` dict |
| **Loading Overlay** | `LoadingOverlay` | `ui/components/loading_spinner.py` | 52 | `QWidget` | Animated spinner + text | `COLOR_*` tokens |
| **Loading Spinner** | `LoadingSpinner` | `ui/components/loading_spinner.py` | 8 | `QWidget` | Circular animated | QPainter |
| **KPI Card** | `KPICard` | `ui/components/kpi_cards.py` | 51 | `QFrame` | Color-coded border | `COLOR_*` tokens |
| **Mini Metric** | `MiniMetricCard` | `ui/components/kpi_cards.py` | 140 | `QFrame` | Compact stat display | `COLOR_*` tokens |
| **Status Badge** | `StatusBadge` | `ui/components/kpi_cards.py` | 195 | `QLabel` | SUCCESS, WARNING, DANGER, INFO | `_severity_color()` |
| **Form Section** | `FormSection` | `ui/components/forms.py` | — | `QWidget` | Grouped form fields | `FormSection` stylesheet |
| **State Helper** | `StateHelper` | `ui/components/state_helper.py` | 27 | `QWidget` | loading, empty, error states | `COLOR_*` tokens |
| **Card** | `_Card` | `ui/control_tower/financial_control_tower_screen.py` | 39 | `QFrame` | Reusable card | `COLOR_*` tokens |
| **Metric Row** | `_MetricRow` | `ui/control_tower/financial_control_tower_screen.py` | 62 | `QWidget` | Label + value | `COLOR_*` tokens |

---

## Forbidden Patterns

| Pattern | Reason | Replacement |
|---|---|---|
| `QPushButton()` directly | Bypasses button variant/style system | `EnterpriseButton(...)` |
| `QDialog` subclass | Bypasses EnterpriseDialog governance | `EnterpriseDialog(...)` subclass |
| `QWidget` for screen | Bypasses BaseScreen lifecycle | `BaseScreen`, `BaseFormScreen`, `BaseListScreen` |
| `setStyleSheet("""...{TOKEN}...""")` without `f` prefix | Token interpolation breaks | Add `f` prefix |
| Hardcoded hex colors | Bypasses ThemeEngine | `COLOR_*` tokens from `ui.constants` |
| `build_table_stylesheet()` direct call | Duplicates UIStyleBuilder | `UIStyleBuilder.get_table_style()` |
| `ui/theme/theme_manager.py` (any) | Deprecated | `theme/theme_engine.py:ThemeEngine` |
| `theme/theme_manager.py` (any) | Deprecated | `theme/theme_engine.py:ThemeEngine` |
| `theme/enterprise_styling.py` (any) | Deprecated | `theme/style_builder.py:UIStyleBuilder` |

---

## Style Authority Chain

```
ThemeEngine (theme/theme_engine.py)
  └── set_active_theme() in ui/constants.py
        └── COLOR_*, SPACING_*, TEXT_*, BORDER_* tokens
              └── UIStyleBuilder (theme/style_builder.py)
                    ├── get_button_style()    → EnterpriseButton
                    ├── get_table_style()     → EnterpriseTable, DataEntryGrid
                    ├── get_input_style()     → Form fields
                    ├── get_tab_style()       → Tab widgets
                    ├── get_card_style()      → Card widgets
                    ├── get_global_style()    → Application-wide QSS
                    └── get_badge_style()     → Badge widgets
              └── Component inline QSS        → Dialog, Notification, KPI, etc.
```

---

## Component Ownership

| Owner | Components |
|---|---|
| `ui/components/` | All 17 enterprise primitives (buttons, tables, dialogs, forms, notifications, kpi cards, state helper, loading spinner) |
| `ui/components/buttons.py` | `EnterpriseButton`, `IconButton`, `SplitButton` |
| `ui/components/tables.py` | `EnterpriseTable`, `DataEntryGrid`, `PaginationWidget`, `TableColumn` |
| `ui/components/dialogs.py` | `EnterpriseDialog`, `ConfirmDialog`, `AlertDialog`, `LoadingDialog` |
| `ui/components/notifications.py` | `NotificationManager`, `NotificationItem` |
| `ui/components/kpi_cards.py` | `KPICard`, `MiniMetricCard`, `StatusBadge` |
| `ui/components/forms.py` | `FormSection`, `EnterpriseForm`, `FormField` |
| `ui/components/state_helper.py` | `StateHelper` |
| `ui/components/loading_spinner.py` | `LoadingSpinner`, `LoadingOverlay` |

---

## Duplication Status Registry

| Duplicate | Status | Action Taken |
|---|---|---|
| `build_table_stylesheet()` (tables.py:55) vs `UIStyleBuilder.get_table_style()` (style_builder.py:185) | **RESOLVED** | `build_table_stylesheet()` now delegates to `UIStyleBuilder.get_table_style()` |
| `BaseDialogWidget` (base_widgets.py:247) vs `EnterpriseDialog` (dialogs.py:42) | **RESOLVED** | `BaseDialogWidget` removed (unused dead code) |
| `LoadingOverlay` (observability/widgets.py:289) vs (loading_spinner.py:52) | **RESOLVED** | Observability version now delegates to canonical component version |
| `theme/enterprise_styling.py` (whole file) | **RESOLVED** | Archived to `docs/archive/` |
| `theme/theme_manager.py` (whole file) | **RESOLVED** | Archived to `docs/archive/` |
| `ui/theme/theme_manager.py` (whole file) | **RESOLVED** | Archived to `docs/archive/` |
| Raw QPushButton in component code (13 instances) | **RESOLVED** | All replaced with `EnterpriseButton`/`IconButton` |
| 31 standalone QDialog subclasses vs EnterpriseDialog | **DOCUMENTED** | Phase UX.3 target |
| 30 screens inheriting from QWidget/QFrame vs BaseScreen | **DOCUMENTED** | Phase UX.3 target |
