"""Financial Integrity Validation Screen.

Displays results from the backend financial integrity validation service.
Shows balance mismatches, orphaned payments, overpaid invoices, and
provides one-click auto-fix functionality.
"""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout,
                                QLabel, QWidget, QFrame, QScrollArea, QGroupBox)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from api.client import APIClient
from datetime import datetime

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, MARGIN_PAGE,
                           TEXT_SECTION_TITLE, TEXT_BODY_SMALL,
                           TEXT_LABEL, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO,
                           BORDER_RADIUS_MD)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.screens.base_screen import BaseScreen
from theme.style_builder import UIStyleBuilder


class FinancialIntegrityScreen(BaseScreen):
    """Screen displaying financial integrity validation results."""

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="financial_integrity")
        self.api_client = api_client or APIClient()
        self.setup_ui()
        self._start_refresh_timer()

    def _on_screen_shown(self):
        """Resume timer when screen is shown."""
        if self._timer and not self._timer.isActive():
            self._timer.start(300000)

    def _on_screen_hidden(self):
        """Pause timer when screen is hidden."""
        if self._timer and self._timer.isActive():
            self._timer.stop()

    def _start_refresh_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.run_validation)
        self._timer.start(300000)  # 5 minutes

    def cleanup(self):
        self._timer.stop()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Financial Integrity Validation")
        title.setStyleSheet(UIStyleBuilder.get_page_header_style())
        header_layout.addWidget(title)

        self.validate_btn = EnterpriseButton(
            text="Run Validation",
            variant=ButtonVariant.PRIMARY,
            size=ButtonSize.SMALL,
        )
        self.validate_btn.clicked.connect(self.run_validation)
        header_layout.addWidget(self.validate_btn)

        self.fix_btn = EnterpriseButton(
            text="Auto-Fix Balances",
            variant=ButtonVariant.WARNING,
            size=ButtonSize.SMALL,
        )
        self.fix_btn.clicked.connect(self.auto_fix_balances)
        header_layout.addWidget(self.fix_btn)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Status bar
        self.status_bar = QLabel("Click 'Run Validation' to check financial integrity.")
        self.status_bar.setStyleSheet(UIStyleBuilder.get_label_style("muted"))
        layout.addWidget(self.status_bar)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(SPACING_LG)

        # Summary cards
        self.summary_cards = self._create_summary_cards()
        content_layout.addWidget(self.summary_cards)

        # Issues table
        issues_group = QGroupBox("Issues Found")
        issues_group.setStyleSheet(UIStyleBuilder.get_form_section_style(primary=True))
        issues_layout = QVBoxLayout(issues_group)

        self.issues_table = EnterpriseTable(columns=[
            TableColumn("Check", "check", 180),
            TableColumn("Detail", "detail", 250),
            TableColumn("Value", "value", 120),
            TableColumn("Expected", "expected", 120),
            TableColumn("Action", "action", 100),
        ])
        issues_layout.addWidget(self.issues_table)
        content_layout.addWidget(issues_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_summary_cards(self):
        card_widget = QWidget()
        card_layout = QGridLayout(card_widget)
        card_layout.setSpacing(SPACING_MD)

        self.card_labels = {}
        configs = [
            ("total_checks", "Total Checks", "7", COLOR_INFO),
            ("passed", "Passed", "0", COLOR_SUCCESS),
            ("failed", "Failed", "0", COLOR_DANGER),
            ("total_issues", "Total Issues", "0", COLOR_WARNING),
        ]

        for i, (key, label, default, color) in enumerate(configs):
            card = self._create_card(label, default, color)
            card_layout.addWidget(card, i // 2, i % 2)

        return card_widget

    def _create_card(self, title, value, color):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(UIStyleBuilder.get_card_style())
        layout = QVBoxLayout(card)
        layout.setSpacing(SPACING_XS)

        title_label = QLabel(title)
        title_label.setStyleSheet(UIStyleBuilder.get_label_style("label_small"))
        layout.addWidget(title_label)

        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        value_label.setStyleSheet(UIStyleBuilder.get_colored_label_style(color, size_pt=20, weight=700))
        layout.addWidget(value_label)

        self.card_labels[title.replace(" ", "_").lower()] = value_label
        return card

    def run_validation(self):
        """Run financial integrity validation asynchronously."""
        self.status_bar.setText("Running validation...")
        self.validate_btn.setEnabled(False)

        def on_success(response):
            self.validate_btn.setEnabled(True)
            if response and response.get("success", True):
                data = response.get("data", response)
                self._update_ui(data)
                self.status_bar.setText(
                    f"Validation complete at {datetime.now().strftime('%H:%M:%S')} — "
                    f"{data.get('total_issues', 0)} issues found"
                )
            else:
                self.status_bar.setText(f"Validation failed: {response}")

        def on_error(message):
            self.validate_btn.setEnabled(True)
            self.status_bar.setText(f"Error: {message}")

        started = self.run_api_request(
            key="financial_integrity_validate",
            method="GET",
            endpoint="/api/ops/financial-integrity/",
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self.validate_btn.setEnabled(True)

    def auto_fix_balances(self):
        """Run auto-fix for balance mismatches asynchronously."""
        self.status_bar.setText("Running auto-fix...")
        self.fix_btn.setEnabled(False)

        def on_success(response):
            self.fix_btn.setEnabled(True)
            if response and response.get("success", True):
                data = response.get("data", response)
                customers_fixed = data.get("customers", {}).get("fixed", 0)
                suppliers_fixed = data.get("suppliers", {}).get("fixed", 0)
                self.status_bar.setText(
                    f"Auto-fix complete: {customers_fixed} customers, {suppliers_fixed} suppliers fixed"
                )
                self.run_validation()
            else:
                self.status_bar.setText(f"Auto-fix failed: {response}")

        def on_error(message):
            self.fix_btn.setEnabled(True)
            self.status_bar.setText(f"Error: {message}")

        started = self.run_api_request(
            key="financial_integrity_auto_fix",
            method="POST",
            endpoint="/api/ops/financial-integrity/",
            data={"auto_fix": True},
            on_success=on_success,
            on_error=on_error,
        )
        if not started:
            self.fix_btn.setEnabled(True)

    def _update_ui(self, data):
        """Update UI with validation results."""
        checks = data.get("checks", {})
        total_issues = data.get("total_issues", 0)

        passed = sum(1 for c in checks.values() if c.get("ok", False))
        failed = len(checks) - passed

        self.card_labels["total_checks"].setText(str(len(checks)))
        self.card_labels["passed"].setText(str(passed))
        self.card_labels["failed"].setText(str(failed))
        self.card_labels["total_issues"].setText(str(total_issues))

        # Build issues list
        issues = []
        for check_name, check_result in checks.items():
            if not check_result.get("ok", True):
                for issue in check_result.get("issues", []):
                    issues.append({
                        "check": check_name.replace("_", " ").title(),
                        "detail": issue.get("customer_code", issue.get("supplier_code",
                                   issue.get("invoice_number", issue.get("type", "N/A")))),
                        "value": issue.get("stored_balance", issue.get("paid_amount",
                                  issue.get("balance", "N/A"))),
                        "expected": issue.get("expected_balance", issue.get("total_amount",
                                      issue.get("balance", "N/A"))),
                        "action": "Auto-fix" if "balance" in check_name else "Review",
                    })

        self.issues_table.set_data(issues)
