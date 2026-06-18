"""Pure data extraction functions for financial report flattening.

These functions convert nested API response structures into flat row dicts
suitable for EnterpriseTable display.  They have NO Qt dependencies and are
easily unit-testable.
"""


def extract_items(data, report_type, config):
    """Extract the correct list of items from the API response based on report type."""
    if not isinstance(data, dict):
        return data if isinstance(data, list) else []

    if report_type == "balance_sheet":
        return extract_balance_sheet_items(data)
    elif report_type == "profit_loss":
        return extract_profit_loss_items(data)
    elif report_type == "cash_flow":
        return extract_cash_flow_items(data)
    elif report_type in ("ar_aging", "ap_aging"):
        return data.get("aging_rows", [])
    elif config.get("data_key"):
        return data.get(config["data_key"], [])
    else:
        return [data]


def extract_balance_sheet_items(data):
    """Convert balance sheet nested structure to flat rows."""
    rows = []
    for section_key in ("assets", "liabilities", "equity"):
        section_data = data.get(section_key, {})
        if not section_data and not isinstance(section_data, dict):
            continue
        rows.append({
            "account_code": "",
            "account_name": section_key.upper(),
            "account_type": "",
            "balance": "",
        })
        for section in section_data.get("sections", []):
            rows.append({
                "account_code": "",
                "account_name": f"  {section.get('category', '')}",
                "account_type": "",
                "balance": str(section.get('total', 0)),
            })
            for acc in section.get("accounts", []):
                rows.append({
                    "account_code": acc.get("account_code", ""),
                    "account_name": f"    {acc.get('account_name', '')}",
                    "account_type": acc.get("category", ""),
                    "balance": str(acc.get('amount', 0)),
                })
        rows.append({
            "account_code": "",
            "account_name": f"Total {section_key.title()}",
            "account_type": "",
            "balance": str(section_data.get('total', 0)),
        })
        rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

    # Include any unknown top-level keys
    known = {"assets", "liabilities", "equity", "is_balanced", "difference"}
    for key in data:
        if key not in known and isinstance(data[key], dict):
            section_data = data[key]
            rows.append({
                "account_code": "",
                "account_name": key.upper(),
                "account_type": "",
                "balance": "",
            })
            for section in section_data.get("sections", []):
                rows.append({
                    "account_code": "",
                    "account_name": f"  {section.get('category', '')}",
                    "account_type": "",
                    "balance": str(section.get('total', 0)),
                })
                for acc in section.get("accounts", []):
                    rows.append({
                        "account_code": acc.get("account_code", ""),
                        "account_name": f"    {acc.get('account_name', '')}",
                        "account_type": acc.get("category", ""),
                        "balance": str(acc.get('amount', 0)),
                    })
            rows.append({
                "account_code": "",
                "account_name": f"Total {key.title()}",
                "account_type": "",
                "balance": str(section_data.get('total', 0)),
            })
            rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

    is_balanced = data.get("is_balanced", False)
    diff = data.get("difference", 0)
    rows.append({
        "account_code": "",
        "account_name": "BALANCED" if is_balanced else f"NOT BALANCED (diff: {diff})",
        "account_type": "",
        "balance": "",
    })
    return rows


def extract_profit_loss_items(data):
    """Convert P&L nested structure to flat rows."""
    rows = []
    rows.append({"account_code": "", "account_name": "REVENUE", "account_type": "", "balance": ""})
    for section in data.get("revenue", []):
        if isinstance(section, dict) and "accounts" in section:
            rows.append({
                "account_code": "",
                "account_name": f"  {section.get('category', '')}",
                "account_type": "",
                "balance": str(section.get('total', 0)),
            })
            for acc in section.get("accounts", []):
                rows.append({
                    "account_code": acc.get("account_code", ""),
                    "account_name": f"    {acc.get('account_name', '')}",
                    "account_type": acc.get("category", ""),
                    "balance": str(acc.get('amount', 0)),
                })
    rows.append({"account_code": "", "account_name": "Total Revenue", "account_type": "", "balance": str(data.get('total_revenue', 0))})
    rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

    rows.append({"account_code": "", "account_name": "COST OF GOODS SOLD", "account_type": "", "balance": ""})
    for section in data.get("cogs", []):
        if isinstance(section, dict) and "accounts" in section:
            for acc in section.get("accounts", []):
                rows.append({
                    "account_code": acc.get("account_code", ""),
                    "account_name": f"    {acc.get('account_name', '')}",
                    "account_type": acc.get("category", ""),
                    "balance": str(acc.get('amount', 0)),
                })
    rows.append({"account_code": "", "account_name": "Total COGS", "account_type": "", "balance": str(data.get('total_cogs', 0))})
    rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

    rows.append({"account_code": "", "account_name": "GROSS PROFIT", "account_type": "", "balance": str(data.get('gross_profit', 0))})
    rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

    rows.append({"account_code": "", "account_name": "EXPENSES", "account_type": "", "balance": ""})
    for section in data.get("expenses", []):
        if isinstance(section, dict) and "accounts" in section:
            rows.append({
                "account_code": "",
                "account_name": f"  {section.get('category', '')}",
                "account_type": "",
                "balance": str(section.get('total', 0)),
            })
            for acc in section.get("accounts", []):
                rows.append({
                    "account_code": acc.get("account_code", ""),
                    "account_name": f"    {acc.get('account_name', '')}",
                    "account_type": acc.get("category", ""),
                    "balance": str(acc.get('amount', 0)),
                })
    rows.append({"account_code": "", "account_name": "Total Expenses", "account_type": "", "balance": str(data.get('total_expenses', 0))})
    rows.append({"account_code": "", "account_name": "", "account_type": "", "balance": ""})

    rows.append({"account_code": "", "account_name": "NET INCOME", "account_type": "", "balance": str(data.get('net_income', 0))})
    return rows


def extract_cash_flow_items(data):
    """Convert cash flow nested structure to flat rows."""
    rows = []
    operating = data.get("operating_activities", {})
    rows.append({"category": "Operating Activities", "amount": ""})
    rows.append({"category": "  Net Income", "amount": str(operating.get('net_income', 0))})
    for wc in operating.get("working_capital_changes", []):
        rows.append({"category": f"  {wc.get('description', '')}", "amount": str(wc.get('change', 0))})
    rows.append({"category": "  Net Cash from Operations", "amount": str(operating.get('net_cash_from_operations', 0))})
    rows.append({"category": "", "amount": ""})

    investing = data.get("investing_activities", {})
    rows.append({"category": "Investing Activities", "amount": ""})
    for item in investing.get("items", []):
        rows.append({"category": f"  {item.get('description', '')}", "amount": str(item.get('change', 0))})
    rows.append({"category": "  Net Cash from Investing", "amount": str(investing.get('net_cash_from_investing', 0))})
    rows.append({"category": "", "amount": ""})

    financing = data.get("financing_activities", {})
    rows.append({"category": "Financing Activities", "amount": ""})
    for item in financing.get("items", []):
        rows.append({"category": f"  {item.get('description', '')}", "amount": str(item.get('change', 0))})
    rows.append({"category": "  Net Cash from Financing", "amount": str(financing.get('net_cash_from_financing', 0))})
    rows.append({"category": "", "amount": ""})

    rows.append({"category": "NET CHANGE IN CASH", "amount": str(data.get('net_change_in_cash', 0))})
    rows.append({"category": "Opening Cash Balance", "amount": str(data.get('opening_cash_balance', 0))})
    rows.append({"category": "Closing Cash Balance", "amount": str(data.get('closing_cash_balance', 0))})
    return rows
