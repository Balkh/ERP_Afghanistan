"""Returns management screen."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout,
                                   QLabel, QLineEdit,
                                   QHeaderView, QComboBox,
                                    QGroupBox, QFormLayout, QWidget,
                                   QTextEdit, QInputDialog, QFileDialog,
                                   QTableWidget, QTableWidgetItem, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, MARGIN_PAGE, TEXT_PAGE_TITLE, TEXT_SECTION_TITLE,
                           TEXT_BODY, TEXT_BODY_SMALL, TEXT_LABEL, BORDER_RADIUS_MD, BORDER_RADIUS_LG, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER,
                           COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
                           COLOR_PRIMARY, COLOR_TEXT_ON_PRIMARY,
                           COLOR_TEXT_TITLE, COLOR_BORDER_DIALOG, COLOR_BORDER_INPUT)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, ConfirmDialog, EnterpriseDialog, DialogType
from ui.components.forms import FormSection
from ui.components.tables import EnterpriseTable, TableColumn, build_table_stylesheet, DataEntryGrid


class ReturnsScreen(BaseScreen):
    """Screen for managing return orders."""
    
    def __init__(self, parent=None, screen_id="returns", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self.returns_data = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Returns Management")
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = EnterpriseButton(text="\u27f3 Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_refresh.clicked.connect(self._load_returns)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Filter section
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Action Buttons
        action_layout = QHBoxLayout()
        
        self.add_button = EnterpriseButton(text="+ New Return", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.add_button.clicked.connect(self._show_add_dialog)
        
        self.approve_button = EnterpriseButton(text="Approve", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.approve_button.clicked.connect(self._approve_return)
        
        self.reject_button = EnterpriseButton(text="Reject", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
        self.reject_button.clicked.connect(self._reject_return)
        
        self.void_button = EnterpriseButton(text="Void", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        self.void_button.clicked.connect(self._void_return)
        self.void_button.setEnabled(False)
        
        self.print_button = EnterpriseButton(text="Print Receipt", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.print_button.clicked.connect(self._print_receipt)
        self.print_button.setEnabled(False)
        
        self.export_button = EnterpriseButton(text="Export CSV", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.export_button.clicked.connect(self._export_csv)
        
        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.approve_button)
        action_layout.addWidget(self.reject_button)
        action_layout.addWidget(self.void_button)
        action_layout.addWidget(self.print_button)
        action_layout.addWidget(self.export_button)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Summary stats label
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}pt; "
            f"padding: {SPACING_XS}px 0;"
        )
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # Loading and Empty states
        self.loading_label = QLabel("Loading return orders...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px;")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No return orders found\n\nUse '+ New Return' to create a return order.\nReturns are used to handle damaged, expired, or returned goods from customers or to suppliers.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; padding: {SPACING_XL + SPACING_MD}px; line-height: 1.6;")
        self.empty_label.setWordWrap(True)
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table section
        columns = [
            TableColumn("return_no", "Return #", width=100),
            TableColumn("type", "Type", width=80),
            TableColumn("invoice_no", "Invoice #", width=100),
            TableColumn("party", "Party", width=150),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("status", "Status", width=80, align="center"),
            TableColumn("reason", "Reason", width=150),
            TableColumn("created", "Created", width=100),
            TableColumn("approved_by", "Approved By", width=120),
        ]
        self.table = EnterpriseTable(columns)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(lambda row, col: self._view_return(row))
        layout.addWidget(self.table)
        
        # Initial button state
        self._on_selection_changed()
        
        self._load_returns()

    def _on_selection_changed(self):
        """Handle table selection change to enable/disable action buttons."""
        selected = self.table.selectedItems()
        has_selection = bool(selected)
        
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.void_button.setEnabled(False)
        self.print_button.setEnabled(False)
        
        if has_selection:
            row = selected[0].row()
            status = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
            
            if status == "PENDING":
                self.approve_button.setEnabled(True)
                self.reject_button.setEnabled(True)
            elif status in ("APPROVED", "VOIDED", "COMPLETED"):
                self.void_button.setEnabled(status == "APPROVED")
                self.print_button.setEnabled(True)

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}; margin-top: {PADDING_INPUT_H}px; padding-top: {PADDING_INPUT_H}px; color: {COLOR_TEXT_PRIMARY}; }}")
        layout = QHBoxLayout(bar)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Type filter
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.return_type_filter = QComboBox()
        self.return_type_filter.setStyleSheet(f"""
            QComboBox {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; padding: {SPACING_XS}px {SPACING_SM}px; }}
            QComboBox QAbstractItemView {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY}; selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: 1px solid {COLOR_BORDER}; }}
        """)
        self.return_type_filter.addItems(["All Types", "Sale Return", "Purchase Return"])
        self.return_type_filter.setMinimumWidth(150)
        self.return_type_filter.currentTextChanged.connect(self._load_returns)
        type_layout.addWidget(self.return_type_filter)
        layout.addLayout(type_layout)

        # Status filter
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.setStyleSheet(f"""
            QComboBox {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; padding: {SPACING_XS}px {SPACING_SM}px; }}
            QComboBox QAbstractItemView {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY}; selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: 1px solid {COLOR_BORDER}; }}
        """)
        self.status_filter.addItems(["All Status", "Pending", "Approved", "Rejected", "Completed"])
        self.status_filter.setMinimumWidth(150)
        self.status_filter.currentTextChanged.connect(self._load_returns)
        status_layout.addWidget(self.status_filter)
        layout.addLayout(status_layout)

        # Search
        search_layout = QVBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by return number...")
        self.search_input.setMinimumWidth(250)
        self.search_input.setMinimumHeight(30)
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        layout.addStretch()
        return bar

    def _create_modern_table(self):
        table = EnterpriseTable([])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return table

    def _on_search(self, text):
        """Handle search input."""
        self._populate_table()
    
    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)

    def _show_empty(self, message="No return orders found"):
        """Show empty state."""
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)

    def _show_data(self):
        """Show data table."""
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.table.setVisible(True)

    def _load_returns(self):
        """Load returns from API with server-side filtering."""
        self._show_loading()
        
        if self._api_client:
            try:
                endpoint = get_endpoint("return-orders")
                params = {}
                
                # Server-side type filter
                type_filter = self.return_type_filter.currentText()
                if type_filter == "Sale Return":
                    params["return_type"] = "SALE_RETURN"
                elif type_filter == "Purchase Return":
                    params["return_type"] = "PURCHASE_RETURN"
                
                # Server-side status filter
                status_filter = self.status_filter.currentText()
                if status_filter != "All Status":
                    params["status"] = status_filter.upper()
                
                # Server-side search
                search_text = self.search_input.text().strip()
                if search_text:
                    params["search"] = search_text
                
                response = self._api_client.get(endpoint, params=params)
                
                if response and isinstance(response, dict) and response.get("success"):
                    self.returns_data = response.get("data", [])
                elif isinstance(response, list):
                    self.returns_data = response
                else:
                    self.returns_data = []
                
                if not self.returns_data:
                    self._show_empty("No return orders match your filters")
                else:
                    self._populate_table()
                    self._load_summary()
            except Exception as e:
                print(f"Error loading returns: {e}")
                self.returns_data = self._get_mock_returns()
                self._populate_table()
        else:
            self.returns_data = self._get_mock_returns()
            self._populate_table()

    def _load_summary(self):
        """Load and display summary statistics from /summary/ endpoint."""
        if not self._api_client:
            return
        try:
            response = self._api_client.get("/api/returns/return-orders/summary/")
            if response and isinstance(response, dict):
                data = response.get("data", response)
                if isinstance(data, dict):
                    summary_text = (
                        f"Total: {data.get('total', 0)} | "
                        f"Pending: {data.get('pending', 0)} | "
                        f"Approved: {data.get('approved', 0)} | "
                        f"Rejected: {data.get('rejected', 0)} | "
                        f"Total Amount: {float(data.get('total_amount', 0)):.2f} AFN"
                    )
                    self.summary_label.setText(summary_text)
                    self.summary_label.setVisible(True)
        except Exception:
            pass

    def _populate_table(self):
        """Populate table with returns data (already filtered server-side)."""
        self.table.setRowCount(0)
        
        if not self.returns_data:
            self._show_empty()
            return

        self._show_data()
        data = []
        for item in self.returns_data:
            return_type = item.get("return_type", "")
            status = item.get("status", "")
            amount = float(item.get("total_amount", 0))
            data.append({
                "return_no": item.get("return_number", ""),
                "type": "Sale" if return_type == "SALE_RETURN" else "Purchase",
                "invoice_no": item.get("invoice_number", item.get("purchase_invoice_number", "")),
                "party": item.get("party_name", item.get("supplier_name", "")),
                "amount": f"{amount:,.2f}",
                "status": status,
                "reason": item.get("reason", "")[:50],
                "created": str(item.get("created_at", ""))[:10],
                "approved_by": item.get("approved_by_name", ""),
            })
        self.table.set_data(data)
    
    def _get_mock_returns(self):
        """Get mock returns for development."""
        return [
            {
                "id": "1",
                "return_number": "SR-001",
                "return_type": "SALE_RETURN",
                "invoice_number": "INV-001",
                "party_name": "Ahmed Pharmacy",
                "total_amount": "1500.00",
                "status": "PENDING",
                "reason": "Damaged goods",
                "created_at": "2026-05-01",
                "approved_by_name": ""
            },
            {
                "id": "2",
                "return_number": "PR-002",
                "return_type": "PURCHASE_RETURN",
                "purchase_invoice_number": "PI-001",
                "supplier_name": "Afghan Medical Corp",
                "total_amount": "2500.00",
                "status": "APPROVED",
                "reason": "Expired items",
                "created_at": "2026-04-28",
                "approved_by_name": "Admin"
            }
        ]

    def _show_add_dialog(self):
        """Show dialog to add new return."""
        dialog = ReturnOrderDialog(self._api_client, self)
        if dialog.exec():
            self._load_returns()
    
    def _approve_return(self):
        """Approve selected return."""
        selected = self.table.selectedItems()
        if not selected:
            AlertDialog.warning("No Selection", "Please select a return to approve.", self)
            return
        
        row = selected[0].row()
        # Find the original data item for this row
        # Since the table is filtered, we need to be careful.
        # A better way is to store the ID in the table item's data
        return_number = self.table.item(row, 0).text()
        
        # Finding the item in returns_data by return_number
        return_item = next((item for item in self.returns_data if item.get("return_number") == return_number), None)
        if not return_item:
            return

        return_id = return_item.get("id")
        
        if not ConfirmDialog.confirm("Approve Return",
            f"Are you sure you want to approve return {return_number}?\nThis will update inventory and accounting.",
            self):
            return

        if self._api_client:
            try:
                employee_id, ok = QInputDialog.getText(
                    self, "Employee ID",
                    "Enter your employee ID for approval audit:",
                    text=""
                )
                if not ok or not employee_id.strip():
                    return
                
                endpoint = f"/api/returns/return-orders/{return_id}/approve/"
                response = self._api_client.post(endpoint, {"employee_id": employee_id.strip()})
                
                if response and isinstance(response, dict) and (response.get("success") or response.get("id")):
                    AlertDialog.info("Success", f"Return {return_number} approved successfully.", self)
                    self._load_returns()
                else:
                    error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed to approve"
                    AlertDialog.error("Error", f"Failed to approve return: {error_msg}", self)
            except Exception as e:
                AlertDialog.error("Error", f"API Error: {e}", self)
        else:
            AlertDialog.info("Success", f"Return {return_number} approved (offline mode).", self)
            self._load_returns()

    def _reject_return(self):
        """Reject selected return."""
        selected = self.table.selectedItems()
        if not selected:
            AlertDialog.warning("No Selection", "Please select a return to reject.", self)
            return
        
        row = selected[0].row()
        return_number = self.table.item(row, 0).text()
        
        return_item = next((item for item in self.returns_data if item.get("return_number") == return_number), None)
        if not return_item:
            return

        return_id = return_item.get("id")
        
        text, ok = QInputDialog.getMultiLineText(
            self, "Reject Return",
            f"Enter reason for rejecting return {return_number}:"
        )
        
        if ok and text.strip():
            if self._api_client:
                try:
                    endpoint = f"/api/returns/return-orders/{return_id}/reject/"
                    response = self._api_client.post(endpoint, {"notes": text.strip()})
                    
                    if response and isinstance(response, dict) and (response.get("success") or response.get("id")):
                        AlertDialog.info("Success", f"Return {return_number} rejected.", self)
                        self._load_returns()
                    else:
                        error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed to reject"
                        AlertDialog.error("Error", f"Failed to reject return: {error_msg}", self)
                except Exception as e:
                    AlertDialog.error("Error", f"API Error: {e}", self)
            else:
                AlertDialog.info("Success", f"Return {return_number} rejected (offline mode).", self)
                self._load_returns()

    def _void_return(self):
        """Void an approved return."""
        selected = self.table.selectedItems()
        if not selected:
            AlertDialog.warning("No Selection", "Please select a return to void.", self)
            return
        
        row = selected[0].row()
        return_number = self.table.item(row, 0).text()
        
        return_item = next((item for item in self.returns_data if item.get("return_number") == return_number), None)
        if not return_item:
            return

        return_id = return_item.get("id")
        
        if not ConfirmDialog.confirm("Void Return",
            f"Are you sure you want to void return {return_number}?\nThis will reverse inventory and accounting entries.",
            self):
            return

        reason, ok = QInputDialog.getText(
            self, "Void Reason",
            "Enter reason for voiding (required):",
            text=""
        )
        if not ok or not reason.strip():
            return

        employee_id, ok = QInputDialog.getText(
            self, "Employee ID",
            "Enter your employee ID for audit:",
            text=""
        )
        if not ok or not employee_id.strip():
            return

        if self._api_client:
            try:
                endpoint = f"/api/returns/return-orders/{return_id}/void/"
                response = self._api_client.post(endpoint, {
                    "employee_id": employee_id.strip(),
                    "reason": reason.strip()
                })

                if response and (response.get("success") or response.get("id")):
                    AlertDialog.info("Success", f"Return {return_number} voided successfully.", self)
                    self._load_returns()
                else:
                    err = response.get("error", "Unknown error") if response else "No response"
                    AlertDialog.error("Error", f"Failed to void: {err}", self)
            except Exception as e:
                AlertDialog.error("Error", f"API Error: {e}", self)
        elif ok:
            AlertDialog.warning("Validation Error", "Rejection reason is required.", self)
    

    
    def _export_csv(self):
        """Export return orders to CSV."""
        if not self._api_client:
            AlertDialog.warning("No Connection", "CSV export requires API connection.", self)
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Returns to CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        
        try:
            response = self._api_client.get("/api/returns/return-orders/export_csv/", raw_response=True)
            if response:
                with open(file_path, 'wb') as f:
                    f.write(response)
                AlertDialog.info("Success", f"Returns exported to:\n{file_path}", self)
            else:
                AlertDialog.error("Error", "Failed to export returns.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Export failed: {e}", self)
    
    def _print_receipt(self):
        """Print/download PDF receipt for selected return."""
        selected = self.table.selectedItems()
        if not selected:
            AlertDialog.warning("No Selection", "Please select a return to print.", self)
            return
        
        row = selected[0].row()
        return_number = self.table.item(row, 0).text()
        
        return_item = next((item for item in self.returns_data if item.get("return_number") == return_number), None)
        if not return_item:
            return
        
        return_id = return_item.get("id")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Return Receipt", f"return_{return_number}.pd", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        
        if self._api_client:
            try:
                response = self._api_client.get(f"/api/returns/return-orders/{return_id}/receipt_pdf/", raw_response=True)
                if response:
                    with open(file_path, 'wb') as f:
                        f.write(response)
                    AlertDialog.info("Success", f"Receipt saved to:\n{file_path}", self)
                else:
                    AlertDialog.error("Error", "Failed to generate receipt.", self)
            except Exception as e:
                AlertDialog.error("Error", f"API Error: {e}", self)
    
    def on_show(self):
        """Called when screen is shown."""
        self._load_returns()


class ReturnOrderDialog(EnterpriseDialog):
    """Dialog for creating return orders with line-item entry."""

    def __init__(self, api_client=None, parent=None):
        self.api_client = api_client
        self._invoice_data = None
        self._items = []
        super().__init__("New Return Order", DialogType.CUSTOM, parent)
        self.setMinimumWidth(750)
        self.setMinimumHeight(600)
        self._build_content()

    def _create_button_area(self):
        return None

    def set_invoice_type(self, return_type):
        """Pre-select return type (SALE_RETURN or PURCHASE_RETURN)."""
        idx = 0 if return_type == "SALE_RETURN" else 1
        self.return_type_cb.setCurrentIndex(idx)

    def prefill_from_invoice(self, invoice_id):
        """Load invoice data and pre-fill return items."""
        if not self.api_client:
            return
        try:
            is_sale = self.return_type_cb.currentText() == "Sale Return"
            endpoint = f"/api/sales/invoices/{invoice_id}/" if is_sale else f"/api/purchases/invoices/{invoice_id}/"
            resp = self.api_client.get(endpoint)
            if resp and isinstance(resp, dict):
                data = resp.get("data", resp)
                self._invoice_data = data
                self._items = data.get("items", [])
                self._populate_items()
        except Exception:
            pass

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        title = QLabel("Create Return Order")
        title.setFont(QFont("Segoe UI", TEXT_SECTION_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_TITLE};")
        layout.addWidget(title)

        section = FormSection("Return Header", primary=True)

        self.return_type_cb = QComboBox()
        self.return_type_cb.addItems(["Sale Return", "Purchase Return"])
        self.return_type_cb.currentIndexChanged.connect(self._on_type_change)
        section.add_field(self.return_type_cb, "Return Type*:")

        self.invoice_search = QLineEdit()
        self.invoice_search.setPlaceholderText("Search invoice by number, customer, or supplier...")
        self.invoice_search.setMinimumHeight(30)
        self.invoice_search.setStyleSheet(
            f"background-color: {COLOR_BG_INPUT}; color: {COLOR_TEXT_PRIMARY}; "
            f"border: 1px solid {COLOR_BORDER_INPUT}; border-radius: {BORDER_RADIUS_MD}; "
            f"padding: 0 {SPACING_SM}px;"
        )
        self.invoice_search.returnPressed.connect(self._load_invoice)
        section.add_field(self.invoice_search, "Invoice:")

        self.party_label = QLabel("Party: —")
        self.party_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        section.add_field(self.party_label, "")

        self.invoice_total_label = QLabel("Invoice Total: —")
        self.invoice_total_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        section.add_field(self.invoice_total_label, "")

        self.reason = QTextEdit()
        self.reason.setPlaceholderText("Enter reason for return...")
        self.reason.setMaximumHeight(60)
        section.add_field(self.reason, "Reason*:")

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Additional internal notes...")
        self.notes.setMaximumHeight(60)
        section.add_field(self.notes, "Notes:")

        layout.addWidget(section)

        items_group = QGroupBox("Return Items")
        items_group.setStyleSheet(
            f"QGroupBox {{ font-weight: bold; border: 1px solid {COLOR_BORDER_DIALOG}; "
            f"border-radius: {BORDER_RADIUS_LG}; margin-top: {SPACING_LG}px; padding-top: {SPACING_LG}px; }}"
        )
        items_layout = QVBoxLayout(items_group)

        self.items_table = DataEntryGrid(
            ["Product", "Sold Qty", "To Return", "Unit Price", "Discount", "Tax", "Total"]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 7):
            self.items_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setMinimumHeight(150)
        self.items_table.cell_value_changed.connect(self._on_cell_changed)
        items_layout.addWidget(self.items_table)

        self.summary_label = QLabel("Refund Preview: 0.00 AFN")
        self.summary_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; font-size: {TEXT_BODY}pt;")
        items_layout.addWidget(self.summary_label)

        layout.addWidget(items_group)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = EnterpriseButton(text="Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        cancel_btn.clicked.connect(self.reject)

        save_btn = EnterpriseButton(text="Save Return", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        save_btn.clicked.connect(self.save)

        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        self.set_content(widget)
        return widget

    def _on_type_change(self):
        self._invoice_data = None
        self._items = []
        self.items_table.clear_all_rows()
        self.party_label.setText("Party: —")
        self.invoice_total_label.setText("Invoice Total: —")
        self.summary_label.setText("Refund Preview: 0.00 AFN")

    def _load_invoice(self):
        query = self.invoice_search.text().strip()
        if not query or not self.api_client:
            return
        try:
            is_sale = self.return_type_cb.currentIndex() == 0
            endpoint = "/api/sales/invoices/" if is_sale else "/api/purchases/invoices/"
            response = self.api_client.get(endpoint, params={"search": query})
            if response and isinstance(response, dict):
                invoices = response.get("results", [])
                if not invoices:
                    invoices = [response] if response.get("id") else []
                if invoices:
                    self._invoice_data = invoices[0]
                    self._populate_items()
                else:
                    AlertDialog.warning("Not Found", f"No invoice found matching '{query}'", self)
        except Exception:
            pass

    def _populate_items(self):
        inv = self._invoice_data
        if not inv:
            return

        self.party_label.setText(f"Party: {inv.get('customer_name', inv.get('supplier_name', 'N/A'))}")
        self.invoice_total_label.setText(f"Invoice Total: {inv.get('total_amount', 0):.2f} AFN")

        items = inv.get("items", [])
        self._items = []
        self.items_table.clear_all_rows()

        for i, item in enumerate(items):
            product_name = item.get("product_name", "Unknown")
            sold_qty = float(item.get("quantity", 0))
            unit_price = float(item.get("unit_price", 0))
            discount = float(item.get("discount", 0))
            tax = float(item.get("tax", 0))

            self._items.append({
                "product": item.get("product"),
                "product_name": product_name,
                "quantity": 0,
                "unit_price": unit_price,
                "discount_amount": discount,
                "tax_amount": tax,
                "max_qty": sold_qty,
            })

            self.items_table.add_row([
                product_name,
                str(int(sold_qty)),
                "0",
                f"{unit_price:.2f}",
                f"{discount:.2f}",
                f"{tax:.2f}",
                "0.00",
            ])

    def _on_cell_changed(self, row, col, value):
        if col != 2 or row >= len(self._items):
            return
        try:
            qty = int(value or "0")
            max_qty = int(self._items[row]["max_qty"])
            if qty < 0:
                qty = 0
            if qty > max_qty:
                qty = max_qty
            self._items[row]["quantity"] = qty

            up = self._items[row]["unit_price"]
            disc = self._items[row]["discount_amount"]
            tax = self._items[row]["tax_amount"]
            ratio = qty / max_qty if max_qty > 0 else 0
            total = (qty * up) - (disc * ratio) + (tax * ratio)

            current = list(self.items_table.get_row_values(row))
            current[6] = f"{total:.2f}"
            self.items_table.set_row_values(row, current)

            refund_total = sum(
                (it["quantity"] * it["unit_price"])
                - (it["discount_amount"] * (it["quantity"] / it["max_qty"] if it["max_qty"] > 0 else 0))
                + (it["tax_amount"] * (it["quantity"] / it["max_qty"] if it["max_qty"] > 0 else 0))
                for it in self._items
            )
            self.summary_label.setText(f"Refund Preview: {refund_total:.2f} AFN")
        except (ValueError, ZeroDivisionError):
            pass

    def save(self):
        if not self.reason.toPlainText().strip():
            AlertDialog.warning("Validation Error", "Reason is required.", self)
            return

        items_to_return = [it for it in self._items if it["quantity"] > 0]
        if not items_to_return:
            AlertDialog.warning("Validation Error", "At least one item must have a return quantity > 0.", self)
            return

        is_sale = self.return_type_cb.currentIndex() == 0
        data = {
            "return_type": "SALE_RETURN" if is_sale else "PURCHASE_RETURN",
            "reason": self.reason.toPlainText().strip(),
            "notes": self.notes.toPlainText().strip(),
            "status": "PENDING",
            "items": [],
        }

        if self._invoice_data:
            data["invoice"] = self._invoice_data.get("id") if is_sale else None
            data["purchase_invoice"] = self._invoice_data.get("id") if not is_sale else None
            data["party"] = self._invoice_data.get("customer", self._invoice_data.get("customer_id"))
            data["supplier"] = self._invoice_data.get("supplier", self._invoice_data.get("supplier_id"))

        total_amount = 0.0
        for it in items_to_return:
            max_qty = it["max_qty"]
            ratio = it["quantity"] / max_qty if max_qty > 0 else 0
            prorated_discount = it["discount_amount"] * ratio
            prorated_tax = it["tax_amount"] * ratio
            item_total = (it["quantity"] * it["unit_price"]) - prorated_discount + prorated_tax
            total_amount += item_total

            data["items"].append({
                "product": it["product"],
                "return_quantity": it["quantity"],
                "unit_price": it["unit_price"],
                "discount_amount": prorated_discount,
                "tax_amount": prorated_tax,
            })

        data["total_amount"] = round(total_amount, 2)

        try:
            if self.api_client:
                response = self.api_client.post("/api/returns/return-orders/", data)
            else:
                import uuid
                response = {
                    "success": True,
                    "data": {
                        "return_number": f"RET-{uuid.uuid4().hex[:8].upper()}",
                        "items_count": len(data["items"]),
                    }
                }

            if response and (response.get("success") or "id" in response):
                AlertDialog.info("Success",
                    f"Return created with {len(data['items'])} item(s)\n"
                    f"Total: {data['total_amount']:.2f} AFN",
                    self
                )
                self.accept()
            else:
                err = response.get("error", "Unknown error") if response else "No response"
                AlertDialog.error("Error", f"Failed to create return: {err}", self)
        except Exception as e:
            AlertDialog.error("Error", f"Failed to create return: {e}", self)