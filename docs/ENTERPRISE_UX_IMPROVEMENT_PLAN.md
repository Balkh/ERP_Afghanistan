# ENTERPRISE UX IMPROVEMENT PLAN

## PHASE 1: CRITICAL FIXES (DO FIRST)

### 1.1 Fix Index Collisions
**Severity:** CRITICAL — POS and ChartOfAccounts can't both be accessed at index 10. User clicking POS gets ChartOfAccounts.

**Action:**
| Collision | Fix |
|-----------|-----|
| Index 10: POS ↔ ChartOfAccounts | Move POS to index 37 (unused) or use a dedicated range 36-39 |
| Index 34: Expenses ↔ CompanyProfile | Move CompanyProfile to index 69 or use index 35+ range |
| Index 48: RoleManagement ↔ CashFlow Report | Move CashFlow Report to index 67 |

### 1.2 Fix Redundant Screen Registrations
**Actions:**
- Keep OperationsDashboard at index 38 only; remove indices 43, 45
- Keep AnalyticsWorkspace at index 40 only; remove indices 41, 42
- Keep DecisionWorkspace at index 47 only; remove index 46
- Keep ObservabilityConsole at index 39 only; remove index 44

### 1.3 Clean Up Sidebar Duplicates
**Actions:**
| Duplicate | Action |
|-----------|--------|
| "Cash Flow" in Reports (idx 48) | Remove from Reports (Finance Cash Flow at idx 22 is the canonical) |
| "Audit Log" in Accounting (idx 59) | Keep in System (idx 30), rename Accounting's to "Financial Audit Log" |

## PHASE 2: COMPONENT STANDARDIZATION

### 2.1 Migrate POS to EnterpriseButton/EnterpriseTable
**Effort:** MEDIUM | **Impact:** HIGH | **Files:** 1

Replace raw QPushButton in `_action_button` helper with `EnterpriseButton` instances using appropriate `ButtonVariant`/`ButtonSize`.

Replace raw `QTableWidget` in cart and search with `EnterpriseTable` using `TableColumn` definitions.

### 2.2 Extend EnterpriseButton to All Screens
**Effort:** LARGE | **Impact:** HIGH | **Files:** ~15+

Audit all screens and replace raw `QPushButton` with `EnterpriseButton`:
- ProductScreen ✓ planned
- CategoryScreen ✓ planned
- WarehouseScreen ✓ planned
- BatchScreen ✓ planned
- CustomerScreen ✓ planned
- SupplierScreen ✓ planned
- SalesInvoiceScreen ✓ planned
- PurchaseInvoiceScreen ✓ planned

### 2.3 Extend EnterpriseTable to All Data Screens
**Effort:** LARGE | **Impact:** HIGH | **Files:** ~15+

Replace raw `QTableWidget` with `EnterpriseTable` in:
- Inventory screens
- Sales/Purchase invoice screens
- Accounting data displays
- HR/employee screens

### 2.4 Implement BaseScreen Everywhere
**Effort:** LARGE | **Impact:** HIGH | **Files:** ~20+

Verify all screen classes inherit from `BaseScreen` (or `BaseFormScreen`/`BaseListScreen`) and implement:
- `on_show()` lifecycle method
- Standardized state management (ScreenStateHelper)
- Standardized layout pattern

## PHASE 3: DEAD CODE CLEANUP

### 3.1 Remove Governance Backup Files
**Effort:** LOW | **Impact:** LOW | **Files:** 17

Delete all `*.governance_backup` files — no functional impact.

### 3.2 Remove Deprecated ThemeManager
**Effort:** LOW | **Impact:** LOW | **Files:** 1

Remove `ui/theme/theme_manager.py` and update any remaining references to use `theme.theme_engine.ThemeEngine`.

### 3.3 Remove Unregistered Screens or Register Them
**Effort:** LOW | **Impact:** LOW | **Files:** 10+

Either remove dead screen directories or register them in MainWindow and add sidebar entries:
- `autonomous/*` — 5 screens
- `investigation/*` — 2 screens
- `truth/*` — 1 screen
- `governance/*` — 5 screens

### 3.4 Clean Up Dead Comments/Code in MainWindow
**Effort:** LOW | **Impact:** LOW | **Files:** 1

Remove commented-out GlobalIntelligenceBar and cognitive bar references.

## PHASE 4: LAYOUT & SPACE ENHANCEMENTS

### 4.1 Apply Density Tiers
**Effort:** MEDIUM | **Impact:** MEDIUM | **Files:** ~20+

Apply density tokens per screen type:
| Screen Type | Density Tier | Implementation |
|-------------|-------------|----------------|
| Financial reports | COMPACT | 26px rows, 8px spacing |
| Inventory tables | COMPACT | 26px rows, 8px spacing |
| Forms | STANDARD | 32px rows, 12px spacing |
| Dashboard | COMFORTABLE | 40px spacing, 44px inputs |
| POS | STANDARD | 32px rows, 12px spacing |

### 4.2 Optimize Sidebar Group Organization
**Effort:** LOW | **Impact:** MEDIUM | **Files:** 1

| Group | Current Items | Recommended Max | Action |
|-------|--------------|-----------------|--------|
| Finance | 12 | 8 | Split into "Finance" (6 items) + "Financial Ops" (6 items) |
| System | 13 | 8 | Split into "Administration" (7 items) + "Intelligence" (6 items) |

Default expansion: Keep "Dashboard" always visible, expand the group containing the item last navigated to.

### 4.3 Add Notification Center
**Effort:** MEDIUM | **Impact:** HIGH | **Files:** 2-3

Create a notification center screen consuming `/api/auth/notifications/` and `/api/auth/notifications/unread-count/` endpoints. Add sidebar entry under System group.

## PHASE 5: VISUAL POLISHING

### 5.1 Add Micro-Interactions
**Effort:** LOW | **Impact:** MEDIUM | **Files:** ~10+

- Table row hover effects (already present in EnterpriseTable)
- Smooth expand/collapse for sidebar groups (already TODO in sidebar.py)
- Transition effects for dialog open/close

### 5.2 Optimize Empty States
**Effort:** LOW | **Impact:** MEDIUM | **Files:** ~15+

Implement consistent empty state pattern across all screens using STATE_EMPTY_TITLE/STATE_EMPTY_SUBTITLE tokens:
- Icon placeholder (EMPTY_STATE_ICON_SIZE)
- Descriptive title
- Action-oriented subtitle
- Primary action button (e.g., "Create First Product")

### 5.3 Standardize Dialog Sizing
**Effort:** LOW | **Impact:** MEDIUM | **Files:** ~10+

Enforce DIALOG_WIDTH_* tokens across all dialog classes:
| Dialog Type | Width Token |
|-------------|-------------|
| Form dialogs | DIALOG_WIDTH_FORM_PREFERRED (580) |
| Preview dialogs | DIALOG_WIDTH_PREFERRED (580) |
| Wide data dialogs | DIALOG_WIDTH_WIDE (900) |
| Minimum width | DIALOG_WIDTH_MIN (400) |

## PHASE 6: QUALITY OF LIFE

### 6.1 Fix Sidebar Default State
**Effort:** LOW | **Impact:** MEDIUM | **Files:** 1

Expand the most commonly used groups by default:
- Inventory (most visited by warehouse role)
- Sales (most visited by cashier role)
- Accounting (most visited by accountant role)

Implement role-aware default expansion.

### 6.2 Add Breadcrumbs to All Screens
**Effort:** LOW | **Impact:** LOW | **Files:** 1

NavigationHeader already exists and generates breadcrumbs. Verify all screens display breadcrumbs correctly and consistently.

### 6.3 Keyboard Shortcut Documentation
**Effort:** LOW | **Impact:** LOW | **Files:** 1

Add a "Keyboard Shortcuts" help dialog accessible from Help menu showing all registered shortcuts (POS: F2/F6/F7/F8/F10/Del; Navigation: Ctrl+1/2/3, Alt+Left, Ctrl+Home, Escape).

---

## IMPLEMENTATION PRIORITY MATRIX

| Priority | Phase | Effort | Impact | Quick Win? |
|----------|-------|--------|--------|------------|
| 🔴 P0 | Phase 1 | LOW | CRITICAL | YES — fix index collisions |
| 🔴 P0 | Phase 1 | LOW | HIGH | YES — remove duplicate nav entries |
| 🟡 P1 | Phase 2 | MEDIUM | HIGH | — Migrate POS components |
| 🟡 P1 | Phase 3 | LOW | MEDIUM | YES — delete backup files |
| 🟢 P2 | Phase 4 | MEDIUM | MEDIUM | — Apply density tiers |
| 🟢 P2 | Phase 4 | MEDIUM | HIGH | — Add notification center |
| 🔵 P3 | Phase 5 | LOW | MEDIUM | YES — optimize empty states |
| 🔵 P3 | Phase 3 | LOW | LOW | YES — remove dead code |
| ⚪ P4 | Phase 6 | LOW | LOW | — Add help documentation |

---

## ESTIMATED TOTAL EFFORT

| Phase | Estimated Hours | Impact Level |
|-------|----------------|--------------|
| Phase 1: Critical Fixes | 2-4 hours | CRITICAL |
| Phase 2: Component Standardization | 20-30 hours | HIGH |
| Phase 3: Dead Code Cleanup | 4-6 hours | MEDIUM |
| Phase 4: Layout Enhancements | 8-12 hours | MEDIUM |
| Phase 5: Visual Polishing | 6-8 hours | MEDIUM |
| Phase 6: Quality of Life | 4-6 hours | LOW |
| **Total** | **44-66 hours** | — |
