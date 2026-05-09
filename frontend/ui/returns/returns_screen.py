from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO, COLOR_BG_LIGHT, COLOR_TEXT_SECONDARY_LIGHT, COLOR_BG_BUTTON_LIGHT, COLOR_BORDER_DIALOG, COLOR_TEXT_DIALOG, COLOR_BG_BUTTON_SECONDARY, COLOR_TABLE_GRIDLINE, COLOR_BORDER_TABLE, COLOR_TEXT_TITLE, SPACING_NONE, MARGIN_TOOLBAR)
"""Returns management screen."""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QDateEdit,
                                  QGroupBox, QFormLayout, QDialog, QDialogButtonBox,
                                  QTextEdit, QScrollArea, QInputDialog, QApplication)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen, ScreenState
from ui.constants import (SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
                          FONT_SIZE_MD, FONT_SIZE_LG, FONT_SIZE_XL, FONT_SIZE_TITLE,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD, TABLE_ROW_HEIGHT_MD,
                          BORDER_RADIUS_MD)


class ReturnsScreen(BaseScreen):
    """Screen for managing return orders."""
    
    def __init__(self, parent=None, screen_id="returns", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self.returns_data = []
    
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Returns Management")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_BG_BUTTON_LIGHT};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_TEXT_SECONDARY_LIGHT};
            }}
        """)
        self.btn_refresh.clicked.connect(self._load_returns)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Filter section
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Action Buttons
        action_layout = QHBoxLayout()
        
        self.add_button = QPushButton("+ New Return")
        self.add_button.setMinimumHeight(38)
        self.add_button.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; border-radius: 5px; font-weight: bold; padding: 0 15px;")
        self.add_button.clicked.connect(self._show_add_dialog)
        
        self.approve_button = QPushButton("Approve")
        self.approve_button.setMinimumHeight(38)
        self.approve_button.setStyleSheet(f"background-color: {COLOR_PRIMARY}; color: white; border-radius: 5px; padding: 0 15px;")
        self.approve_button.clicked.connect(self._approve_return)
        
        self.reject_button = QPushButton("Reject")
        self.reject_button.setMinimumHeight(38)
        self.reject_button.setStyleSheet(f"background-color: {COLOR_DANGER}; color: white; border-radius: 5px; padding: 0 15px;")
        self.reject_button.clicked.connect(self._reject_return)
        
        action_layout.addWidget(self.add_button)
        action_layout.addWidget(self.approve_button)
        action_layout.addWidget(self.reject_button)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Loading and Empty states
        self.loading_label = QLabel("Loading return orders...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No return orders found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table section
        self.table = self._create_modern_table()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Return #", "Type", "Invoice #", "Party", "Amount", "Status", 
            "Reason", "Created", "Approved By"
        ])
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
        
        self.approve_button.setEnabled(has_selection)
        self.reject_button.setEnabled(has_selection)
        
        if has_selection:
            row = selected[0].row()
            # We can further refine this by checking the status of the selected item
            # For example, only enable approve/reject if status is PENDING

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        bar.setStyleSheet(f"QGroupBox { border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 10px; color: {COLOR_TEXT_PRIMARY}; }")
        layout = QHBoxLayout(bar)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Type filter
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.return_type_filter = QComboBox()
        self.return_type_filter.addItems(["All Types", "Sale Return", "Purchase Return"])
        self.return_type_filter.setMinimumWidth(150)
        self.return_type_filter.currentTextChanged.connect(self._load_returns)
        type_layout.addWidget(self.return_type_filter)
        layout.addLayout(type_layout)

        # Status filter
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
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
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ border: none; gridline-color: {{COLOR_TABLE_GRIDLINE}}; }}
            QHeaderView::section {{ background-color: {{COLOR_BG_ELEVATED}}; padding: {SPACING_SM}; border: none; border-bottom: 2px solid {{COLOR_BORDER_TABLE}}; font-weight: bold; }}
            QTableWidget::item {{ padding: {SPACING_LG}; }}
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return table
    
    def _view_return(self, row):
        """View details of a return order."""
        # This is typically called on double click or if there was a view button
        return_number = self.table.item(row, 0).text()
        return_item = next((item for item in self.returns_data if item.get("return_number") == return_number), None)
        
        if return_item:
            # For now, just show a message or we could open the dialog in read-only mode
            details = f"Return #: {return_item.get('return_number')}\n"
            details += f"Type: {return_item.get('return_type')}\n"
            details += f"Party: {return_item.get('party_name', return_item.get('supplier_name', ''))}\n"
            details += f"Amount: {return_item.get('total_amount')}\n"
            details += f"Status: {return_item.get('status')}\n"
            details += f"Reason: {return_item.get('reason')}\n"
            details += f"Notes: {return_item.get('notes', '')}"
            
            QMessageBox.information(self, "Return Details", details)

    def _on_search(self, text):
        """Handle search input."""
        self._populate_table()
    
    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        QApplication.processEvents()

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
        """Load returns from API or show mock data."""
        self._show_loading()
        
        if self._api_client:
            try:
                endpoint = get_endpoint("return-orders")
                response = self._api_client.get(endpoint)
                
                if response and isinstance(response, dict) and response.get("success"):
                    self.returns_data = response.get("data", [])
                elif isinstance(response, list):
                    self.returns_data = response
                else:
                    self.returns_data = []
            except Exception as e:
                print(f"Error loading returns: {e}")
                self.returns_data = []
        else:
            self.returns_data = self._get_mock_returns()
        
        self._populate_table()

    def _populate_table(self):
        """Populate table with returns data."""
        self.table.setRowCount(0)
        
        type_filter = self.return_type_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        filtered_data = []
        for item in self.returns_data:
            return_type = item.get("return_type", "")
            status = item.get("status", "")
            
            if type_filter == "Sale Return" and return_type != "SALE_RETURN":
                continue
            if type_filter == "Purchase Return" and return_type != "PURCHASE_RETURN":
                continue
            if status_filter != "All Status" and status_filter.upper() != status.upper():
                continue
            filtered_data.append(item)

        if not filtered_data:
            self._show_empty()
            return

        self._show_data()
        self.table.setRowCount(len(filtered_data))
        
        for row, item in enumerate(filtered_data):
            return_type = item.get("return_type", "")
            status = item.get("status", "")
            
            self.table.setItem(row, 0, QTableWidgetItem(item.get("return_number", "")))
            self.table.setItem(row, 1, QTableWidgetItem("Sale" if return_type == "SALE_RETURN" else "Purchase"))
            self.table.setItem(row, 2, QTableWidgetItem(item.get("invoice_number", item.get("purchase_invoice_number", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(item.get("party_name", item.get("supplier_name", ""))))
            
            amount = float(item.get("total_amount", 0))
            amount_item = QTableWidgetItem(f"{amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, amount_item)
            
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if status == "APPROVED":
                status_item.setForeground(QColor("COLOR_SUCCESS"))
            elif status == "PENDING":
                status_item.setForeground(QColor("COLOR_WARNING"))
            elif status == "REJECTED":
                status_item.setForeground(QColor("COLOR_DANGER"))
            self.table.setItem(row, 5, status_item)
            
            reason = item.get("reason", "")
            self.table.setItem(row, 6, QTableWidgetItem(reason[:30] + "..." if len(reason) > 30 else reason))
            self.table.setItem(row, 7, QTableWidgetItem(item.get("created_at", "")[:10]))
            self.table.setItem(row, 8, QTableWidgetItem(item.get("approved_by_name", "")))
            
            self.table.setRowHeight(row, 45)
    
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
        dialog.exec()
    
    def _approve_return(self):
        """Approve selected return."""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a return to approve.")
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
        
        reply = QMessageBox.question(
            self, "Approve Return",
            f"Are you sure you want to approve return {return_number}?\nThis will update inventory and accounting.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self._api_client:
                try:
                    endpoint = f"/api/returns/return-orders/{return_id}/approve/"
                    response = self._api_client.post(endpoint, {"employee_id": "00000000-0000-0000-0000-000000000001"})
                    
                    if response and isinstance(response, dict) and (response.get("success") or response.get("id")):
                        QMessageBox.information(self, "Success", f"Return {return_number} approved successfully.")
                        self._load_returns()
                    else:
                        error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed to approve"
                        QMessageBox.critical(self, "Error", f"Failed to approve return: {error_msg}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"API Error: {e}")
            else:
                QMessageBox.information(self, "Success", f"Return {return_number} approved (offline mode).")
                self._load_returns()

    def _reject_return(self):
        """Reject selected return."""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a return to reject.")
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
                        QMessageBox.information(self, "Success", f"Return {return_number} rejected.")
                        self._load_returns()
                    else:
                        error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else "Failed to reject"
                        QMessageBox.critical(self, "Error", f"Failed to reject return: {error_msg}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"API Error: {e}")
            else:
                QMessageBox.information(self, "Success", f"Return {return_number} rejected (offline mode).")
                self._load_returns()
        elif ok:
            QMessageBox.warning(self, "Validation Error", "Rejection reason is required.")
    
    def _view_return(self, row):
        """View return details."""
        return_number = self.table.item(row, 0).text()
        QMessageBox.information(self, "Return Details", f"Viewing return: {return_number}")
    
    def on_show(self):
        """Called when screen is shown."""
        self._load_returns()


class ReturnOrderDialog(QDialog):
    """Dialog for creating/editing return orders."""
    
    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("New Return Order")
        self.setMinimumWidth(550)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QDialog { background-color: {COLOR_BG_LIGHT}; }
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid {COLOR_BORDER_DIALOG}; 
                border-radius: 8px; 
                margin-top: 15px;
                padding-top: 15px;
                background-color: white;
            }
            QLabel { color: {COLOR_TEXT_DIALOG}; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        title = QLabel("Create Return Order")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {{COLOR_TEXT_TITLE}};")
        layout.addWidget(title)

        form_group = QGroupBox("Return Details")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(SPACING_MD + SPACING_XS)

        self.return_type = QComboBox()
        self.return_type.addItems(["Sale Return", "Purchase Return"])
        self.return_type.setMinimumHeight(30)
        
        self.invoice = QLineEdit()
        self.invoice.setPlaceholderText("Enter original invoice number")
        self.invoice.setMinimumHeight(30)
        
        self.party = QLineEdit()
        self.party.setPlaceholderText("Customer or Supplier name")
        self.party.setMinimumHeight(30)
        
        self.reason = QTextEdit()
        self.reason.setPlaceholderText("Enter reason for return...")
        self.reason.setMaximumHeight(80)
        
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Additional internal notes...")
        self.notes.setMaximumHeight(60)
        
        form_layout.addRow("Return Type*:", self.return_type)
        form_layout.addRow("Invoice #*:", self.invoice)
        form_layout.addRow("Party Name*:", self.party)
        form_layout.addRow("Reason*:", self.reason)
        form_layout.addRow("Notes:", self.notes)
        
        layout.addWidget(form_group)

        # Buttons
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(35)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setStyleSheet(f"background-color: {{COLOR_BG_BUTTON_SECONDARY}}; color: {{COLOR_TEXT_DIALOG}}; border-radius: 5px;")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Return")
        save_btn.setMinimumHeight(35)
        save_btn.setMinimumWidth(120)
        save_btn.setStyleSheet(f"background-color: {COLOR_SUCCESS}; color: white; border-radius: 5px; font-weight: bold;")
        save_btn.clicked.connect(self.save)
        
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)
    
    def save(self):
        """Save return order."""
        if not self.invoice.text().strip():
            QMessageBox.warning(self, "Validation Error", "Invoice number is required.")
            return
        
        if not self.party.text().strip():
            QMessageBox.warning(self, "Validation Error", "Party name is required.")
            return
        
        if not self.reason.toPlainText().strip():
            QMessageBox.warning(self, "Validation Error", "Reason is required.")
            return
        
        import uuid
        data = {
            "return_type": "SALE_RETURN" if self.return_type.currentText() == "Sale Return" else "PURCHASE_RETURN",
            "invoice": self.invoice.text().strip(),
            "party_name": self.party.text().strip(),
            "reason": self.reason.toPlainText().strip(),
            "notes": self.notes.toPlainText().strip(),
            "status": "PENDING",
            "return_number": f"RET-{uuid.uuid4().hex[:8].upper()}",
        }
        
        endpoint = get_endpoint("return-orders")
        if self.api_client:
            try:
                response = self.api_client.post(endpoint, data)
                if response and isinstance(response, dict):
                    if response.get("success") or response.get("id"):
                        QMessageBox.information(self, "Success", "Return order created successfully.")
                        self.accept()
                        return
                error_msg = response.get("error", {}).get("message", "Failed to create return") if isinstance(response, dict) else "Failed to create return"
                QMessageBox.warning(self, "Error", error_msg)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save: {e}")
        else:
            QMessageBox.information(self, "Success", "Return order created (offline mode).")
            self.accept()