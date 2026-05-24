# Unused UI Report - Phase 36.5

## Unregistered Screens

### 1. `CognitiveDashboard`
- **File**: `frontend/ui/cognitive/cognitive_dashboard.py`
- **Status**: **UNUSED**
- **Analysis**: Not imported in `MainWindow` or `sidebar.py`. Replaced by `IntelligenceHubScreen`.
- **Recommendation**: Archive.

### 2. `CausalReasoningDashboard`
- **File**: `frontend/ui/cognitive_reasoning/causal_dashboard.py`
- **Status**: **UNUSED**
- **Analysis**: Not registered in `MainWindow`. Functional logic moved to `DecisionWorkspace`.
- **Recommendation**: Archive.

---

## Duplicate Widgets & Components

### 1. KPI Cards
- **Files**: `frontend/ui/components/kpi_cards.py` vs `frontend/ui/observability/widgets.py`
- **Analysis**: Overlap in metric display widgets. 
- **Recommendation**: Consolidate into `ui/components/kpi_cards.py` as the system standard.

### 2. Table Renderers
- **Files**: `frontend/ui/components/tables.py` vs `frontend/ui/rendering/table_renderer.py`
- **Analysis**: `EnterpriseTable` in `components` is the active standard. `table_renderer.py` appears to be a speculative abstraction for a future generic rendering system.
- **Status**: **LEGACY_ACTIVE / DUPLICATE**
- **Recommendation**: Consolidate or archive `rendering/` if unused.

---

## Dead Navigation Paths

### 1. Production Screen
- **Sidebar Label**: "Production"
- **Status**: **LEGACY_ACTIVE** (Non-functional)
- **Analysis**: References a removed backend module. 
- **Recommendation**: Remove from `sidebar.py`.

### 2. Settings Duplicate
- **Status**: **DUPLICATE**
- **Analysis**: Settings appears both as a standalone button and within the "System" group in some role configurations.
- **Recommendation**: Standardize to bottom-sidebar button only.
