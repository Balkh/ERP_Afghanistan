# DEAD UI & DUPLICATION REPORT

## 1. Orphan/Backup Files

| File | Reason | Action |
|------|--------|--------|
| `frontend/ui/dashboard.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/main_window.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/sidebar.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/accounting/components/account_form_dialog.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/hr/employee_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/hr/payroll_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/system/control_center_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/system/intelligence_hub_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/finance/cost_centers_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/finance/expense_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/observability/observability_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/observability/replay_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/observability/widgets.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/inventory/base_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/autonomous/decision_options_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/autonomous/master_dashboard.py.governance_backup` | Governance audit backup | 🗑️ Remove |
| `frontend/ui/system/fixed_assets_screen.py.governance_backup` | Governance audit backup | 🗑️ Remove |

**Total dead files:** 17 `.governance_backup` files — all can be safely removed.

## 2. Duplicate Screen Registrations

### 2.1 Index Collisions
| Index | First Registration | Second Registration | Impact |
|-------|-------------------|--------------------|--------|
| 10 | POSScreen (line ~113) | ChartOfAccountsScreen (line ~120) | ChartOfAccounts OVERWRITES POS **Critical Bug** |
| 34 | ExpenseScreen | CompanyProfileScreen | CompanyProfile OVERWRITES Expenses |
| 48 | RoleManagementScreen | ReportBrowser(cash_flow) | ReportBrowser OVERWRITES RoleManagement |

### 2.2 Redundant Registrations (Same Screen, Multiple Indices)
| Screen | Indices | Count | Impact |
|--------|---------|-------|--------|
| OperationsDashboard | 38, 43, 45 | 3 | 2 redundant indices with no sidebar access |
| AnalyticsWorkspace | 40, 41, 42 | 3 | 3 indices with no sidebar access |
| DecisionWorkspace | 46, 47 | 2 | 1 redundant index with no sidebar access |
| ObservabilityConsole | 39, 44 | 2 | 1 redundant index with no sidebar access |
| ReportBrowser (cash_flow) | 48 | 1 | Collides with RoleManagement |

## 3. Duplicate Navigation Entries

| Item | Location 1 | Location 2 | Confusion Risk |
|------|-----------|-----------|----------------|
| Cash Flow | Reports group (idx 48) | Finance group (idx 22) | HIGH — user doesn't know which to choose |
| Audit Log | Accounting group (idx 59) | System group (idx 30) | MEDIUM — different purposes |
| Control Center | System group (idx 38) | Sidebar "Control Center" text | LOW — only one entry |

## 4. Deprecated/Unused Systems

### 4.1 Theme Engine
| Component | Status | Notes |
|-----------|--------|-------|
| ThemeEngine | ✅ ACTIVE | Canonical singleton — used everywhere |
| ThemeManager | 🗑️ DEPRECATED | Warns on import, should be removed |

### 4.2 Navigation
| Component | Status | Notes |
|-----------|--------|-------|
| MainWindow navigation_history | ✅ ACTIVE | Stack-based, max 20 entries |
| NavigationManager (navigation/navigation_manager.py) | 🗑️ STANDALONE | QObject-based with forward/back stacks, not wired to MainWindow |

### 4.3 Autonomous Screens (Possibly Dead)
| Screen | Registered? | Sidebar? | Status |
|--------|-------------|----------|--------|
| anomaly_warning_center.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| decision_options_screen.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| forecast_dashboard.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| master_dashboard.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |

### 4.4 Investigation Screens (Possibly Dead)
| Screen | Registered? | Sidebar? | Status |
|--------|-------------|----------|--------|
| anomaly_investigation_screen.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| event_investigation_screen.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |

### 4.5 Truth Screens (Possibly Dead)
| Screen | Registered? | Sidebar? | Status |
|--------|-------------|----------|--------|
| event_store_screen.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |

### 4.6 Governance Screens (Possibly Dead)
| Screen | Registered? | Sidebar? | Status |
|--------|-------------|----------|--------|
| approval_screen.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| audit_scanner.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| auto_fixer.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| consistency_audit.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |
| ux_governor.py | ❌ Not in main_window | ❌ | 🗑️ UNUSED |

## 5. Dead Code in Main Files

### 5.1 MainWindow
| Code | Location | Status |
|------|----------|--------|
| GlobalIntelligenceBar imports/comments | Lines ~125-135 | 🗑️ DEAD — commented out |
| Cognitive bar reference | Commented | 🗑️ DEAD |

### 5.2 Dashboard
| Code | Location | Status |
|------|----------|--------|
| _build_static_ui full rebuild in refresh_theme | dashboard.py | ⚠️ POTENTIALLY HEAVY | 
| Mock data fallbacks | _get_mock_returns in ReturnsScreen | ⚠️ DEV ONLY |

## 6. Summary of Findings

| Category | Count | Details |
|----------|-------|---------|
| Governance backup files | 17 | All removable |
| Index collisions | 3 | POS/COA, Expenses/Company, RoleMgmt/CashFlow — **Critical** |
| Redundant registrations | 10+ | Same screen at multiple indices |
| Dead screens (unregistered) | 10+ | autonomous/*, investigation/*, truth/*, governance/* |
| Deprecated systems | 2 | ThemeManager, NavigationManager |
| Duplicate nav entries | 2 | Cash Flow, Audit Log |
| Commented dead code | 2 | GlobalIntelligenceBar in MainWindow |
