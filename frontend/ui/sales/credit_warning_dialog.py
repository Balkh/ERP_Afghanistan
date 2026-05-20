"""Credit Warning Dialog.

Displays when a customer approaches or exceeds their credit limit.
Shows current balance, credit limit, utilization percentage, and
whether the transaction is blocked or allowed with warning.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QFrame, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG,
                           MARGIN_PAGE, MARGIN_CARD,
                           TEXT_PAGE_TITLE, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_BODY, TEXT_BODY_SMALL,
                           COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
                           BORDER_RADIUS_MD, BORDER_RADIUS_LG)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize


class CreditWarningDialog(QDialog):
    """Dialog warning about customer credit limit status."""

    def __init__(self, customer_name, current_balance, credit_limit,
                 invoice_amount=None, is_blocked=False, parent=None):
        super().__init__(parent)
        self.customer_name = customer_name
        self.current_balance = current_balance
        self.credit_limit = credit_limit
        self.invoice_amount = invoice_amount or 0
        self.is_blocked = is_blocked
        self.proceed = False
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Credit Limit Warning" if not self.is_blocked else "Credit Limit Exceeded")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)
        layout.setContentsMargins(MARGIN_CARD, MARGIN_CARD, MARGIN_CARD, MARGIN_CARD)

        # Warning icon + title
        if self.is_blocked:
            title_text = "Transaction Blocked"
            title_color = COLOR_DANGER
        else:
            title_text = "Credit Limit Warning"
            title_color = COLOR_WARNING

        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {title_color};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Customer info
        customer_label = QLabel(f"Customer: {self.customer_name}")
        customer_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY};")
        customer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(customer_label)

        # Credit details card
        details_card = QFrame()
        details_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_MD};
            }}
        """)
        details_layout = QVBoxLayout(details_card)
        details_layout.setSpacing(SPACING_SM)

        utilization = (self.current_balance / self.credit_limit * 100) if self.credit_limit > 0 else 0
        new_balance = self.current_balance + self.invoice_amount
        new_utilization = (new_balance / self.credit_limit * 100) if self.credit_limit > 0 else 0

        rows = [
            ("Current Balance", f"{self.current_balance:,.2f} AFN"),
            ("Credit Limit", f"{self.credit_limit:,.2f} AFN"),
            ("Current Utilization", f"{utilization:.1f}%"),
        ]
        if self.invoice_amount > 0:
            rows.append(("Invoice Amount", f"{self.invoice_amount:,.2f} AFN"))
            rows.append(("Balance After Invoice", f"{new_balance:,.2f} AFN"))
            rows.append(("New Utilization", f"{new_utilization:.1f}%"))

        for label_text, value_text in rows:
            row_layout = QHBoxLayout()
            label = QLabel(label_text)
            label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY};")
            row_layout.addWidget(label)
            row_layout.addStretch()
            value = QLabel(value_text)
            value.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}; font-weight: bold;")
            row_layout.addWidget(value)
            details_layout.addLayout(row_layout)

        layout.addWidget(details_card)

        # Warning message
        if self.is_blocked:
            msg = "This customer has exceeded their credit limit. The transaction cannot proceed."
            msg_color = COLOR_DANGER
        elif utilization >= 90:
            msg = "Customer is near their credit limit. Proceed with caution."
            msg_color = COLOR_DANGER
        elif utilization >= 80:
            msg = "Customer has used 80%+ of their credit limit. Consider reviewing their account."
            msg_color = COLOR_WARNING
        else:
            msg = "Customer credit status is within acceptable limits."
            msg_color = COLOR_SUCCESS

        msg_label = QLabel(msg)
        msg_label.setStyleSheet(f"color: {msg_color}; font-size: {TEXT_BODY_SMALL};")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        if not self.is_blocked:
            self.cancel_btn = EnterpriseButton(
                text="Cancel",
                variant=ButtonVariant.SECONDARY,
                size=ButtonSize.SMALL,
            )
            self.cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(self.cancel_btn)

            self.proceed_btn = EnterpriseButton(
                text="Proceed Anyway",
                variant=ButtonVariant.WARNING,
                size=ButtonSize.SMALL,
            )
            self.proceed_btn.clicked.connect(self.on_proceed)
            btn_layout.addWidget(self.proceed_btn)
        else:
            self.ok_btn = EnterpriseButton(
                text="OK",
                variant=ButtonVariant.PRIMARY,
                size=ButtonSize.SMALL,
            )
            self.ok_btn.clicked.connect(self.reject)
            btn_layout.addWidget(self.ok_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def on_proceed(self):
        self.proceed = True
        self.accept()
