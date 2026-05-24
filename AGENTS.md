# Pharmacy ERP — Project Context

## Project Overview
- **Name**: Pharmacy ERP
- **Type**: Desktop ERP for pharmaceutical distribution
- **Frontend**: PySide6 (Qt for Python) — `D:\Projects\Pharmacy_ERP\frontend\`
- **Backend**: Django + DRF — `D:\Projects\Pharmacy_ERP\backend\`
- **Database**: PostgreSQL (configured in `backend/config/settings.py`)
- **Base Currency**: AFN (Afghan Afghani) / USD

---

## Current Status: Phase UX.5 COMPLETE

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Foundation (models, base UI) | ✅ Complete |
| Phase 2A-2E | Inventory (products, categories, warehouses, batches, UI) | ✅ Complete |
| Phase 3A-3E | Sales & Purchase (invoices, stock integration, UI, PDF) | ✅ Complete |
| Phase 4A | Chart of Accounts (37 accounts, hierarchy) | ✅ Complete |
| Phase 4B | Journal Entry Engine (double-entry, posting, reversal) | ✅ Complete |
| Phase 4C | Payment & Financial Transactions (Cash, Bank, Mobile, Hawala) | ✅ Complete |
| Phase 4D | Financial Reports (Trial Balance, P&L, Balance Sheet, AR/AP Aging, Cash Flow, CSV export) | ✅ Complete |
| **Phase 4E** | **Accounting UI (dashboard, ledger, journal forms, report screens)** | **✅ Complete** |
| **Phase 6D** | **Final Testing + Code Cleanup (test suite, coverage, bug fixes)** | **✅ Complete** |
| **Phase 5** | **Auth, Warehouse Transfers, Notifications** | **✅ Complete** |
| **Phase 7A** | **HR Foundation (Employee, Department, Position)** | ✅ Complete |
| **Phase 7B** | **Attendance System (Attendance, Leave, Overtime)** | ✅ Complete |
| **Phase 7C** | **Payroll Foundation (Salary, Allowance, Deduction, PayrollCycle)** | ✅ Complete |
| **Phase 7D** | **Payroll Accounting (PayrollAccountingService)** | ✅ Complete |
| **Phase 7E** | **HR & Payroll Reports** | ✅ Complete |
| **Phase 7F** | **Restore System (RestorePoint, validation, rollback)** | ✅ Complete |
| **Phase 8** | **API Standardization (StandardizedJSONRenderer, APIResponse)** | ✅ Complete |
| **Phase 9** | **Production Operations (health, financial/inventory integrity, alerts)** | ✅ Complete |
| **Phase 9B** | **API Observability (bad request intelligence, slow request detection)** | ✅ Complete |
| **Phase 9C** | **Future Stability (scalability, concurrency, data integrity)** | ✅ Complete |
| **Phase 9D** | **Sustainability Guardrails (complexity control, performance budgets)** | ✅ Complete |
| **Phase 9E** | **Enterprise Stability Refinement (adaptive sampling, config versioning)** | ✅ Complete |
| **Phase 11** | **Enterprise Control Center (ControlCenterAggregator dashboards)** | ✅ Complete |
| **Phase 12** | **Advanced Operational Intelligence (SLA, Capacity Forecast, Alerts)** | ✅ Complete |
| **Phase 12.1** | **Intelligence Stability Patch (RuleRegistry, SignalCoordinator)** | ✅ Complete |
| **Phase 13** | **Decision Intelligence Engine + Configuration Integrity** | ✅ Complete |
| **Phase 3B.5** | **Intelligence Stabilization Audit (audit layer, health report)** | ✅ Complete |
| **Phase 6D** | **Returns Cycle (backend models, approval, reconciliation, void/reversal, 39 tests)** | ✅ Complete |
| **Phase 14** | **Reconciliation UI + Void/Reversal Flow (reconciliation screen, void button, return from invoice)** | ✅ Complete |
| **Phase 14C** | **Export & Print (CSV export for returns/reconciliation, PDF receipt generation, 3 new tests)** | ✅ Complete |
| **Phase UX.1** | **Bug Fix Layer (34 bugs: token interpolation, navigation, sidebar tracking, hardcoded hex)** | ✅ Complete |
| **Phase UX.2** | **Enterprise Component Governance (dead UI cleanup, component consolidation, 6-layer audit)** | ✅ Complete |
| **Phase UX.3** | **Enterprise UI Foundation Migration (BaseScreen + EnterpriseDialog governance)** | ✅ Complete |
| **Phase UX.4** | **Enterprise UI Governance Lockdown (accounting BaseScreen, dialog standard, visual density, theme token enforcement)** | ✅ Complete |
| **Phase UX.5** | **Intelligent UX Operations & Runtime Governance (telemetry, perceived performance, workflow intelligence, observability, design system freeze)** | ✅ Complete |

### Test Suite Summary
- **1358+ tests passing** (995 ERP + 363 simulation)
- **Coverage**: Inventory 93.94%, Accounting 72.11%, Sales ~96%, Purchases ~96%, Overall ~50%
- **Key fixes in Phase 5**:
  - Fixed `StockMovement._update_batch_quantity()` to skip TRANSFER movements (was resetting batch to 0)
  - Fixed `Batch.save()` to handle `remaining_quantity` correctly (was treating Decimal('0.00') as falsy)
  - Fixed Notification model `object_id` field to allow NULL
- **Transfer bug**: `StockMovement._update_batch_quantity()` only counted IN/OUT movements, not TRANSFER. When transfer OUT movement was created, it calculated -50 (no IN yet) and reset batch to 0. Fix: Skip recalculation for TRANSFER movements.
- **Test files**: `test_accounting.py`, `test_inventory.py`, `test_sales.py`, `test_purchases.py`, `test_api.py`, `test_lifecycle.py`, `test_edge_cases.py`, `test_lifecycle_full.py`, `test_accounting_viewset.py`, `test_accounting_views.py`, `test_inventory_views.py`, `test_sales_views.py`, `test_purchases_views.py`, `test_financial_reports.py`, `test_services.py`, `test_auth.py`, `test_transfer.py`, `test_notifications.py`
- **Simulation test files**: `test_simulation.py`, `test_agents.py`, `test_workflows.py`, `test_truth_engine.py`, `test_root_cause.py`, `test_audit.py`

### Phase 7E Steps Completed
1. ✅ Created HR Reports service (`hr/services/reports.py`)
2. ✅ Created Payroll Reports service (`payroll/services/reports.py`)
3. ✅ Added employee list, attendance, leave, payroll API endpoints

### Phase 7F Steps Completed
1. ✅ Added RestorePoint model (`backup/models.py`)
2. ✅ Added RestoreValidation model (`backup/models.py`)
3. ✅ Created RestoreService with validation (`backup/services/restore_service.py`)
4. ✅ Created restore API endpoints (`backup/views.py`)
5. ✅ Added serializers (`backup/serializers.py`)
6. ✅ Added routes (`backup/urls.py`)
7. ✅ Created migration (`backup/migrations/0002_restorepoint_restorevalidation_and_more.py`)
8. ✅ Created restore tests (`tests/test_restore.py`)

### Phase 7F Files Created/Modified
- `backup/models.py`: Added RestorePoint, RestoreValidation models
- `backup/services/restore_service.py`: RestoreService with validation
- `backup/views.py`: Added RestorePointViewSet
- `backup/serializers.py`: Added RestorePointSerializer, RestoreValidationSerializer
- `backup/urls.py`: Added restore-points route
- `tests/test_restore.py`: Restore service tests

### API Contract Standardization (Phase 8)
All API responses now follow a standardized format with automatic company context injection.

**New Files:**
| File | Purpose |
|------|---------|
| `core/api/responses.py` | APIResponse class (success, error, paginated methods) |
| `core/api/errors.py` | Error code registry (40+ codes: AUTH_*, FIN_*, INV_*, etc.) |
| `core/api/pagination.py` | StandardizedPagination for consistent pagination |
| `core/api/renderers.py` | StandardizedJSONRenderer - auto-wraps all responses |
| `core/api/mixins.py` | StandardizedResponseMixin for ViewSets |

**Standard Response Format:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "company_id": "uuid"  (when company context set)
  }
}
```

**Error Response Format:**
```json
{
  "success": false,
  "error": { "code": "AUTH_001", "message": "..." },
  "meta": { ... }
}
```

**API Versioning:** Accept-header based (`Accept: application/json; version=v1`)

### Phase 12 Steps Completed
Advanced Operational Intelligence Layer - DETERMINISTIC (NO AI/ML):
1. ✅ Created `core/operations/operational_intelligence.py` with:
   - RuleBasedAnomalyDetector (8 static rules with thresholds)
   - TrendIdentifier (latency, error, stock trend detection)
   - RiskPredictor (SLA, stockout, journal imbalance, batch expiry prediction)
   - SLAMonitoringEngine (compliance score 0-100, violations, degradation timeline)
   - CapacityForecastEngine (linear extrapolation, moving average, historical comparison)
   - IntelligenceAlertSystem (structured alerts with explanation, metric comparison, baseline)
   - CachedIntelligenceAggregator (60s TTL cache, no blocking operations)
2. ✅ Created `tests/test_operational_intelligence.py` (63 tests)
3. ✅ Added endpoint `/api/control-center/intelligence/`
4. ✅ All tests passing

### Phase 12 Validation Output
| Component | Status |
|---|---|
| BASELINE ENGINE | PASS |
| ANOMALY DETECTION | PASS |
| TREND DETECTION | PASS |
| SLA MONITORING | PASS |
| CAPACITY FORECAST | PASS |
| ALERT SYSTEM | PASS |
| PERFORMANCE IMPACT | LOW |
| PRODUCTION READINESS | READY |

### Phase 12 Files Created
- `core/operations/operational_intelligence.py`: All intelligence components
- `tests/test_operational_intelligence.py`: 63 tests for all components

### Phase 12.1 Validation Output
| Component | Status |
|---|---|
| RULE REGISTRY | PASS |
| NO INLINE RULES IN INTELLIGENCE ENGINE | PASS |
| SIGNAL DEDUPLICATION WORKS | PASS |
| CONTROL CENTER CONSISTENCY | PASS |
| ALERT DUPLICATION ELIMINATED | PASS |
| PRODUCTION READINESS | READY |

### Phase 12.1 Files Created
- `core/operations/signal_coordinator.py`: Signal deduplication layer
- RuleRegistry: Centralized rule governance (20+ rules)
- SignalCoordinator: 10-min deduplication window, severity override, signal merging

### Phase 12.1 Architecture
- Intelligence Layer = signal producer ONLY
- SignalCoordinator = single truth layer
- Control Center = signal consumer ONLY
- Alert System = formatted output ONLY

### Phase 3A — Truth Comparison Engine (Simulation)
| Component | Status |
|---|---|
| ExpectedStateCollector | ✅ Done |
| ActualStateCollector (read-only Django ORM) | ✅ Done |
| TruthComparator (6 mismatch types) | ✅ Done |
| IntegrityScorer (5 scores, penalty-based) | ✅ Done |
| TruthReportGenerator (severity, hints, conclusion) | ✅ Done |
| SnapshotManager (versioned, bounded) | ✅ Done |
| TruthEngine orchestrator | ✅ Done |
| Wired into SimulationEngine (passive hook) | ✅ Done |
| Test suite (55 + 8 integration = 63 tests) | ✅ Done |

### Phase 3A Key Architecture
- **TruthEngine** (`simulation/truth_engine/engine.py`): Orchestrates collect → compare → score → report → snapshot
- **SimulationEngine integration**: Passive observation via `enable_truth_engine: True` config flag
- **Isolation**: All 6 collector methods chain via `return self` for fluent API; `build()` returns `ActualState`
- **Exception safety**: TruthEngine failures are caught and logged, never crash the simulation
- **Read-only**: No ERP writes, no automatic correction, all mismatches explicitly logged

### Phase 3A Files Created
- `simulation/truth_engine/models/models.py`: Mismatch, MismatchType, MismatchSeverity, ExpectedState, ActualState, DriftReport
- `simulation/truth_engine/collector/expected.py`: ExpectedStateCollector
- `simulation/truth_engine/collector/actual.py`: ActualStateCollector (Django ORM, read-only)
- `simulation/truth_engine/comparator/comparator.py`: TruthComparator
- `simulation/truth_engine/scoring/scorer.py`: IntegrityScorer
- `simulation/truth_engine/reports/reporter.py`: TruthReportGenerator
- `simulation/truth_engine/snapshot/snapshot.py`: SnapshotManager
- `simulation/truth_engine/engine.py`: TruthEngine orchestrator
- `simulation/tests/test_truth_engine.py`: 55 tests
- `simulation/tests/test_simulation.py`: 8 integration tests (TestTruthEngineIntegration)

### Phase 3B — Root Cause Intelligence Engine
| Component | Status |
|---|---|
| EventCorrelator (event chain linking) | ✅ Done |
| RootCauseClassifier (7 cause types, confidence scoring) | ✅ Done |
| CausalAnalyzer (dependency chain analysis) | ✅ Done |
| DriftPatternDetector (5 rule-based patterns) | ✅ Done |
| RootCauseExplainer (structured explanations) | ✅ Done |
| CausalGraphBuilder (DAG construction) | ✅ Done |
| DriftMemoryStore (historical pattern storage) | ✅ Done |
| RootCauseEngine orchestrator | ✅ Done |
| Read-only architecture (no ERP writes) | ✅ Verified |
| Test suite (71 tests) | ✅ Done |

### Phase 3B Key Architecture
- **RootCauseEngine** (`simulation/truth_engine/root_cause/engine.py`): Orchestrates analyze → classify → explain → graph → remember
- **Phase 3A integration**: Reads mismatch data from TruthEngine output — read-only, no mutations
- **7 cause types**: LOGIC_ERROR, CONCURRENCY_ISSUE, MISSING_MAPPING, WORKFLOW_DESIGN_FLAW, DATA_INCONSISTENCY, TIMING_DESYNC, UNKNOWN_CAUSE
- **5 drift patterns**: repeated_inventory_drift, payment_failure_under_load, journal_imbalance_concurrency, partial_workflow_execution, concurrent_access_conflict
- **Exception safety**: All failures caught and logged, never crash the simulation

### Phase 3B Files Created
- `simulation/truth_engine/root_cause/models.py`: RootCause, CausalChain, CausalLink, DriftPattern, CausalGraph, Explanation
- `simulation/truth_engine/root_cause/correlator/event_correlator.py`: EventCorrelator
- `simulation/truth_engine/root_cause/classifier/root_cause_classifier.py`: RootCauseClassifier
- `simulation/truth_engine/root_cause/analyzer/causal_analyzer.py`: CausalAnalyzer
- `simulation/truth_engine/root_cause/patterns/drift_pattern_detector.py`: DriftPatternDetector
- `simulation/truth_engine/root_cause/explainer/explanation_engine.py`: RootCauseExplainer
- `simulation/truth_engine/root_cause/graph/causal_graph_builder.py`: CausalGraphBuilder
- `simulation/truth_engine/root_cause/history/drift_memory.py`: DriftMemoryStore
- `simulation/truth_engine/root_cause/engine.py`: RootCauseEngine orchestrator
- `simulation/tests/test_root_cause.py`: 71 tests

### Phase 3B.5 — Intelligence Stabilization Audit
| Component | Status |
|---|---|
| EventLifecycleAnalyzer (orphans, duplicates, recursion, fan-out) | ✅ Done |
| EventRetentionValidator (bounded history, leak detection) | ✅ Done |
| EventTopologyReporter | ✅ Done |
| GraphIntegrityValidator (DAG cycles, orphans, density) | ✅ Done |
| GraphMemoryAuditor (bounded node/edge storage) | ✅ Done |
| GraphComplexityAnalyzer (depth, branching, traversal cost) | ✅ Done |
| MemoryBoundaryValidator (bounded maxlen across structures) | ✅ Done |
| StoragePressureAnalyzer | ✅ Done |
| RetentionPolicyVerifier | ✅ Done |
| DependencyAnalyzer (production import scanner) | ✅ Done |
| LayerIsolationValidator (strict separation) | ✅ Done |
| CouplingRiskReporter | ✅ Done |
| SimulationLoadAnalyzer | ✅ Done |
| ScalabilityEstimator | ✅ Done |
| StabilityThresholdValidator | ✅ Done |
| IntelligenceHealthReportGenerator (score 0–100) | ✅ Done |
| Test suite (37+ tests, 43 in test_audit.py) | ✅ Done |

### Phase 3B.5 Key Architecture
- **Read-only**: All 16 components are analyzers — they read simulation structures, never mutate them
- **Bounded memory**: Every bounded structure audited for maxlen enforcement (deque, list caps)
- **DAG safety**: GraphIntegrityValidator detects cycles before they enter the graph
- **Layer isolation**: DependencyAnalyzer scans file-level imports; `ALLOWED_BRIDGE_FILES` exempts the one legitimate production bridge (`actual.py`)
- **No prediction**: All alerts are rule-based threshold checks, zero AI/ML
- **Exception safety**: All component failures caught and logged, never crash the audit

### Phase 3B.5 Files Created
| File | Purpose |
|------|---------|
| `simulation/audit/event_lifecycle/analyzer.py` | EventLifecycleAnalyzer |
| `simulation/audit/event_lifecycle/validator.py` | EventRetentionValidator |
| `simulation/audit/event_lifecycle/reporter.py` | EventTopologyReporter |
| `simulation/audit/graph/validator.py` | GraphIntegrityValidator |
| `simulation/audit/graph/auditor.py` | GraphMemoryAuditor |
| `simulation/audit/graph/analyzer.py` | GraphComplexityAnalyzer |
| `simulation/audit/memory/validator.py` | MemoryBoundaryValidator |
| `simulation/audit/memory/analyzer.py` | StoragePressureAnalyzer |
| `simulation/audit/memory/verifier.py` | RetentionPolicyVerifier |
| `simulation/audit/dependencies/analyzer.py` | DependencyAnalyzer |
| `simulation/audit/dependencies/validator.py` | LayerIsolationValidator |
| `simulation/audit/dependencies/reporter.py` | CouplingRiskReporter |
| `simulation/audit/performance/analyzer.py` | SimulationLoadAnalyzer |
| `simulation/audit/performance/estimator.py` | ScalabilityEstimator |
| `simulation/audit/performance/validator.py` | StabilityThresholdValidator |
| `simulation/audit/reporting/generator.py` | IntelligenceHealthReportGenerator |
| `simulation/tests/test_audit.py` | 43 tests across 18 test classes |

---

## Where to Start Next

### Recommended Next Steps
1. **Migrate accounting screens (6)** to BaseScreen: ChartOfAccounts, JournalEntry, AccountLedger, ReportBrowser, FinancialIntegrity, FinancialAudit
2. **Migrate simple dialogs (7)** to EnterpriseDialog: EmailConfigDialog, BatchFormDialog, CategoryFormDialog, WarehouseFormDialog, ProductFormDialog, CreditWarningDialog, AccountFormDialog
3. **Remove remaining hardcoded hex colors** in 9 screen files
4. **Replace remaining raw QPushButton** (~15 instances)
5. **Run backend**: `cd backend && python manage.py runserver`
6. **Seed data**: `python manage.py seed_payments` (payment methods + accounts)

### Quick Verification Commands
```bash
# Backend health check
cd backend && python manage.py check

# Verify payment data seeded
python manage.py shell -c "from payments.models import PaymentMethod; print(PaymentMethod.objects.count())"

# Verify accounting data
python manage.py shell -c "from accounting.models import Account; print(Account.objects.count())"
```

### UI Architecture Standards (CANONICAL)
**Single source of truth for all screen implementations.**

**Screen inheritance:**
- ALL new screens MUST inherit from `ui/screens/base_screen.py:BaseScreen`
- Use `BaseFormScreen` for form-based screens, `BaseListScreen` for list/table screens
- Do NOT use `QWidget` or `QFrame` directly — you will miss lifecycle features

**Component usage (mandatory):**
- Buttons: `EnterpriseButton` + `ButtonVariant` + `ButtonSize` — never raw `QPushButton`
- Display tables: `EnterpriseTable` + `TableColumn` — never raw `QTableWidget` for read-only data
- Editable grids: `DataEntryGrid` — for interactive line-item entry
- Forms grouping: `FormSection` — wraps QGroupBox + QFormLayout with consistent spacing
- Loading/error/empty states: `ScreenStateHelper` — standardized label management
- Typography: Use `TEXT_PAGE_TITLE`, `TEXT_CARD_TITLE`, `TEXT_BODY`, `TEXT_HELPER` only
- Spacing: Use `MARGIN_PAGE`, `SPACING_SM/MD/LG/XL` only

**Forbidden:**
- Raw hex colors (must use `COLOR_*` tokens)
- Renderer-layer classes (`ButtonRenderer`, `TableRenderer`, `DialogRenderer`, `CardRenderer`, `BadgeRenderer`)
- Inline `setStyleSheet()` with hardcoded values (only with `COLOR_*`/`SPACING_*` tokens)

---

## Architecture Overview

### Backend (`backend/`)
```
backend/
├── config/                  # Django settings, URLs
├── accounting/              # Chart of accounts, journal entries, financial reports
│   ├── models.py            # Account, JournalEntry, JournalEntryLine
│   ├── services/
│   │   ├── account_hierarchy.py
│   │   ├── journal_engine.py       # Double-entry engine
│   │   ├── financial_reports.py    # All financial reports
│   │   └── report_exporter.py      # CSV/text export
│   └── views_account.py            # All accounting API endpoints
├── payments/                # Payment infrastructure
│   ├── models.py            # PaymentMethod, PaymentAccount, FinancialTransaction, Settlement
│   ├── services.py          # PaymentEngine (receipts, payments, transfers, refunds)
│   └── views.py             # Payment API endpoints
├── sales/                   # Customers, sales invoices, payments
├── purchases/               # Suppliers, purchase invoices, payments
├── inventory/               # Products, batches, warehouses, stock movements
└── core/                    # Base models, auth
```

### Frontend (`frontend/`)
```
frontend/
├── ui/
│   ├── main_window.py       # Main window with QStackedWidget (21 pages)
│   ├── sidebar.py           # Navigation sidebar (21 items with group headers)
│   ├── accounting/          # All accounting screens
│   │   ├── accounting_dashboard.py
│   │   ├── chart_of_accounts_screen.py
│   │   ├── journal_entry_screen.py
│   │   ├── account_ledger_screen.py
│   │   ├── base_report_screen.py
│   │   ├── trial_balance_screen.py
│   │   ├── profit_loss_screen.py
│   │   ├── balance_sheet_screen.py
│   │   ├── arap_ageing_screen.py
│   │   └── components/
│   │       ├── account_form_dialog.py
│   │       ├── journal_entry_form.py
│   │       ├── journal_entry_detail.py
│   │       └── report_preview_dialog.py
│   ├── inventory/           # Product, category, warehouse, batch screens
│   ├── sales/               # Sales invoice screen
│   └── purchases/           # Purchase invoice screen
└── api/client.py            # API client (requests-based)
```

---

## Key Integration Points

### Auto Journal Entry Creation
- **Sales Invoice dispatch** → Creates SALE journal entry (Dr AR, Cr Revenue, Cr Tax)
- **Sales payment** → Creates RECEIPT journal entry (Dr Cash, Cr AR)
- **Sales cancel** → Reverses journal entry
- **Purchase receive** → Creates PURCHASE journal entry (Dr Inventory, Cr AP)
- **Purchase payment** → Creates PAYMENT journal entry (Dr AP, Cr Cash)
- **Purchase cancel** → Reverses journal entry

### Payment Flow
- `CustomerPayment.save()` → Auto-creates `FinancialTransaction` via `PaymentEngine.process_receipt()`
- `SupplierPayment.save()` → Auto-creates `FinancialTransaction` via `PaymentEngine.process_payment()`

### API Base URL
- Backend: `http://localhost:8000`
- Frontend API client default: `http://localhost:8000`

---

## Key Files to Reference

| Purpose | File |
|---|---|
| All accounting models | `backend/accounting/models.py` |
| Journal engine | `backend/accounting/services/journal_engine.py` |
| Financial reports | `backend/accounting/services/financial_reports.py` |
| Payment engine | `backend/payments/services.py` |
| Frontend main window | `frontend/ui/main_window.py` |
| Frontend sidebar | `frontend/ui/sidebar.py` |
| API client | `frontend/api/client.py` |

---

## Seeded Data (via management commands)
- **37 default accounts** (Chart of Accounts)
- **6 payment methods** (Cash, Bank, Mobile, Hawala, Cheque, CC)
- **5 payment accounts** (Main Cash AFN, USD Cash, AIB Bank, M-Paisa, Al-Farooq Hawala)

---

## Phase UX.3 Files Created/Modified

### New Reports (Layer 1 & 5)
| File | Purpose |
|------|---------|
| `docs/BASESCREEN_MIGRATION_MAP.md` | 43 screens classified by migration risk |
| `docs/ENTERPRISEDIALOG_MIGRATION_MAP.md` | 30 QDialog + 1 QWidget classified by migration risk |
| `docs/UI_LIFECYCLE_RISK_REPORT.md` | Lifecycle risks, BaseScreen adoption gaps |
| `docs/UI_MEMORY_STABILITY_REPORT.md` | Signal/timer/leak audit (score: 95/100) |
| `docs/UI_FOUNDATION_GOVERNANCE_REPORT.md` | Post-migration governance summary |
| `docs/UPDATED_FRONTEND_SCORECARD.md` | Phase UX.3 scorecard (90/100, +3) |
| `docs/COMPONENT_STANDARDIZATION_REPORT.md` | Component usage metrics, remaining work |

### Migrated Screens (Layer 2 — BaseScreen)
| File | Screen | Index | From | To |
|------|--------|-------|------|----|
| `frontend/ui/finance/customer_payment_workspace.py` | CustomerPaymentWorkspace | 60 | QWidget | BaseScreen |
| `frontend/ui/finance/supplier_payment_workspace.py` | SupplierPaymentWorkspace | 61 | QWidget | BaseScreen |
| `frontend/ui/finance/payment_allocation_explorer.py` | PaymentAllocationExplorer | 62 | QWidget | BaseScreen |
| `frontend/ui/finance/returns_explainability.py` | ReturnsExplainabilityScreen | 63 | QWidget | BaseScreen |
| `frontend/ui/finance/journal_reversal_explorer.py` | JournalReversalExplorer | 64 | QWidget | BaseScreen |
| `frontend/ui/finance/financial_operations_console.py` | FinancialOperationsConsole | 65 | QWidget | BaseScreen |

### Phase UX.4 Layer 1 — Accounting Screen Migration

| File | Screen | Index | From | To |
|------|--------|-------|------|----|
| `frontend/ui/accounting/chart_of_accounts_screen.py` | ChartOfAccountsScreen | 10 | QFrame | BaseScreen |
| `frontend/ui/accounting/journal_entry_screen.py` | JournalEntryScreen | 11 | QFrame | BaseScreen |
| `frontend/ui/accounting/account_ledger_screen.py` | AccountLedgerScreen | 12 | QFrame | BaseScreen |
| `frontend/ui/accounting/report_browser.py` | ReportBrowser | 13-17, 49-56 | QWidget | BaseScreen |
| `frontend/ui/accounting/financial_integrity_screen.py` | FinancialIntegrityScreen | 58 | QWidget | BaseScreen |
| `frontend/ui/accounting/financial_audit_log_screen.py` | FinancialAuditLogScreen | 59 | QWidget | BaseScreen |

### Fixes Applied
- `frontend/ui/accounting/financial_audit_log_screen.py`: Fixed pre-existing bug — `FINANCIAL_ACTIONS` constant was referenced but never defined; added full constant with 16 financial action types matching backend
- All screens: Added `_on_screen_shown()` no-op override to prevent double-loading from BaseScreen's `showEvent`
- `report_browser.py`: Uses dynamic `screen_id=f"report_{report_type}"` for 14 instances

### Phase UX.4 Scorecard (Layer 1 + Layer 2)
| Metric | Value |
|--------|-------|
| BaseScreen screens | 37 (24 pre-UX.3 + 6 finance + 7 accounting) |
| EnterpriseDialog subclasses | 8 (4 pre-UX.3 + 1 UX.3 + 7 UX.4) |
| QWidget/QFrame screens remaining | 0 (all accounting now on BaseScreen) |
| Pre-existing bugs fixed | 1 (FINANCIAL_ACTIONS) |
| LSP errors (all PySide6 false positives) | No actual code errors |

### Migrated Dialogs (Layer 2 — EnterpriseDialog)
| File | Dialog | From | To |
|------|--------|------|----|
| `frontend/ui/system/backup_screen.py` | RestoreConfirmDialog | QDialog | EnterpriseDialog |
| `frontend/ui/accounting/components/account_form_dialog.py` | AccountFormDialog | QDialog | EnterpriseDialog |
| `frontend/ui/inventory/components/batch_form_dialog.py` | BatchFormDialog | QDialog | EnterpriseDialog |
| `frontend/ui/inventory/components/category_form_dialog.py` | CategoryFormDialog | QDialog | EnterpriseDialog |
| `frontend/ui/inventory/components/warehouse_form_dialog.py` | WarehouseFormDialog | QDialog | EnterpriseDialog |
| `frontend/ui/inventory/components/product_form.py` | ProductFormDialog | QDialog | EnterpriseDialog |
| `frontend/ui/sales/credit_warning_dialog.py` | CreditWarningDialog | QDialog | EnterpriseDialog |
| `frontend/ui/system/email_config_dialog.py` | EmailConfigDialog | QDialog | EnterpriseDialog |

### Migration Pattern (EnterpriseDialog)
```python
class MyDialog(EnterpriseDialog):
    def __init__(self, parent=None):
        super().__init__("Dialog Title", DialogType.CUSTOM, parent)
        content = self._build_content()
        self.set_content(content)

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        # ... form fields ...
        return widget

    def _create_button_area(self):
        # Override to provide custom buttons, or use default Cancel/Save for CUSTOM type
        button_area = QFrame()
        button_area.setFixedHeight(60)
        layout = QHBoxLayout(button_area)
        layout.addStretch()
        cancel_btn = EnterpriseButton("Cancel", ...)
        cancel_btn.clicked.connect(self.reject)
        save_btn = EnterpriseButton("Save", ...)
        save_btn.clicked.connect(self.accept)
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)
        return button_area
```

---

## Phase UX.5 — Intelligent UX Operations & Runtime Governance

### Summary
| Metric | Value |
|--------|-------|
| UX Governance Score | 77.6/100 (baseline) |
| Runtime Stability | 100/100 |
| Observability | Enabled |
| Perceived Performance | Improved (skeleton loaders, deferred rendering) |
| UI Responsiveness | Stable |
| Maintainability | Increased |

### Layer 1 — Runtime UX Telemetry
- **New file**: `runtime/ux_telemetry.py` — `_TelemetryBuffer` (thread-safe, bounded deque at 500 events)
- **Metrics**: screen load time, navigation frequency, dialog open/close duration, table render time, form completion rate, exit points
- **Instrumentation**: 1-3 line hooks in `main_window.py:change_page/closeEvent/logout`, `dialogs.py:EnterpriseDialog.showEvent/done`, `tables.py:EnterpriseTable.set_data`, `base_screen.py:BaseFormScreen.submit_form/cancel_form`
- **Storage**: Buffered in-memory → `ux_telemetry.jsonl` every 30s (non-blocking)
- **Reports**: `UX_RUNTIME_TELEMETRY_REPORT.md`, `SCREEN_USAGE_ANALYTICS.md`

### Layer 2 — Smart Loading & Perceived Performance
- **New file**: `runtime/deferred_renderer.py` — `defer()`, `defer_until()`, `ChunkedRenderer` utilities
- **New file**: `ui/components/skeleton_loader.py` — `SkeletonTable`, `SkeletonRow` (animated placeholder widgets)
- **Improvements**: `EnterpriseTable.set_data_deferred()` and `set_data_chunked()` for large datasets
- **Existing**: LazyScreenManager, BaseScreen.show_skeleton_loader signal hook

### Layer 3 — Workflow Intelligence
- **New file**: `runtime/workflow_intelligence.py` — `RecentActionStore` (100-entry bounded), `SuggestionEngine` (20+ rules, 4 workflow chains), `NavigationAccelerator`
- **Rules**: Sales flow, Purchases flow, Accounting close, HR cycle — all rule-based, NO AI/ML
- **Integration**: Hooked into `main_window.py:change_page` for automatic navigation recording

### Layer 4 — Frontend Observability
- **New file**: `runtime/ui_observability.py` — `_SignalStormDetector` (>50 signals/sec), `_RepaintMonitor`, `_WidgetCostTracker`, `_UIObservabilityAggregator`
- **Thresholds**: Slow screen >3000ms, slow dialog >5000ms, slow table >200ms, expensive widget >500ms
- **Reports**: `UX_OBSERVABILITY_REPORT.md`, `SLOW_UI_COMPONENTS_REPORT.md`

### Layer 5 — Design System Freeze & Enforcement
- **Audit**: Codebase scanned for 8 enforcement rules
- **LOCKED rules** (0 violations): ThemeEngine only source, BaseScreen mandatory, EnterpriseDialog mandatory, no inline hex colors
- **OPEN rules** (violations remain): QPushButton → EnterpriseButton (68 violations in 30 files), tokenized spacing (41 style + 6 margin violations), QColor raw RGB (1 violation)
- **Reports**: `DESIGN_SYSTEM_ENFORCEMENT_REPORT.md`, `UI_GOVERNANCE_FINAL_LOCK.md`

### Phase UX.5 Files Created/Modified

**New files:**
| File | Purpose |
|------|---------|
| `runtime/ux_telemetry.py` | Layer 1 — UX Telemetry engine |
| `runtime/deferred_renderer.py` | Layer 2 — Deferred rendering utilities |
| `runtime/workflow_intelligence.py` | Layer 3 — Workflow intelligence engine |
| `runtime/ui_observability.py` | Layer 4 — UI observability engine |
| `ui/components/skeleton_loader.py` | Layer 2 — Skeleton loader widget |

**Modified files (instrumentation hooks):**
| File | Change |
|------|--------|
| `ui/main_window.py` | Telemetry + workflow recording in `change_page`; exit points in `closeEvent`/`logout` |
| `ui/components/dialogs.py` | Dialog open/close timing in `showEvent`/`done` |
| `ui/components/tables.py` | Table render timing + `set_data_deferred`/`set_data_chunked` methods |
| `ui/screens/base_screen.py` | Form action tracking in `submit_form`/`cancel_form` |

**New reports:**
| File | Purpose |
|------|---------|
| `frontend/docs/UX_RUNTIME_TELEMETRY_REPORT.md` | Layer 1 report |
| `frontend/docs/SCREEN_USAGE_ANALYTICS.md` | Layer 1 report |
| `frontend/docs/UX_OBSERVABILITY_REPORT.md` | Layer 4 report |
| `frontend/docs/SLOW_UI_COMPONENTS_REPORT.md` | Layer 4 report |
| `frontend/docs/DESIGN_SYSTEM_ENFORCEMENT_REPORT.md` | Layer 5 report |
| `frontend/docs/UI_GOVERNANCE_FINAL_LOCK.md` | Layer 5 report |

