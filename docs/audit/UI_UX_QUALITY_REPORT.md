# UI/UX QUALITY REPORT — Pharmacy ERP

## CRITICAL: 17 Token Interpolation Failures

All component stylesheets using `setStyleSheet("""...{TOKEN}...""")` with **non-f-strings** have silently broken styling. Tokens render as literal text; Qt ignores invalid QSS properties.

### File-by-File Breakdown

| File | Lines | Broken Tokens | Visual Impact |
|------|-------|---------------|---------------|
| `buttons.py` | 209-221 | `{COLOR_PRIMARY}`, `{COLOR_TEXT_ON_PRIMARY}`, `{SPACING_SM}`, `{BORDER_RADIUS_SM}`, `{COLOR_PRIMARY_HOVER}` | SplitButton completely unstyled — no primary color, no rounded corners, no hover state |
| `dialogs.py` | 91-95 | `{COLOR_BG_DIALOG}` | Dialog background never applies — always default system gray |
| `dialogs.py` | 133-142 | `{COLOR_BG_SECTION}`, `{COLOR_TEXT_PRIMARY}`, `{COLOR_HEADER_DARK}` | Dialog headers missing background/foreground colors |
| `dialogs.py` | 184-191 | `{COLOR_BG_MAIN}`, `{COLOR_FORM_FOOTER_BORDER}`, `{BORDER_RADIUS_LG}` | Dialog button areas missing styling |
| `kpi_cards.py` | 78-85 | `{COLOR_BG_ELEVATED}`, `{COLOR_BORDER}`, `{BORDER_RADIUS_LG}`, `{self._color}` | KPICard completely unstyled — no accent border, no elevation, no rounded corners |
| `kpi_cards.py` | 121-128 | Same tokens | KPICard color changes on value update never apply |
| `kpi_cards.py` | 158-164 | `{COLOR_BG_SURFACE}`, `{COLOR_BORDER}`, `{BORDER_RADIUS_MD}` | MiniMetricCard completely unstyled |
| `kpi_cards.py` | 213-223 | `{COLOR_BG_ELEVATED}`, `{SPACING_XS}`, `{SPACING_SM}`, `{BORDER_RADIUS_MD}`, `{TEXT_TABLE}`, `{color}` | StatusBadge completely unstyled — no background, no padding, no font |
| `state_helper.py` | 57-63 | `{COLOR_BG_SURFACE}`, `{COLOR_BORDER}`, `{BORDER_RADIUS_LG}` | Loading overlay container never styles |
| `state_helper.py` | 104-110 | Same tokens | Empty state container never styles |
| `state_helper.py` | 150-161 | `{COLOR_PRIMARY}`, `white`, `{BORDER_RADIUS_MD}`, `{SPACING_SM}`, `{COLOR_PRIMARY_HOVER}` | Empty state action buttons never get primary color |
| `state_helper.py` | 187-193 | `{COLOR_BG_SURFACE}`, `{COLOR_DANGER}`, `{BORDER_RADIUS_LG}` | Error state container never styles |
| `state_helper.py` | 229-239 | `{COLOR_PRIMARY}`, `white`, `{BORDER_RADIUS_MD}`, `{SPACING_SM}`, `{COLOR_PRIMARY_HOVER}` | Error state buttons never style |
| `navigation_header.py` | 42-67 | **10+ tokens**: `{COLOR_TEXT_PRIMARY}`, `{COLOR_BORDER}`, `{BORDER_RADIUS_SM}`, `{SPACING_6}`, `{TEXT_SECTION_TITLE}`, `{COLOR_BG_ELEVATED}`, `{COLOR_PRIMARY}`, `{COLOR_BORDER}`, `{COLOR_BORDER_LIGHT}`, `{COLOR_BG_ELEVATED}` | NavigationHeader completely unstyled — title, buttons, borders all wrong |
| `notifications.py` | 109-115 | `{bg_color}`, `{BORDER_RADIUS_LG}`, `{text_color}` | NotificationItem background/text colors never apply |
| `notifications.py` | 156-167 | `{text_color}`, `{TEXT_CARD_TITLE}`, `{BORDER_RADIUS_LG}` | Notification close button never styles |
| `loading_spinner.py` | 69-75 | `{COLOR_PRIMARY}`, `{TEXT_BODY}` | Loading overlay label color/size never apply |

---

## HIGH: Hardcoded Colors Bypassing the Design System

### `financial_control_tower_screen.py` — COMPLETE THEME BYPASS
Lines 22-36: Defines its own `COLORS` dict with 11 hardcoded hex values:
```python
COLORS = {
    'bg_main': '#1a1a2e', 'bg_card': '#16213e', 'bg_accent': '#0f3460',
    'text_primary': '#e0e0e0', 'text_secondary': '#a0a0a0',
    'success': '#4caf50', 'warning': '#ff9800', 'danger': '#f44336',
    'primary': '#2196f3', 'hover': '#2a2a4a', 'danger_dark': '#d32f2f'
}
```
Plus its own `SPACING` dict. Entirely bypasses `ui/constants.py` and `ThemeEngine`.

### `pos_screen.py` — 6 Hardcoded Hex Values
| Line | Value | Usage |
|------|-------|-------|
| 98 | `#0f1a14` | Text color |
| 442 | `#0f1118` | Text color |
| 563 | `#0f1a14` | Text color |
| 689 | `#1a1508` | Text color |
| 721 | `#0f1a14` | Text color |
| 774 | `#0f1a14` | Text color |

### `dashboard.py` — 2 Hardcoded Hex Values
| Line | Value | Usage |
|------|-------|-------|
| 26 | `#8B5CF6` | Mauve accent color |
| 27 | `#F97316` | Peach accent color |

### Hardcoded Colors in Component Files
| File | Line | Value | Usage |
|------|------|-------|-------|
| `dialogs.py` | 140 | `white` | Header text color |
| `state_helper.py` | 153, 232 | `white` | Action button text color |
| `notifications.py` | 164 | `rgba(255,255,255,0.2)` | Close button hover |
| `document_action_dialog.py` | 112 | `white` | WhatsApp button text |
| `sidebar.py` | 567 | `#f1f5f9` | Hover fallback |

---

## HIGH: Raw QPushButton Usage (Must Use EnterpriseButton)

242 raw `QPushButton` instances across the codebase. Key locations:

| Screen File | Lines | Buttons |
|-------------|-------|---------|
| `navigation_header.py` | 77, 84, 111 | Back, Home, Close buttons |
| `state_helper.py` | 147, 152, 226 | Action buttons in overlays |
| `tables.py` | 523-526 | Pagination widget (`<<`, `<`, `>`, `>>`) |
| `document_action_dialog.py` | 76, 83, 109, 122 | Print, PDF, Share, Cancel |
| `truth/event_store_screen.py` | 54, 59 | Refresh, Verify Claim |
| `system/user_management_screen.py` | 405, 423 | Cancel, Save User |
| `system/fixed_assets_screen.py` | 92,97,127,130,167,170,217,246 | 8 raw buttons |
| `system/control_center_screen.py` | 261 | Manual Refresh |
| `system/audit_screen.py` | 79, 87 | Clear Filters, Export CSV |
| `sales/sales_invoice_screen.py` | 460, 491 | Select Batch, Remove |
| `sales/customer_screen.py` | 406 | Save Customer |
| `purchases/purchase_invoice_screen.py` | 478 | Remove |
| `purchases/supplier_screen.py` | 428, 445 | Cancel, Save Supplier |
| `pos/pos_screen.py` | 438, 560, 600 | Multiple raw buttons |

Raw `QPushButton` lacks: loading state, variant colors, size standardization, disabled styling, click-with-data signal.

---

## HIGH: Direct QWidget/QFrame Bypassing BaseScreen

21 registered screens inherit from QWidget or QFrame instead of BaseScreen. Missing features:
- Lifecycle hooks (`showEvent` → `_on_screen_shown`, `_on_screen_hidden`)
- State machine (`LOADING → READY | ERROR | EMPTY`)
- `set_loading()`, `show_error()`, `show_empty()` helpers
- Auto-refresh via QTimer + timer_registry
- Data caching (`cache_data()`, `get_cached_data()`)
- `navigation_requested` signal
- `ScreenStateHelper` integration

**Most impactful**: SalesInvoiceScreen (index 5), PurchaseInvoiceScreen (index 6), ChartOfAccountsScreen (index 10), JournalEntryScreen (index 11), AccountLedgerScreen (index 12) — **core operational screens** missing lifecycle management.

---

## MEDIUM: Missing Loading/Error/Empty States

| Component | Missing | Impact |
|-----------|---------|--------|
| `EnterpriseTable` | No built-in loading/empty/error | `empty_state_text` parameter exists but never used in `_refresh_display()` |
| `EnterpriseForm` | No loading state during submission | Users can double-submit; no busy indicator |
| `EnterpriseDialog` | No built-in loading overlay | Long operations show no feedback |

---

## MEDIUM: Redundant Code

| Location | Issue |
|----------|-------|
| `state_helper.py` lines 57-63, 104-110, 187-193 | Three nearly identical QFrame container setups |
| `state_helper.py` lines 147-164, 226-243 | Two identical action button creation blocks |
| `tables.py` lines 55-176 + `style_builder.py` lines 185-270 | Two divergent table stylesheet generators |

---

## Form Readability Issues

| Issue | Locations | Impact |
|-------|-----------|--------|
| Required indicator uses inline HTML span | `forms.py:144` | Bypasses design system |
| Hardcoded dialog heights | `dialogs.py:88,121,151` | Not responsive |
| No form loading state | `forms.py:510` | No feedback on submit |
| Forms across screens lack consistent spacing | All QFrame-based screens | Inconsistent visual rhythm |

---

## Notation & Quality Summary

| Category | Rating | Critical Issues |
|----------|--------|-----------------|
| Token system usage | ❌ **FAIL** | 17 interpolation bugs break all components |
| Design system compliance | ❌ **FAIL** | financial_control_tower bypasses entirely |
| BaseScreen inheritance | ⚠️ **POOR** | 21/55 registered screens violate mandate |
| Button standardization | ⚠️ **POOR** | 242 raw QPushButton instances |
| Color consistency | ⚠️ **POOR** | Hardcoded hex in 5+ files |
| Form/table readability | ✅ **FAIR** | Token bugs aside, structure is reasonable |
| Loading states | ✅ **FAIR** | BaseScreen has them but many QWidget screens don't |
| Error handling | ✅ **GOOD** | API client has robust error handling |
| Notification system | ✅ **GOOD** | Comprehensive toast system (when tokens work) |
