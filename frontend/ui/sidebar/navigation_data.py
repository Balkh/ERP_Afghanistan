"""
Sidebar navigation data — group definitions and item indices.

Single source of truth for all navigation items, groups, and their
page indices. Used by Sidebar, RoleRenderer, and test helpers.
"""

# Navigation item: (title, page_id, page_index)
NAVIGATION_GROUPS = {
    "inventory": {
        "title": "Inventory",
        "items": [
            ("Products", "products", 1),
            ("Categories", "categories", 2),
            ("Warehouses", "warehouses", 3),
            ("Batches", "batches", 4),
            ("Drift Reconciliation", "drift_reconciliation", 68),
        ],
    },
    "sales": {
        "title": "Sales",
        "items": [
            ("Sales Invoice", "sales_invoice", 5),
            ("POS Terminal", "pos", 37),
            ("Customers", "customers", 7),
        ],
    },
    "purchases": {
        "title": "Purchases",
        "items": [
            ("Purchase Invoice", "purchase_invoice", 6),
            ("Suppliers", "suppliers", 8),
        ],
    },
    "returns": {
        "title": "Returns",
        "items": [
            ("Return Orders", "returns", 9),
            ("Reconciliation", "reconciliation", 57),
        ],
    },
    "accounting": {
        "title": "Accounting",
        "items": [
            ("Chart of Accounts", "chart_of_accounts", 10),
            ("Journal Entries", "journal_entries", 11),
            ("Account Ledger", "account_ledger", 12),
            ("Financial Integrity", "financial_integrity", 58),
            ("Financial Audit Log", "financial_audit", 59),
        ],
    },
    "reports": {
        "title": "Reports",
        "items": [
            ("Trial Balance", "trial_balance", 13),
            ("Profit & Loss", "profit_loss", 14),
            ("Balance Sheet", "balance_sheet", 15),
            ("AR Ageing", "ar_ageing", 16),
            ("AP Ageing", "ap_ageing", 17),
        ],
    },
    "finance": {
        "title": "Finance",
        "items": [
            ("Payments", "payments", 18),
            ("Expenses", "expenses", 34),
            ("Budgeting", "budgeting", 19),
            ("Tax", "tax", 20),
            ("Cost Centers", "cost_centers", 21),
            ("Cash Flow", "cashflow", 22),
            ("Customer Payments", "customer_payments", 60),
            ("Supplier Payments", "supplier_payments", 61),
            ("Allocation Explorer", "allocation_explorer", 62),
            ("Returns Explainability", "returns_explainability", 63),
            ("Journal Reversals", "journal_reversals", 64),
            ("Operations Console", "operations_console", 65),
        ],
    },
    "hr": {
        "title": "HR",
        "items": [
            ("Employees", "employees", 23),
            ("Departments & Positions", "departments_positions", 67),
            ("Attendance", "attendance", 24),
            ("Leave", "leave", 25),
            ("Payroll", "payroll", 26),
        ],
    },
    "hr_reports": {
        "title": "HR Reports",
        "items": [
            ("Employee Summary", "employee_summary", 49),
            ("Attendance Report", "attendance_report", 50),
            ("Leave Report", "leave_report", 51),
            ("Overtime Report", "overtime_report", 52),
        ],
    },
    "payroll_reports": {
        "title": "Payroll Reports",
        "items": [
            ("Payroll Summary", "payroll_summary", 53),
            ("Payroll Trend", "payroll_trend", 54),
            ("Dept Cost", "payroll_dept_cost", 55),
            ("Employee History", "payroll_emp_history", 56),
        ],
    },
    "system": {
        "title": "System",
        "items": [
            ("Intelligence Hub", "intelligence_hub", 32),
            ("Control Center", "control_center", 38),
            ("Analytics", "analytics", 40),
            ("Observability Console", "observability", 39),
            ("Decision Support", "decision_workspace", 47),
            ("Invoice Templates", "invoice_templates", 33),
            ("Company Profile", "company_profile", 66),
            ("Business Entities", "entities", 35),
            ("Licensing", "licensing", 36),
            ("Fixed Assets", "fixed_assets", 29),
            ("Backup & Restore", "backup", 27),
            ("Audit Log", "audit", 30),
            ("User Management", "user_management", 31),
            ("Role Management", "role_management", 48),
        ],
    },
}

# Standalone items (not in groups)
NAVIGATION_STANDALONE = [
    ("Dashboard", "dashboard", 0),
    ("Settings", "settings", 28),
]

# Default expansion state for all groups
DEFAULT_EXPANDED_STATE = {
    group_name: False for group_name in NAVIGATION_GROUPS
}

# Group name → set of page_ids (for role-based visibility filtering)
GROUP_PAGE_IDS = {
    group_name: {item[1] for item in group_data["items"]}
    for group_name, group_data in NAVIGATION_GROUPS.items()
}
