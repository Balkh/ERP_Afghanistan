"""
Phase 5B.16 — Cash Flow Report Screen.

Uses existing FinancialReportEngine API via BaseReportScreen.
"""
from ui.accounting.base_report_screen import BaseReportScreen
from ui.constants import COLOR_TEXT_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER


class CashFlowScreen(BaseReportScreen):
    """Cash flow statement report."""

    def __init__(self, parent=None):
        super().__init__("Cash Flow Statement", parent)
        self.report_api_endpoint = "/api/accounting/accounts/cash_flow/"

    def run_report(self):
        self._show_loading(True)
        try:
            params = self._get_report_params()
            resp = self.api_client.get(self.report_api_endpoint, params=params)
            self.report_data = resp.get("data", resp) if isinstance(resp, dict) else resp
            self._populate_table()
            self._show_loading(False)
        except Exception as e:
            self._show_error(f"Failed to load cash flow: {e}")

    def _populate_table(self):
        data = self.report_data if isinstance(self.report_data, dict) else {}
        sections = [
            ("Operating Activities", data.get("operating", [])),
            ("Investing Activities", data.get("investing", [])),
            ("Financing Activities", data.get("financing", [])),
        ]
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Category", "Amount", "Subtotal"])

        rows = []
        totals = {"operating": 0, "investing": 0, "financing": 0}
        for section_name, items in sections:
            rows.append((f"[{section_name}]", "", ""))
            section_total = 0
            for item in items if isinstance(items, list) else []:
                name = item.get("name", item.get("account", ""))
                amount = float(item.get("amount", item.get("balance", 0)))
                section_total += amount
                rows.append(("  " + name, f"{amount:,.2f}", ""))
            rows.append(("", "", f"{section_total:,.2f}"))
            rows.append(("", "", ""))

        net_change = sum(totals.values())
        rows.append(("NET CASH FLOW", "", f"{net_change:,.2f}"))

        self.table.setRowCount(len(rows))
        for i, (col0, col1, col2) in enumerate(rows):
            self.table.setItem(i, 0, self._item(col0))
            self.table.setItem(i, 1, self._item(col1))
            self.table.setItem(i, 2, self._item(col2) if col2 else self._item(""))

        self.summary_label.setText(f"Net Cash Flow: {net_change:,.2f} {data.get('currency', 'AFN')}")
