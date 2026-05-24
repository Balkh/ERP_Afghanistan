# UI STYLE USAGE REPORT

## 1. STYLE ABSTRACTION AUDIT

| Classification | Description | Count |
|----------------|-------------|-------|
| **GOVERNED** | Using centralized abstraction (e.g. `build_table_stylesheet`) | ~5% |
| **PARTIALLY_GOVERNED** | Using `ui.constants` tokens but inline `setStyleSheet(f"""...""")` | ~90% |
| **UNGOVERNED** | Using hardcoded hex values or local styling logic | ~5% |

## 2. KEY VIOLATIONS

### Inline Style Construction (PARTIALLY_GOVERNED)
92+ files found in `frontend/ui` using `setStyleSheet(f"""...""")`.
Examples:
- `ui/components/buttons.py`
- `ui/components/forms.py`
- `ui/main_window.py`
- `ui/sidebar.py`
- `ui/system/user_management_screen.py`

### Hardcoded Logic Drift
Components like `PrintableInvoice` and `UserManagementScreen` (previously) had manual color replacement or hardcoded hex values.

## 3. RECOMMENDATION
Create a centralized `UIStyleBuilder` in `frontend/theme/style_builder.py` to abstract all CSS generation. UI components should only request styles by semantic role (e.g. `get_button_style("primary")`).
