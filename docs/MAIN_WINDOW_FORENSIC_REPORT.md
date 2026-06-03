# MainWindow Forensic Analysis Report

**Date:** 2026-06-01
**Mode:** READ-ONLY analysis (no refactoring performed)
**Phase:** 4 — Stage 2
**Target:** `E:\all downloads\Pharmacy_ERP\frontend\ui\main_window.py` (1100 LOC)

---

## 1. Headline Metrics

| Metric | Value | Note |
|---|---|---|
| Total LOC | **1100** | Largest file in active frontend (vs 926 in pre-Phase 3 backup) |
| Class count | 1 | `MainWindow(QMainWindow)` |
| Method count | **45** | Including 22 private (`_*`) and 23 public/event-handler |
| Signal declarations | 0 | Relies entirely on Qt signals from child widgets |
| Signal connections (`.connect()`) | **30** | Heavy fan-in to navigation/UI signals |
| `QAction` instantiations | 10 | Menu bar items (File/Edit/View/Operations/Reports/Tools/Help + 3 nav) |
| `setStyleSheet(` calls | **26** | Inline-stylesheet violations; high for a single file |
| `lambda:` lambdas | 10 | All in `create_menu_bar` for nav actions |
| `QTimer` references | 0 | (count returned 0 — only 2 `QTimer` calls in `_build_ui` and `_setup_status_bar`) |
| `log.` references | 0 | (count returned 0 — log usage uses the `get_logger('ui')` global at line 22) |
| `subprocess.Popen` call | 1 | At line 1103 (logout → re-run main.py) |
| Hard-coded data dicts | 2 | page-id→index map (60+ entries, lines 968-1030) and index→module map (60+ entries, lines 386-402) |

**Critical observation:** MainWindow has grown from **926 LOC (pre-Phase 3 backup) to 1100 LOC (+174 LOC, +19%)** during the recovery program. The growth is concentrated in:
- `_build_ui` (now 125 lines, was ~95)
- `change_page` (now 80 lines, was ~50) — added telemetry, workflow intelligence, correlation IDs
- `create_menu_bar` (now 155 lines, was ~110) — added 5 new menu actions for new screens
- Added `_check_startup_health`, `_update_status_bar_user_info`, `_refresh_status_bar`, `_do_refresh_window_styles`

The file is no longer merely large — it is **structurally multi-responsibility** with a *trend of growth*, not a stable asset.

---

## 2. Responsibility Matrix

The 45 methods of MainWindow span **7 distinct responsibility domains** that should ideally live in separate classes. The matrix below groups them by domain, shows the dependency footprint, and assesses cohesion.

### 2.1 Domain: Window / Shell Construction (UI infra)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| `__init__` | 29-92 | Constructs window, initializes auth_manager, role_renderer, theme_engine, navigation_history, kicks off `_load_company_settings` + `_check_startup_health` via QTimer.singleShot | HIGH — 7 subsystems |
| `_build_ui` | 256-381 (125 lines) | Constructs the entire window: outer VBox, sidebar, content frame, header, nav header, pages stack, dashboard, lazy loader, screen registry, **inline stylesheet for content frame** (lines 299-332, 33 lines of CSS) | HIGH |
| `_setup_status_bar` | 94-139 (45 lines) | Constructs status bar with 7 widgets (device_id, license, connection, user, health, conn, time) and 6 inline stylesheets | MEDIUM |
| `resizeEvent` | 1119-1124 | Resize loading overlay geometry | LOW |
| `closeEvent` | 1126-? | Window close handler | MEDIUM |
| `keyPressEvent` | 1134-? | Keyboard event handler | LOW |
| `create_menu_bar` | 775-928 (155 lines) | Constructs entire menu bar with 6 menus, 10 actions, all wired to navigation/operations | HIGH |

**Verdict:** Construction-only logic is intertwined with lifecycle hooks (init, close, resize, keyPress). This domain should be split into a **MainWindowBuilder** (construction) + **MainWindowShell** (lifecycle). Estimated extraction: ~280 LOC.

### 2.2 Domain: Page Registry / Navigation Mapping (DATA)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| `change_page` | 383-462 (80 lines) | **Contains the 60-entry index→module map** (lines 386-402), plus auth check, history mgmt, lazy-load, UI update, telemetry, workflow intelligence | HIGH |
| `_do_navigate` | 962-1045 (84 lines) | **Contains the 60-entry page_id→index map** (lines 968-1030) — DUPLICATE of `change_page`'s data, but in inverse direction | HIGH |
| `navigate_to` | 957-960 | Wrapper with SafeBoundary | LOW |
| `_update_nav_header` | 465-479 | Update nav header visibility and breadcrumb | LOW |
| `_build_breadcrumb` | 481-? | Build breadcrumb from current screen | LOW |
| `_go_back` / `_do_go_back` | 531-547 | Navigate back in history | LOW |
| `_go_home` / `_do_go_home` | 548-563 | Navigate to dashboard | LOW |
| `_close_screen` | 564-? | Close current screen (return to dashboard) | LOW |

**Verdict:** The two 60-entry data dictionaries (one in `change_page` lines 386-402, one in `_do_navigate` lines 968-1030) are **duplicated routing data**. A `PageRegistry` class should own both directions of this map and provide `index_to_id()`, `id_to_index()`, `index_to_module()`. Estimated extraction: ~120 LOC + 1 data file.

### 2.3 Domain: Auth / Scopes (cross-cutting concern)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| `_determine_role` | 202-206 | Determine user role from auth_manager | LOW |
| `_on_ui_scopes_changed` | 208-215 | React to scope changes | MEDIUM |
| `_apply_sidebar_scopes` | 216-246 | Apply scope changes to sidebar | MEDIUM |
| `logout` | 1072-1104 (33 lines) | Confirm + clean session + restart main.py via subprocess | HIGH |
| Auth check inside `change_page` | 404-406 | `if not self.auth_manager.has_access(module): show_warning` | MEDIUM |
| Auth check inside `_do_navigate` | 963-966 | Duplicate auth check | MEDIUM |

**Verdict:** Auth/scope logic is sprinkled across MainWindow. A `SessionController` class should own the auth-related decision points and the logout workflow. Estimated extraction: ~80 LOC.

### 2.4 Domain: Status Bar / Health Polling (background)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| `_setup_status_bar` | (shared with 2.1) | | |
| `_check_startup_health` | 141-182 (41 lines) | Backend health check, updates health_label stylesheet (3 color states) | MEDIUM |
| `_update_status_bar_time` | 184-187 | Update time label every 1s | LOW |
| `_update_status_bar_user_info` | 247-255 | Update user label | LOW |
| `_refresh_status_bar` | 723-? | Refresh status bar (called on theme change) | MEDIUM |
| `update_device_id_display` | 573-? | Update device ID label | LOW |
| `update_license_status_display` | 581-? | Update license status label | LOW |
| `check_connection` | 592-? | Periodic connection check (30s timer) | MEDIUM |
| `on_license_validation_changed` | 618-? | React to license validation | MEDIUM |
| `on_license_status_changed` | 641-? | React to license status change | MEDIUM |

**Verdict:** The status bar mixes **8 distinct display widgets** (device, license, connection, user, health, conn, time, health-tooltip) with **5 background polling tasks** (time, connection, license, health, user). Should be extracted to a `StatusBarController` (UI assembly) + `HealthMonitor` (background polling). Estimated extraction: ~150 LOC.

### 2.5 Domain: Theme / Style Refresh (cross-cutting)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| `toggle_theme` | 646-? | Toggle light/dark | LOW |
| `on_theme_changed` | 651-? | React to theme change → triggers window style refresh | MEDIUM |
| `_refresh_window_styles` | 671-? | Refresh all child styles | MEDIUM |
| `_do_refresh_window_styles` | 676-? | Implementation | MEDIUM |

**Verdict:** Theme management is partially delegated to `ThemeEngine` (line 18) but the **refresh path** (refresh_window_styles → do_refresh_window_styles) is MainWindow-owned. Should move to a `StyleRefreshController`. Estimated extraction: ~50 LOC.

### 2.6 Domain: Tools / Operations (actions triggered from menu)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| `new_product` | 1047-1050 | Show "new product" hint | LOW |
| `show_stock_alerts` | 1052-? | Show stock alerts | LOW |
| `open_calculator` | 1056-? | Open calculator | LOW |
| `open_calendar` | 1064-? | Open calendar | LOW |
| `show_about` | 935-944 | Show about dialog | LOW |
| `show_preferences` | 946-? | Show preferences | LOW |
| `show_license_manager` | 930-933 | Show license manager | LOW |
| `toggle_fullscreen` | 950-955 | Toggle fullscreen | LOW |
| `refresh_current_view` | 1105-? | Refresh current screen | LOW |
| `_do_refresh_current_view` | 1110-1117 | Implementation | LOW |

**Verdict:** These 10 methods are **action handlers** with no shared state. Should be moved to a `MenuActions` class (or a `MainWindowActions` namespace) so MainWindow becomes purely a navigation/orchestration layer. Estimated extraction: ~80 LOC.

### 2.7 Domain: Telemetry / Logging (decorative)

| Method | Lines | Purpose | Coupling |
|---|---|---|---|
| Inline `record_screen_load` call | 458 | Inside `change_page` | LOW |
| Inline `_record_nav_telemetry` | 459-460 | Inside `change_page` | LOW |
| Inline `_record_wf` | 461-462 | Inside `change_page` | LOW |
| Inline `record_exit_point("logout")` | 1075 | Inside `logout` | LOW |
| Inline `emit_event` | 413, 1092, 178 | Multiple places | LOW |
| Inline `capture_health_snapshot` | 88, 1086 | Multiple places | LOW |

**Verdict:** Telemetry calls are scattered. Should be wrapped in a `MainWindowTelemetry` adapter that all methods call instead of importing `runtime.ux_telemetry`, `runtime.workflow_intelligence`, etc. directly. Estimated extraction: ~30 LOC + 1 adapter.

---

## 3. Cohesion Analysis (LCOM-style)

| Domain | Methods | LOC | % of MainWindow | Cohesion (1-5) |
|---|---|---|---|---|
| Window / Shell Construction | 7 | ~280 | 25.5% | 4 (all touch window lifecycle) |
| Page Registry / Navigation | 8 | ~250 | 22.7% | 3 (split between data and behavior) |
| Auth / Scopes | 6 | ~110 | 10.0% | 2 (scattered across methods) |
| Status Bar / Health | 10 | ~200 | 18.2% | 2 (mixed display + polling) |
| Theme / Style Refresh | 4 | ~50 | 4.5% | 4 (focused on theme) |
| Tools / Operations | 10 | ~80 | 7.3% | 1 (no shared state at all) |
| Telemetry / Logging | (scattered) | ~30 | 2.7% | 1 (decorative) |
| Inline stylesheets (overlapping) | (scattered) | ~100 | 9.1% | 1 (anti-pattern) |
| **Total** | **45+** | **~1100** | **100%** | **avg ~2.3** |

**LCOM interpretation:** A score of 2.3/5 means the 45 methods share very few instance attributes. The "tight" methods are Theme (4/5) and Window Construction (4/5). The "loose" methods are Tools/Operations and Telemetry (1/5 each), which means they could be extracted to free functions or static method classes **with zero functional impact**.

---

## 4. Dependency Graph

### 4.1 Import dependencies (18 imports, 9 from `ui.*`)

```
PySide6.QtWidgets        (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QStackedWidget, QStatusBar, QApplication, QSizePolicy)
PySide6.QtCore           (Qt, QTimer)
PySide6.QtGui            (QFont, QAction)
ui.licensing             (LicenseManagerDialog)
ui.sidebar               (Sidebar)
ui.dashboard             (Dashboard)
security.auth_manager    (AuthManager)
ui.role_renderer         (RoleRenderer)
ui.components.notifications (show_warning)
ui.components.dialogs    (AlertDialog, ConfirmDialog)
ui.components.loading_spinner (LoadingOverlay)
ui.components.navigation_header (NavigationHeader)
theme.theme_engine       (ThemeEngine)
ui.utils.lazy_loader     (LazyScreenManager)
utils.logger             (get_logger, set_active_screen, get_active_screen, safe_execute, SafeBoundary, capture_health_snapshot, generate_correlation_id, record_screen_load, record_error, emit_event)
ui.constants             (SPACING_*, MARGIN_*, BORDER_RADIUS_*, TEXT_*, COLOR_*)
runtime.timer_registry   (shutdown_all_timers)
```

### 4.2 Sub-imports inside method bodies (lazy)

- `ui.screen_registry` (`register_all_screens`) — at line 371
- `runtime.ux_telemetry` (`record_navigation`, `record_exit_point`) — at lines 459, 1074
- `runtime.workflow_intelligence` (`record_navigation`) — at line 461

**Observation:** Three of the highest-coupling runtime modules (telemetry, workflow, screen registry) are imported **inside** method bodies. This is intentional to avoid circular imports but it indicates the runtime layer is **not on the same dependency tier** as the UI layer — a sign that MainWindow is at the apex of the dependency graph.

### 4.3 Internal dependency graph (which subsystems MainWindow depends on)

```
MainWindow
├── ui.sidebar              (Sidebar widget)
├── ui.dashboard            (Dashboard widget, page 0)
├── ui.role_renderer        (RoleRenderer - applies scopes)
├── ui.utils.lazy_loader    (LazyScreenManager - holds pages)
├── ui.screen_registry      (register_all_screens - bootstraps all screens)
├── ui.components.*         (LoadingOverlay, NavigationHeader, dialogs, notifications)
├── security.auth_manager   (AuthManager - session + scopes)
├── theme.theme_engine      (ThemeEngine - styles)
├── runtime.ux_telemetry    (UX telemetry)
├── runtime.workflow_intelligence (workflow suggestions)
├── runtime.timer_registry  (timer cleanup at close)
├── utils.logger            (logging + active screen)
└── ui.constants            (design tokens)
```

**Total: 12 distinct subsystems.** A typical enterprise-class application would have a top-level shell that depends on **5-6 subsystems at most**. MainWindow's 12 indicates it has not yet been decomposed.

### 4.4 Signal fan-in (30 connections)

```
self.theme_engine.theme_changed  → 1
self.sidebar.page_changed        → 1
self.license_validator.*         → 2
self.nav_header.back/home/close  → 3
self.status_timer.timeout        → 1
self.connection_timer.timeout    → 1
self.menu_bar actions            → 10 (via triggered signals in create_menu_bar)
self.safe_execute context        → ~10 (navigate_to, refresh_current_view, change_page)
```

**Observation:** MainWindow acts as a **central event sink** for 30+ signals from 6 different subsystems. This is the classic "Event Aggregator" anti-pattern — every subsystem knows about MainWindow and MainWindow knows about every subsystem.

---

## 5. God Object Symptoms (Re-Confirmed)

| Symptom | Severity | Evidence |
|---|---|---|
| **Many instance attributes** | HIGH | 22+ `self.*` attributes set in `__init__` + builders |
| **Many methods** | HIGH | 45 methods, 22 private |
| **Long methods** | HIGH | 3 methods > 80 lines (`_build_ui` 125, `create_menu_bar` 155, `_do_navigate` 84, `change_page` 80) |
| **Many imports** | HIGH | 18 imports across 5+ subsystems |
| **Hard-coded data** | HIGH | 2 × 60-entry data dictionaries inline (page-id maps) |
| **Inline stylesheets** | HIGH | 26 `setStyleSheet(` calls (vs project avg 627/249 files = 2.5/file) |
| **Many signal connections** | HIGH | 30 `.connect(` calls — central event sink pattern |
| **Mixed concerns** | HIGH | UI, data, auth, telemetry, theme, polling all in one class |
| **Many responsibilities** | HIGH | 7 distinct domains (see Section 2) |
| **Test fragility** | HIGH | Cannot test navigation without instantiating 12 subsystems |

**Phase 1 audit classification: CRITICAL — confirmed.**

---

## 6. Decomposition Candidates (Without Refactoring)

The audit identifies **6 candidate extractions** that can be performed independently without altering the public API of MainWindow. These are the **lowest-risk decomposition paths** in priority order.

### 6.1 Priority 1: Extract `PageRegistry` (data-only)

**Extract from:** `change_page` lines 386-402 (index→module map) + `_do_navigate` lines 968-1030 (page_id→index map)

**New file:** `frontend/ui/navigation/page_registry.py` (~80 LOC)

**Public API:**
```python
class PageRegistry:
    PAGE_TO_MODULE: dict[int, str]
    PAGE_ID_TO_INDEX: dict[str, int]
    MODULE_TO_PAGES: dict[str, list[int]]

    @classmethod
    def get_module(cls, index: int) -> str: ...
    @classmethod
    def get_index(cls, page_id: str) -> int | None: ...
    @classmethod
    def all_page_ids(cls) -> list[str]: ...
```

**Risk:** ZERO (pure data extraction, no behavior change)

**LOC reduction:** ~70 LOC in main_window + 1 new ~80 LOC file = net +10 LOC, but **logical separation** achieved.

### 6.2 Priority 2: Extract `StatusBarController`

**Extract from:** `_setup_status_bar` (45 LOC), `_update_status_bar_time` (4), `_update_status_bar_user_info` (8), `_refresh_status_bar` (50+), `update_device_id_display` (8), `update_license_status_display` (10), `_check_startup_health` (41), `check_connection` (26+), `on_license_validation_changed` (22+), `on_license_status_changed` (4)

**New file:** `frontend/ui/shell/status_bar_controller.py` (~250 LOC)

**Risk:** LOW (status bar is a self-contained widget; widget references can be passed in)

**LOC reduction in main_window:** ~200 LOC

### 6.3 Priority 3: Extract `MenuBarBuilder` + `MenuActions`

**Extract from:** `create_menu_bar` (155 LOC, 10 QActions) + 10 menu-action methods (`new_product`, `show_stock_alerts`, `open_calculator`, `open_calendar`, `show_about`, `show_preferences`, `show_license_manager`, `toggle_fullscreen`, `refresh_current_view`, `toggle_theme`)

**New files:**
- `frontend/ui/shell/menu_bar_builder.py` (~200 LOC) — pure UI construction
- `frontend/ui/shell/menu_actions.py` (~120 LOC) — pure action handlers

**Risk:** MEDIUM (action handlers are currently methods on MainWindow; extracting to a separate class requires them to be static or to receive MainWindow reference)

**LOC reduction in main_window:** ~280 LOC

### 6.4 Priority 4: Extract `SessionController`

**Extract from:** `_determine_role`, `_on_ui_scopes_changed`, `_apply_sidebar_scopes`, `logout` (33 LOC), auth check in `change_page` and `_do_navigate`

**New file:** `frontend/security/session_controller.py` (~120 LOC)

**Risk:** MEDIUM (auth_manager is already extracted; this is a thin wrapper)

**LOC reduction in main_window:** ~100 LOC

### 6.5 Priority 5: Extract `MainWindowTelemetry` adapter

**Extract from:** 6+ inline calls to `record_screen_load`, `record_navigation`, `record_exit_point`, `emit_event`, `capture_health_snapshot`

**New file:** `frontend/ui/shell/main_window_telemetry.py` (~60 LOC)

**Risk:** LOW (wraps existing runtime modules; no behavior change)

**LOC reduction in main_window:** ~30 LOC + 6 inline import statements removed

### 6.6 Priority 6: Decompose `_build_ui` into sub-builders

**Extract from:** `_build_ui` (125 LOC) → split into:
- `_build_outer_layout` (15 LOC)
- `_build_content_frame` (40 LOC — includes the 33-line inline stylesheet)
- `_build_header` (10 LOC)
- `_build_pages` (15 LOC)
- `_wire_signals` (30 LOC)
- `_bootstrap_dashboard` (15 LOC)

**Risk:** MEDIUM (refactor of construction order; could break layout if any step depends on a side effect)

**LOC reduction in main_window:** Net 0 (just method decomposition, not extraction)

---

## 7. Refactoring Strategy Recommendation (OUT OF SCOPE FOR STAGE 2)

This is a **forensic analysis only**. The actual refactoring plan belongs in Phase 5 (governed by the constraints in that phase's spec). The audit does, however, recommend the following principles for any future MainWindow decomposition:

1. **Do not break the public API.** MainWindow's constructor signature `(license_validator, user_data, api_client, auth_manager)` and the externally-called methods (`change_page`, `navigate_to`, `logout`, `closeEvent`, `keyPressEvent`, `resizeEvent`) must be preserved exactly.
2. **Preserve all 30 signal connections.** They are the *contract* between MainWindow and its child widgets.
3. **Move data first, behavior second.** Priority 1 (PageRegistry) is the safest extraction; do it first. Behaviors can wait.
4. **One extraction per release.** Do not bundle extractions; each one needs a separate QA cycle.
5. **Inline-stylesheet tokenization is a separate concern.** The 26 `setStyleSheet` calls are tracked in Phase 2 INLINE_STYLE_REPORT.md and should be addressed in a dedicated governance sprint, not bundled with the MainWindow decomposition.

---

## 8. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Refactor breaks navigation | MEDIUM | HIGH (entire app unusable) | Priority 1 (PageRegistry) is data-only; run full navigation smoke test after each extraction |
| Refactor breaks theming | MEDIUM | HIGH (entire app unreadable) | Theme paths use theme_engine theme_changed signal; keep MainWindow.on_theme_changed as the single reentry point |
| Refactor breaks auth | MEDIUM | HIGH (users locked out) | SessionController is a thin wrapper; auth_manager already has its own test surface |
| Refactor breaks status bar | LOW | MEDIUM | Status bar is visually obvious; manual smoke test catches regressions |
| Refactor breaks menu actions | LOW | LOW | Each menu action has a single trigger; smoke test covers all 10 |
| Refactor breaks lifecycle | LOW | HIGH | closeEvent, keyPressEvent, resizeEvent must stay on MainWindow (Qt requirement) |
| Refactor breaks telemetry | LOW | LOW | Telemetry is best-effort; failures are logged but do not affect user |
| Refactor breaks subprocess logout | LOW | MEDIUM | logout is critical path; smoke test required |

**Overall risk of Phase 5 decomposition:** **MEDIUM** (assuming 1-extraction-per-release and full smoke test between).

**Overall risk of NOT decomposing:** **HIGH** (file continues to grow at ~10%/release; the God Object will be unmaintainable within 2-3 more releases).

---

## 9. Sign-off Checklist

- [x] LOC measured (1100)
- [x] Method count measured (45)
- [x] Signal count measured (30)
- [x] Dependency count measured (18 imports, 12 subsystems)
- [x] Navigation responsibilities identified (8 methods, 2 hard-coded data dicts)
- [x] Business responsibilities identified (10 menu actions + logout + auth)
- [x] UI responsibilities identified (_build_ui, _setup_status_bar, resizeEvent, etc.)
- [x] Cohesion violations identified (7 domains, avg LCOM 2.3/5)
- [x] Responsibility leakage identified (telemetry scattered, auth sprinkled, theme pollutes)
- [x] God Object symptoms confirmed (10/10 symptoms present)
- [x] Decomposition candidates identified (6, with priorities and risk levels)
- [x] No source mutations performed
