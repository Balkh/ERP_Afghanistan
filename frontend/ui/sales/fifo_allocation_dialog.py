"""FIFO Payment Allocation Dialog.

Allows users to allocate unallocated customer payments to outstanding
invoices using the FIFO (First In, First Out) strategy. Shows available
payments, outstanding invoices, and the allocation results.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QFrame, QGroupBox, QHeaderView, QTableWidget,
                                QTableWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, MARGIN_CARD,
                           TEXT_SECTION_TITLE, TEXT_BODY_SMALL,
                           COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_PRIMARY, COLOR_WARNING,
                           COLOR_INFO, BORDER_RADIUS_MD)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from api.client import APIClient


class FIFOAllocationDialog(QDialog):
    """Dialog for allocating unallocated payments to invoices via FIFO."""

    def __init__(self, customer_id=None, customer_name=None, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.customer_id = customer_id
        self.customer_name = customer_name or "All Customers"
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle(f"FIFO Payment Allocation — {self.customer_name}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACING_MD)
        layout.setContentsMargins(MARGIN_CARD, MARGIN_CARD, MARGIN_CARD, MARGIN_CARD)

        # Header
        title = QLabel("FIFO Payment Allocation")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(title)

        subtitle = QLabel(
            "Automatically allocate unallocated payments to the oldest outstanding invoices first."
        )
        subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY_SMALL};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Summary cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(SPACING_MD)

        self.unallocated_card = self._create_summary_card("Unallocated Payments", "0.00", COLOR_WARNING)
        summary_layout.addWidget(self.unallocated_card)

        self.outstanding_card = self._create_summary_card("Outstanding Invoices", "0", COLOR_INFO)
        summary_layout.addWidget(self.outstanding_card)

        self.allocated_card = self._create_summary_card("To Be Allocated", "0.00", COLOR_PRIMARY)
        summary_layout.addWidget(self.allocated_card)

        layout.addLayout(summary_layout)

        # Unallocated payments table
        payments_group = QGroupBox("Unallocated Payments")
        payments_group.setStyleSheet("""
            QGroupBox {{
                font-size: {TEXT_SECTION_TITLE};
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                margin-top: {SPACING_MD};
                padding-top: {SPACING_MD};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: {SPACING_MD}; padding: 0 {SPACING_SM}; }}
        """)
        payments_layout = QVBoxLayout(payments_group)

        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(4)
        self.payments_table.setHorizontalHeaderLabels(["Date", "Payment #", "Amount", "Method"])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.payments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.payments_table.setAlternatingRowColors(True)
        payments_layout.addWidget(self.payments_table)

        layout.addWidget(payments_group)

        # Outstanding invoices table
        invoices_group = QGroupBox("Outstanding Invoices (Oldest First)")
        invoices_group.setStyleSheet("""
            QGroupBox {{
                font-size: {TEXT_SECTION_TITLE};
                font-weight: bold;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                margin-top: {SPACING_MD};
                padding-top: {SPACING_MD};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: {SPACING_MD}; padding: 0 {SPACING_SM}; }}
        """)
        invoices_layout = QVBoxLayout(invoices_group)

        self.invoices_table = QTableWidget()
        self.invoices_table.setColumnCount(4)
        self.invoices_table.setHorizontalHeaderLabels(["Invoice #", "Date", "Total", "Remaining"])
        self.invoices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setAlternatingRowColors(True)
        invoices_layout.addWidget(self.invoices_table)

        layout.addWidget(invoices_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.allocate_btn = EnterpriseButton(
            text="Run FIFO Allocation",
            variant=ButtonVariant.PRIMARY,
            size=ButtonSize.SMALL,
        )
        self.allocate_btn.clicked.connect(self.run_allocation)
        btn_layout.addWidget(self.allocate_btn)

        self.close_btn = EnterpriseButton(
            text="Close",
            variant=ButtonVariant.SECONDARY,
            size=ButtonSize.SMALL,
        )
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _create_summary_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_MD};
                padding: {SPACING_MD};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(SPACING_XS)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY_SMALL};")
        card_layout.addWidget(title_label)

        value_label = QLabel(str(value))
        value_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color};")
        card_layout.addWidget(value_label)

        return card

    def load_data(self):
        """Load unallocated payments and outstanding invoices."""
        try:
            # Load unallocated payments
            payments_resp = self.api_client.get("sales/customer-payments/unallocated/")
            payments = []
            if payments_resp and payments_resp.get("success", True):
                data = payments_resp.get("data", payments_resp)
                if isinstance(data, list):
                    payments = data
                elif isinstance(data, dict):
                    payments = data.get("results", data.get("payments", []))

            self.payments_table.setRowCount(len(payments))
            total_unallocated = 0
            for i, p in enumerate(payments):
                if self.customer_id and str(p.get("customer_id", "")) != str(self.customer_id):
                    continue
                self.payments_table.setItem(i, 0, QTableWidgetItem(str(p.get("date", ""))))
                self.payments_table.setItem(i, 1, QTableWidgetItem(str(p.get("reference", p.get("id", "")))))
                amount = float(p.get("amount", 0))
                total_unallocated += amount
                self.payments_table.setItem(i, 2, QTableWidgetItem(f"{amount:,.2f}"))
                self.payments_table.setItem(i, 3, QTableWidgetItem(str(p.get("payment_method", ""))))

            # Load outstanding invoices
            invoices_resp = self.api_client.get("sales/invoices/")
            invoices = []
            if invoices_resp and invoices_resp.get("success", True):
                data = invoices_resp.get("data", invoices_resp)
                if isinstance(data, list):
                    invoices = data
                elif isinstance(data, dict):
                    invoices = data.get("results", data.get("invoices", []))

            # Filter to outstanding (not fully paid) and sort by date (oldest first)
            outstanding = [
                inv for inv in invoices
                if float(inv.get("remaining_amount", inv.get("balance", 0))) > 0
            ]
            outstanding.sort(key=lambda x: x.get("invoice_date", x.get("date", "")))

            if self.customer_id:
                outstanding = [
                    inv for inv in outstanding
                    if str(inv.get("customer_id", "")) == str(self.customer_id)
                ]

            self.invoices_table.setRowCount(len(outstanding))
            total_outstanding = 0
            for i, inv in enumerate(outstanding):
                self.invoices_table.setItem(i, 0, QTableWidgetItem(str(inv.get("invoice_number", inv.get("id", "")))))
                self.invoices_table.setItem(i, 1, QTableWidgetItem(str(inv.get("invoice_date", inv.get("date", "")))))
                total = float(inv.get("total_amount", 0))
                remaining = float(inv.get("remaining_amount", inv.get("balance", 0)))
                total_outstanding += remaining
                self.invoices_table.setItem(i, 2, QTableWidgetItem(f"{total:,.2f}"))
                self.invoices_table.setItem(i, 3, QTableWidgetItem(f"{remaining:,.2f}"))

            # Update summary cards
            self.unallocated_card.findChild(QLabel, "", Qt.FindChildOption.FindDirectChildrenOnly)
            # Update card values by accessing the value labels
            for child in self.unallocated_card.findChildren(QLabel):
                if child.text() != "Unallocated Payments":
                    child.setText(f"{total_unallocated:,.2f} AFN")
            for child in self.outstanding_card.findChildren(QLabel):
                if child.text() != "Outstanding Invoices":
                    child.setText(str(len(outstanding)))
            for child in self.allocated_card.findChildren(QLabel):
                if child.text() != "To Be Allocated":
                    child.setText(f"{min(total_unallocated, total_outstanding):,.2f} AFN")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load data: {e}")

    def run_allocation(self):
        """Run FIFO allocation via backend endpoint."""
        try:
            self.allocate_btn.setEnabled(False)
            response = self.api_client.post("sales/customer-payments/fifo_allocate/", {})
            if response and response.get("success", True):
                data = response.get("data", response)
                allocated_count = data.get("allocated_count", 0)
                total_allocated = data.get("total_allocated", 0)
                QMessageBox.information(
                    self, "Allocation Complete",
                    f"Allocated {allocated_count} payments\n"
                    f"Total: {total_allocated:,.2f} AFN"
                )
                self.load_data()
            else:
                QMessageBox.warning(self, "Allocation Failed", str(response))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to run allocation: {e}")
        finally:
            self.allocate_btn.setEnabled(True)
