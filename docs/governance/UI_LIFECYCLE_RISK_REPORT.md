# UI Lifecycle Risk Report — Phase UX.3 Layer 1

**Generated:** 2026-05-24

---

## Risk Summary

| Risk Level | Count | Screens | Dialogs |
|------------|-------|---------|---------|
| SAFE_MIGRATION | 6 | 6 finance workspaces (60-65) | 7 simple dialogs |
| MEDIUM_RISK | 7 | PaymentScreen, FinancialIntegrity, FinancialAudit, ReportBrowser, Analytics, OperationsDashboard, DecisionWorkspace | 10 moderate dialogs |
| HIGH_RISK | 6 | SalesInvoice, PurchaseInvoice, POS, ChartOfAccounts, JournalEntry, AccountLedger | 14 complex dialogs |
| DO_NOT_TOUCH | 24 | Dashboard, observability stack, inventory bases, report bases, HR/System already migrated | 0 |

## Lifecycle Risks Identified

### 1. Singleton Screen Cache (Memory Leak Risk)
- **Severity**: MEDIUM
- **Description**: `ScreenFactory` caches screen instances indefinitely. Screens are never destroyed once created. In a long-running session with 66+ screens, this accumulates widget memory.
- **Impact**: Gradual memory growth over hours/days of use.
- **Mitigation**: `ScreenFactory.reset()` exists but is never called. Could be used during `reset_all()` or on logout.

### 2. Duplicate Data Loading
- **Severity**: LOW
- **Description**: Several screens (PaymentAllocationExplorer, ReturnsExplainability, JournalReversalExplorer, FinancialOperationsConsole) load data in `__init__`. If migrated to BaseScreen, `showEvent` will trigger `_on_screen_shown → load_data` which could cause double-loading.
- **Mitigation**: Override `_on_screen_shown` to be a no-op, or remove __init__ data loading in favor of `load_data()`.

### 3. Missing Signal Cleanup
- **Severity**: LOW
- **Description**: No screen in the codebase explicitly disconnects signals on hide/destroy. Qt's parent-child ownership handles widget deletion, but signal connections to external objects (API client, navigation manager) may persist.
- **Mitigation**: BaseScreen provides `screen_hidden` signal for cleanup hooks. Not currently used by any screen.

### 4. Timer Cleanup
- **Severity**: LOW
- **Description**: `set_auto_refresh` in BaseScreen registers timers via `runtime.timer_registry`. Screens not using BaseScreen have no timer cleanup. Only screens with auto-refresh are affected.
- **Mitigation**: None currently needed — no screens use auto-refresh.

### 5. Dialog Modal Chains
- **Severity**: MEDIUM
- **Description**: Complex screens (SalesInvoice, PurchaseInvoice) open multiple nested dialogs (BatchSelection → PrintableInvoice, ProductSelection). Modal chains using `exec()` block the UI thread.
- **Mitigation**: Documented for Phase UX.3 dialog migration.

## BaseScreen Feature Utilization

| BaseScreen Feature | Used By |
|--------------------|---------|
| `load_data()` override | 24 existing BaseScreen screens |
| `_on_screen_shown()` override | 0 (default calls load_data) |
| `_on_screen_hidden()` override | 0 |
| `set_loading()` | 24 existing BaseScreen screens |
| `show_error()/show_empty()` | 24 existing BaseScreen screens |
| `set_auto_refresh()` | 0 |
| `screen_shown` / `screen_hidden` signals | 0 |
| `navigation_requested` signal | 0 |
| `state_changed` signal | 0 |

## Recommendations

1. **Batch 1**: Migrate 6 finance workspace screens to BaseScreen — lowest risk
2. **Batch 2**: Migrate 7 medium-risk screens after validation
3. **Batch 3**: Dialog migrations after screen migrations stabilize
4. **Deferred**: High-risk screens (sales, purchases, POS, accounting) — leave for dedicated phase
