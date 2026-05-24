# Engine Duplication Report - Phase 36.5

## Overview
This report identifies overlapping orchestration systems and duplicate engines within the Enterprise ERP.

## Duplicate Engine Candidates

### 1. Control Center Aggregation
- **Production Engine**: `core.operations.control_center.ControlCenterAggregator`
- **Simulation Engine**: `simulation.control_center.orchestrator.ControlCenterEngine`
- **Overlap Score**: 85%
- **Analysis**: Both engines aggregate system health, financial summaries, and inventory metrics. The production version uses direct DB queries (DRF views), while the simulation version uses a complex signal/event processing pipeline.
- **Danger Level**: LOW
- **Recommendation**: Maintain both but clearly separate their domains. Production version is for real-time KPIs; Simulation version is for advanced observability and drift detection.

### 2. Truth Verification
- **Production Engine**: `core.operations.truth.gateway.TruthGateway`
- **Simulation Engine**: `simulation.truth_engine.engine.TruthEngine`
- **Overlap Score**: 90%
- **Analysis**: Both attempt to verify "truth" by comparing expected vs actual states. `TruthGateway` is integrated into the `api/v1/truth/` production layer.
- **Danger Level**: MEDIUM
- **Recommendation**: **Consolidate**. `TruthGateway` should be the single source of truth verification logic to avoid "Truth Drift".

### 3. Decision Logic
- **Production Engine**: `core.services.financial_policy_engine.FinancialPolicyEngine`
- **Simulation Engine**: `core.operations.decision_engine.DecisionEngine`
- **Overlap Score**: 60%
- **Analysis**: `FinancialPolicyEngine` handles critical business blocks (credit limits, overdue invoices). `DecisionEngine` handles observability signals (auth failures, performance).
- **Danger Level**: LOW
- **Recommendation**: Keep both as they serve different domains (Business Policy vs System Observability).

### 4. Reconciliation
- **Engine A**: `accounting.services.reconciliation.AccountingReconciliationService` (Integrity)
- **Engine B**: `core.services.reconciliation_v2.ReconciliationAssistanceV2` (Payment Matching)
- **Overlap Score**: 30%
- **Analysis**: These are named similarly but serve different purposes. No consolidation required.

---

## Speculative Abstractions
- **`core.operations.execution.simulation_engine.py`**: A v2.0 "hardened" engine that only models plans without execution. While speculative, it is actively used by the Governance API for "What-If" analysis before approvals.
- **Classification**: **ACTIVE (Governance Layer)**.
