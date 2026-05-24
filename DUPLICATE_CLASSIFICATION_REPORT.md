# Duplicate Classification Report - Phase 41 (BUG-058)

## Overview
A safety-first analysis of duplicate classes and modules was performed. No structural changes were made; instead, items were classified for future consolidation.

## 1. Simulation vs Core Duplicates

### `ControlCenterEngine`
- **Simulation**: `simulation.control_center.orchestrator.control_center_engine.py`
- **Core**: `core.operations.control_center.py` (Aggregator)
- **Classification**: **ACTIVE BOTH**
- **Analysis**: Simulation version handles event-based state; Core version handles DB-based KPIs.
- **Recommendation**: **KEEP SEPARATE**. Preservation of architectural boundaries is critical.

### `TruthEngine`
- **Simulation**: `simulation.truth_engine.engine.py`
- **Core**: `core.operations.truth.gateway.TruthGateway`
- **Classification**: **LEGACY (Simulation) / ACTIVE (Core)**
- **Analysis**: `TruthGateway` is the authoritative SSOT. Simulation `TruthEngine` is used in passive observability.
- **Recommendation**: **ARCHIVE Simulation version** in Phase 42.

### `IntegrityValidators`
- **Simulation**: `simulation.digital_twin.integrity/`
- **Core**: `core.services.financial_integrity.py`
- **Classification**: **ACTIVE BOTH**
- **Analysis**: Simulation validators check "What-if" states; Core validators check "Real-world" DB state.
- **Recommendation**: **KEEP BOTH**. They serve different domains (Virtual vs Real).

## 2. Redundant Utilities

### `BalanceSyncService` vs `FinancialIntegrityService.auto_fix`
- **Classification**: **ACTIVE (BalanceSync) / DUPLICATE (Integrity fix)**
- **Analysis**: `FinancialIntegrityService` calls `BalanceSyncService` internally for fixes.
- **Recommendation**: **CONSOLIDATE**. Move all fix logic into `BalanceSyncService`.

## 3. Safe Archive Candidates
- **`backend/core/operations/decision_engine.py`**: Overlapped by `FinancialPolicyEngine`.
- **`backend/simulation/recovery/`**: Abandoned simulation sub-system.

## Final Assessment
The duplication (BUG-058) is largely intentional to preserve the **Simulation vs Production** isolation. Blind merging would risk "Simulation Leakage" into production workflows. Consolidation should only occur where utility logic is identical and domain-neutral.
