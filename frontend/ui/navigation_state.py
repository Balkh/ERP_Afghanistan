"""Canonical navigation state for MainWindow.

Single source of truth for all page routing data previously duplicated
across change_page(), _build_breadcrumb(), and _do_navigate() in
ui/main_window.py.

Extracted in Refactor Step 2 to eliminate ~120 lines of duplicate maps.
"""

# ---------------------------------------------------------------------------
# PAGE_REGISTRY -- one entry per screen index
# ---------------------------------------------------------------------------
# Each entry: {
#   "id":     str  -- snake_case page identifier (used by navigate_to / sidebar)
#   "name":   str  -- human-readable display name (breadcrumb / nav header)
#   "module": str  -- access-control module key (passed to auth_manager.has_access)
#   "group":  str  -- breadcrumb group ("Inventory", "Sales", etc.)
#   "load":   tuple(str, str) | None  -- (screen.load_method, telemetry_tag) or None
# }

PAGE_REGISTRY = {
    # Dashboard
    0:  {"id": "dashboard",           "name": "Dashboard",             "module": "dashboard",   "group": None,              "load": None},

    # Inventory
    1:  {"id": "products",            "name": "Products",              "module": "inventory",   "group": "Inventory",       "load": ("load_products", "products")},
    2:  {"id": "categories",          "name": "Categories",            "module": "inventory",   "group": "Inventory",       "load": ("load_categories", "categories")},
    3:  {"id": "warehouses",          "name": "Warehouses",            "module": "inventory",   "group": "Inventory",       "load": ("load_warehouses", "warehouses")},
    4:  {"id": "batches",             "name": "Batches",               "module": "inventory",   "group": "Inventory",       "load": ("load_batches", "batches")},

    # Sales
    5:  {"id": "sales_invoice",       "name": "Sales Invoice",         "module": "sales",       "group": "Sales",           "load": None},
    7:  {"id": "customers",           "name": "Customers",             "module": "sales",       "group": "Sales",           "load": ("load_customers", "customers")},
    37: {"id": "pos",                 "name": "POS Terminal",          "module": "sales",       "group": "Sales",           "load": None},

    # Purchases
    6:  {"id": "purchase_invoice",    "name": "Purchase Invoice",      "module": "purchases",   "group": "Purchases",       "load": None},
    8:  {"id": "suppliers",           "name": "Suppliers",             "module": "purchases",   "group": "Purchases",       "load": ("load_suppliers", "suppliers")},

    # Returns
    9:  {"id": "returns",             "name": "Returns",               "module": "returns",     "group": "Returns",         "load": None},
    57: {"id": "reconciliation",      "name": "Reconciliation",        "module": "dashboard",   "group": "Returns",         "load": None},

    # Accounting
    10: {"id": "chart_of_accounts",   "name": "Chart of Accounts",     "module": "accounting",  "group": "Accounting",      "load": None},
    11: {"id": "journal_entries",     "name": "Journal Entries",       "module": "accounting",  "group": "Accounting",      "load": ("load_entries", "journal_entries")},
    12: {"id": "account_ledger",      "name": "Account Ledger",        "module": "accounting",  "group": "Accounting",      "load": ("load_accounts", "account_ledger")},
    58: {"id": "financial_integrity", "name": "Financial Integrity",   "module": "accounting",  "group": "Accounting",      "load": None},
    59: {"id": "financial_audit",     "name": "Financial Audit",       "module": "accounting",  "group": "Accounting",      "load": None},

    # Reports
    13: {"id": "trial_balance",       "name": "Trial Balance",         "module": "reports",     "group": "Reports",         "load": None},
    14: {"id": "profit_loss",         "name": "Profit & Loss",         "module": "reports",     "group": "Reports",         "load": None},
    15: {"id": "balance_sheet",       "name": "Balance Sheet",         "module": "reports",     "group": "Reports",         "load": None},
    16: {"id": "ar_ageing",           "name": "AR Ageing",             "module": "reports",     "group": "Reports",         "load": None},
    17: {"id": "ap_ageing",           "name": "AP Ageing",             "module": "reports",     "group": "Reports",         "load": None},

    # Finance
    18: {"id": "payments",            "name": "Payments",              "module": "finance",     "group": "Finance",         "load": None},
    19: {"id": "budgeting",           "name": "Budgeting",             "module": "finance",     "group": "Finance",         "load": None},
    20: {"id": "tax",                 "name": "Tax",                   "module": "finance",     "group": "Finance",         "load": None},
    21: {"id": "cost_centers",        "name": "Cost Centers",          "module": "finance",     "group": "Finance",         "load": None},
    22: {"id": "cashflow",            "name": "Cash Flow",             "module": "finance",     "group": "Finance",         "load": None},
    34: {"id": "expenses",            "name": "Expenses",              "module": "finance",     "group": "Finance",         "load": ("load_expenses", "expenses")},
    60: {"id": "customer_payments",   "name": "Customer Payments",     "module": "finance",     "group": "Finance",         "load": None},
    61: {"id": "supplier_payments",   "name": "Supplier Payments",     "module": "finance",     "group": "Finance",         "load": None},
    62: {"id": "allocation_explorer", "name": "Allocation Explorer",   "module": "finance",     "group": "Finance",         "load": None},
    63: {"id": "returns_explainability", "name": "Returns Explainability", "module": "finance", "group": "Finance",        "load": None},
    64: {"id": "journal_reversals",   "name": "Journal Reversals",     "module": "finance",     "group": "Finance",         "load": None},
    65: {"id": "operations_console",  "name": "Operations Console",    "module": "finance",     "group": "Finance",         "load": None},

    # HR
    23: {"id": "employees",           "name": "Employees",             "module": "hr",          "group": "HR",              "load": None},
    24: {"id": "attendance",          "name": "Attendance",            "module": "hr",          "group": "HR",              "load": None},
    25: {"id": "leave",               "name": "Leave",                 "module": "hr",          "group": "HR",              "load": None},
    26: {"id": "payroll",             "name": "Payroll",               "module": "hr",          "group": "HR",              "load": None},
    67: {"id": "hr",                  "name": "HR",                    "module": "hr",          "group": "HR",              "load": None},
    49: {"id": "employee_summary",    "name": "Employee Summary",      "module": "hr",          "group": "HR",              "load": None},
    50: {"id": "attendance_report",   "name": "Attendance Report",     "module": "hr",          "group": "HR",              "load": None},
    51: {"id": "leave_report",        "name": "Leave Report",          "module": "hr",          "group": "HR",              "load": None},
    52: {"id": "overtime_report",     "name": "Overtime Report",       "module": "hr",          "group": "HR",              "load": None},
    53: {"id": "payroll_summary",     "name": "Payroll Summary",       "module": "hr",          "group": "HR",              "load": None},
    54: {"id": "payroll_trend",       "name": "Payroll Trend",         "module": "hr",          "group": "HR",              "load": None},
    55: {"id": "payroll_dept_cost",   "name": "Payroll Dept Cost",     "module": "hr",          "group": "HR",              "load": None},
    56: {"id": "payroll_emp_history", "name": "Payroll Employee History", "module": "hr",      "group": "HR",              "load": None},

    # System
    27: {"id": "backup",              "name": "Backup",                "module": "system",      "group": "System",          "load": None},
    28: {"id": "settings",            "name": "Settings",              "module": "system",      "group": "System",          "load": None},
    29: {"id": "fixed_assets",        "name": "Fixed Assets",          "module": "system",      "group": "System",          "load": None},
    30: {"id": "audit",               "name": "Audit",                 "module": "system",      "group": "System",          "load": None},
    31: {"id": "user_management",     "name": "User Management",       "module": "system",      "group": "System",          "load": None},
    32: {"id": "intelligence_hub",    "name": "Intelligence Hub",      "module": "system",      "group": "System",          "load": None},
    33: {"id": "invoice_templates",   "name": "Invoice Templates",     "module": "system",      "group": "System",          "load": None},
    35: {"id": "entities",            "name": "Entities",              "module": "system",      "group": "System",          "load": ("load_entities", "entities")},
    36: {"id": "licensing",           "name": "Licensing",             "module": "system",      "group": "System",          "load": ("load_license_info", "licensing")},
    38: {"id": "control_center",      "name": "Control Center",        "module": "system",      "group": "System",          "load": None},
    39: {"id": "observability",       "name": "Observability",         "module": "system",      "group": "System",          "load": None},
    40: {"id": "analytics",           "name": "Analytics",             "module": "system",      "group": "System",          "load": None},
    47: {"id": "decision_workspace",  "name": "Decision Workspace",    "module": "system",      "group": "System",          "load": None},
    48: {"id": "role_management",     "name": "Role Management",       "module": "system",      "group": "System",          "load": None},
    66: {"id": "company_profile",     "name": "Company Profile",       "module": "system",      "group": "System",          "load": None},
}


# ---------------------------------------------------------------------------
# Derived lookup maps (built once at import time)
# ---------------------------------------------------------------------------

# page_id (str) -> index (int)  -- used by navigate_to()
ID_TO_INDEX = {entry["id"]: idx for idx, entry in PAGE_REGISTRY.items()}

# index (int) -> module (str)  -- used by change_page() access control
INDEX_TO_MODULE = {idx: entry["module"] for idx, entry in PAGE_REGISTRY.items()}

# index (int) -> display name (str)  -- used by _build_breadcrumb()




def get_load_method(index):
    """Return (method_name, telemetry_tag) for the given screen index, or None."""
    entry = PAGE_REGISTRY.get(index)
    if entry:
        return entry.get("load")
    return None


def build_breadcrumb(index, fallback_title=""):
    """Build breadcrumb list for the given page index.

    Returns e.g. ["Home", "Inventory", "Products"] or ["Home", "Products"]
    if no group is defined.
    """
    entry = PAGE_REGISTRY.get(index)
    if not entry:
        return ["Home", fallback_title]
    name = entry.get("name", fallback_title)
    group = entry.get("group")
    if group:
        return ["Home", group, name]
    return ["Home", name]
