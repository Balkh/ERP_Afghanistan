"""Compatibility wrapper for the consolidated report browser."""
from ui.accounting.report_browser import ReportBrowser


class ProfitAndLossScreen(ReportBrowser):
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent=parent, report_type="profit_loss", api_client=api_client)
