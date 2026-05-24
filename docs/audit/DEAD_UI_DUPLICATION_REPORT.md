# DEAD UI & DUPLICATION REPORT — Pharmacy ERP

## ORPHAN SCREEN FILES (29 Files)

These files exist on disk but are **never imported** in any production code path. They are dead code.

### Accounting — Replaced by ReportBrowser (5 files)
| File | Class | Reason Dead |
|------|-------|-------------|
| `ui/accounting/trial_balance_screen.py` | TrialBalanceScreen | Replaced by `ReportBrowser("trial_balance")` at index 13 |
| `ui/accounting/profit_loss_screen.py` | ProfitAndLossScreen | Replaced by `ReportBrowser("profit_loss")` at index 14 |
| `ui/accounting/balance_sheet_screen.py` | BalanceSheetScreen | Replaced by `ReportBrowser("balance_sheet")` at index 15 |
| `ui/accounting/arap_ageing_screen.py` | ARAPAgeingScreen | Replaced by `ReportBrowser("ar_aging"/"ap_aging")` at indices 16-17 |
| `ui/accounting/cash_flow_screen.py` | CashFlowScreen | Never registered; `cashflow_screen.py` in `finance/` is the active screen |

### Accounting Dashboard (1 file)
| File | Class | Reason Dead |
|------|-------|-------------|
| `ui/accounting/accounting_dashboard.py` | AccountingDashboard(QWidget) | Never registered in MainWindow |

### HR Reports — Replaced by ReportBrowser (4 files)
| File | Classes |
|------|---------|
| `ui/hr/report_screens.py` | EmployeeSummaryScreen, AttendanceReportScreen, LeaveReportScreen, OvertimeReportScreen |

### Payroll Reports — Replaced by ReportBrowser (4 files)
| File | Classes |
|------|---------|
| `ui/payroll/report_screens.py` | PayrollSummaryScreen, PayrollTrendScreen, PayrollDepartmentCostScreen, PayrollEmployeeHistoryScreen |

### Control Tower — Orphaned Subdirectory (1 file)
| File | Class |
|------|-------|
| `ui/control_tower/dashboard.py` | ControlTowerDashboard(QWidget) |

### Autonomous — Fully Orphaned Subdirectory (4 files)
| File | Class |
|------|-------|
| `ui/autonomous/master_dashboard.py` | MasterIntelligenceDashboard |
| `ui/autonomous/forecast_dashboard.py` | ForecastDashboard |
| `ui/autonomous/decision_options_screen.py` | DecisionOptionsScreen |
| `ui/autonomous/anomaly_warning_center.py` | AnomalyWarningCenterScreen |

### Investigation — Fully Orphaned Subdirectory (2 files)
| File | Class |
|------|-------|
| `ui/investigation/event_investigation_screen.py` | EventInvestigationScreen |
| `ui/investigation/anomaly_investigation_screen.py` | AnomalyInvestigationScreen |

### Navigation — Fully Orphaned Subdirectory (1 file)
| File | Class |
|------|-------|
| `ui/navigation/navigation_manager.py` | NavigationManager, NavigationHistory |

### Governance — Mostly Orphaned Subdirectory (5 files)
| File | Class |
|------|-------|
| `ui/governance/ux_governor.py` | UXGovernor |
| `ui/governance/consistency_audit.py` | ConsistencyAudit |
| `ui/governance/auto_fixer.py` | AutoFixer |
| `ui/governance/audit_scanner.py` | AuditScanner |
| `ui/governance/registry.py` | Registry |

### Licensing — Standalone/Unregistered (2 files)
| File | Class |
|------|-------|
| `ui/licensing/activation_screen.py` | ActivationScreen |
| `ui/licensing/license_status_screen.py` | LicenseStatusScreen |

### Truth — Standalone (1 file)
| File | Class |
|------|-------|
| `ui/truth/event_store_screen.py` | EventStoreScreen |

### Finance — Standalone (1 file)
| File | Class |
|------|-------|
| `ui/finance/mixed_payment_builder.py` | MixedPaymentBuilder |

---

## DUPLICATE SCREEN IMPLEMENTATIONS

### Duplicate Dashboard Classes (3 implementations)

| File | Class | Status |
|------|-------|--------|
| `ui/dashboard.py` | `Dashboard(QWidget)` | ✅ Active (index 0) |
| `ui/control_tower/dashboard.py` | `ControlTowerDashboard(QWidget)` | ❌ Orphaned |
| `ui/autonomous/master_dashboard.py` | `MasterIntelligenceDashboard` | ❌ Orphaned |

### Duplicate Report Screens (2 parallel implementations)

**Legacy individual screens** (orphaned, all extend `BaseReportScreen(QFrame)`):
- `trial_balance_screen.py`, `profit_loss_screen.py`, `balance_sheet_screen.py`, `arap_ageing_screen.py`, `cash_flow_screen.py`

**Active unified browser** (extends `QWidget`, registered at indices 13-17 and 49-56):
- `report_browser.py` — handles all report types via `report_type` parameter

### Duplicate HR/Payroll Report Screens (2 parallel implementations)

**Legacy individual screens** (orphaned):
- `hr/report_screens.py` — EmployeeSummaryScreen, etc.
- `payroll/report_screens.py` — PayrollSummaryScreen, etc.

**Active unified browser**:
- `report_browser.py` handles HR/Payroll reports at indices 49-56

### Duplicate Table Stylesheet Generators (2 implementations)

| Source | File | Lines |
|--------|------|-------|
| `build_table_stylesheet()` | `ui/components/tables.py` | 55-176 |
| `UIStyleBuilder.get_table_style()` | `theme/style_builder.py` | 185-270 |

---

## DUPLICATE PAGE MAPS IN MAIN WINDOW

Two separate dictionaries mapping page identifiers to indices:

1. **Breadcrumb page_map** (`_build_breadcrumb()`, line 640): index → title
2. **Navigation page_map** (`_do_navigate()`, line 1132): page_id → index

These are **duplicated** and have **diverged** — the navigation map has 13 off-by-one errors and both have missing entries.

---

## DUPLICATE SOURCE OF TRUTH: COLOR_BG_HOVER

`ui/constants.py:81` defines `COLOR_BG_HOVER = ""` — an empty string. This is used as a design token but provides no actual value.

---

## EMPTY DIRECTORY: `ui/base/`

The entire `ui/base/` directory contains nothing but an empty `__init__.py` (0 bytes). Despite being reserved for base classes, it serves no purpose.

---

## ORPHANED SIDEBAR GROUP: `cash_flow`

`sidebar.py:94` has `"cash_flow": {"cash_flow"}` in `group_items_map`, but there is NO `_create_group()` call for `"cash_flow"` in `setup_ui()`. This is dead mapping code.

---

## PHANTOM SCREEN: Index 40 (AnalyticsWorkspace)

Registered in `main_window.py` at index 40 but:
- Not present in sidebar
- Not in `page_to_module` auth mapping
- No breadcrumb mapping
- No menu shortcut
- **Cannot be navigated to by any user action**

---

## LEGACY/DEPRECATED FILES

| File | Status | Notes |
|------|--------|-------|
| `theme/enterprise_styling.py` | Deprecated | Marked at line 2, retained for reference |
| `theme/theme_manager.py` | Legacy | Not used by active ThemeEngine |
| `ui/theme/theme_manager.py` | Legacy | Delegates to theme.theme_engine |

---

## REPEATED IMPORTS / CODE SMELLS

- `ui/accounting/profit_loss_screen.py:7`: `COLOR_SUCCESS` and `COLOR_DANGER` each imported twice: `from ui.constants import (COLOR_SUCCESS, COLOR_DANGER, COLOR_SUCCESS, COLOR_DANGER)`
- `ui/components/tables.py:81-85`: Constants re-imported inside `build_table_stylesheet()` even though already imported at module level

---

## SUMMARY

| Category | Count | Action |
|----------|-------|--------|
| Orphan screen files | 29 | Remove or register |
| Duplicate dashboard classes | 2 extra | Remove |
| Duplicate report implementations | 2 sets | Legacy files → remove |
| Duplicate table style generators | 1 extra | Consolidate |
| Duplicate page maps | 1 extra | Consolidate |
| Empty directories | 1 | Populate or remove |
| Phantom sidebar group | 1 | Remove dead mapping |
| Phantom screen | 1 | Register or remove |
| Deprecated files | 3 | Archive or remove |
| Code smells (dup imports) | 2 files | Fix |
| Empty/placeholder tokens | 1 | Fix COLOR_BG_HOVER |
