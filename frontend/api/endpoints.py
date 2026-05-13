"""
Central API Endpoints Registry
Single source of truth for all frontend API endpoints.
"""

API_ENDPOINTS = {
    # Sales
    "customers": "/api/sales/customers/",
    "customer_balance": "/api/sales/customers/{id}/balance/",
    "sales_invoices": "/api/sales/invoices/",
    "sales_items": "/api/sales/items/",
    "sales_payments": "/api/sales/payments/",

    # Purchases
    "suppliers": "/api/purchases/suppliers/",
    "supplier_balance": "/api/purchases/suppliers/{id}/balance/",
    "purchase_invoices": "/api/purchases/invoices/",
    "purchase_items": "/api/purchases/items/",
    "purchase_payments": "/api/purchases/payments/",

    # Returns
    "return-orders": "/api/returns/return-orders/",
    "reconciliation": "/api/returns/reconciliation/",

    # Inventory
    "products": "/api/inventory/products/",
    "categories": "/api/inventory/categories/",
    "warehouses": "/api/inventory/warehouses/",
    "batches": "/api/inventory/batches/",
    "stock_movements": "/api/inventory/stock-movements/",

    # Accounting
    "accounts": "/api/accounting/accounts/",
    "leaf_accounts": "/api/accounting/accounts/leaf_accounts/",
    "journal_entries": "/api/accounting/journal-entries/",
    "trial_balance": "/api/accounting/accounts/trial_balance/",
    "profit_loss": "/api/accounting/accounts/profit_loss/",
    "balance_sheet": "/api/accounting/accounts/balance_sheet/",
    "ar_aging": "/api/accounting/accounts/ar_aging/",
    "ap_aging": "/api/accounting/accounts/ap_aging/",
    "ledger": "/api/accounting/accounts/ledger/",

    # HR
    "employees": "/api/hr/employees/",
    "departments": "/api/hr/departments/",
    "positions": "/api/hr/positions/",
    "attendance": "/api/hr/reports/attendance-summary/",
    "leave": "/api/hr/reports/leave-summary/",

    # Payroll
    "payroll_cycles": "/api/payroll/cycles/",
    "salaries": "/api/payroll/records/",
    "payroll_records": "/api/payroll/records/",
    "allowances": "/api/payroll/allowances/",
    "deductions": "/api/payroll/deductions/",

    # Fixed Assets
    "assets": "/api/assets/assets/",
    "asset_categories": "/api/assets/categories/",
    "depreciations": "/api/assets/depreciations/",

    # Budgeting
    "budgets": "/api/budgets/budgets/",
    "budget_lines": "/api/budgets/lines/",

    # Tax
    "tax_categories": "/api/tax/categories/",
    "tax_rates": "/api/tax/rates/",
    "tax_returns": "/api/tax/returns/",
    "tax_transactions": "/api/tax/transactions/",

    # Cost Centers
    "cost_centers": "/api/cost-centers/centers/",

    # Cashflow
    "cashflow": "/api/cashflow/items/",
    "cashflow_items": "/api/cashflow/items/",
    "cashflow_forecasts": "/api/cashflow/forecasts/",
    "cashflow_scenarios": "/api/cashflow/scenarios/",

    # Audit
    "audit_logs": "/api/audit/logs/",

    # Payments
    "payments": "/api/payments/transactions/",
    "payment_methods": "/api/payments/methods/",
    "payment_accounts": "/api/payments/accounts/",
    "settlements": "/api/payments/settlements/",

    # Backup
    "restore_points": "/api/backup/restore-points/",
    "backup_records": "/api/backup/records/",

    # Operations
    "control_center": "/api/control-center/",
    "control_health": "/api/control-center/health/",
    "control_financial": "/api/control-center/financial/",
    "control_inventory": "/api/control-center/inventory/",
    "control_operations": "/api/control-center/operations/",
    "control_hr": "/api/control-center/hr/",
    "intelligence": "/api/control-center/intelligence/",
    "control_signals": "/api/control-center/signals/",
    "control_jobs": "/api/control-center/jobs/",

    # Health
    "health": "/api/health/",
    "health_db": "/api/health/db/",
    "health_system": "/api/health/system/",

    # Notifications
    "notifications": "/api/auth/notifications/",
    "notifications_unread": "/api/auth/notifications/unread-count/",

    # Auth
    "login": "/api/auth/login/",
    "logout": "/api/auth/logout/",
    "profile": "/api/auth/profile/",
    "change_password": "/api/auth/change-password/",
}


def get_endpoint(key, **kwargs):
    """Get endpoint URL with optional path parameters."""
    url = API_ENDPOINTS.get(key)
    if url and kwargs:
        try:
            return url.format(**kwargs)
        except KeyError:
            return url
    return url or ""


def extract_list(response):
    """Extract a list from any API response format.
    
    Handles:
    - Direct list: [...]
    - Paginated: {"data": {"count": N, "results": [...]}}
    - Non-paginated: {"data": [...]}
    - Plain dict with results: {"results": [...]}
    """
    if isinstance(response, list):
        return response
    if not isinstance(response, dict):
        return []
    data = response.get("data", response)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        results = data.get("results", data.get("data", []))
        if isinstance(results, list):
            return results
    results = response.get("results", [])
    return results if isinstance(results, list) else []