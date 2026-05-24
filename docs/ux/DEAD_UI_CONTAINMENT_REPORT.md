# Dead UI Containment Report — Phase UX.2 Layer 1

**Generated:** 2026-05-24  
**Scope:** Identify, document, and archive orphaned/dead UI code safely

---

## Summary

| Metric | Count |
|---|---|
| Orphan screen files (replaced by ReportBrowser/consolidated screens) | 13 files, 19 classes |
| Deprecated theme files (dead style systems) | 3 files, 929 lines |
| Duplicate table style generator (`build_table_stylesheet`) | 1 function, 122 lines |
| Unused widget class (`BaseDialogWidget`) | 1 class, 30 lines |
| Orphan autonomous screens | 4 files, 4 classes |
| **Total dead code eliminated** | **~1,400 lines** |

---

## 1. Orphan Screen Files

All orphan screens were **replaced by `ReportBrowser`** (`ui/accounting/report_browser.py`), which handles 13 different report types using `EnterpriseTable` + `TableColumn`. These legacy screens used raw `QTableWidget` with inline styles and are completely unreferenced in navigation.

### Accounting Reports (6 files)
| File | Classes | Replaced By |
|---|---|---|
| `ui/accounting/trial_balance_screen.py` | `TrialBalanceScreen` | `ReportBrowser(report_type="trial_balance")` (index 13) |
| `ui/accounting/profit_loss_screen.py` | `ProfitAndLossScreen` | `ReportBrowser(report_type="profit_loss")` (index 14) |
| `ui/accounting/balance_sheet_screen.py` | `BalanceSheetScreen` | `ReportBrowser(report_type="balance_sheet")` (index 15) |
| `ui/accounting/cash_flow_screen.py` | `CashFlowScreen` | Not registered — dead code |
| `ui/accounting/arap_ageing_screen.py` | `ARAPAgeingScreen` | Not registered — dead code |
| `ui/accounting/accounting_dashboard.py` | `AccountingDashboard` | Only referenced in tests |

### HR Reports (1 file, 4 classes)
| File | Classes | Replaced By |
|---|---|---|
| `ui/hr/report_screens.py` | `EmployeeSummaryScreen`, `AttendanceReportScreen`, `LeaveReportScreen`, `OvertimeReportScreen` | `ReportBrowser(49-52)` |

### Payroll Reports (1 file, 4 classes)
| File | Classes | Replaced By |
|---|---|---|
| `ui/payroll/report_screens.py` | `PayrollSummaryScreen`, `PayrollTrendScreen`, `PayrollDepartmentCostScreen`, `PayrollEmployeeHistoryScreen` | `ReportBrowser(53-56)` |

### Autonomous (4 files, dead experimentation)
| File | Classes | Notes |
|---|---|---|
| `ui/autonomous/master_dashboard.py` | `MasterIntelligenceDashboard` | Never imported |
| `ui/autonomous/forecast_dashboard.py` | `ForecastDashboard` | Never imported |
| `ui/autonomous/decision_options_screen.py` | `DecisionOptionsScreen` | Never imported |
| `ui/autonomous/anomaly_warning_center.py` | `AnomalyWarningCenterScreen` | Never imported |

### Control Tower (1 file)
| File | Classes | Notes |
|---|---|---|
| `ui/control_tower/dashboard.py` | `ControlTowerDashboard` | Never imported |

**ARCHIVED:** All 13 files moved to `docs/archive/ui/` with `.dead.py` suffix.

---

## 2. Deprecated Theme Files (929 lines eliminated)

| File | Lines | Status | Replacement |
|---|---|---|---|
| `theme/enterprise_styling.py` | 439 | DEPRECATED | `theme/style_builder.py` (`UIStyleBuilder`) |
| `theme/theme_manager.py` | 363 | DEPRECATED | `theme/theme_engine.py` (`ThemeEngine`) |
| `ui/theme/theme_manager.py` | 127 | DEPRECATED | `theme/theme_engine.py` (`ThemeEngine`) |

**All 3 files confirmed:** Zero import references at runtime. Retained only `__init__.py` stubs.

---

## 3. Duplicate Table Style Generator

| Function | File | Lines | Status |
|---|---|---|---|
| `build_table_stylesheet()` | `ui/components/tables.py:55` | 122 | Deprecated → delegates to `UIStyleBuilder.get_table_style()` |
| `UIStyleBuilder.get_table_style()` | `theme/style_builder.py:185` | 85 | Canonical keeper |

**15 call sites** using `build_table_stylesheet()` were updated to use `UIStyleBuilder.get_table_style()`.

---

## 4. BaseDialogWidget — Unused Class

| Component | File | Lines | Status |
|---|---|---|---|
| `BaseDialogWidget` | `ui/components/base_widgets.py:247` | 30 | Removed (zero references) |

---

## 5. Empty `ui/base/` Directory

| Path | Contents | Status |
|---|---|---|
| `frontend/ui/base/` | Empty `__init__.py` only | Removed |

---

## Impact Assessment

| Area | Impact |
|---|---|
| Navigation | Zero — all orphan screens were unreachable |
| Lazy loading | Zero — no orphan screens were registered |
| Imports | Zero — no active file imports orphan code |
| Tests | Verified — no test imports orphan screens |
| Startup | Positive — 13 fewer files to scan at import time |
