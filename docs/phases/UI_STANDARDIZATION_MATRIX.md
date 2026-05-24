# UI Standardization Matrix - Phase 37

## UI Component Standards

### 1. KPI & Metrics
- **Standard**: `ui.components.kpi_cards.KPICard`
- **Mini Standard**: `ui.components.kpi_cards.MiniMetricCard`
- **Status Indicator**: `ui.components.kpi_cards.StatusBadge`
- **Rule**: All dashboards must use `KPICard` for primary metrics. No inline-styled frames allowed.

### 2. Data Tables
- **Standard**: `ui.components.tables.EnterpriseTable`
- **Columns**: Must use `TableColumn` definitions.
- **Styling**: Theme-aware headers, hover states, and zebra-striping enforced.

### 3. Dialogs & Modals
- **Standard**: `ui.components.dialogs.EnterpriseDialog`
- **Buttons**: Must use `EnterpriseButton` with standard variants (PRIMARY, SECONDARY, DANGER).
- **Rule**: No bare `QDialog` usage. Must inherit from `EnterpriseDialog`.

### 4. Notifications
- **Standard**: `ui.components.notifications.NotificationManager`
- **Usage**: `show_success()`, `show_warning()`, `show_error()`.
- **Rule**: No bare `QMessageBox` for non-critical alerts.

### 5. Loading & Progress
- **Standard**: `ui.components.loading_spinner.LoadingOverlay`
- **Standard**: `ui.components.base_widgets.StandardProgressBar`

---

## Architecture Lockdown Rules

### 1. Style & Theme
- **Rule**: NO hardcoded hex colors in `.py` files.
- **Enforcement**: Must use `COLOR_*` tokens from `ui.constants`.
- **Theme**: Unified `ThemeEngine` is the single source of truth for UI colors.

### 2. Layouts
- **Rule**: Must use `SPACING_*` and `MARGIN_PAGE` constants for layouts.
- **Constraint**: Fixed sizes are forbidden except for icons and specific sidebars.

### 3. Navigation
- **Standard**: `MainWindow.navigate_to(page_id)`
- **Standard**: `LazyScreenManager` for all main screens.
- **Rule**: NO manual `QStackedWidget.setCurrentIndex()` calls outside of `MainWindow`.

---

## Cleaned Components (Phase 37)
- **Removed**: `frontend/ui/rendering/` (Speculative renderer).
- **Removed**: `frontend/ui/cognitive/` (Abandoned dashboard).
- **Standardized**: Observability widgets now inherit from `ui.components`.
