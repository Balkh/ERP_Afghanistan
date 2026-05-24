# Cleanup Execution Plan - Phase 36.5

## Phased Governance Strategy
**MANDATORY RULE**: ARCHIVE FIRST. DELETE LATER.
All candidates must be moved to `/archive/legacy/` and pass full regression tests before final deletion.

---

## Phase A: Safe Archive (Low Risk)
**Target**: Orphan modules and unused utilities.
1. Move `backend/pharmacy/` to `/archive/legacy/pharmacy/`.
2. Move `backend/core/services/transaction_service.py` to `/archive/legacy/core/`.
3. Move `frontend/ui/cognitive/` and `frontend/ui/cognitive_reasoning/` to `/archive/legacy/ui/`.
4. Delete duplicate `backend/management/commands/seed_erp_data.py`.

**Validation**: 
- Run `pytest backend/tests/` (Verify no broken imports).
- Verify app startup.

---

## Phase B: UI Navigation Cleanup
**Target**: Legacy UI placeholders.
1. Remove "Production" item from `frontend/ui/sidebar.py`.
2. Unregister `ProductionScreen` (Index 37) in `MainWindow.py`.
3. Remove `production_screen.py` from `frontend/ui/system/`.

**Validation**:
- Verify sidebar rendering for all roles.
- Verify no "Widget not found" errors in `MainWindow`.

---

## Phase C: Engine Consolidation (Medium Risk)
**Target**: Duplicate truth and decision engines.
1. Merge `simulation.truth_engine.engine` logic into `core.operations.truth.gateway.TruthGateway`.
2. Redirect `observability` views to use `TruthGateway` instead of `TruthEngine`.
3. Archive `backend/simulation/truth_engine/`.

**Validation**:
- Verify "Truth" dashboard in Observability Console.
- Run `test_truth_verification.py`.

---

## Phase D: Simulation Isolation (High Risk)
**Target**: Abandoned simulation sub-systems.
1. Identify and archive `simulation/recovery/` and `simulation/audit/`.
2. Verify that no leakage exists in `core.operations.observability`.

**Validation**:
- Full system regression.
- Manual verification of Observability Timeline and Incidents.

---

## Rollback Strategy
- All archived files are preserved in the repository under `/archive/`.
- In case of regression, move files back to their original locations and restore imports.
- Transactional integrity is guaranteed as no `CRITICAL_CORE` systems (JournalEngine, etc.) are modified.
