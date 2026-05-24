# Component Standardization Report — Phase UX.3 Layer 5

**Generated:** 2026-05-24

---

## BaseScreen Standardization

### Standard Features Now Available to 30 Screens
- `screen_shown` / `screen_hidden` lifecycle signals
- `load_data()` / `refresh_data()` lifecycle contract
- `set_loading()` / `show_error()` / `show_empty()` state management
- `state_changed` signal for UI reactivity
- `set_api_client()` / `get_api_client()` client injection
- `set_navigation_manager()` / `navigate_to()` navigation contract
- `cache_data()` / `get_cached_data()` in-memory caching
- `set_auto_refresh()` managed timer support
- `screen_id` property for identification
- `_on_screen_shown()` / `_on_screen_hidden()` lifecycle hooks (no-op by default — preserves existing init-based loading)

### Migration Pattern Validated
```python
# Before
class MyScreen(QWidget):
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self.setup_ui()

# After
class MyScreen(BaseScreen):
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="my_screen")
        self.api_client = api_client or APIClient()
        self.setup_ui()

    def _on_screen_shown(self):
        # Override to prevent auto-load if data loaded in __init__
        pass
```

## EnterpriseDialog Standardization

### Standard Features Now Available to 4 Dialog Subclasses
- Width governance (DIALOG_WIDTH_MIN/MIN/MAX)
- Standard header with title
- Standard bottom-anchored button area
- Token-based spacing (MARGIN_CARD, SPACING_MD/SM)
- Themed background (COLOR_BG_DIALOG, COLOR_HEADER_DARK)
- `set_content()` / `set_title()` API
- `get_result()` / `set_result()` result contract
- ESC handling via Qt.WindowType.CloseButtonHint

### Migration Pattern Validated
```python
# Before
class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dialog")
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        # ... content ...

# After
class MyDialog(EnterpriseDialog):
    def __init__(self, parent=None):
        super().__init__("Dialog", DialogType.CUSTOM, parent)
        content = self._build_content()
        self.set_content(content)

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # ... content ...
        return widget
```

## Component Usage Metrics

| Component | Used By | Replaced |
|-----------|---------|---------|
| EnterpriseTable | 38 active screens | — |
| EnterpriseButton | All screens | 15 raw QPushButton remaining |
| FormSection | ~8 form screens | — |
| SectionHeader | ~15 screens | 2 definitions (duplicate, merged in UX.2) |
| MiniMetricCard | ~20 screens | — |
| ScreenStateHelper | ~10 screens | — |
| EnterpriseDialog | 4 dialog classes | 30 QDialog remaining |
| ConfirmDialog | ~10 call sites | — |
| AlertDialog | ~5 call sites | — |
| LoadingSpinner / LoadingOverlay | ~8 screens | Consolidated in UX.2 |

## Recommendation Summary

| Action | Target | Effort | Impact |
|--------|--------|--------|--------|
| Migrate accounting screens to BaseScreen | 6 files | MEDIUM | HIGH |
| Migrate simple dialogs to EnterpriseDialog | 7 files | LOW | MEDIUM |
| Remove remaining hardcoded hex | 9 files | LOW | MEDIUM |
| Replace remaining raw QPushButton | ~15 instances | LOW | LOW |
| Migrate complex screens to BaseScreen | 7 files | HIGH | HIGH |
| Migrate complex dialogs to EnterpriseDialog | 14 files | HIGH | HIGH |
