from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QPushButton, QComboBox, QLineEdit, QDateEdit,
                               QMessageBox, QGroupBox, QApplication)
from PySide6.QtCore import Qt, Slot, Signal, QTimer
from PySide6.QtGui import QFont, QColor
from api.client import APIClient
from api.endpoints import get_endpoint
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)


class JournalEntryScreen(QFrame):
    """Journal Entry list screen with filtering and actions."""

    entry_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.entries = []
        self._is_loading = False
        self.setup_ui()
        try:
            self.load_entries()
        except Exception as e:
            print(f"Initial load failed: {e}")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section with title and refresh button
        header_layout = QHBoxLayout()
        header = QLabel("Journal Entries")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("⟳ Refresh")
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_TEXT_MUTED}};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_XS} {SPACING_MD};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {{COLOR_BORDER}};
            }}
        """)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Toolbar for actions
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Filter section
        filter_bar = self._create_filter_bar()
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading journal entries...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No journal entries found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        # Table section
        self.table = self._create_table()
        layout.addWidget(self.table)

    def _create_toolbar(self):
        toolbar = QFrame()
        toolbar.setStyleSheet(f"background-color: {COLOR_BG_MAIN}; border: 1px solid {COLOR_BORDER}; border-radius: 8px;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM + SPACING_XS)

        self.btn_new = QPushButton(" New Entry")
        self.btn_view = QPushButton(" View Details")
        self.btn_post = QPushButton(" Post")
        self.btn_unpost = QPushButton(" Unpost")
        self.btn_reverse = QPushButton(" Reverse")

        # Style buttons with modern dark theme colors
        self.btn_new.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_SUCCESS}};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: {SPACING_SM} {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_SUCCESS}};
            }}
        """)
        self.btn_view.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_PRIMARY}};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_PRIMARY}};
            }}
        """)
        self.btn_post.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_WARNING}};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_WARNING}};
            }}
        """)
        self.btn_unpost.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_WARNING}};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_WARNING}};
            }}
        """)
        self.btn_reverse.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_DANGER}};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_DANGER}};
            }}
        """)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_TEXT_MUTED}};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
            }}
            QPushButton:hover {{
                background-color: {{COLOR_BORDER}};
            }}
        """)

        for btn in [self.btn_new, self.btn_view, self.btn_post, self.btn_unpost, self.btn_reverse]:
            btn.setMinimumHeight(38)
            btn.setMinimumWidth(130)
            btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
            layout.addWidget(btn)

        for btn in [self.btn_view, self.btn_post, self.btn_unpost, self.btn_reverse]:
            btn.setEnabled(False)

        layout.addStretch()

        self.btn_new.clicked.connect(self._on_new)
        self.btn_view.clicked.connect(self._on_view)
        self.btn_post.clicked.connect(self._on_post)
        self.btn_unpost.clicked.connect(self._on_unpost)
        self.btn_reverse.clicked.connect(self._on_reverse)
        self.btn_refresh.clicked.connect(self.load_entries)

        return toolbar

    def _create_filter_bar(self):
        bar = QGroupBox("Filters")
        bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        bar.setStyleSheet(f"QGroupBox { border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 10px; color: {COLOR_TEXT_PRIMARY}; }")
        layout = QHBoxLayout(bar)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Type filter
        type_layout = QVBoxLayout()
        type_layout.addWidget(QLabel("Entry Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItem("All", "")
        for t in ["SALE", "PURCHASE", "PAYMENT", "RECEIPT", "ADJUSTMENT", "TRANSFER", "OPENING", "CLOSING", "REVERSAL"]:
            self.type_filter.addItem(t, t)
        self.type_filter.setMinimumWidth(120)
        type_layout.addWidget(self.type_filter)
        layout.addLayout(type_layout)

        # Status filter
        status_layout = QVBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("All", "")
        self.status_filter.addItem("Posted", "posted")
        self.status_filter.addItem("Draft", "draft")
        self.status_filter.setMinimumWidth(100)
        status_layout.addWidget(self.status_filter)
        layout.addLayout(status_layout)

        # Date range
        date_layout = QVBoxLayout()
        date_label_layout = QHBoxLayout()
        date_label_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        date_label_layout.addWidget(self.date_from)
        
        date_label_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        date_label_layout.addWidget(self.date_to)
        date_layout.addLayout(date_label_layout)
        layout.addLayout(date_layout)

        # Search
        search_layout = QVBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Entry # or description...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMinimumHeight(30)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Apply button
        self.btn_apply = QPushButton("Apply Filters")
        self.btn_apply.setMinimumHeight(35)
        self.btn_apply.setMinimumWidth(100)
        self.btn_apply.setStyleSheet(f"background-color: {COLOR_TEXT_SECONDARY}; color: white; border-radius: 5px;")
        self.btn_apply.clicked.connect(self.load_entries)
        
        btn_layout = QVBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        return bar

    def _create_table(self):
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Entry #", "Date", "Type", "Description", "Debit", "Credit", "Status", "Reference"
        ])
        
        # Style header
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid {{COLOR_BORDER_LIGHT}};
                border-radius: 5px;
                gridline-color: {{COLOR_BG_ELEVATED}};
            }}
            QHeaderView::section {{
                background-color: {{COLOR_BG_ELEVATED}};
                padding: {SPACING_SM};
                border: none;
                border-bottom: 2px solid {{COLOR_BORDER_LIGHT}};
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: {SPACING_SM};
            }}
        """)
        
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.itemSelectionChanged.connect(self._on_selection_changed)
        table.itemDoubleClicked.connect(self._on_view)

        return table

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self._is_loading = show
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No entries found"):
        """Show empty state."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self._is_loading = False
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def load_entries(self):
        self._show_loading()
        params = {"page_size": 100}

        type_val = self.type_filter.currentData()
        if type_val:
            params["entry_type"] = type_val

        status_val = self.status_filter.currentData()
        if status_val == "posted":
            params["is_posted"] = "true"
        elif status_val == "draft":
            params["is_posted"] = "false"

        search = self.search_input.text().strip()
        if search:
            params["search"] = search

        try:
            endpoint = get_endpoint("journal_entries")
            data = self.api_client.get(endpoint, params=params)
            if data and isinstance(data, dict):
                raw_entries = data.get("results", []) or data.get("data", []) or []
            elif data and isinstance(data, list):
                raw_entries = data
            else:
                raw_entries = []
            self.entries = [e for e in raw_entries if isinstance(e, dict)]
            self._populate_table()
        except Exception as e:
            self.entries = []
            self._populate_table()
            print(f"Error loading entries: {e}")

    def _populate_table(self):
        if not self.entries:
            self.table.setRowCount(0)
            self._show_empty("No journal entries found matching these criteria.")
            return

        self._show_data()
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            if not isinstance(entry, dict):
                continue

            # Entry Number
            num_item = QTableWidgetItem(entry.get("entry_number") or "")
            num_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, num_item)
            
            # Date
            date_item = QTableWidgetItem(entry.get("entry_date") or "")
            date_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, date_item)
            
            # Type
            type_item = QTableWidgetItem(entry.get("entry_type") or "")
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, type_item)

            # Description
            description = entry.get("description") or ""
            self.table.setItem(row, 3, QTableWidgetItem(description[:60] if len(description) > 60 else description))

            # Debit
            debit = self._safe_float(entry.get("total_debit"))
            debit_item = QTableWidgetItem(f"{debit:,.2f}")
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            debit_item.setForeground(QColor("{COLOR_SUCCESS}"))
            self.table.setItem(row, 4, debit_item)

            # Credit
            credit = self._safe_float(entry.get("total_credit"))
            credit_item = QTableWidgetItem(f"{credit:,.2f}")
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            credit_item.setForeground(QColor({COLOR_DANGER}))
            self.table.setItem(row, 5, credit_item)

            # Status
            is_posted = entry.get("is_posted") or False
            status = "Posted" if is_posted else "Draft"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if is_posted:
                status_item.setForeground(QColor({COLOR_SUCCESS}))
                status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            else:
                status_item.setForeground(QColor({COLOR_WARNING}))
            self.table.setItem(row, 6, status_item)

            # Reference
            self.table.setItem(row, 7, QTableWidgetItem(entry.get("reference") or ""))

            entry_id = entry.get("id")
            if entry_id:
                for col in range(8):
                    item = self.table.item(row, col)
                    if item:
                        item.setData(Qt.UserRole, entry_id)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        has_selection = bool(selected)
        self.btn_view.setEnabled(has_selection)

        if has_selection:
            row = selected[0].row()
            entry = self.entries[row] if row < len(self.entries) else None
            is_posted = entry.get("is_posted", False) if entry else False
            self.btn_post.setEnabled(not is_posted)
            self.btn_unpost.setEnabled(is_posted)
            self.btn_reverse.setEnabled(is_posted)

    def _on_new(self):
        from ui.accounting.components.journal_entry_form import JournalEntryFormDialog
        dialog = JournalEntryFormDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_entries()

    def _on_view(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry = self.entries[row] if row < len(self.entries) else None
        if entry:
            self._show_entry_detail(entry)

    def _on_post(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry = self.entries[row] if row < len(self.entries) else None
        if not entry:
            return

        reply = QMessageBox.question(
            self, "Confirm Post",
            f"Are you sure you want to post journal entry {entry.get('entry_number')}?\nThis action cannot be undone."
        )
        if reply == QMessageBox.Yes:
            try:
                self.api_client.post(f"/api/accounting/journal-entries/{entry['id']}/post_entry/")
                self.load_entries()
                QMessageBox.information(self, "Success", "Journal entry posted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to post entry: {e}")

    def _on_unpost(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry = self.entries[row] if row < len(self.entries) else None
        if not entry:
            return

        reply = QMessageBox.question(
            self, "Confirm Unpost",
            f"Are you sure you want to unpost journal entry {entry.get('entry_number')}?"
        )
        if reply == QMessageBox.Yes:
            try:
                self.api_client.post(f"/api/accounting/journal-entries/{entry['id']}/unpost_entry/")
                self.load_entries()
                QMessageBox.information(self, "Success", "Journal entry unposted successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to unpost entry: {e}")

    def _on_reverse(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        entry = self.entries[row] if row < len(self.entries) else None
        if not entry:
            return

        reply = QMessageBox.question(
            self, "Confirm Reverse",
            f"Are you sure you want to reverse journal entry {entry.get('entry_number')}?\nA new reversal entry will be created."
        )
        if reply == QMessageBox.Yes:
            try:
                self.api_client.post(
                    f"/api/accounting/journal-entries/{entry['id']}/reverse_entry/",
                    data={"reason": "Reversed from UI"}
                )
                self.load_entries()
                QMessageBox.information(self, "Success", "Journal entry reversed successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reverse entry: {e}")

    def _show_entry_detail(self, entry):
        from ui.accounting.components.journal_entry_detail import JournalEntryDetailDialog
        dialog = JournalEntryDetailDialog(self, entry, self.api_client)
        dialog.exec()
