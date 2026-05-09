from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                  QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
                                  QHeaderView, QMessageBox, QComboBox, QDateEdit,
                                  QGroupBox, QFormLayout, QDialog, QDialogButtonBox,
                                  QTextEdit, QAbstractItemView, QApplication)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from ui.screens.base_screen import BaseScreen
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
from ui.constants import (SPACING_MD, SPACING_LG, FONT_SIZE_LG, FONT_SIZE_XL,
                          BUTTON_HEIGHT_MD, INPUT_HEIGHT_MD)
from api.client import APIClient
from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)

class ExpenseScreen(BaseScreen):
    """Screen for managing pharmacy expenses."""
    
    def __init__(self, parent=None, screen_id="expenses", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self.api_client = api_client or APIClient()
        self.expenses_data = []
        self.setup_ui()
        self.load_expenses()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD + SPACING_XS)

        # Header section
        header_layout = QHBoxLayout()
        header = QLabel("Pharmacy Expenses")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {{COLOR_TEXT_MUTED}};
                border: none;
                border-radius: 6px;
                padding: {SPACING_SM} {SPACING_MD};
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {{COLOR_BORDER}};
            }}
        """)
        self.btn_refresh.clicked.connect(self.load_expenses)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Action section
        action_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Record Expense")
        self.add_btn.setMinimumHeight(38)
        self.add_btn.setStyleSheet(f"background-color: {{COLOR_DANGER}}; color: white; border-radius: 5px; font-weight: bold; padding: 0 {SPACING_MD};")
        self.add_btn.clicked.connect(self.show_add_expense_dialog)
        action_layout.addWidget(self.add_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Filters
        filter_bar = QGroupBox("Filter Expenses")
        filter_bar.setFont(QFont("Segoe UI", 10, QFont.Bold))
        filter_bar.setStyleSheet(f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; padding-top: 10px; color: {COLOR_TEXT_PRIMARY}; }}")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setSpacing(SPACING_MD + SPACING_XS)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search expenses...")
        self.search_input.setMinimumHeight(30)
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self.load_expenses)
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setMinimumHeight(30)
        filter_layout.addWidget(QLabel("From:"))
        filter_layout.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMinimumHeight(30)
        filter_layout.addWidget(QLabel("To:"))
        filter_layout.addWidget(self.date_to)
        
        layout.addWidget(filter_bar)

        # Loading and Empty states
        self.loading_label = QLabel("Loading expenses...")
        self.loading_label.setFont(QFont("Segoe UI", 12))
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.loading_label.setVisible(False)
        layout.addWidget(self.loading_label)

        self.empty_label = QLabel("No expenses found")
        self.empty_label.setFont(QFont("Segoe UI", 12))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {{COLOR_TEXT_MUTED}}; padding: {SPACING_XL + SPACING_MD};")
        self.empty_label.setVisible(False)
        layout.addWidget(self.empty_label)

        self.error_label = QLabel("Error loading expenses")
        self.error_label.setFont(QFont("Segoe UI", 12))
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(f"color: {{COLOR_DANGER}}; padding: {SPACING_XL + SPACING_MD};")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # Table
        self.table = self._create_modern_table()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Date", "Expense #", "Category", "Payment Method", "Payee", "Amount", "Description"
        ])
        layout.addWidget(self.table)

    def _create_modern_table(self):
        table = QTableWidget()
        table.setStyleSheet(f"""
            QTableWidget {{ background-color: {COLOR_BG_MAIN}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; gridline-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY}; }}
            QHeaderView::section {{ background-color: {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY}; padding: 8px; border: none; border-bottom: 2px solid {COLOR_BORDER}; font-weight: bold; }}
            QTableWidget::item {{ padding: 10px; border-bottom: 1px solid {COLOR_BG_ELEVATED}; color: {COLOR_TEXT_PRIMARY}; }}
            QTableWidget::item:selected {{ background-color: {COLOR_PRIMARY}; color: white; }}
        """)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return table

    def _show_loading(self, show=True):
        """Show/hide loading state."""
        self.loading_label.setVisible(show)
        self.table.setVisible(not show)
        self.empty_label.setVisible(False)
        self.error_label.setVisible(False)
        self.btn_refresh.setEnabled(not show)
        if show:
            QApplication.processEvents()

    def _show_empty(self, message="No expenses found"):
        """Show empty state."""
        self.loading_label.setVisible(False)
        self.table.setVisible(False)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.error_label.setVisible(False)
        self.btn_refresh.setEnabled(True)

    def _show_data(self):
        """Show data table."""
        self.loading_label.setVisible(False)
        self.empty_label.setVisible(False)
        self.error_label.setVisible(False)
        self.table.setVisible(True)
        self.btn_refresh.setEnabled(True)

    def load_expenses(self):
        self._show_loading()
        try:
            params = {
                'search': self.search_input.text(),
                'start_date': self.date_from.date().toString("yyyy-MM-dd"),
                'end_date': self.date_to.date().toString("yyyy-MM-dd")
            }
            response = self.api_client.get("/api/expenses/", params=params)
            if response and response.get('success'):
                self.expenses_data = response['data'].get('results', [])
                if not self.expenses_data:
                    self._show_empty()
                else:
                    self._show_data()
                    self._populate_table()
            else:
                self._show_empty()
        except Exception as e:
            print(f"Failed to load expenses: {e}")
            self._show_empty(f"Error: {e}")
            self.error_label.setVisible(True)

    def _populate_table(self):
        self.table.setRowCount(0)
        for exp in self.expenses_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(exp.get('date', '')))
            self.table.setItem(row, 1, QTableWidgetItem(exp.get('expense_number', '')))
            self.table.setItem(row, 2, QTableWidgetItem(exp.get('expense_account_name', '')))
            self.table.setItem(row, 3, QTableWidgetItem(exp.get('payment_account_name', '')))
            self.table.setItem(row, 4, QTableWidgetItem(exp.get('payee', '')))
            
            amount_item = QTableWidgetItem(f"{float(exp.get('amount', 0)):,.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount_item.setForeground(QColor(COLOR_DANGER))
            self.table.setItem(row, 5, amount_item)
            
            self.table.setItem(row, 6, QTableWidgetItem(exp.get('description', '')))

    def show_add_expense_dialog(self):
        dialog = AddExpenseDialog(self, api_client=self.api_client)
        if dialog.exec():
            self.load_expenses()

class AddExpenseDialog(QDialog):
    """Dialog to record a new expense."""
    
    def __init__(self, parent=None, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("Record Pharmacy Expense")
        self.setMinimumWidth(450)
        self.setup_ui()
        self._load_accounts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(QDate.currentDate())
        form.addRow("Date:", self.date)
        
        self.expense_account = QComboBox()
        form.addRow("Expense Category:", self.expense_account)
        
        self.payment_account = QComboBox()
        form.addRow("Paid From:", self.payment_account)
        
        self.amount = QLineEdit()
        self.amount.setPlaceholderText("0.00")
        form.addRow("Amount:", self.amount)
        
        self.payee = QLineEdit()
        self.payee.setPlaceholderText("e.g. Landlord, Electric Co.")
        form.addRow("Payee:", self.payee)
        
        self.description = QTextEdit()
        self.description.setMaximumHeight(80)
        form.addRow("Description:", self.description)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save_expense)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_accounts(self):
        try:
            # Load expense accounts
            exp_res = self.api_client.get("/api/accounting/accounts/", params={'account_type': 'EXPENSE'})
            if exp_res and exp_res.get('success'):
                data = exp_res['data']
                results = data.get('results', data) if isinstance(data, dict) else data
                for acc in results:
                    self.expense_account.addItem(f"{acc['code']} - {acc['name']}", acc['id'])
            
            # Load payment accounts
            pay_res = self.api_client.get("/api/payments/accounts/")
            if pay_res and pay_res.get('success'):
                data = pay_res['data']
                results = data.get('results', data) if isinstance(data, dict) else data
                for acc in results:
                    self.payment_account.addItem(acc['name'], acc['id'])
        except Exception as e:
            print(f"Failed to load accounts for expense: {e}")

    def save_expense(self):
        try:
            amount = float(self.amount.text())
            if amount <= 0:
                raise ValueError("Amount must be positive.")
                
            data = {
                "date": self.date.date().toString("yyyy-MM-dd"),
                "expense_account": self.expense_account.currentData(),
                "payment_account": self.payment_account.currentData(),
                "amount": amount,
                "payee": self.payee.text(),
                "description": self.description.toPlainText()
            }
            
            response = self.api_client.post("/api/expenses/", data)
            if response and response.get('id'):
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save expense.")
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
