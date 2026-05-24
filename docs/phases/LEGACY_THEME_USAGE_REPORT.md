# LEGACY THEME USAGE REPORT

## 1. LEGACY SYSTEM INVENTORY

| Component | Path | Status | Risk Level | Action |
|-----------|------|--------|------------|--------|
| ThemeManager (Legacy) | `frontend/theme/theme_manager.py` | LEGACY_SAFE | Low | Mark Deprecated / Remove later |
| ThemeManager (UI) | `frontend/ui/theme/theme_manager.py` | LEGACY_SAFE | Low | Mark Deprecated / Remove later |
| Enterprise Styling | `frontend/theme/enterprise_styling.py` | LEGACY_SAFE | Low | Mark Deprecated |

## 2. HARDCODED COLOR USAGE (VIOLATIONS)

| File | Line(s) | Usage | Classification |
|------|---------|-------|----------------|
| `ui/common/printable_invoice.py` | 147-155, 170-180 | HTML/PDF Styles | ACTIVE (Rendering dependency) |
| `ui/system/user_management_screen.py` | 72-82 | Manual Color Replacement | ACTIVE (Hidden styling logic) |
| `ui/components/tables.py` | 218-219 | Contrast Fallback | LEGACY_SAFE (Governance Exempt) |

## 3. AUDIT SUMMARY
- **ThemeManager**: No active production dependencies found in `main.py` or major screens.
- **Color Drift**: Minor drift found in specialized rendering components (Invoices).
- **Hidden Logic**: Found manual hex-to-token replacement in `user_management_screen.py`.
