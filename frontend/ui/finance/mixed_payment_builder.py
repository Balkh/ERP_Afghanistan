"""Phase 20: Mixed Payment Builder dialog."""
from decimal import Decimal
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QGroupBox,
    QHeaderView, QWidget,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from api.client import APIClient
from ui.constants import (
    SPACING_XS, SPACING_SM, SPACING_LG, TEXT_PAGE_TITLE, TEXT_CARD_TITLE,
    TEXT_BODY, TEXT_LABEL, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_SUCCESS,
    COLOR_DANGER, COLOR_BG_ELEVATED, COLOR_BG_INPUT,
    COLOR_BORDER, COLOR_VALID_SUCCESS, COLOR_VALID_ERROR,
    BORDER_RADIUS_SM, BORDER_RADIUS_LG, DIALOG_WIDTH_WIDE,
)
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import AlertDialog, EnterpriseDialog, DialogType
from ui.components.tables import DataEntryGrid
from ui.components.styles import combo_stylesheet


class MixedPaymentBuilderDialog(EnterpriseDialog):
    """Dialog for building mixed/split payments across multiple methods."""

    payment_validated = Signal(dict)

    def __init__(self, parent=None, api_client=None, total_amount=Decimal("0.00"), entity_type="customer", entity_id=None):
        self.api_client = api_client or APIClient()
        self.total_amount = total_amount
        self.entity_type = entity_type  # "customer" or "supplier"
        self.entity_id = entity_id
        self.splits = []
        self.payment_methods = []
        self.payment_accounts = []
        super().__init__("Mixed Payment Builder", DialogType.CUSTOM, parent)
        self.setMinimumWidth(DIALOG_WIDTH_WIDE)
        self._build_content()
        self._load_payment_data()

    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(SPACING_LG)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Mixed Payment Builder")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_PAGE_TITLE}pt; font-weight: 700;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Total amount display
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Total Amount:"))
        self.total_amount_label = QLabel(f"{float(self.total_amount):,.2f}")
        self.total_amount_label.setStyleSheet(
            f"color: {COLOR_PRIMARY}; font-size: {TEXT_CARD_TITLE}pt; font-weight: 700;"
        )
        amount_layout.addWidget(self.total_amount_label)
        amount_layout.addStretch()
        layout.addLayout(amount_layout)

        # Splits table
        splits_group = QGroupBox("Payment Splits")
        splits_group.setFont(QFont("Segoe UI", TEXT_LABEL))
        splits_group.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; "
            f"margin-top: {SPACING_SM}px; padding-top: {SPACING_SM}px; color: {COLOR_TEXT_PRIMARY}; }}"
        )
        splits_layout = QVBoxLayout(splits_group)

        self.splits_table = DataEntryGrid(["Payment Method", "Account", "Amount", ""])
        header = self.splits_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.splits_table.setColumnWidth(2, 120)
        self.splits_table.setColumnWidth(3, 40)
        splits_layout.addWidget(self.splits_table)

        # Add split button
        add_btn = EnterpriseButton(text="+ Add Split", variant=ButtonVariant.SECONDARY, size=ButtonSize.SMALL)
        add_btn.clicked.connect(self._add_split_row)
        splits_layout.addWidget(add_btn)

        layout.addWidget(splits_group)

        # Validation summary
        self.validation_group = QGroupBox("Validation")
        self.validation_group.setFont(QFont("Segoe UI", TEXT_LABEL))
        self.validation_group.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: {BORDER_RADIUS_LG}px; "
            f"margin-top: {SPACING_SM}px; padding-top: {SPACING_SM}px; color: {COLOR_TEXT_PRIMARY}; }}"
        )
        validation_layout = QGridLayout(self.validation_group)

        self.lbl_split_total = QLabel("Split Total: 0.00")
        self.lbl_difference = QLabel("Difference: 0.00")
        self.lbl_status = QLabel("Status: —")

        self.lbl_split_total.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}pt;")
        self.lbl_difference.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_BODY}pt;")
        self.lbl_status.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: {TEXT_BODY}pt; font-weight: 600;")

        validation_layout.addWidget(self.lbl_split_total, 0, 0)
        validation_layout.addWidget(self.lbl_difference, 0, 1)
        validation_layout.addWidget(self.lbl_status, 0, 2)

        layout.addWidget(self.validation_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_validate = EnterpriseButton(text="Validate", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
        self.btn_validate.clicked.connect(self._validate_splits)
        button_layout.addWidget(self.btn_validate)

        self.btn_cancel = EnterpriseButton(text="Cancel", variant=ButtonVariant.GHOST, size=ButtonSize.MEDIUM)
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)

        self.btn_submit = EnterpriseButton(text="Process Payment", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
        self.btn_submit.clicked.connect(self._submit_payment)
        button_layout.addWidget(self.btn_submit)

        layout.addLayout(button_layout)

        self.set_content(widget)
        return widget

    def _load_payment_data(self):
        """Load payment methods and accounts."""
        self.run_api_request(
            "mixed_payment:methods", "GET", "/api/v1/payment-operations/payment-methods/",
            on_success=self._on_payment_methods_loaded,
            on_error=lambda m: print(f"Error loading payment methods: {m}"),
        )
        self.run_api_request(
            "mixed_payment:accounts", "GET", "/api/v1/payment-operations/payment-accounts/",
            on_success=self._on_payment_accounts_loaded,
            on_error=lambda m: print(f"Error loading payment accounts: {m}"),
        )
        self._add_split_row()

    def _on_payment_methods_loaded(self, methods_response):
        if methods_response and methods_response.get("success"):
            self.payment_methods = methods_response.get("data", [])

    def _on_payment_accounts_loaded(self, accounts_response):
        if accounts_response and accounts_response.get("success"):
            self.payment_accounts = accounts_response.get("data", [])

    def _add_split_row(self):
        """Add a new split row to the table."""
        self.splits_table.add_row()

        row = self.splits_table.rowCount() - 1

        method_combo = QComboBox()
        method_combo.addItem("-- Select Method --", None)
        for m in self.payment_methods:
            method_combo.addItem(m.get("name", ""), m.get("code"))
        method_combo.setStyleSheet(combo_stylesheet(min_height=28, custom_arrow=False))
        self.splits_table.set_cell_widget(row, 0, method_combo)

        account_combo = QComboBox()
        account_combo.addItem("-- Select Account --", None)
        for a in self.payment_accounts:
            account_combo.addItem(f"{a.get('name', '')} ({a.get('code', '')})", a.get("code"))
        account_combo.setStyleSheet(combo_stylesheet(min_height=28, custom_arrow=False))
        self.splits_table.set_cell_widget(row, 1, account_combo)

        amount_input = QLineEdit()
        amount_input.setPlaceholderText("0.00")
        amount_input.setStyleSheet(self._input_style())
        amount_input.textChanged.connect(self._update_validation)
        self.splits_table.set_cell_widget(row, 2, amount_input)

        remove_btn = EnterpriseButton("×", variant=ButtonVariant.GHOST)
        remove_btn.setFixedWidth(30)
        remove_btn.setStyleSheet(f"""
            EnterpriseButton {{
                background-color: transparent;
                color: {COLOR_DANGER};
                font-size: {TEXT_CARD_TITLE}pt;
                font-weight: bold;
                border: none;
            }}
            EnterpriseButton:hover {{
                background-color: {COLOR_DANGER}20;
                border-radius: {BORDER_RADIUS_SM}px;
            }}
        """)
        remove_btn.clicked.connect(self._on_remove_btn_clicked)
        self.splits_table.set_cell_widget(row, 3, remove_btn)

    def _on_remove_btn_clicked(self):
        """Handle remove-button click — find owning row via sender() to avoid stale row index."""
        btn = self.sender()
        for row in range(self.splits_table.rowCount()):
            if self.splits_table.cell_widget(row, 3) is btn:
                self._remove_split_row(row)
                return

    def _remove_split_row(self, row):
        """Remove a split row."""
        if self.splits_table.rowCount() > 1:
            self.splits_table.remove_row(row)
            self._update_validation()

    def _update_validation(self):
        """Update validation display."""
        split_total = self._calculate_split_total()
        difference = float(self.total_amount) - split_total

        self.lbl_split_total.setText(f"Split Total: {split_total:,.2f}")
        self.lbl_difference.setText(f"Difference: {difference:,.2f}")

        if abs(difference) < 0.001:
            self.lbl_difference.setStyleSheet(f"color: {COLOR_VALID_SUCCESS}; font-size: {TEXT_BODY}pt;")
            self.lbl_status.setText("Status: Valid")
            self.lbl_status.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: {TEXT_BODY}pt; font-weight: 600;")
        else:
            self.lbl_difference.setStyleSheet(f"color: {COLOR_VALID_ERROR}; font-size: {TEXT_BODY}pt;")
            self.lbl_status.setText("Status: Invalid")
            self.lbl_status.setStyleSheet(f"color: {COLOR_DANGER}; font-size: {TEXT_BODY}pt; font-weight: 600;")

    def _calculate_split_total(self):
        """Calculate total of all splits."""
        total = 0.0
        for row in range(self.splits_table.rowCount()):
            amount_widget = self.splits_table.cell_widget(row, 2)
            if amount_widget:
                try:
                    total += float(amount_widget.text() or "0")
                except ValueError:
                    pass
        return total

    def _validate_splits(self):
        """Validate splits via API."""
        splits = self._get_splits_data()
        if not splits:
            AlertDialog.warning("No Splits", "Please add at least one payment split.", self)
            return

        try:
            endpoint = "/api/v1/payment-operations/validate-mixed-payment/"
            payload = {
                "total_amount": str(self.total_amount),
                "splits": splits,
            }
            if not hasattr(self, "_async_validate_response"):
                self.run_api_request(
                    "mixed_payment:validate", "POST", endpoint, data=payload,
                    on_success=lambda r: self._resume_api_request("_async_validate_response", self._validate_splits, r),
                    on_error=lambda m: self._resume_api_request("_async_validate_response", self._validate_splits, {"success": False, "error": m}),
                )
                return
            response = self._take_api_response("_async_validate_response")
            if response and response.get("success"):
                data = response.get("data", {})
                if data.get("is_valid"):
                    AlertDialog.info("Valid", "Mixed payment is valid.", self)
                    self.payment_validated.emit(data)
                else:
                    errors = data.get("errors", [])
                    AlertDialog.warning("Invalid", "\n".join(errors), self)
        except Exception as e:
            AlertDialog.error("Validation Error", str(e), self)

    def _get_splits_data(self):
        """Get splits data from table."""
        splits = []
        for row in range(self.splits_table.rowCount()):
            method_combo = self.splits_table.cell_widget(row, 0)
            account_combo = self.splits_table.cell_widget(row, 1)
            amount_input = self.splits_table.cell_widget(row, 2)

            method_code = method_combo.currentData()
            account_code = account_combo.currentData()
            amount = amount_input.text()

            if method_code and account_code and amount:
                splits.append({
                    "payment_method_code": method_code,
                    "payment_account_code": account_code,
                    "amount": amount,
                })
        return splits

    def _submit_payment(self):
        """Submit the mixed payment."""
        splits = self._get_splits_data()
        if not splits:
            AlertDialog.warning("No Splits", "Please add at least one payment split.", self)
            return

        split_total = self._calculate_split_total()
        if abs(float(self.total_amount) - split_total) > 0.001:
            AlertDialog.warning("Amount Mismatch", "Split total must equal the payment amount.", self)
            return

        # Return the splits data for processing
        self.result_data = {
            "total_amount": str(self.total_amount),
            "splits": splits,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
        }
        self.accept()

    def get_result(self):
        """Get the payment result data."""
        return getattr(self, "result_data", None)

    def _input_style(self):
        return f"""
            QLineEdit {{
                background-color: {COLOR_BG_INPUT};
                border: 1px solid {COLOR_BORDER};
                border-radius: {BORDER_RADIUS_SM}px;
                padding: {SPACING_XS}px {SPACING_SM}px;
                color: {COLOR_TEXT_PRIMARY};
                min-height: 28px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_PRIMARY};
            }}
        """
