"""Phase 20: Supplier Payment Workspace screen."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QGroupBox, QMessageBox, QApplication,
    QSplitter,
)
from PySide6.QtCore import Qt, Signal, Qt as QtCore
from PySide6.QtGui import QFont

from api.client import APIClient
from api.endpoints import get_endpoint, extract_list
from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE,
    TEXT_BODY, TEXT_LABEL, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING,
    COLOR_DANGER, COLOR_BG_ELEVATED, COLOR_BORDER,
    BORDER_RADIUS_SM, BORDER_RADIUS_LG,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.kpi_cards import MiniMetricCard, SectionHeader
from ui.screens.base_screen import BaseScreen


class SupplierPaymentWorkspace(BaseScreen):
    """Supplier payment workspace - unified view for supplier payment operations."""

    payment_processed = Signal(dict)
    allocation_completed = Signal(dict)

    def __init__(self, parent=None, api_client=None):
        super().__init__(parent, screen_id="supplier_payments")
        self.api_client = api_client or APIClient()
        self.supplier_id = None
        self.supplier_data = None
        self.outstanding_invoices = []
        self.unallocated_payments = []
        self._is_loading = False
        self.setup_ui()

    def _on_screen_shown(self):
        """Prevent BaseScreen from auto-loading on show — we load on supplier selection."""

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_LG)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Supplier Payment Workspace")
        self.title_label.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;"
        )
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.supplier_combo = QComboBox()
        self.supplier_combo.setMinimumWidth(250)
        self.supplier_combo.setStyleSheet(self._combo_style())
        self.supplier_combo.currentIndexChanged.connect(self._on_supplier_selected)
        header_layout.addWidget(QLabel("Supplier:"))
        header_layout.addWidget(self.supplier_combo)

        self.btn_refresh = EnterpriseButton(text="⟳ Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self.refresh_workspace)
        header_layout.addWidget(self.btn_refresh)

        self.btn_process_payment = EnterpriseButton(
            text="+ Process Payment", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM
        )
        self.btn_process_payment.clicked.connect(self._on_process_payment)
        header_layout.addWidget(self.btn_process_payment)

        layout.addLayout(header_layout)

        # Loading label
        self.loading_label = QLabel("Loading workspace...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;"
        )
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        # Main content area
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SPACING_LG)

        # KPI Cards row
        self.kpi_layout = QGridLayout()
        self.kpi_layout.setSpacing(SPACING_MD)
        self.kpi_supplier_balance = MiniMetricCard("Supplier Balance", "0.00", COLOR_DANGER)
        self.kpi_outstanding = MiniMetricCard("Outstanding Invoices", "0", COLOR_WARNING)
        self.kpi_unallocated = MiniMetricCard("Unallocated Payments", "0.00", COLOR_SUCCESS)
        self.kpi_total_purchases = MiniMetricCard("Total Purchases", "0.00", COLOR_PRIMARY)
        self.kpi_layout.addWidget(self.kpi_supplier_balance, 0, 0)
        self.kpi_layout.addWidget(self.kpi_outstanding, 0, 1)
        self.kpi_layout.addWidget(self.kpi_unallocated, 0, 2)
        self.kpi_layout.addWidget(self.kpi_total_purchases, 0, 3)
        content_layout.addLayout(self.kpi_layout)

        # Splitter for invoices and payments
        splitter = QSplitter(QtCore.Vertical)

        # Outstanding Invoices section
        invoices_section = self._create_invoices_section()
        splitter.addWidget(invoices_section)

        # Unallocated Payments section
        payments_section = self._create_payments_section()
        splitter.addWidget(payments_section)

        splitter.setSizes([400, 300])
        content_layout.addWidget(splitter)

        # Allocation Summary
        self.allocation_summary = self._create_allocation_summary()
        content_layout.addWidget(self.allocation_summary)

        layout.addWidget(self.content_widget)
        self.content_widget.setVisible(False)

        # Load suppliers for dropdown
        self._load_suppliers()

    def _create_invoices_section(self):
        """Create outstanding invoices section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, SPACING_MD, 0, 0)
        layout.setSpacing(SPACING_MD)

        header = SectionHeader("Outstanding Invoices")
        layout.addWidget(header)

        columns = [
            TableColumn("invoice_number", "Invoice #", width=120),
            TableColumn("invoice_date", "Date", width=100, align="center"),
            TableColumn("due_date", "Due Date", width=100, align="center"),
            TableColumn("total_amount", "Total", width=100, align="right"),
            TableColumn("paid_amount", "Paid", width=100, align="right"),
            TableColumn("remaining", "Remaining", width=100, align="right"),
            TableColumn("status", "Status", width=100, align="center"),
        ]
        self.invoices_table = EnterpriseTable(columns)
        self.invoices_table.set_density("compact")
        layout.addWidget(self.invoices_table)

        return section

    def _create_payments_section(self):
        """Create unallocated payments section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, SPACING_MD, 0, 0)
        layout.setSpacing(SPACING_MD)

        header_layout = QHBoxLayout()
        header = SectionHeader("Unallocated Payments")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.btn_allocate = EnterpriseButton(
            text="Allocate FIFO", variant=ButtonVariant.SUCCESS, size=ButtonSize.SMALL
        )
        self.btn_allocate.clicked.connect(self._on_allocate_fifo)
        header_layout.addWidget(self.btn_allocate)

        layout.addLayout(header_layout)

        columns = [
            TableColumn("payment_number", "Payment #", width=120),
            TableColumn("payment_date", "Date", width=100, align="center"),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("method", "Method", width=100),
            TableColumn("reference", "Reference", width=120),
            TableColumn("status", "Status", width=80, align="center"),
        ]
        self.payments_table = EnterpriseTable(columns)
        self.payments_table.set_density("compact")
        layout.addWidget(self.payments_table)

        return section

    def _create_allocation_summary(self):
        """Create allocation summary section."""
        section = QGroupBox("Allocation Summary")
        section.setFont(QFont("Segoe UI", TEXT_LABEL))
        section.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; "
            f"margin-top: 10px; padding-top: 10px; color: {COLOR_TEXT_PRIMARY}; }}"
        )
        layout = QGridLayout(section)
        layout.setSpacing(SPACING_MD)

        self.lbl_total_invoices = QLabel("Total Invoices: 0")
        self.lbl_total_payments = QLabel("Total Payments: 0")
        self.lbl_fully_paid = QLabel("Fully Paid: 0")
        self.lbl_partial = QLabel("Partial: 0")
        self.lbl_total_allocated = QLabel("Total Allocated: 0.00")

        labels = [
            self.lbl_total_invoices, self.lbl_total_payments,
            self.lbl_fully_paid, self.lbl_partial,
            self.lbl_total_allocated,
        ]
        for i, lbl in enumerate(labels):
            lbl.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}pt;")
            row, col = divmod(i, 3)
            layout.addWidget(lbl, row, col)

        return section

    def _combo_style(self):
        return """
            QComboBox {{
                background-color: {COLOR_BG_ELEVATED};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM};
                padding: {SPACING_XS}px {SPACING_SM}px;
                color: {COLOR_TEXT_PRIMARY};
                min-height: 30px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {COLOR_TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_BG_ELEVATED};
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY};
            }}
        """

    def _show_loading(self, show=True):
        self._is_loading = show
        self.loading_label.setVisible(show)
        self.content_widget.setVisible(not show)
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_data(self):
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.content_widget.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _load_suppliers(self):
        """Load supplier list for dropdown."""
        try:
            endpoint = get_endpoint("suppliers") or "/api/purchases/suppliers/"
            response = self.api_client.get(endpoint, params={"page_size": 100})
            suppliers = extract_list(response)
            self.supplier_combo.clear()
            self.supplier_combo.addItem("-- Select Supplier --", None)
            for s in suppliers:
                self.supplier_combo.addItem(s.get("name", ""), s.get("id"))
        except Exception as e:
            print(f"Error loading suppliers: {e}")

    def _on_supplier_selected(self, index):
        """Handle supplier selection."""
        supplier_id = self.supplier_combo.itemData(index)
        if supplier_id:
            self.supplier_id = supplier_id
            self.load_workspace(supplier_id)

    def load_workspace(self, supplier_id):
        """Load complete payment workspace for a supplier."""
        self._show_loading()
        try:
            endpoint = f"/api/v1/payment-operations/suppliers/{supplier_id}/payment-workspace/"
            response = self.api_client.get(endpoint)
            if response and response.get("success"):
                data = response.get("data", {})
                self._update_workspace(data)
            else:
                self._show_error("Failed to load workspace")
        except Exception as e:
            print(f"Error loading workspace: {e}")
            self._show_error(f"Error: {e}")
        self._show_data()

    def _update_workspace(self, data):
        """Update all workspace components with data."""
        # Supplier data
        supplier = data.get("supplier", {})
        self.supplier_data = supplier
        self.kpi_supplier_balance.update_value(f"{self._safe_float(supplier.get('balance', 0)):,.2f}")

        # Outstanding invoices
        self.outstanding_invoices = data.get("outstanding_invoices", [])
        self.kpi_outstanding.update_value(str(len(self.outstanding_invoices)))
        self._update_invoices_table()

        # Unallocated payments
        self.unallocated_payments = data.get("unallocated_payments", [])
        total_unallocated = sum(
            self._safe_float(p.get("unallocated_amount", p.get("amount", 0)))
            for p in self.unallocated_payments
        )
        self.kpi_unallocated.update_value(f"{total_unallocated:,.2f}")
        self._update_payments_table()

        # Allocation summary
        summary = data.get("allocation_summary", {})
        self.lbl_total_invoices.setText(f"Total Invoices: {summary.get('total_invoices', 0)}")
        self.lbl_total_payments.setText(f"Total Payments: {summary.get('total_payments', 0)}")
        self.lbl_fully_paid.setText(f"Fully Paid: {summary.get('fully_paid', 0)}")
        self.lbl_partial.setText(f"Partial: {summary.get('partial', 0)}")
        self.lbl_total_allocated.setText(
            f"Total Allocated: {self._safe_float(summary.get('total_allocated', 0)):,.2f}"
        )

    def _update_invoices_table(self):
        """Update invoices table."""
        data = []
        for inv in self.outstanding_invoices:
            data.append({
                "invoice_number": inv.get("invoice_number", ""),
                "invoice_date": str(inv.get("invoice_date", ""))[:10],
                "due_date": str(inv.get("due_date", ""))[:10],
                "total_amount": f"{self._safe_float(inv.get('total_amount', 0)):,.2f}",
                "paid_amount": f"{self._safe_float(inv.get('paid_amount', 0)):,.2f}",
                "remaining": f"{self._safe_float(inv.get('remaining', 0)):,.2f}",
                "status": inv.get("status", ""),
            })
        self.invoices_table.set_data(data)

    def _update_payments_table(self):
        """Update payments table."""
        data = []
        for pay in self.unallocated_payments:
            data.append({
                "payment_number": pay.get("payment_number", ""),
                "payment_date": str(pay.get("payment_date", ""))[:10],
                "amount": f"{self._safe_float(pay.get('amount', 0)):,.2f}",
                "method": pay.get("payment_method", ""),
                "reference": pay.get("reference_number", ""),
                "status": pay.get("status", ""),
            })
        self.payments_table.set_data(data)

    def _show_error(self, message):
        """Show error state."""
        self._is_loading = False
        self.loading_label.setText(message)
        self.loading_label.setStyleSheet(
            f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;"
        )
        self.loading_label.setVisible(True)
        self.content_widget.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def refresh_workspace(self):
        """Refresh workspace data."""
        if self.supplier_id:
            self.load_workspace(self.supplier_id)

    def _on_process_payment(self):
        """Open process payment dialog."""
        if not self.supplier_id:
            QMessageBox.warning(self, "No Supplier", "Please select a supplier first.")
            return
        QMessageBox.information(self, "Coming Soon", "Payment processing dialog will be implemented next.")

    def _on_allocate_fifo(self):
        """Run FIFO allocation for unallocated payments."""
        if not self.supplier_id:
            return
        try:
            endpoint = f"/api/v1/payment-operations/suppliers/{self.supplier_id}/allocate-unallocated/"
            response = self.api_client.post(endpoint, {})
            if response and response.get("success"):
                data = response.get("data", {})
                QMessageBox.information(
                    self, "Allocation Complete",
                    f"Allocated {data.get('allocations_created', 0)} payments.\n"
                    f"Total: {self._safe_float(data.get('total_allocated', 0)):,.2f}"
                )
                self.allocation_completed.emit(data)
                self.refresh_workspace()
        except Exception as e:
            QMessageBox.critical(self, "Allocation Error", str(e))

    def _safe_float(self, value, default=0.0):
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
