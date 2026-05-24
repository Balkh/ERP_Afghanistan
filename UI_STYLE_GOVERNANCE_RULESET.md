# UI STYLE GOVERNANCE RULESET

## 1. MANDATORY STYLING RULES

| Rule ID | Rule Name | Description | Authority |
|---------|-----------|-------------|-----------|
| **STYLE-01** | Abstraction Requirement | All UI styling MUST be generated via `UIStyleBuilder`. | `frontend/theme/style_builder.py` |
| **STYLE-02** | Token-Only Colors | Direct use of `#hex` or `COLOR_*` constants in `setStyleSheet` is forbidden. | `ui/constants.py` |
| **STYLE-03** | Semantic Role Selection | Components must request styles by semantic role (e.g. `title`, `success`, `ghost`). | `UIStyleBuilder` |
| **STYLE-04** | Theme Engine Authority | Theme switching is ONLY allowed through `ThemeEngine`. | `theme/theme_engine.py` |

## 2. FORBIDDEN PRACTICES

- ❌ **Inline f-strings**: `setStyleSheet(f"background: {COLOR_BG}")` is strictly prohibited.
- ❌ **Hardcoded Hex**: Any usage of `#[0-9a-fA-F]{6}` in UI code will trigger a governance violation.
- ❌ **Local Overrides**: Ad-hoc style overrides inside business screens are forbidden.
- ❌ **Legacy Fallbacks**: Usage of `ThemeManager` or `EnterpriseStyling` (Legacy) is blocked.

## 3. NEW STYLE PROCEDURE

If a new UI pattern is required:
1. Define new tokens in `ui/constants.py` (if needed).
2. Add a new abstraction method to `UIStyleBuilder`.
3. Call the new method from the UI component.

## 4. AUTOMATED ENFORCEMENT (Planned)
- CI check for `setStyleSheet(f"` patterns.
- Grep-based audit for raw hex values in `.py` files.
