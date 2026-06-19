"""Unit tests for report_extractors pure functions.

Tests all extraction functions: extract_items, extract_balance_sheet_items,
extract_profit_loss_items, extract_cash_flow_items.
No Qt dependencies — pure Python data transformations.
"""

import pytest
from ui.accounting.report_extractors import (
    extract_items,
    extract_balance_sheet_items,
    extract_profit_loss_items,
    extract_cash_flow_items,
)


# ---------------------------------------------------------------------------
# extract_items dispatcher
# ---------------------------------------------------------------------------

class TestExtractItems:
    """Test the extract_items dispatcher function."""

    def test_list_input_passthrough(self):
        """Non-dict list input should pass through unchanged."""
        data = [{"a": 1}, {"b": 2}]
        assert extract_items(data, "trial_balance", {"data_key": "accounts"}) == data

    def test_non_dict_non_list_returns_empty(self):
        """Non-dict, non-list input returns empty list."""
        assert extract_items("string", "trial_balance", {}) == []
        assert extract_items(42, "trial_balance", {}) == []
        assert extract_items(None, "trial_balance", {}) == []

    def test_simple_data_key(self):
        """Dict with matching data_key returns that list."""
        data = {"accounts": [{"code": "100"}]}
        config = {"data_key": "accounts"}
        result = extract_items(data, "trial_balance", config)
        assert result == [{"code": "100"}]

    def test_data_key_missing(self):
        """Dict with missing data_key returns empty list."""
        data = {"other": [{"code": "100"}]}
        config = {"data_key": "accounts"}
        result = extract_items(data, "trial_balance", config)
        assert result == []

    def test_none_data_key_wraps_in_list(self):
        """data_key=None wraps the dict in a list."""
        data = {"status": "ok", "count": 5}
        config = {"data_key": None}
        result = extract_items(data, "employee_summary", config)
        assert result == [data]

    def test_balance_sheet_dispatch(self):
        """report_type='balance_sheet' routes to extract_balance_sheet_items."""
        data = {
            "assets": {"sections": [], "total": 100},
            "liabilities": {"sections": [], "total": 50},
            "equity": {"sections": [], "total": 50},
            "is_balanced": True,
            "difference": 0,
        }
        result = extract_items(data, "balance_sheet", {})
        assert isinstance(result, list)
        assert any("BALANCED" in row.get("account_name", "") for row in result)

    def test_profit_loss_dispatch(self):
        """report_type='profit_loss' routes to extract_profit_loss_items."""
        data = {
            "revenue": [],
            "cogs": [],
            "expenses": [],
            "total_revenue": 0,
            "total_cogs": 0,
            "gross_profit": 0,
            "total_expenses": 0,
            "net_income": 0,
        }
        result = extract_items(data, "profit_loss", {})
        assert isinstance(result, list)
        assert any("NET INCOME" in row.get("account_name", "") for row in result)

    def test_cash_flow_dispatch(self):
        """report_type='cash_flow' routes to extract_cash_flow_items."""
        data = {
            "operating_activities": {},
            "investing_activities": {},
            "financing_activities": {},
            "net_change_in_cash": 0,
            "opening_cash_balance": 0,
            "closing_cash_balance": 0,
        }
        result = extract_items(data, "cash_flow", {})
        assert isinstance(result, list)
        assert any("CLOSING CASH BALANCE" in row.get("category", "").upper() for row in result)

    def test_ar_aging_dispatch(self):
        """report_type='ar_aging' returns aging_rows."""
        data = {"aging_rows": [{"customer_name": "Acme"}]}
        result = extract_items(data, "ar_aging", {})
        assert result == [{"customer_name": "Acme"}]

    def test_ap_aging_dispatch(self):
        """report_type='ap_aging' returns aging_rows."""
        data = {"aging_rows": [{"supplier_name": "Globex"}]}
        result = extract_items(data, "ap_aging", {})
        assert result == [{"supplier_name": "Globex"}]


# ---------------------------------------------------------------------------
# extract_balance_sheet_items
# ---------------------------------------------------------------------------

class TestExtractBalanceSheetItems:
    """Test balance sheet flattening."""

    def test_empty_sections(self):
        """All empty sections should produce header + total rows."""
        data = {
            "assets": {"sections": [], "total": 0},
            "liabilities": {"sections": [], "total": 0},
            "equity": {"sections": [], "total": 0},
            "is_balanced": True,
            "difference": 0,
        }
        rows = extract_balance_sheet_items(data)
        assert len(rows) > 0
        assert rows[0]["account_name"] == "ASSETS"

    def test_section_with_accounts(self):
        """Section with accounts should produce category, account, and total rows."""
        data = {
            "assets": {
                "sections": [
                    {
                        "category": "Current Assets",
                        "total": 500,
                        "accounts": [
                            {"account_code": "1000", "account_name": "Cash", "category": "Asset", "amount": 500},
                        ],
                    }
                ],
                "total": 500,
            },
            "liabilities": {"sections": [], "total": 0},
            "equity": {"sections": [], "total": 0},
            "is_balanced": True,
            "difference": 0,
        }
        rows = extract_balance_sheet_items(data)
        names = [r["account_name"] for r in rows]
        assert "ASSETS" in names
        assert "  Current Assets" in names
        assert "    Cash" in names
        assert "Total Assets" in names

    def test_balanced_footer(self):
        """Balanced report should show BALANCED."""
        data = {
            "assets": {"sections": [], "total": 100},
            "liabilities": {"sections": [], "total": 50},
            "equity": {"sections": [], "total": 50},
            "is_balanced": True,
            "difference": 0,
        }
        rows = extract_balance_sheet_items(data)
        footer = rows[-1]["account_name"]
        assert "BALANCED" in footer

    def test_unbalanced_footer(self):
        """Unbalanced report should show NOT BALANCED with difference."""
        data = {
            "assets": {"sections": [], "total": 100},
            "liabilities": {"sections": [], "total": 50},
            "equity": {"sections": [], "total": 45},
            "is_balanced": False,
            "difference": 5,
        }
        rows = extract_balance_sheet_items(data)
        footer = rows[-1]["account_name"]
        assert "NOT BALANCED" in footer
        assert "5" in footer

    def test_all_three_sections_present(self):
        """All three section keys (assets, liabilities, equity) should appear."""
        data = {
            "assets": {"sections": [], "total": 0},
            "liabilities": {"sections": [], "total": 0},
            "equity": {"sections": [], "total": 0},
            "is_balanced": True,
            "difference": 0,
        }
        rows = extract_balance_sheet_items(data)
        names = [r["account_name"] for r in rows]
        assert "ASSETS" in names
        assert "LIABILITIES" in names
        assert "EQUITY" in names


# ---------------------------------------------------------------------------
# extract_profit_loss_items
# ---------------------------------------------------------------------------

class TestExtractProfitLossItems:
    """Test P&L flattening."""

    def test_empty_data(self):
        """Empty P&L data should produce section headers and totals."""
        data = {
            "revenue": [],
            "cogs": [],
            "expenses": [],
            "total_revenue": 0,
            "total_cogs": 0,
            "gross_profit": 0,
            "total_expenses": 0,
            "net_income": 0,
        }
        rows = extract_profit_loss_items(data)
        names = [r["account_name"] for r in rows]
        assert "REVENUE" in names
        assert "COST OF GOODS SOLD" in names
        assert "EXPENSES" in names
        assert "NET INCOME" in names

    def test_revenue_with_sections(self):
        """Revenue sections with accounts should flatten correctly."""
        data = {
            "revenue": [
                {
                    "category": "Product Sales",
                    "total": 1000,
                    "accounts": [
                        {"account_code": "4000", "account_name": "Sales", "category": "Revenue", "amount": 1000},
                    ],
                }
            ],
            "cogs": [],
            "expenses": [],
            "total_revenue": 1000,
            "total_cogs": 0,
            "gross_profit": 1000,
            "total_expenses": 0,
            "net_income": 1000,
        }
        rows = extract_profit_loss_items(data)
        names = [r["account_name"] for r in rows]
        assert "REVENUE" in names
        assert "  Product Sales" in names
        assert "    Sales" in names
        assert "Total Revenue" in names

    def test_net_income_row(self):
        """NET INCOME row should be the last row."""
        data = {
            "revenue": [],
            "cogs": [],
            "expenses": [],
            "total_revenue": 0,
            "total_cogs": 0,
            "gross_profit": 0,
            "total_expenses": 0,
            "net_income": 500,
        }
        rows = extract_profit_loss_items(data)
        last = rows[-1]
        assert last["account_name"] == "NET INCOME"
        assert last["balance"] == "500"

    def test_gross_profit_present(self):
        """GROSS PROFIT row should appear between COGS and expenses."""
        data = {
            "revenue": [],
            "cogs": [],
            "expenses": [],
            "total_revenue": 0,
            "total_cogs": 0,
            "gross_profit": 250,
            "total_expenses": 0,
            "net_income": 250,
        }
        rows = extract_profit_loss_items(data)
        names = [r["account_name"] for r in rows]
        gp_idx = names.index("GROSS PROFIT")
        cogs_idx = names.index("COST OF GOODS SOLD")
        exp_idx = names.index("EXPENSES")
        assert cogs_idx < gp_idx < exp_idx


# ---------------------------------------------------------------------------
# extract_cash_flow_items
# ---------------------------------------------------------------------------

class TestExtractCashFlowItems:
    """Test cash flow flattening."""

    def test_empty_data(self):
        """Empty cash flow data should produce section headers and totals."""
        data = {
            "operating_activities": {},
            "investing_activities": {},
            "financing_activities": {},
            "net_change_in_cash": 0,
            "opening_cash_balance": 0,
            "closing_cash_balance": 0,
        }
        rows = extract_cash_flow_items(data)
        cats = [r["category"] for r in rows]
        assert "Operating Activities" in cats
        assert "Investing Activities" in cats
        assert "Financing Activities" in cats

    def test_operating_with_working_capital(self):
        """Operating section should include working capital changes."""
        data = {
            "operating_activities": {
                "net_income": 100,
                "working_capital_changes": [
                    {"description": "Increase in AR", "change": -20},
                    {"description": "Increase in Inventory", "change": -10},
                ],
                "net_cash_from_operations": 70,
            },
            "investing_activities": {},
            "financing_activities": {},
            "net_change_in_cash": 0,
            "opening_cash_balance": 0,
            "closing_cash_balance": 0,
        }
        rows = extract_cash_flow_items(data)
        cats = [r["category"] for r in rows]
        assert "  Net Income" in cats
        assert "  Increase in AR" in cats
        assert "  Increase in Inventory" in cats
        assert "  Net Cash from Operations" in cats

    def test_closing_balance(self):
        """Closing Cash Balance should be the last row."""
        data = {
            "operating_activities": {},
            "investing_activities": {},
            "financing_activities": {},
            "net_change_in_cash": 100,
            "opening_cash_balance": 200,
            "closing_cash_balance": 300,
        }
        rows = extract_cash_flow_items(data)
        last = rows[-1]
        assert "Closing Cash Balance" in last["category"]
        assert last["amount"] == "300"

    def test_all_three_activity_sections(self):
        """All three activity sections should have net cash lines."""
        data = {
            "operating_activities": {"net_cash_from_operations": 50},
            "investing_activities": {"items": [], "net_cash_from_investing": -30},
            "financing_activities": {"items": [], "net_cash_from_financing": -10},
            "net_change_in_cash": 10,
            "opening_cash_balance": 100,
            "closing_cash_balance": 110,
        }
        rows = extract_cash_flow_items(data)
        cats = [r["category"] for r in rows]
        assert "  Net Cash from Operations" in cats
        assert "  Net Cash from Investing" in cats
        assert "  Net Cash from Financing" in cats
