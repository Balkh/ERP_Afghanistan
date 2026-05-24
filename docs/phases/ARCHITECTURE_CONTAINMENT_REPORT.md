# ARCHITECTURE CONTAINMENT REPORT
## Phase 32 — Layer 1: Engine Containment Audit

**Generated:** May 21, 2026
**Scope:** Full inventory of *Engine, Manager, Coordinator, Orchestrator, Processor, Controller, Pipeline* classes
**Rule:** Report only — no deletions, no refactors, no merges

---

## EXECUTIVE SUMMARY

| Metric | Count |
|---|---|
| Total Engine classes | **59** |
| Total Manager classes | **27** |
| Total Orchestrator classes | **5** |
| Total Coordinator classes | **2** |
| Total Controller classes | **1** |
| Total Pipeline classes | **7** |
| **GRAND TOTAL** | **101** |
|---|---|
| Active Production | **28** |
| Simulation Only | **40** |
| Duplicated (simulation) | **6** |
| Shadow/Overlapping | **8** |
| Frontend UI | **8** |
| Frontend Runtime | **3** |
| Deprecated/Dead | **1** |
| CI Script | **2** |
| Production importing simulation | **4 imports** in 1 file |

**Assessment:** SEVERE engine sprawl. 101 engine-type classes across 5 domains. Simulation code (40 classes) has leaked into production imports. 6 duplicated classes. Multiple overlapping intelligence/observability layers.

---

## SECTION 1 — COMPLETE ENGINE INVENTORY

### 1.1 ACTIVE PRODUCTION ENGINES (19)
Core business-logic engines actively used in production workflows.

| # | Class | File | Domain | Risk |
|---|---|---|---|---|
| 1 | `JournalEngine` | accounting/services/journal_engine.py | Accounting | LOW — core double-entry |
| 2 | `PaymentEngine` | payments/services.py | Payments | LOW — core payment processing |
| 3 | `FinancialReportEngine` | accounting/services/financial_reports.py | Accounting | LOW — core reports |
| 4 | `ExportEngine` | accounting/services/export_engine.py | Accounting | LOW — data export |
| 5 | `PrintEngine` | frontend/utils/print_engine.py | Printing | LOW — thermal/regular printing |
| 6 | `ThemeEngine` | frontend/theme/theme_engine.py | Theming | LOW — theme application |
| 7 | `InvoiceTemplateEngine` | frontend/utils/invoice_template_engine.py | Invoicing | LOW — HTML rendering |
| 8 | `AnomalyDetectionEngine` | core/services/anomaly_detection.py | Ops | MEDIUM — single responsibility |
| 9 | `FinancialPolicyEngine` | core/services/financial_policy_engine.py | Finance | LOW — credit/policy enforcement |
| 10 | `CreditPolicyEngine` | core/services/credit_policy_engine.py | Finance | LOW — credit limits |
| 11 | `CashFlowEngine` | cashflow/services/cashflow_engine.py | Cashflow | LOW — cash flow calc |
| 12 | `FinancialTruthEngine` | core/services/financial_truth_engine.py | Finance | MEDIUM — overlaps with StateReconstructionEngine |
| 13 | `OperationalIntelligenceEngine` | core/operations/operational_intelligence.py | Ops | LOW — Phase 12 |
| 14 | `SLAMonitoringEngine` | core/operations/operational_intelligence.py | Ops | LOW — Phase 12 |
| 15 | `CapacityForecastEngine` | core/operations/operational_intelligence.py | Ops | LOW — Phase 12 |
| 16 | `PharmacyRulesEngine` | pharmacy/services/rules_engine.py | Pharmacy | LOW |
| 17 | `DecisionEngine` | core/operations/decision_engine.py | Ops | MEDIUM — Phase 13 |
| 18 | `AlertManager` | core/operations/alerts.py | Ops | LOW — Phase 9 |
| 19 | `SignalCoordinator` | core/operations/signal_coordinator.py | Ops | LOW — Phase 12.1 |

### 1.2 INTELLIGENCE AUTONOMOUS ENGINES (4)
Autonomous intelligence layer added in Phase 17. Production-active but heavy.

| # | Class | File | Risk |
|---|---|---|---|
| 20 | `ReasoningEngine` | core/operations/intelligence_autonomous/reasoning_engine.py | MEDIUM — heavy abstraction |
| 21 | `PredictionEngine` | core/operations/intelligence_autonomous/prediction_engine.py | MEDIUM — overlaps with CapacityForecastEngine |
| 22 | `RiskEngine` | core/operations/intelligence_autonomous/risk_engine.py | MEDIUM — overlaps with FinancialPolicyEngine |
| 23 | `AnomalyForesightEngine` | core/operations/intelligence_autonomous/anomaly_foresight.py | MEDIUM — overlaps with AnomalyDetectionEngine |

**NOTE:** All 4 are wired through `AutonomousIntelligenceGateway` and exposed via `/api/v1/autonomous/`. They have partial overlap with existing production engines (CapacityForecastEngine, FinancialPolicyEngine, AnomalyDetectionEngine).

### 1.3 INTELLIGENCE MINING ENGINES (4)
Pattern mining and anomaly graph engines from Phase 17 intelligence layer.

| # | Class | File | Risk |
|---|---|---|---|
| 24 | `DriftDetectionEngine` | core/operations/intelligence/drift.py | MEDIUM — overlaps with operational_intelligence |
| 25 | `EventPatternMiningEngine` | core/operations/intelligence/patterns.py | MEDIUM — overlapping observability |
| 26 | `CrossDomainAnomalyGraphEngine` | core/operations/intelligence/anomaly_graph.py | MEDIUM — overlapping anomaly detection |
| 27 | `ReplayAnomalyReconstructionEngine` | core/operations/intelligence/reconstruction.py | MEDIUM — overlapping |

**NOTE:** All 4 are wired through `IntelligenceGateway` and have significant functional overlap with `AnomalyDetectionEngine` and `OperationalIntelligenceEngine`.

### 1.4 SHADOW OBSERVABILITY ENGINES (4)
Observability engines that overlap with the main operations layer.

| # | Class | File | Issue |
|---|---|---|---|
| 28 | `EventTraceEngine` | core/operations/observability/trace_engine.py | Overlaps with ops observability views |
| 29 | `CrossDomainCorrelationEngine` | core/operations/observability/correlation.py | Overlaps with SignalCoordinator |
| 30 | `ReplayVisualizationEngine` | core/operations/observability/replay.py | **CRITICAL** — simulation engine in production tree |
| 31 | `StateReconstructionEngine` | core/operations/truth/verifier.py | Overlaps with FinancialTruthEngine |

**CRITICAL:** `ReplayVisualizationEngine` lives in production code (`core/operations/observability/`) but is a simulation replay tool. It imports simulation engines directly.

### 1.5 PRODUCTION UTILITY ENGINE (1)

| # | Class | File | Risk |
|---|---|---|---|
| 32 | `BulkImportEngine` | core/import_pipeline.py | LOW — used by import views |

### 1.6 FRONTEND UI ENGINES (7)
Engines in the frontend — some are dashboard screens that may be experimental.

| # | Class | File | Status |
|---|---|---|---|
| 33 | `CausalReasoningEngine` | frontend/ui/cognitive_reasoning/causal_engine.py | ACTIVE — used by why_analysis_panel |
| 34 | `CognitiveFusionEngine` | frontend/ui/cognitive/fusion_engine.py | ACTIVE — used by cognitive_dashboard |
| 35 | `DecisionImpactEngine` | frontend/ui/causal_scoring/decision_impact_engine.py | ACTIVE — used by decision_ranking_dashboard |
| 36 | `CausalScoringEngine` | frontend/ui/causal_scoring/causal_scoring_engine.py | ACTIVE — used by causal_strength_panel |
| 37 | `ConsistencyEngine` | frontend/ui/governance/consistency_audit.py | ACTIVE — governance dashboard |
| 38 | `CorrelationEngine` | frontend/utils/logger.py | ACTIVE — log correlation |
| 39 | `BatchFixEngine` | frontend/scripts/batch_fix_engine.py | CI SCRIPT — not runtime |

### 1.7 FRONTEND RUNTIME ENGINES (3)
Runtime layer engines in `frontend/runtime/`.

| # | Class | File | Status |
|---|---|---|---|
| 40 | `IntentDetectionEngine` | frontend/runtime/orchestrator.py | ACTIVE — runtime intent detection |
| 41 | `PolicyEngine` | frontend/runtime/orchestrator.py | ACTIVE — runtime policy |
| 42 | `AutoHealingEngine` | frontend/runtime/auto_healer.py | MINIMALLY USED — only referenced by CognitiveFusionEngine |

### 1.8 SIMULATION ENGINES (27)
All engines in `backend/simulation/` tree.

| # | Class | File | Notes |
|---|---|---|---|
| 43 | `SimulationEngine` | simulation/engine/engine.py | Core simulation |
| 44 | `TruthEngine` | simulation/truth_engine/engine.py | Phase 3A |
| 45 | `RootCauseEngine` | simulation/truth_engine/root_cause/engine.py | Phase 3B |
| 46 | `ReplayEngine` | simulation/replay/replay_engine/replay_engine.py | **LEAKED** — imported by production views |
| 47 | `ControlCenterEngine` | simulation/control_center/orchestrator/control_center_engine.py | **LEAKED** — imported by production views |
| 48 | `EscalationEngine` | simulation/control_center/incidents/escalation_engine.py | DUPLICATED (also in recovery/) |
| 49 | `OperationalPriorityEngine` | simulation/control_center/state/operational_priority_engine.py | |
| 50 | `ContainmentEngine` | simulation/recovery/containment/containment_engine.py | |
| 51 | `PartialRollbackEngine` | simulation/recovery/execution/partial_rollback.py | |
| 52 | `ExternalRollbackEngine` | simulation/recovery/execution/external_rollback.py | |
| 53 | `RecoveryExecutionEngine` | simulation/recovery/execution/execution_engine.py | |
| 54 | `PredictiveEngine` | simulation/predictive/engine.py | |
| 55 | `FailureProbabilityEngine` | simulation/predictive/probability/failure_probability_engine.py | **DUPLICATED** |
| 56 | `FailureProbabilityEngine` | simulation/predictive/probability/engine.py | **DUPLICATED** (copied) |
| 57 | `BlastRadiusEngine` | simulation/recovery/blast_radius/blast_radius_engine.py | |
| 58 | `SimulationPolicyEngine` | simulation/workflows/policies/policies.py | |
| 59 | `EarlyWarningEngine` | simulation/predictive/warnings/early_warning_engine.py | **DUPLICATED** |
| 60 | `EarlyWarningEngine` | simulation/predictive/warnings/engine.py | **DUPLICATED** (copied) |
| 61 | `EscalationPolicyEngine` | simulation/recovery/escalation/escalation_policy.py | |
| 62 | `DigitalTwinPipeline` | simulation/digital_twin/pipeline/orchestrator.py | |
| 63 | `RecoveryPipeline` | simulation/recovery/orchestration/recovery_pipeline.py | **DUPLICATED** |
| 64 | `RecoveryPipeline` | simulation/recovery/models.py | **DUPLICATED** (model class) |
| 65 | `ReplayController` | simulation/replay/replay_engine/replay_controller.py | |
| 66 | `ReplayPipeline` | simulation/replay/orchestration/replay_pipeline.py | |
| 67 | `ReplaySessionManager` | simulation/replay/replay_engine/replay_session.py | |
| 68 | `TimelineCursorManager` | simulation/replay/timeline/timeline_cursor.py | |
| 69 | `SnapshotManager` | simulation/truth_engine/snapshot/snapshot.py | |

### 1.9 MANAGERS — ACTIVE PRODUCTION (14)

| # | Class | File | Notes |
|---|---|---|---|
| M1 | `BackupManager` | backup/backup_system.py | Core backup |
| M2 | `AuthManager` | frontend/security/auth_manager.py | Auth |
| M3 | `RSAKeyManager` | licensing/rsa.py | Key management |
| M4 | `CompanyManager` | core/models/system.py | Django ORM manager |
| M5 | `CompanyScopedManager` | core/multitenant/models.py | Django ORM manager |
| M6 | `NavigationManager` | frontend/ui/navigation/navigation_manager.py | Navigation |
| M7 | `LocaleManager` | frontend/i18n/localization.py | i18n |
| M8 | `LazyScreenManager` | frontend/ui/utils/lazy_loader.py | Screen loading |
| M9 | `InvoiceTemplateManager` | frontend/ui/system/invoice_template_manager.py | Invoice templates |
| M10 | `NotificationManager` | frontend/ui/components/notifications.py | Notifications |
| M11 | `LicenseManagerDialog` | frontend/ui/licensing/license_manager_dialog.py | Licensing |
| M12 | `RollbackManager` | core/drift_prevention/rollback_manager.py | Drift prevention |
| M13 | `StartupManager` | runner/startup.py | Startup orchestration |
| M14 | `_LoggerManager` | frontend/utils/logger.py | Logging |

### 1.10 MANAGERS — DEPRECATED / REDUNDANT (1)

| # | Class | File | Issue |
|---|---|---|---|
| M15 | `ThemeManager` | frontend/ui/theme/theme_manager.py | **DEPRECATED** — replaced by ThemeEngine in frontend/theme/ + SystemConfig API |

### 1.11 SIMULATION MANAGERS (8)

| # | Class | File | Notes |
|---|---|---|---|
| M16 | `SnapshotManager` | simulation/truth_engine/snapshot/snapshot.py | |
| M17 | `WarningRetentionManager` | simulation/predictive/warnings/warning_retention_manager.py | **DUPLICATED** |
| M18 | `WarningRetentionManager` | simulation/predictive/warnings/retention.py | **DUPLICATED** |
| M19 | `ReplaySessionManager` | simulation/replay/replay_engine/replay_session.py | |
| M20 | `ProbabilityThresholdManager` | simulation/predictive/probability/thresholds.py | **DUPLICATED** |
| M21 | `ProbabilityThresholdManager` | simulation/predictive/probability/probability_threshold_manager.py | **DUPLICATED** |
| M22 | `TimelineCursorManager` | simulation/replay/timeline/timeline_cursor.py | |
| M23 | `QuarantineManager` | simulation/recovery/containment/quarantine_manager.py | |

### 1.12 SCRIPTS (2)

| # | Class | File | Notes |
|---|---|---|---|
| S1 | `ClassificationPipeline` | frontend/scripts/classification_pipeline.py | CI script |
| S2 | `CIRolloutManager` | frontend/scripts/ci_rollout_strategy.py | CI script |

---

## SECTION 2 — DEPENDENCY MAP

### 2.1 CRITICAL: Production importing Simulation

**File:** `backend/core/operations/observability/views.py`
```python
from simulation.control_center.orchestrator.control_center_engine import ControlCenterEngine
from simulation.control_center.orchestrator.control_center_router import ControlCenterRouter
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.digital_twin.pipeline.digital_twin import DigitalTwin
```

**Risk:** HIGH. Production observability views depend on simulation infrastructure. If simulation code changes, production breaks. This is a reverse dependency — simulation should depend on production, not the other way.

**Recommendation:** Extract the simulation-needed interfaces into the production layer and have simulation import from production.

### 2.2 Intelligence Layer Gateway Chain

```
AutonomousIntelligenceGateway
  ├── ReasoningEngine → DecisionSuggester
  ├── PredictionEngine
  ├── AnomalyForesightEngine
  └── RiskEngine

IntelligenceGateway
  ├── DriftDetectionEngine
  ├── EventPatternMiningEngine
  ├── CrossDomainAnomalyGraphEngine
  └── ReplayAnomalyReconstructionEngine
```

**Risk:** MEDIUM. Two separate gateway engines with overlapping responsibilities. The autonomous layer (PredictionEngine, RiskEngine) overlaps with production engines (CapacityForecastEngine, FinancialPolicyEngine, AnomalyDetectionEngine).

### 2.3 Simulation Engine Internal Dependencies

```
SimulationEngine → SimulationPolicyEngine
SimulationEngine → TruthEngine → RootCauseEngine
SimulationEngine → ReplayEngine → ReplayPipeline → ReplayController
SimulationEngine → RecoveryExecutionEngine → ContainmentEngine, BlastRadiusEngine, EscalationEngine
SimulationEngine → PredictiveEngine → FailureProbabilityEngine, EarlyWarningEngine
EscalationEngine → EscalationPolicyEngine
```

**Risk:** HIGH complexity. The simulation engine depends on 25+ sub-engines in a deep hierarchy. Any change has cascading effects.

---

## SECTION 3 — DUPLICATION MAP

| Class Name | File 1 | File 2 | Notes |
|---|---|---|---|
| `FailureProbabilityEngine` | simulation/predictive/probability/failure_probability_engine.py | simulation/predictive/probability/engine.py | Exact duplicate |
| `EarlyWarningEngine` | simulation/predictive/warnings/early_warning_engine.py | simulation/predictive/warnings/engine.py | Exact duplicate |
| `RecoveryPipeline` | simulation/recovery/models.py | simulation/recovery/orchestration/recovery_pipeline.py | Different implementations |
| `EscalationEngine` | simulation/control_center/incidents/escalation_engine.py | simulation/recovery/escalation/escalation_engine.py | Related but different |
| `WarningRetentionManager` | simulation/predictive/warnings/warning_retention_manager.py | simulation/predictive/warnings/retention.py | Exact duplicate |
| `ProbabilityThresholdManager` | simulation/predictive/probability/thresholds.py | simulation/predictive/probability/probability_threshold_manager.py | Exact duplicate |

**6 duplicated classes** — all in simulation tree. The `engine.py` / `warning_retention_manager.py` / `thresholds.py` copies suggest an abandoned refactoring attempt.

### 3.1 Functional Overlaps

| Overlap Group | Engines Involved | Risk |
|---|---|---|
| **Anomaly Detection** | AnomalyDetectionEngine, AnomalyForesightEngine, CrossDomainAnomalyGraphEngine, DriftDetectionEngine | 4 engines for anomaly detection |
| **Financial Truth** | FinancialTruthEngine, StateReconstructionEngine | 2 engines for same purpose |
| **Prediction/Forecast** | PredictionEngine, CapacityForecastEngine, PredictiveEngine | 3 engines for prediction |
| **Policy enforcement** | FinancialPolicyEngine, CreditPolicyEngine, PolicyEngine (frontend) | 3 policy engines |
| **Observability** | EventTraceEngine, CrossDomainCorrelationEngine, operational_intelligence | Duplicated observability |

---

## SECTION 4 — DEAD CODE CANDIDATES

| Class | File | Reason |
|---|---|---|
| `ThemeManager` | frontend/ui/theme/theme_manager.py | Marked deprecated, replaced by ThemeEngine |
| `BatchFixEngine` | frontend/scripts/batch_fix_engine.py | Script-only, not imported at runtime |
| `FailureProbabilityEngine` (duplicate) | simulation/predictive/probability/engine.py | Exact duplicate |
| `EarlyWarningEngine` (duplicate) | simulation/predictive/warnings/engine.py | Exact duplicate |
| `WarningRetentionManager` (duplicate) | simulation/predictive/warnings/retention.py | Exact duplicate |
| `ProbabilityThresholdManager` (duplicate) | simulation/predictive/probability/probability_threshold_manager.py | Exact duplicate |

---

## SECTION 5 — SIMULATION BOUNDARIES

### 5.1 Clean Separation (✅)
- `backend/simulation/` tree — 27 engines, all isolated
- `tests/test_simulation*.py` — properly contained
- `tests/test_audit.py` — properly contained

### 5.2 Boundary Violations (❌)
1. **`core/operations/observability/views.py`** imports 4 simulation classes
2. **`core/operations/observability/replay.py`** contains `ReplayVisualizationEngine` — a simulation visualization tool living in production code
3. **`frontend/runtime/auto_healer.py`** is in production but only referenced by frontend cognitive dashboard

---

## SECTION 6 — RISK CLASSIFICATION

### CRITICAL RISKS
1. **Production ⇄ Simulation dependency** — `views.py` imports simulation engines
2. **6 duplicated classes** — abandoned refactoring attempt in simulation tree
3. **4 anomaly engines** — functional overlap causing confusion

### HIGH RISKS
4. **2 intelligence gateways** — AutonomousIntelligenceGateway + IntelligenceGateway with overlapping scopes
5. **3 prediction engines** — PredictionEngine, CapacityForecastEngine, PredictiveEngine
6. **Simulation engine hierarchy** — 25+ sub-engines in deep dependency chain

### MEDIUM RISKS
7. **Frontend UI engines (7)** — Cognitive/Causal engines increase frontend complexity
8. **OperationalIntelligenceEngine + SLAMonitoringEngine + CapacityForecastEngine** — could be simplified to 1 engine

### LOW RISKS
9. **Frontend runtime engines (3)** — limited impact, contained in runtime/
10. **Single-class Managers (14)** — minimal risk, standard pattern

---

## SECTION 7 — REMOVAL CANDIDATES

| Class | File | Justification | Priority |
|---|---|---|---|
| `ThemeManager` (deprecated) | frontend/ui/theme/theme_manager.py | Superseded by ThemeEngine | HIGH |
| Duplicate simulation classes (6) | simulation/predictive/probability/ | Abandoned refactoring artifacts | HIGH |
| `ReplayVisualizationEngine` | core/operations/observability/replay.py | Simulation tool in production tree | MEDIUM |
| `AutoHealingEngine` | frontend/runtime/auto_healer.py | Only used in 1 place, minimal value | MEDIUM |
| `StateReconstructionEngine` | core/operations/truth/verifier.py | Overlaps with FinancialTruthEngine | LOW |

---

## SECTION 8 — RECOMMENDATIONS

### Must Fix (Phase 32.1)
1. **Remove production ⇄ simulation dependency**: Extract interfaces needed by observability views into production code. Simulation engines should not be importable by production.
2. **Consolidate anomaly detection**: Merge AnomalyDetectionEngine + DriftDetectionEngine + CrossDomainAnomalyGraphEngine + AnomalyForesightEngine into a single engine
3. **Remove duplicated simulation classes**: Delete the 6 duplicated files (abandoned refactoring artifacts)

### Should Fix (Phase 32.2)
4. **Consolidate prediction**: Merge PredictionEngine + CapacityForecastEngine
5. **Deprecate frontend `ui/theme/theme_manager.py`**: Already superseded
6. **Move ReplayVisualizationEngine to simulation/ tree**

### Could Fix (Phase 32.3)
7. **Merge FinancialTruthEngine + StateReconstructionEngine**
8. **Simplify observability engines**: Reduce EventTraceEngine + CrossDomainCorrelationEngine overlap
9. **Remove unused frontend runtime engines** if confirmed dead code

---

## APPENDIX A — FULL CLASSIFICATION TABLE

```
LEGEND:
  [ACT] = Active Production     [SIM] = Simulation Only
  [DUP] = Duplicated            [SHD] = Shadow/Overlapping
  [UI ] = Frontend UI           [RTE] = Frontend Runtime
  [DEP] = Deprecated/Dead       [SCR] = CI Script
  [LEAK] = Simulation in Production

Engine Classes (59):
  [ACT] JournalEngine                    backend/accounting/services/journal_engine.py
  [ACT] PaymentEngine                    backend/payments/services.py
  [ACT] FinancialReportEngine            backend/accounting/services/financial_reports.py
  [ACT] ExportEngine                     backend/accounting/services/export_engine.py
  [ACT] PrintEngine                      frontend/utils/print_engine.py
  [ACT] ThemeEngine                      frontend/theme/theme_engine.py
  [ACT] InvoiceTemplateEngine            frontend/utils/invoice_template_engine.py
  [ACT] AnomalyDetectionEngine           backend/core/services/anomaly_detection.py
  [ACT] FinancialPolicyEngine            backend/core/services/financial_policy_engine.py
  [ACT] CreditPolicyEngine               backend/core/services/credit_policy_engine.py
  [ACT] CashFlowEngine                   backend/cashflow/services/cashflow_engine.py
  [ACT] FinancialTruthEngine             backend/core/services/financial_truth_engine.py
  [ACT] OpsIntelligenceEngine            backend/core/operations/operational_intelligence.py
  [ACT] SLAMonitoringEngine              backend/core/operations/operational_intelligence.py
  [ACT] CapacityForecastEngine           backend/core/operations/operational_intelligence.py
  [ACT] PharmacyRulesEngine              backend/pharmacy/services/rules_engine.py
  [ACT] DecisionEngine                   backend/core/operations/decision_engine.py
  [ACT] BulkImportEngine                 backend/core/import_pipeline.py
  [ACT] EventTraceEngine                 backend/core/operations/observability/trace_engine.py
  [ACT] CrossDomainCorrelationEngine     backend/core/operations/observability/correlation.py
  [SHD] StateReconstructionEngine        backend/core/operations/truth/verifier.py
  [SHD] ReplayVisualizationEngine        backend/core/operations/observability/replay.py
  [INT] ReasoningEngine                  backend/core/operations/intelligence_autonomous/reasoning_engine.py
  [INT] PredictionEngine                 backend/core/operations/intelligence_autonomous/prediction_engine.py
  [INT] RiskEngine                       backend/core/operations/intelligence_autonomous/risk_engine.py
  [INT] AnomalyForesightEngine           backend/core/operations/intelligence_autonomous/anomaly_foresight.py
  [INT] DriftDetectionEngine             backend/core/operations/intelligence/drift.py
  [INT] EventPatternMiningEngine         backend/core/operations/intelligence/patterns.py
  [INT] CrossDomainAnomalyGraphEngine    backend/core/operations/intelligence/anomaly_graph.py
  [INT] ReplayAnomalyReconstructionEng   backend/core/operations/intelligence/reconstruction.py
  [UI ] CausalReasoningEngine            frontend/ui/cognitive_reasoning/causal_engine.py
  [UI ] CognitiveFusionEngine            frontend/ui/cognitive/fusion_engine.py
  [UI ] DecisionImpactEngine             frontend/ui/causal_scoring/decision_impact_engine.py
  [UI ] CausalScoringEngine              frontend/ui/causal_scoring/causal_scoring_engine.py
  [UI ] ConsistencyEngine                frontend/ui/governance/consistency_audit.py
  [UI ] CorrelationEngine                frontend/utils/logger.py
  [SCR] BatchFixEngine                   frontend/scripts/batch_fix_engine.py
  [RTE] IntentDetectionEngine            frontend/runtime/orchestrator.py
  [RTE] PolicyEngine                     frontend/runtime/orchestrator.py
  [RTE] AutoHealingEngine                frontend/runtime/auto_healer.py
  [SIM] SimulationEngine                 backend/simulation/engine/engine.py
  [SIM] TruthEngine                      backend/simulation/truth_engine/engine.py
  [SIM] RootCauseEngine                  backend/simulation/truth_engine/root_cause/engine.py
  [SIM] ReplayEngine                     backend/simulation/replay/replay_engine/replay_engine.py
  [LEAK] ControlCenterEngine             backend/simulation/control_center/orchestrator/...
  [SIM] EscalationEngine                 backend/simulation/control_center/incidents/...
  [SIM] OperationalPriorityEngine        backend/simulation/control_center/state/...
  [SIM] ContainmentEngine                backend/simulation/recovery/containment/...
  [SIM] PartialRollbackEngine            backend/simulation/recovery/execution/...
  [SIM] ExternalRollbackEngine           backend/simulation/recovery/execution/...
  [SIM] RecoveryExecutionEngine          backend/simulation/recovery/execution/...
  [SIM] PredictiveEngine                 backend/simulation/predictive/engine.py
  [DUP] FailureProbabilityEngine         backend/simulation/predictive/probability/...
  [SIM] BlastRadiusEngine                backend/simulation/recovery/blast_radius/...
  [SIM] SimulationPolicyEngine           backend/simulation/workflows/policies/policies.py
  [DUP] EarlyWarningEngine               backend/simulation/predictive/warnings/...
  [SIM] EscalationPolicyEngine           backend/simulation/recovery/escalation/...
  [SIM] DigitalTwinPipeline              backend/simulation/digital_twin/pipeline/...
  [DUP] RecoveryPipeline                 backend/simulation/recovery/...
```

---

**End of Report**
