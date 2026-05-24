# BaseScreen Migration Map — Phase UX.3 Layer 1

**Generated:** 2026-05-24

---

## Current State

| Category | Count | Details |
|----------|-------|---------|
| Screens already on BaseScreen | 24 | HR(4), System(10), Sales(2), Purchases(2), Returns(2), Finance(4) |
| QWidget/QFrame screens (registered) | 20 | Accounting(6), Finance(6), Sales(1), Purchases(1), POS(1), System(2), Observability(1), Control Tower(1), Causal Scoring(1) |
| QWidget screens (non-registered) | 14 | See below |
| Sub-screens (tab children) | 9 | Observability dashboards(7), Decision workspace tabs(2) |

## Migration Targets (Priority Order)

### BATCH 1 — SAFE (no dialog deps, simple structure)
| Priority | Index | Screen | File | Risk |
|----------|-------|--------|------|------|
| 1 | 60 | CustomerPaymentWorkspace | `ui/finance/customer_payment_workspace.py` | LOW |
| 2 | 61 | SupplierPaymentWorkspace | `ui/finance/supplier_payment_workspace.py` | LOW |
| 3 | 62 | PaymentAllocationExplorer | `ui/finance/payment_allocation_explorer.py` | LOW |
| 4 | 63 | ReturnsExplainabilityScreen | `ui/finance/returns_explainability.py` | LOW |
| 5 | 64 | JournalReversalExplorer | `ui/finance/journal_reversal_explorer.py` | LOW |
| 6 | 65 | FinancialOperationsConsole | `ui/finance/financial_operations_console.py` | LOW |

### BATCH 2 — MEDIUM (simple structure, no dialog deps)
| Priority | Index | Screen | File | Risk |
|----------|-------|--------|------|------|
| 7 | 18 | PaymentScreen | `ui/finance/payment_screen.py` | MEDIUM |
| 8 | 58 | FinancialIntegrityScreen | `ui/accounting/financial_integrity_screen.py` | MEDIUM |
| 9 | 59 | FinancialAuditLogScreen | `ui/accounting/financial_audit_log_screen.py` | MEDIUM |
| 10 | 13-17,49-56 | ReportBrowser | `ui/accounting/report_browser.py` | MEDIUM |
| 11 | 40 | AnalyticsWorkspace | `ui/system/analytics_workspace.py` | MEDIUM |
| 12 | 38 | OperationsDashboard | `ui/control_tower/operations_dashboard.py` | MEDIUM |
| 13 | 47 | DecisionWorkspace | `ui/causal_scoring/decision_workspace.py` | MEDIUM |

### BATCH 3 — HIGH RISK (dialog deps, complex logic)
| Priority | Index | Screen | File | Risk |
|----------|-------|--------|------|------|
| 14 | 5 | SalesInvoiceScreen | `ui/sales/sales_invoice_screen.py` | HIGH |
| 15 | 6 | PurchaseInvoiceScreen | `ui/purchases/purchase_invoice_screen.py` | HIGH |
| 16 | 37 | POSScreen | `ui/pos/pos_screen.py` | HIGH |
| 17 | 10 | ChartOfAccountsScreen | `ui/accounting/chart_of_accounts_screen.py` | HIGH |
| 18 | 11 | JournalEntryScreen | `ui/accounting/journal_entry_screen.py` | HIGH |
| 19 | 12 | AccountLedgerScreen | `ui/accounting/account_ledger_screen.py` | HIGH |

### DO NOT TOUCH
| Screen | File | Reason |
|--------|------|--------|
| Dashboard (index 0) | `ui/dashboard.py` | Eager-loaded, page 0 special |
| ObservabilityConsole (39) | `ui/observability/observability_console.py` | Complex tab container, stable |
| ObservabilityScreen | `ui/observability/observability_screen.py` | Tab sub-screen |
| ReplayTimeTravelScreen | `ui/observability/replay_screen.py` | Tab sub-screen |
| All dashboards.py classes | `ui/observability/dashboards.py` | 7 sub-dashboard tabs |
| All widgets.py classes | `ui/observability/widgets.py` | Utility widgets |
| BaseInventoryScreen | `ui/inventory/base_screen.py` | Base class for inventory |
| BaseReportScreen | `ui/accounting/base_report_screen.py` | Base class for reports |

## Migration Pattern

### FROM (current pattern):
```python
class MyScreen(QWidget):
    signal1 = Signal(dict)
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client or APIClient()
        self._is_loading = False
        self.setup_ui()
        self.load_data()
```

### TO (BaseScreen pattern):
```python
class MyScreen(BaseScreen):
    signal1 = Signal(dict)
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="my_screen")
        self.api_client = api_client or APIClient()
        self._is_loading = False
        self.setup_ui()
    
    def load_data(self, params=None):
        """Override BaseScreen.load_data."""
        # existing loading logic
```

## Validation Steps (After Each Migration)
1. MainWindow startup succeeds
2. Screen renders correctly on navigation
3. Theme switching works
4. Data loads correctly
5. Refresh works
6. Signal connections intact
7. No duplicate data loads
