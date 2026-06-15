"""Reconciliation management screen for returns."""
import logging
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                                QComboBox, QGroupBox, QInputDialog, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from api.endpoints import get_endpoint
from ui.screens.base_screen import BaseScreen
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog
from ui.components.state_helper import StateHelper
from ui.constants import (PADDING_INPUT_H, SPACING_XS, SPACING_SM, SPACING_MD, SPACING_XL, MARGIN_PAGE,
                           TEXT_PAGE_TITLE, TEXT_LABEL, TEXT_BODY, TEXT_BODY_SMALL,
                           COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BORDER, COLOR_TEXT_PRIMARY,
                           COLOR_TEXT_MUTED, COLOR_PRIMARY, BORDER_RADIUS_LG, BORDER_RADIUS_MD,
                           COLOR_TEXT_TITLE, COLOR_TEXT_ON_PRIMARY)


class ReconciliationScreen(BaseScreen):
    """Screen for managing reconciliation entries and mismatches."""

    def __init__(self, api_client=None, parent=None):
        super().__init__(parent=parent)
        self._api_client = api_client
        self.entries_data = []

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # Title
        title = QLabel("Reconciliation Management")
        title.setFont(QFont("Segoe UI", TEXT_PAGE_TITLE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_TEXT_TITLE};")
        layout.addWidget(title)

        # Summary bar
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY_SMALL}pt; padding: {SPACING_XS}px 0;"
        )
        layout.addWidget(self.summary_label)

        # Filter bar
        layout.addWidget(self._create_filter_bar())

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(SPACING_SM)

        self.refresh_btn = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.refresh_btn.clicked.connect(self._load_entries)
        action_layout.addWidget(self.refresh_btn)

        self.fix_btn = EnterpriseButton(text="Fix Mismatch", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.fix_btn.clicked.connect(self._fix_mismatch)
        self.fix_btn.setEnabled(False)
        action_layout.addWidget(self.fix_btn)

        self.view_btn = EnterpriseButton(text="View Details", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.view_btn.clicked.connect(self._view_entry)
        self.view_btn.setEnabled(False)
        action_layout.addWidget(self.view_btn)

        self.export_btn = EnterpriseButton(text="Export CSV", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.export_btn.clicked.connect(self._export_csv)
        action_layout.addWidget(self.export_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Loading, empty, and error states (managed by StateHelper)
        self.state_helper = StateHelper(layout)

        # Table
        columns = [
            TableColumn("id", "ID", width=60),
            TableColumn("type", "Type", width=80),
            TableColumn("invoice", "Invoice", width=100),
            TableColumn("return", "Return", width=100),
            TableColumn("party", "Party", width=120),
            TableColumn("amount", "Amount", width=100, align="right"),
            TableColumn("status", "Status", width=90, align="center"),
            TableColumn("notes", "Notes", width=200),
            TableColumn("fixed_by", "Fixed By", width=100),
        ]
        self.table = EnterpriseTable(columns)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(lambda row, col: self._view_entry())
        layout.addWidget(self.table)

        self._on_selection_changed()
        self._load_entries()

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar.setFont(QFont("Segoe UI", TEXT_LABEL, QFont.Weight.Bold))
        bar.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; "
            f"margin-top: {PADDING_INPUT_H}px; padding-top: {PADDING_INPUT_H}px; color: {COLOR_TEXT_PRIMARY}; }}"
        )
        layout = QHBoxLayout(bar)
        layout.setSpacing(SPACING_MD + SPACING_XS)

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
        self.status_filter.addItems(["All Status", "PENDING", "MATCHED", "MISMATCHED", "FIXED"])
        self.status_filter.setMinimumWidth(140)
        self.status_filter.currentTextChanged.connect(self._load_entries)
        status_layout.addWidget(self.status_filter)
        layout.addLayout(status_layout)

        # Type filter
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Transaction Type:"))
        self.type_filter = QComboBox()
        self.type_filter.setStyleSheet(f"""
            QComboBox {{ background-color: {COLOR_BG_SURFACE}; color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_MD}px; padding: {SPACING_XS}px {SPACING_SM}px; }}
            QComboBox QAbstractItemView {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_PRIMARY}; selection-color: {COLOR_TEXT_ON_PRIMARY};
                border: 1px solid {COLOR_BORDER}; }}
        """)
        self.type_filter.addItems(["All Types", "INVOICE", "RETURN", "PAYMENT", "ADJUSTMENT"])
        self.type_filter.setMinimumWidth(140)
        self.type_filter.currentTextChanged.connect(self._load_entries)
        type_layout.addWidget(self.type_filter)
        layout.addLayout(type_layout)

        # Mismatch quick filter
        self.mismatch_btn = EnterpriseButton(text="Show Mismatches Only", variant=ButtonVariant.WARNING, size=ButtonSize.MEDIUM)
        self.mismatch_btn.clicked.connect(self._show_mismatches_only)
        layout.addWidget(self.mismatch_btn)

        layout.addStretch()
        return bar

    def _on_selection_changed(self):
        """Handle table selection change."""
        selected = self.table.selectedItems()
        has_selection = bool(selected)
        self.fix_btn.setEnabled(has_selection)
        self.view_btn.setEnabled(has_selection)

    def _load_entries(self):
        """Load reconciliation entries from API."""
        self.state_helper.show_loading("Loading reconciliation entries...")
        self.table.setVisible(False)

        if self._api_client:
            try:
                endpoint = get_endpoint("reconciliation")
                params = {}

                status_filter = self.status_filter.currentText()
                if status_filter != "All Status":
                    params["status"] = status_filter

                type_filter = self.type_filter.currentText()
                if type_filter != "All Types":
                    params["transaction_type"] = type_filter

                response = self._api_client.get(endpoint, params=params)

                if response and isinstance(response, dict) and response.get("success"):
                    self.entries_data = response.get("data", [])
                elif isinstance(response, list):
                    self.entries_data = response
                else:
                    self.entries_data = []

                if not self.entries_data:
                    self.state_helper.show_empty(
                        title="No reconciliation entries found",
                        subtitle="Reconciliation matches return orders against invoices to identify discrepancies.\nUse the filters above to narrow results, or click 'Show Mismatches Only' to view unresolved entries.",
                    )
                    self.table.setVisible(False)
                else:
                    self.state_helper.hide()
                    self._populate_table()
                    self._load_summary()
            except Exception as e:
                logging.getLogger(__name__).warning(f"Error loading reconciliation: {e}")
                self.state_helper.show_error(f"Error loading data: {e}", on_retry=self._load_entries)
        else:
            self.state_helper.show_empty("No reconciliation entries found")

    def _show_mismatches_only(self):
        """Show only mismatched entries."""
        self.status_filter.setCurrentText("MISMATCHED")

    def _load_summary(self):
        """Load summary statistics."""
        if not self.entries_data:
            return
        total = len(self.entries_data)
        mismatched = sum(1 for e in self.entries_data if e.get("status") == "MISMATCHED")
        pending = sum(1 for e in self.entries_data if e.get("status") == "PENDING")
        fixed = sum(1 for e in self.entries_data if e.get("status") == "FIXED")

        self.summary_label.setText(
            f"Total: {total} | Pending: {pending} | Mismatched: {mismatched} | Fixed: {fixed}"
        )
        self.summary_label.setVisible(True)

    def _populate_table(self):
        """Populate table with reconciliation data."""
        self.table.setRowCount(0)

        if not self.entries_data:
            self.state_helper.show_empty("No reconciliation entries found")
            self.table.setVisible(False)
            return

        self.state_helper.hide()
        self.table.setVisible(True)

        data = []
        for item in self.entries_data:
            amount = float(item.get("amount", 0))
            data.append({
                "id": str(item.get("id", ""))[:8],
                "type": item.get("transaction_type", ""),
                "invoice": item.get("invoice_number", item.get("purchase_invoice_number", "")),
                "return": item.get("return_number", ""),
                "party": item.get("party_name", item.get("supplier_name", "")),
                "amount": f"{amount:,.2f}",
                "status": item.get("status", ""),
                "notes": (item.get("notes", "") or "")[:40],
                "fixed_by": item.get("fixed_by_name", ""),
            })
        self.table.set_data(data)

    def _view_entry(self):
        """View reconciliation entry details."""
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        entry_id = self.table.item(row, 0).text()

        entry = next((e for e in self.entries_data if str(e.get("id", ""))[:8] == entry_id), None)
        if not entry:
            return

        details = (
            f"ID: {entry.get('id')}\n"
            f"Type: {entry.get('transaction_type')}\n"
            f"Status: {entry.get('status')}\n"
            f"Amount: {entry.get('amount', 0):.2f}\n"
            f"Party: {entry.get('party_name', entry.get('supplier_name', ''))}\n"
            f"Invoice: {entry.get('invoice_number', entry.get('purchase_invoice_number', ''))}\n"
            f"Return: {entry.get('return_number', 'N/A')}\n"
            f"Notes: {entry.get('notes', 'None')}\n"
            f"Fixed By: {entry.get('fixed_by_name', 'N/A')}"
        )
        AlertDialog.info("Reconciliation Details", details, self)

    def _fix_mismatch(self):
        """Fix a mismatched reconciliation entry."""
        selected = self.table.selectedItems()
        if not selected:
            AlertDialog.warning("No Selection", "Please select an entry to fix.", self)
            return

        row = selected[0].row()
        entry_id = self.table.item(row, 0).text()

        entry = next((e for e in self.entries_data if str(e.get("id", ""))[:8] == entry_id), None)
        if not entry:
            return

        if entry.get("status") != "MISMATCHED":
            AlertDialog.warning("Invalid Action", "Only MISMATCHED entries can be fixed.", self)
            return

        notes, ok = QInputDialog.getText(
            self, "Fix Mismatch",
            "Enter fix notes (required):",
            text=""
        )
        if not ok or not notes.strip():
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
                endpoint = f"/api/returns/reconciliation/{entry['id']}/fix/"
                response = self._api_client.post(endpoint, {
                    "employee_id": employee_id.strip(),
                    "notes": notes.strip()
                })

                if response and (response.get("success") or response.get("id")):
                    AlertDialog.info("Success", "Reconciliation entry marked as FIXED.", self)
                    self._load_entries()
                else:
                    err = response.get("error", "Unknown error") if response else "No response"
                    AlertDialog.error("Error", f"Failed to fix: {err}", self)
            except Exception as e:
                AlertDialog.error("Error", f"API Error: {e}", self)

    def _export_csv(self):
        """Export reconciliation entries to CSV."""
        if not self._api_client:
            AlertDialog.warning("No Connection", "CSV export requires API connection.", self)
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Reconciliation to CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        
        try:
            params = {}
            status_filter = self.status_filter.currentText()
            if status_filter != "All Status":
                params["status"] = status_filter
            type_filter = self.type_filter.currentText()
            if type_filter != "All Types":
                params["transaction_type"] = type_filter
            
            response = self._api_client.get("/api/returns/reconciliation/export_csv/", params=params, raw_response=True)
            if response:
                with open(file_path, 'wb') as f:
                    f.write(response)
                AlertDialog.info("Success", f"Reconciliation exported to:\n{file_path}", self)
            else:
                AlertDialog.error("Error", "Failed to export reconciliation.", self)
        except Exception as e:
            AlertDialog.error("Error", f"Export failed: {e}", self)

    def on_show(self):
        """Called when screen is shown."""
        self._load_entries()
