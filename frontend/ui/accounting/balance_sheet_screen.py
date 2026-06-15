"""Compatibility wrapper for the consolidated report browser."""
from ui.accounting.report_browser import ReportBrowser


class BalanceSheetScreen(ReportBrowser):
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent=parent, report_type="balance_sheet", api_client=api_client)
