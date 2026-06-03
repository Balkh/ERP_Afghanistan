# WS-E: Safe Extraction Map

**Audit ID:** `PHASE6_0_20260602_144256`  
**Generated:** 2026-06-02T14:42:56.046229  
**Purpose:** Dependency-safe extraction plan — **no architectural rewrites**, only helper/service/presenter/validator extractions.

---

## 1. Extraction Rules

**Allowed:**
- Helper extraction (private functions → module-level functions in a new file)
- Service extraction (business logic → `services/<domain>_service.py`)
- Presenter extraction (UI logic → `presenters/<screen>_presenter.py`)
- Validator extraction (precondition checks → `validators/<model>_validator.py`)

**Forbidden:**
- Architectural rewrites (no layer inversions, no dependency injection containers)
- Database redesign (no model changes, no migration)
- Model redesign (no field changes, no manager changes)
- Public API changes (existing imports/URLs must continue to work)

---

## 2. Class-Level Extractions (Top 40)

Headers: # | File | Class | Current LOC | Strategy | Risk | ROI

| # | File | Class | LOC | Strategy | Risk | ROI |
|---|---|---|---|---|---|---|
| 1 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | 1392 | PRESENTER | LOW | HIGH |
| 2 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | 1147 | PRESENTER | LOW | HIGH |
| 3 | backend\core\api\v1\payment_operations.py | PaymentOperationsViewSet | 1077 | PRESENTER | LOW | HIGH |
| 4 | backend\inventory\service\stock_integration.py | StockIntegrationService | 827 | PRESENTER | LOW | HIGH |
| 5 | frontend\ui\main_window.py | MainWindow | 1124 | PRESENTER | LOW | HIGH |
| 6 | frontend\ui\pos\pos_screen.py | POSScreen | 859 | PRESENTER | LOW | HIGH |
| 7 | frontend\ui\purchases\purchase_invoice_screen.py | PurchaseInvoiceScreen | 866 | PRESENTER | LOW | HIGH |
| 8 | frontend\ui\sales\sales_invoice_screen.py | SalesInvoiceScreen | 861 | PRESENTER | LOW | HIGH |
| 9 | backend\backup\backup_system.py | BackupManager | 540 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 10 | backend\payments\services.py | PaymentEngine | 788 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 11 | backend\production_gate\gate_validator.py | ProductionGateValidator | 739 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 12 | backend\returns\models.py | ReturnOrder | 519 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 13 | backend\accounting\services\advanced_reports.py | AdvancedReportsService | 506 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 14 | backend\accounting\services\financial_reports.py | FinancialReportEngine | 743 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 15 | backend\core\services\financial_explainability.py | FinancialExplainability | 603 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 16 | backend\simulation\control_center\orchestrator\control_center_engine.py | ControlCenterEngine | 534 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 17 | frontend\api\client.py | APIClient | 667 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 18 | frontend\ui\sidebar.py | Sidebar | 648 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 19 | frontend\ui\returns\returns_screen.py | ReturnsScreen | 552 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 20 | frontend\ui\system\backup_screen.py | BackupControlScreen | 633 | SERVICE_OR_VALIDATOR | LOW | MEDIUM |
| 21 | backend\pre_production_hardening\hardening_validator.py | (module-level) | 1460 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 22 | backend\core\governance\industrial_test_suite.py | (module-level) | 1351 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 23 | backend\core\operations\operational_intelligence.py | (module-level) | 1254 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 24 | backend\production_infrastructure\migration_validator.py | (module-level) | 1207 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 25 | frontend\utils\logger.py | (module-level) | 1156 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 26 | frontend\ui\main_window.py | (module-level) | 1152 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 27 | backend\core\api\v1\payment_operations.py | (module-level) | 1111 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |
| 28 | backend\security\views.py | (module-level) | 1034 | HELPER_OR_MODULE_SPLIT | MEDIUM | MEDIUM |

---

## 3. Method-Level Extractions (Top Methods)

Headers: # | File | Class | Method | LOC | CC | Nesting | Strategy | Risk | ROI

| # | File | Class | Method | LOC | CC | Nesting | Strategy | Risk | ROI |
|---|---|---|---|---|---|---|---|---|---|
| 1 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_multi_user_operations | 250 | 44 | 5 | Extract to helper | LOW | HIGH |
| 2 | backend\core\operations\decision_engine.py | DecisionEngine | evaluate_all | 240 | 24 | 2 | Extract to helper | LOW | HIGH |
| 3 | backend\core\seeders\accounting.py | AccountingSeeder | seed | 271 | 16 | 4 | Extract to helper | LOW | HIGH |
| 4 | backend\core\seeders\inventory.py | InventorySeeder | seed | 211 | 14 | 4 | Extract to helper | LOW | HIGH |
| 5 | backend\simulation\control_center\orchestrator\control_center_router.py | ControlCenterRouter | route_query | 301 | 17 | 6 | Extract to helper | LOW | HIGH |
| 6 | backend\simulation\control_center\orchestrator\operational_command_orchestrator.py | OperationalCommandOrchestrator | execute_command | 314 | 20 | 5 | Extract to helper | LOW | HIGH |
| 7 | frontend\ui\purchases\purchase_invoice_screen.py | PurchaseInvoiceScreen | _setup_screen | 296 | 1 | 1 | Extract to helper | LOW | HIGH |
| 8 | frontend\ui\purchases\supplier_screen.py | SupplierDialog | _build_content | 204 | 1 | 0 | Extract to helper | LOW | HIGH |
| 9 | frontend\ui\sales\sales_invoice_screen.py | SalesInvoiceScreen | _setup_screen | 303 | 1 | 1 | Extract to helper | LOW | HIGH |
| 10 | backend\backup\backup_system.py | BackupManager | create_backup | 150 | 19 | 5 | Extract to helper | LOW | HIGH |
| 11 | backend\backup\backup_system.py | BackupManager | restore_backup | 109 | 19 | 5 | Extract to helper | LOW | HIGH |
| 12 | backend\payments\services.py | PaymentEngine | process_payment | 101 | 7 | 1 | Extract to helper | LOW | HIGH |
| 13 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_database_hardening | 114 | 15 | 4 | Extract to helper | LOW | HIGH |
| 14 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_operator_resilience | 171 | 17 | 3 | Extract to helper | LOW | HIGH |
| 15 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_session_security | 186 | 22 | 3 | Extract to helper | LOW | HIGH |
| 16 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_export_reliability | 169 | 25 | 6 | Extract to helper | LOW | HIGH |
| 17 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_deployment_recovery | 141 | 24 | 5 | Extract to helper | LOW | HIGH |
| 18 | backend\pre_production_hardening\hardening_validator.py | PreProductionHardeningValidator | validate_performance | 195 | 18 | 4 | Extract to helper | LOW | HIGH |
| 19 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | validate_postgresql_migration | 138 | 13 | 3 | Extract to helper | LOW | HIGH |
| 20 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | validate_transaction_isolation | 166 | 26 | 6 | Extract to helper | LOW | HIGH |
| 21 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | validate_redis_event_layer | 108 | 10 | 3 | Extract to helper | LOW | HIGH |
| 22 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | validate_security_hardening | 124 | 15 | 4 | Extract to helper | LOW | HIGH |
| 23 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | validate_performance | 106 | 11 | 4 | Extract to helper | LOW | HIGH |
| 24 | backend\production_infrastructure\migration_validator.py | ProductionInfrastructureValidator | validate_observability | 116 | 8 | 2 | Extract to helper | LOW | HIGH |
| 25 | backend\returns\models.py | ReturnOrder | void | 109 | 18 | 3 | Extract to helper | LOW | HIGH |
| 26 | backend\sales\views.py | CustomerViewSet | credit_risk | 101 | 12 | 4 | Extract to helper | LOW | HIGH |
| 27 | backend\accounting\services\financial_reports.py | FinancialReportEngine | get_cash_flow_statement | 119 | 17 | 2 | Extract to helper | LOW | HIGH |
| 28 | backend\accounting\services\inventory_accounting.py | InventoryAccountingService | process_inventory_adjustment | 114 | 13 | 3 | Extract to helper | LOW | HIGH |
| 29 | backend\accounting\services\invoice_calculator.py | InvoiceCalculator | calculate | 152 | 15 | 3 | Extract to helper | LOW | HIGH |

---

## 4. Extraction Pattern Templates

### 4.1 Presenter Extraction (UI Layer)

```python
# BEFORE: ui/screens/<screen>.py
class BigScreen(BaseScreen):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()        # UI
        self._load_data()        # logic
        self._validate_form()    # logic
        self._save_record()      # logic
    def _save_record(self):    # 80 LOC of business logic
        ...

# AFTER: ui/screens/<screen>.py + presenters/<screen>_presenter.py
class BigScreen(BaseScreen):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presenter = BigScreenPresenter(self)
        self._build_ui()
        self.presenter.load_data()

# presenters/<screen>_presenter.py
class BigScreenPresenter:
    def __init__(self, view): self.view = view
    def load_data(self): ...
    def validate_form(self): ...
    def save_record(self): ...
```

### 4.2 Validator Extraction (Service Layer)

```python
# BEFORE: services/journal_service.py
def create_entry(...):
    if not entry.is_balanced(): raise ...
    if entry.total == 0: raise ...
    if not entry.has_lines(): raise ...
    # ... 30 more lines of preconditions

# AFTER: services/journal_service.py + validators/journal_validator.py
def create_entry(...):
    JournalValidator.validate_entry(entry)
    # ... rest of business logic

# validators/journal_validator.py
class JournalValidator:
    @staticmethod
    def validate_entry(entry): ...
```

### 4.3 Helper Extraction (Module-Level)

```python
# BEFORE: ui/screens/big_form.py (mixed UI + helpers)
def _compute_total(items): ...
def _format_currency(v): ...
def _validate_email(e): ...

# AFTER: ui/screens/big_form.py + ui/utils/form_helpers.py
from ui.utils.form_helpers import compute_total, format_currency, validate_email
```

---

## 5. Risk Classification

| Risk | Criteria | Refactor Approach |
|------|----------|-------------------|
| **LOW** | Private methods only, no inheritance, no signal overrides | Direct extraction, no behavior change |
| **MEDIUM** | Methods called by other classes in the same module, or via inheritance | Extract + deprecation alias, run regression tests |
| **HIGH** | Public API, signals, mixins, abstract methods | Do not extract; consider only internal refactoring (split method body) |

For this codebase, **no HIGH-risk extractions are recommended** — all top-tier candidates fall into LOW or MEDIUM.

---

## 6. Conclusion

- 28 class-level extractions are recommended.
- 29 method-level extractions are recommended.
- All extractions are **LOW or MEDIUM risk** and **HIGH or MEDIUM ROI**.
- The extraction plan preserves the public API of every file.
