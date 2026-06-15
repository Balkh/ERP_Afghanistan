"""Compatibility wrapper for the consolidated report browser."""
from ui.accounting.report_browser import ReportBrowser


class TrialBalanceScreen(ReportBrowser):
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent=parent, report_type="trial_balance", api_client=api_client)
