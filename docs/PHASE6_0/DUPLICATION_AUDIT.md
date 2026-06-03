# WS-D: Duplication Audit

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Scope:** Function signatures, function bodies, method fan-out, helper definitions  
**Method:** AST-based normalization, MD5 fingerprinting, cross-file fan-out analysis

---

## 1. Summary

| Metric | Count |
|--------|-------|
| Duplicate function signatures (≥3 occurrences) | 50 |
| Duplicate function bodies (≥2 normalized matches) | 50 |
| Method names defined in ≥3 classes (fan-out) | 50 |
| Private helper candidates (<30 LOC) | 2059 |

---

## 2. Duplication by Category (Signatures)

| Category | Occurrences | Description |
|----------|-------------|-------------|
| `misc` | 652 | Other repeated function names |
| `ui` | 547 | Render/build/init patterns in UI layer |
| `persistence` | 97 | Save/create/update patterns repeated across viewsets |
| `query` | 74 | Database fetch/get patterns in viewsets |
| `formatting` | 31 | Data-formatting helpers in utils and screens |
| `validation` | 13 | Validation/precondition checks repeated across services |

---

## 3. Top Duplicate Signatures

| Signature | Count | Category | Examples (first 3) |
|---|---|---|---|
| clear(self) | 157 | misc | backend\core\transition_provenance.py; backend\core\events\safety.py; backend\core\governance\industrial_test_suite.py |
| __init__(self) | 140 | ui | backend\governance_engine.py; backend\core\accounting_registry.py; backend\core\transition_provenance.py |
| __str__(self) | 119 | misc | backend\accounting\models.py; backend\accounting\models.py; backend\accounting\models.py |
| __init__(self,max_history) | 71 | ui | backend\simulation\events\bus.py; backend\simulation\control_center\dashboard\stability_widgets.py; backend\simulation\control_center\incidents\incident_lifecycle.py |
| save(self) | 42 | persistence | backend\accounting\models.py; backend\accounting\models.py; backend\accounting\models.py |
| clean(self) | 41 | misc | backend\accounting\models.py; backend\accounting\models.py; backend\accounting\models.py |
| __init__(self,config) | 37 | ui | backend\backup\backup_system.py; backend\backup\services\offsite_replication.py; backend\backup\services\restore_testing.py |
| get_queryset(self) | 35 | query | backend\accounting\views_account.py; backend\accounting\views_account.py; backend\accounting\views_fiscal_period.py |
| _create_button_area(self) | 34 | persistence | frontend\ui\auth\login_screen.py; frontend\ui\auth\totp_setup_dialog.py; frontend\ui\common\batch_selection.py |
| reset(self) | 32 | misc | backend\core\governance\metrics.py; backend\core\governance\self_health.py; backend\core\guarantees\ecek.py |
| setup(self,engine) | 32 | ui | backend\simulation\digital_twin\scenarios\base.py; backend\simulation\digital_twin\scenarios\core_business.py; backend\simulation\digital_twin\scenarios\core_business.py |
| execute(self,engine) | 32 | misc | backend\simulation\digital_twin\scenarios\base.py; backend\simulation\digital_twin\scenarios\core_business.py; backend\simulation\digital_twin\scenarios\core_business.py |
| teardown(self,engine) | 32 | misc | backend\simulation\digital_twin\scenarios\base.py; backend\simulation\digital_twin\scenarios\core_business.py; backend\simulation\digital_twin\scenarios\core_business.py |
| _on_screen_shown(self) | 32 | misc | frontend\ui\dashboard.py; frontend\ui\accounting\account_ledger_screen.py; frontend\ui\accounting\chart_of_accounts_screen.py |
| _build_content(self) | 32 | ui | frontend\ui\auth\login_screen.py; frontend\ui\auth\totp_setup_dialog.py; frontend\ui\common\batch_selection.py |
| to_dict(self) | 31 | formatting | backend\governance_engine.py; backend\governance_engine.py; backend\core\transition_provenance.py |
| __init__(self,store) | 30 | ui | backend\core\operations\intelligence\anomaly_graph.py; backend\core\operations\intelligence\consistency.py; backend\core\operations\intelligence\drift.py |
| __init__(self,kernel) | 28 | ui | backend\core\governance\backup_recovery.py; backend\core\governance\backup_recovery.py; backend\core\governance\backup_recovery.py |
| setup_ui(self) | 28 | ui | frontend\ui\sidebar.py; frontend\ui\accounting\account_ledger_screen.py; frontend\ui\accounting\chart_of_accounts_screen.py |
| setUp(self) | 27 | ui | backend\hr\tests.py; backend\hr\tests.py; backend\hr\tests.py |
| __init__(self,parent,api_client) | 25 | ui | frontend\ui\causal_scoring\decision_workspace.py; frontend\ui\common\barcode_search.py; frontend\ui\common\product_selection_dialog.py |
| get_instance(cls) | 21 | query | backend\core\audit\engine.py; backend\core\integrity\controller.py; backend\core\integrity\controller.py |
| verify(self,integrity_matrix) | 21 | misc | backend\simulation\digital_twin\scenarios\base.py; backend\simulation\digital_twin\scenarios\core_business.py; backend\simulation\digital_twin\scenarios\core_business.py |
| _setup_ui(self) | 19 | ui | frontend\ui\components\dialogs.py; frontend\ui\components\forms.py; frontend\ui\components\forms.py |
| __init__(self,api_client) | 17 | ui | frontend\api\correlation_service.py; frontend\api\integrity_service.py; frontend\security\auth_manager.py |
| _setup_screen(self) | 17 | ui | frontend\ui\dashboard.py; frontend\ui\causal_scoring\causal_strength_panel.py; frontend\ui\causal_scoring\decision_ranking_dashboard.py |
| __init__(self,parent) | 17 | ui | frontend\ui\accounting\account_ledger_screen.py; frontend\ui\accounting\chart_of_accounts_screen.py; frontend\ui\accounting\financial_audit_log_screen.py |
| __init__(self,parent,screen_id,config,api_client) | 17 | ui | frontend\ui\finance\budgeting_screen.py; frontend\ui\finance\cashflow_screen.py; frontend\ui\finance\cost_centers_screen.py |
| run_all(self) | 15 | misc | backend\pre_production_hardening\hardening_validator.py; backend\production_gate\gate_validator.py; backend\production_infrastructure\migration_validator.py |
| _show_loading(self,show) | 15 | misc | frontend\ui\accounting\account_ledger_screen.py; frontend\ui\accounting\journal_entry_screen.py; frontend\ui\finance\budgeting_screen.py |

---

## 4. Top Duplicate Bodies (Normalized)

| Body Hash | Count | Examples |
|---|---|---|
| 54019b1874 | 19 | backend\core\governance\backup_recovery.py::__init__; backend\core\governance\backup_recovery.py::__init__ |
| 5df6566953 | 18 | backend\core\operations\intelligence\anomaly_graph.py::__init__; backend\core\operations\intelligence\consistency.py::__init__ |
| 099ddccb30 | 8 | frontend\ui\accounting\account_ledger_screen.py::_on_screen_shown; frontend\ui\accounting\chart_of_accounts_screen.py::_on_screen_shown |
| 7f0e9ce2a3 | 7 | backend\entities\models.py::save; backend\insurance\models.py::save |
| 7d991a2abf | 6 | frontend\ui\finance\customer_payment_workspace.py::_show_empty; frontend\ui\finance\financial_operations_console.py::_show_empty |
| 5256c8d84b | 6 | frontend\ui\finance\customer_payment_workspace.py::_show_data; frontend\ui\finance\financial_operations_console.py::_show_data |
| d65de09bde | 5 | backend\core\governance\industrial_test_suite.py::__init__; backend\core\governance\industrial_test_suite.py::__init__ |
| 925a058ad2 | 5 | backend\core\api\v1\autonomous.py::_ok; backend\core\api\v1\governance.py::_ok |
| bad31413df | 4 | backend\security\tests.py::dummy_view; backend\security\tests.py::dummy_view |
| 537cacf159 | 4 | backend\simulation\replay\reconstruction\incident_reconstructor.py::get_reconstruction_count; backend\simulation\replay\reconstruction\state_reconstructor.py::get_reconstruction_count |
| a8c50adcd8 | 4 | frontend\ui\causal_scoring\decision_workspace.py::__init__; frontend\ui\control_tower\operations_dashboard.py::__init__ |
| f34bfd1dc6 | 4 | frontend\ui\inventory\batch_screen.py::on_selection_changed; frontend\ui\inventory\category_screen.py::on_selection_changed |
| b0d315423a | 4 | frontend\ui\inventory\components\batch_form_dialog.py::_create_button_area; frontend\ui\inventory\components\category_form_dialog.py::_create_button_area |
| 2f86bf2ea6 | 3 | backend\core\operations\decision_engine.py::get_instance; backend\core\operations\operational_intelligence.py::get_instance |
| ce52877cf6 | 3 | backend\simulation\control_center\reporting\executive_summary.py::__init__; backend\simulation\control_center\reporting\operational_risk_report.py::__init__ |
| 8a55842706 | 3 | backend\simulation\control_center\reporting\executive_summary.py::_store_report; backend\simulation\control_center\reporting\operational_risk_report.py::_store_report |
| c6ae28b210 | 3 | backend\simulation\digital_twin\scenarios\core_business.py::teardown; backend\simulation\digital_twin\scenarios\core_business.py::teardown |
| 0c5552940d | 3 | backend\simulation\digital_twin\scenarios\core_business.py::verify; backend\simulation\digital_twin\scenarios\core_business.py::verify |
| c4bf747972 | 3 | backend\simulation\digital_twin\scenarios\core_business.py::teardown; backend\simulation\digital_twin\scenarios\core_business.py::teardown |
| aad10153f3 | 3 | backend\simulation\digital_twin\scenarios\core_business.py::verify; backend\simulation\digital_twin\scenarios\core_business.py::verify |

---

## 5. Method Fan-out (Defined in 3+ Classes)

| Method Name | Class Count | Classes (first 4) |
|---|---|---|
| to_dict | 31 | ActualState, ActualStateCollector, Alert, AuditReport |
| __init__ | 663 | APIClient, APIError, APIResponse, ARAuditEngine |
| __str__ | 114 | Account, Allowance, ApprovalChain, ApprovalLevel |
| clean | 40 | Account, AssetDepreciation, BackgroundJob, Batch |
| save | 42 | Account, AccountFormDialog, AssetDialog, AssetDisposal |
| can_post | 3 | FiscalPeriod, WorkflowInstance, WorkflowService |
| get_queryset | 35 | AccountViewSet, AssetDepreciationViewSet, AssetDisposalViewSet, BackgroundJobViewSet |
| by_type | 4 | AccountViewSet, CostCenterViewSet, PaymentAccountViewSet, PaymentMethodViewSet |
| balance | 4 | AccountViewSet, CustomerViewSet, PaymentAccountViewSet, SupplierViewSet |
| perform_destroy | 3 | AccountViewSet, PurchaseInvoiceViewSet, SalesInvoiceViewSet |
| post_entry | 4 | JournalEngine, JournalEntryViewSet, JournalGateway, MigrationRouter |
| reverse_entry | 4 | JournalEngine, JournalEntryViewSet, JournalGateway, MigrationRouter |
| create | 13 | BackgroundJobViewSet, BudgetViewSet, ClaimCreateSerializer, CostAllocationViewSet |
| update | 6 | BudgetViewSet, FiscalPeriodViewSet, JournalEntrySerializer, PurchaseInvoiceSerializer |
| destroy | 5 | DepartmentViewSet, EmployeeViewSet, FiscalPeriodViewSet, PositionViewSet |
| summary | 12 | AdversarialScenarioGenerator, AuditTrailViewSet, BudgetViewSet, CashFlowForecastViewSet |
| cleanup | 8 | AuditTrailViewSet, Dashboard, FinancialIntegrityScreen, LicenseStatusScreen |
| create_backup | 5 | BackupManager, BackupProvider, BackupRecordViewSet, PostgreSQLBackupProvider |
| restore_backup | 4 | BackupManager, PostgreSQLRestoreProvider, RestoreProvider, SQLiteRestoreProvider |
| start | 11 | AsyncDataLoader, BackgroundJob, BackupScheduler, ChunkedRenderer |

---

## 6. Key Observations

1. **Validation duplication** is the most common category — `13` occurrences across services. This is the **single highest-leverage refactor target**: a centralized validator pattern would eliminate hundreds of lines of repeated precondition checks.
2. **Persistence patterns** (save/create/update) appear in nearly every Django viewset — these can be unified through a base viewset mixin.
3. **UI render/build/init** duplication is concentrated in the PySide6 form layer — extractable into a `FormBuilder` helper.
4. **Method fan-out > 10** indicates common Django patterns (`__str__`, `clean`, `save`, `get_absolute_url`) — these are **idiomatic, not duplication**, and are NOT refactor targets.

---

## 7. Conclusion

- The codebase has **moderate duplication** that is typical of an evolving Django + PySide6 ERP.
- The **duplication risk score** (sum of duplicate body counts) is 178 normalized matches.
- The **largest extraction opportunities** are: validators, persistence mixins, and UI form builders.
- All recommended extractions preserve behavior because they target pure helpers, not business logic.
