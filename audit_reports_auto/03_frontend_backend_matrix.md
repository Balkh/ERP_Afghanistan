# Frontend-Backend Matrix (automated)

## frontend\ui\accounting\account_ledger_screen.py
- Line 5: `from api.client import APIClient`
- Line 6: `from api.endpoints import get_endpoint, extract_list`
- Line 21: `self.api_client = APIClient()`
## frontend\ui\accounting\chart_of_accounts_screen.py
- Line 5: `from api.client import APIClient`
- Line 6: `from api.endpoints import get_endpoint, extract_list`
- Line 23: `self.api_client = APIClient()`
## frontend\ui\accounting\financial_audit_log_screen.py
- Line 12: `from api.client import APIClient`
- Line 47: `self.api_client = APIClient()`
## frontend\ui\accounting\financial_integrity_screen.py
- Line 11: `from api.client import APIClient`
- Line 29: `self.api_client = APIClient()`
## frontend\ui\accounting\journal_entry_screen.py
- Line 7: `from api.client import APIClient`
- Line 8: `from api.endpoints import get_endpoint, extract_list`
- Line 27: `self.api_client = APIClient()`
## frontend\ui\accounting\report_browser.py
- Line 11: `from api.client import APIClient`
- Line 205: `self.api_client = APIClient()`
## frontend\ui\auth\login_screen.py
- Line 15: `from api.client import APIClient`
- Line 29: `self.api_client = api_client or APIClient()`
## frontend\ui\auth\totp_setup_dialog.py
- Line 18: `from api.client import APIClient`
- Line 30: `self.api_client = api_client or APIClient()`
## frontend\ui\causal_scoring\causal_scoring_engine.py
- Line 18: `from api.client import APIClient`
- Line 19: `from api.autonomous_client import AutonomousAPIClient`
- Line 20: `from api.intelligence_client import IntelligenceAPIClient`
- Line 21: `from api.truth_client import TruthAPIClient`
- Line 77: `def __init__(self, api_client: APIClient):`
## frontend\ui\causal_scoring\causal_strength_panel.py
- Line 13: `from api.client import APIClient`
- Line 30: `def __init__(self, api_client: APIClient = None):`
- Line 31: `self._api_client = api_client or APIClient()`
- Line 143: `def set_api_client(self, client: APIClient):`
## frontend\ui\causal_scoring\decision_impact_engine.py
- Line 15: `from api.client import APIClient`
- Line 16: `from api.autonomous_client import AutonomousAPIClient`
- Line 17: `from api.intelligence_client import IntelligenceAPIClient`
- Line 57: `def __init__(self, api_client: APIClient):`
## frontend\ui\causal_scoring\decision_ranking_dashboard.py
- Line 16: `from api.client import APIClient`
- Line 30: `def __init__(self, api_client: APIClient = None):`
- Line 31: `self._api_client = api_client or APIClient()`
- Line 204: `def set_api_client(self, client: APIClient):`
## frontend\ui\common\printable_invoice.py
- Line 5: `from api.document_action_service import DocumentActionService`
- Line 10: `from api.client import APIClient`
- Line 22: `self._api_client = api_client or APIClient()`
## frontend\ui\components\document_action_dialog.py
- Line 33: `from api.document_action_service import DocumentActionService`
## frontend\ui\control_tower\financial_control_tower_screen.py
- Line 21: `from api.client import APIClient`
- Line 83: `self._api = api_client or APIClient()`
## frontend\ui\control_tower\system_health_screen.py
- Line 10: `from api.client import APIClient`
- Line 11: `from api.observability_client import ObservabilityAPIClient`
- Line 12: `from api.intelligence_client import IntelligenceAPIClient`
- Line 13: `from api.truth_client import TruthAPIClient`
- Line 44: `def __init__(self, api_client: APIClient = None):`
- Line 45: `self._api = api_client or APIClient()`
- Line 156: `def set_api_client(self, client: APIClient):`
## frontend\ui\control_tower\workflow_execution_screen.py
- Line 12: `from api.client import APIClient`
- Line 13: `from api.governance_client import GovernanceAPIClient`
- Line 14: `from api.truth_client import TruthAPIClient`
- Line 15: `from api.observability_client import ObservabilityAPIClient`
- Line 29: `def __init__(self, api_client: APIClient = None):`
- Line 30: `self._api = api_client or APIClient()`
- Line 212: `def set_api_client(self, client: APIClient):`
## frontend\ui\finance\budgeting_screen.py
- Line 7: `from api.endpoints import get_endpoint`
- Line 8: `from api.client import APIClient`
- Line 23: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\cashflow_screen.py
- Line 7: `from api.endpoints import get_endpoint`
- Line 8: `from api.client import APIClient`
- Line 22: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\cost_centers_screen.py
- Line 8: `from api.endpoints import get_endpoint`
- Line 9: `from api.client import APIClient`
- Line 24: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\customer_payment_workspace.py
- Line 10: `from api.client import APIClient`
- Line 11: `from api.endpoints import get_endpoint, extract_list`
- Line 33: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\expense_screen.py
- Line 11: `from api.client import APIClient`
- Line 22: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\financial_operations_console.py
- Line 8: `from api.client import APIClient`
- Line 9: `from api.endpoints import get_endpoint, extract_list`
- Line 26: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\journal_reversal_explorer.py
- Line 8: `from api.client import APIClient`
- Line 9: `from api.endpoints import get_endpoint, extract_list`
- Line 26: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\mixed_payment_builder.py
- Line 11: `from api.client import APIClient`
- Line 31: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\payment_allocation_explorer.py
- Line 8: `from api.client import APIClient`
- Line 9: `from api.endpoints import get_endpoint, extract_list`
- Line 28: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\payment_screen.py
- Line 7: `from api.client import APIClient`
- Line 8: `from api.endpoints import get_endpoint`
- Line 20: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\returns_explainability.py
- Line 9: `from api.client import APIClient`
- Line 10: `from api.endpoints import get_endpoint, extract_list`
- Line 28: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\supplier_payment_workspace.py
- Line 10: `from api.client import APIClient`
- Line 11: `from api.endpoints import get_endpoint, extract_list`
- Line 33: `self.api_client = api_client or APIClient()`
## frontend\ui\finance\tax_screen.py
- Line 6: `from api.client import APIClient`
- Line 19: `self.api_client = api_client or APIClient()`
## frontend\ui\governance\approval_screen.py
- Line 14: `from api.client import APIClient`
- Line 15: `from api.governance_client import GovernanceAPIClient`
- Line 26: `def __init__(self, api_client: APIClient = None):`
- Line 27: `self._api = GovernanceAPIClient(api_client or APIClient())`
- Line 164: `def set_api_client(self, client: APIClient):`
## frontend\ui\hr\attendance_screen.py
- Line 6: `from api.client import APIClient`
- Line 7: `from api.endpoints import get_endpoint`
- Line 20: `self.api_client = api_client or APIClient()`
## frontend\ui\hr\employee_screen.py
- Line 8: `from api.client import APIClient`
- Line 9: `from api.endpoints import get_endpoint`
- Line 26: `self.api_client = api_client or APIClient()`
- Line 255: `self.api_client = api_client or APIClient()`
## frontend\ui\hr\leave_screen.py
- Line 5: `from api.client import APIClient`
- Line 6: `from api.endpoints import get_endpoint`
- Line 19: `self.api_client = api_client or APIClient()`
## frontend\ui\hr\payroll_screen.py
- Line 8: `from api.endpoints import get_endpoint`
- Line 9: `from api.client import APIClient`
- Line 24: `self.api_client = api_client or APIClient()`
## frontend\ui\inventory\batch_screen.py
- Line 1: `from api.client import APIClient`
- Line 2: `from api.endpoints import get_endpoint`
- Line 14: `self.api_client = api_client or APIClient()`
## frontend\ui\inventory\category_screen.py
- Line 1: `from api.client import APIClient`
- Line 2: `from api.endpoints import get_endpoint`
- Line 14: `self.api_client = api_client or APIClient()`
## frontend\ui\inventory\product_screen.py
- Line 4: `from api.client import APIClient`
- Line 5: `from api.endpoints import get_endpoint`
- Line 13: `self.api_client = api_client or APIClient()`
## frontend\ui\inventory\warehouse_screen.py
- Line 1: `from api.client import APIClient`
- Line 2: `from api.endpoints import get_endpoint`
- Line 14: `self.api_client = api_client or APIClient()`
## frontend\ui\investigation\anomaly_investigation_screen.py
- Line 13: `from api.client import APIClient`
- Line 14: `from api.intelligence_client import IntelligenceAPIClient`
- Line 15: `from api.observability_client import ObservabilityAPIClient`
- Line 16: `from api.truth_client import TruthAPIClient`
- Line 27: `def __init__(self, api_client: APIClient = None):`
- Line 28: `self._api = api_client or APIClient()`
- Line 174: `def set_api_client(self, client: APIClient):`
## frontend\ui\investigation\event_investigation_screen.py
- Line 13: `from api.client import APIClient`
- Line 14: `from api.truth_client import TruthAPIClient`
- Line 15: `from api.observability_client import ObservabilityAPIClient`
- Line 16: `from api.intelligence_client import IntelligenceAPIClient`
- Line 27: `def __init__(self, api_client: APIClient = None):`
- Line 28: `self._api = api_client or APIClient()`
- Line 187: `def set_api_client(self, client: APIClient):`
## frontend\ui\observability\replay_screen.py
- Line 15: `from api.client import APIClient`
- Line 16: `from api.observability_client import ObservabilityAPIClient`
- Line 28: `def __init__(self, api_client: APIClient = None):`
- Line 29: `self._api = ObservabilityAPIClient(api_client or APIClient())`
- Line 178: `def set_api_client(self, client: APIClient):`
## frontend\ui\pos\pos_screen.py
- Line 21: `from api.endpoints import get_endpoint`
## frontend\ui\purchases\purchase_invoice_screen.py
- Line 11: `from api.endpoints import get_endpoint`
## frontend\ui\purchases\supplier_screen.py
- Line 8: `from api.endpoints import get_endpoint`
## frontend\ui\returns\reconciliation_screen.py
- Line 6: `from api.endpoints import get_endpoint`
## frontend\ui\returns\returns_screen.py
- Line 10: `from api.endpoints import get_endpoint`
## frontend\ui\sales\customer_screen.py
- Line 8: `from api.endpoints import get_endpoint`
## frontend\ui\sales\fifo_allocation_dialog.py
- Line 19: `from api.client import APIClient`
- Line 26: `self.api_client = APIClient()`
## frontend\ui\sales\sales_invoice_screen.py
- Line 13: `from api.endpoints import get_endpoint`
## frontend\ui\system\backup_screen.py
- Line 18: `from api.client import APIClient`
- Line 217: `self.api_client = api_client or APIClient()`
## frontend\ui\system\control_center_screen.py
- Line 52: `from api.control_center_service import ControlCenterService`
## frontend\ui\system\correlation_screen.py
- Line 20: `from api.correlation_service import CorrelationIntelligenceService`
## frontend\ui\system\drift_intelligence_screen.py
- Line 16: `from api.drift_intelligence_service import DriftIntelligenceService`
## frontend\ui\system\entity_management_screen.py
- Line 8: `from api.client import APIClient`
- Line 15: `self._api_client = api_client or APIClient()`
## frontend\ui\system\fixed_assets_screen.py
- Line 10: `from api.endpoints import get_endpoint`
## frontend\ui\system\integrity_screen.py
- Line 19: `from api.integrity_service import SystemIntegrityService`
## frontend\ui\system\invoice_template_manager.py
- Line 13: `from api.client import APIClient`
- Line 20: `self._api_client = api_client or APIClient()`
## frontend\ui\system\licensing_screen.py
- Line 12: `from api.client import APIClient`
- Line 28: `self._api = api_client or APIClient()`
## frontend\ui\system\workflow_intelligence_screen.py
- Line 18: `from api.client import APIClient`
- Line 30: `def __init__(self, api_client: APIClient):`
- Line 162: `self._api_client = api_client or APIClient()`
## frontend\ui\truth\event_store_screen.py
- Line 12: `from api.client import APIClient`
- Line 13: `from api.truth_client import TruthAPIClient`
- Line 25: `def __init__(self, api_client: APIClient = None):`
- Line 26: `self._api = TruthAPIClient(api_client or APIClient())`
- Line 116: `def set_api_client(self, client: APIClient):`
## frontend\ui\accounting\components\account_form_dialog.py
- Line 5: `from api.client import APIClient`
- Line 6: `from api.endpoints import extract_list`
- Line 25: `self.api_client = api_client or APIClient()`
## frontend\ui\accounting\components\journal_entry_form.py
- Line 9: `from api.client import APIClient`
- Line 28: `self._api_client = api_client or APIClient()`
## frontend\ui\accounting\components\report_preview_dialog.py
- Line 6: `from api.document_action_service import DocumentActionService`
## frontend\ui\inventory\components\product_form.py
- Line 12: `from api.endpoints import get_endpoint, extract_list`