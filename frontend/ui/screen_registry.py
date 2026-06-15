"""
Lazy screen registration — modules imported on first navigation only.
"""
from __future__ import annotations

import importlib
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow
    from ui.utils.lazy_loader import LazyScreenManager


def _import_class(module_path: str, class_name: str):
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _screen_builder(module_path: str, class_name: str, extra: Callable | None = None):
    """Return a LazyScreenManager factory that imports the module on first open."""

    def builder(api_client=None, **kw):
        cls = _import_class(module_path, class_name)
        if extra is not None:
            return extra(cls, api_client=api_client, **kw)
        return cls(api_client=api_client, **kw)

    return builder


def register_all_screens(lazy: "LazyScreenManager", main: "MainWindow") -> None:
    """Register all lazy screen indices (same routing as pre-sprint MainWindow)."""
    _register = lazy.register
    auth = main.auth_manager

    def _b(module_path: str, class_name: str):
        return _screen_builder(module_path, class_name)

    # 1-9 Inventory & Sales
    _register(1, _b("ui.inventory.product_screen", "ProductScreen"))
    _register(2, _b("ui.inventory.category_screen", "CategoryScreen"))
    _register(3, _b("ui.inventory.warehouse_screen", "WarehouseScreen"))
    _register(4, _b("ui.inventory.batch_screen", "BatchScreen"))
    _register(
        5,
        _screen_builder(
            "ui.sales.sales_invoice_screen",
            "SalesInvoiceScreen",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, auth_manager=auth, **kw),
        ),
    )
    _register(
        6,
        _screen_builder(
            "ui.purchases.purchase_invoice_screen",
            "PurchaseInvoiceScreen",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, auth_manager=auth, **kw),
        ),
    )
    _register(7, _b("ui.sales.customer_screen", "CustomerScreen"))
    _register(8, _b("ui.purchases.supplier_screen", "SupplierScreen"))
    _register(9, _b("ui.returns.returns_screen", "ReturnsScreen"))
    _register(
        37,
        _screen_builder(
            "ui.pos.pos_screen",
            "POSScreen",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, auth_manager=auth, **kw),
        ),
    )

    # 10-17 Accounting
    _register(10, _b("ui.accounting.chart_of_accounts_screen", "ChartOfAccountsScreen"))
    _register(11, _b("ui.accounting.journal_entry_screen", "JournalEntryScreen"))
    _register(12, _b("ui.accounting.account_ledger_screen", "AccountLedgerScreen"))

    def _report(report_type: str):
        return _screen_builder(
            "ui.accounting.report_browser",
            "ReportBrowser",
            lambda cls, api_client=None, **kw: cls(report_type=report_type, api_client=api_client, **kw),
        )

    _register(13, _report("trial_balance"))
    _register(14, _report("profit_loss"))
    _register(15, _report("balance_sheet"))
    _register(16, _report("ar_aging"))
    _register(17, _report("ap_aging"))

    # 18-22 Finance
    _register(18, _b("ui.finance.payment_screen", "PaymentScreen"))
    _register(19, _b("ui.finance.budgeting_screen", "BudgetingScreen"))
    _register(20, _b("ui.finance.tax_screen", "TaxScreen"))
    _register(21, _b("ui.finance.cost_centers_screen", "CostCentersScreen"))
    _register(22, _b("ui.finance.cashflow_screen", "CashflowScreen"))
    _register(34, _b("ui.finance.expense_screen", "ExpenseScreen"))

    # 23-26 HR
    _register(23, _b("ui.hr.employee_screen", "EmployeeScreen"))
    _register(24, _b("ui.hr.attendance_screen", "AttendanceScreen"))
    _register(25, _b("ui.hr.leave_screen", "LeaveScreen"))
    _register(26, _b("ui.hr.payroll_screen", "PayrollScreen"))

    # 27-39 System
    _register(27, _b("ui.system.backup_screen", "BackupControlScreen"))
    _register(28, _b("ui.system.settings_screen", "SettingsScreen"))
    _register(29, _b("ui.system.fixed_assets_screen", "FixedAssetsScreen"))
    _register(30, _b("ui.system.audit_screen", "AuditScreen"))
    _register(31, _b("ui.system.user_management_screen", "UserManagementScreen"))
    _register(48, _b("ui.system.role_management_screen", "RoleManagementScreen"))
    _register(32, _b("ui.system.intelligence_hub_screen", "IntelligenceHubScreen"))
    _register(33, _b("ui.system.invoice_template_manager", "InvoiceTemplateManager"))
    _register(66, _b("ui.system.company_profile_screen", "CompanyProfileScreen"))
    _register(35, _b("ui.system.entity_management_screen", "EntityManagementScreen"))
    _register(36, _b("ui.system.licensing_screen", "LicensingScreen"))
    _register(
        38,
        _screen_builder(
            "ui.control_tower.operations_dashboard",
            "OperationsDashboard",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, **kw),
        ),
    )
    _register(
        39,
        _screen_builder(
            "ui.observability.observability_console",
            "ObservabilityConsole",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, **kw),
        ),
    )
    _register(
        40,
        _screen_builder(
            "ui.system.analytics_workspace",
            "AnalyticsWorkspace",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, **kw),
        ),
    )
    _register(
        47,
        _screen_builder(
            "ui.causal_scoring.decision_workspace",
            "DecisionWorkspace",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, **kw),
        ),
    )

    # 49-57 Reports & reconciliation
    _register(49, _report("employee_summary"))
    _register(50, _report("attendance_report"))
    _register(51, _report("leave_report"))
    _register(52, _report("overtime_report"))
    _register(53, _report("payroll_summary"))
    _register(54, _report("payroll_trend"))
    _register(55, _report("payroll_dept_cost"))
    _register(56, _report("payroll_emp_history"))
    _register(57, _b("ui.returns.reconciliation_screen", "ReconciliationScreen"))

    _register(58, _b("ui.accounting.financial_integrity_screen", "FinancialIntegrityScreen"))
    _register(59, _b("ui.accounting.financial_audit_log_screen", "FinancialAuditLogScreen"))

    _register(60, _b("ui.finance.customer_payment_workspace", "CustomerPaymentWorkspace"))
    _register(61, _b("ui.finance.supplier_payment_workspace", "SupplierPaymentWorkspace"))
    _register(62, _b("ui.finance.payment_allocation_explorer", "PaymentAllocationExplorer"))
    _register(63, _b("ui.finance.returns_explainability", "ReturnsExplainabilityScreen"))
    _register(64, _b("ui.finance.journal_reversal_explorer", "JournalReversalExplorer"))
    _register(
        65,
        _screen_builder(
            "ui.finance.financial_operations_console",
            "FinancialOperationsConsole",
            lambda cls, api_client=None, **kw: cls(api_client=api_client, **kw),
        ),
    )

    # 67 — HR departments/positions
    _register(67, _b("ui.hr.departments_screen", "DepartmentsScreen"))
