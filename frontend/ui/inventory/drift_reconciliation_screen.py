"""
Stock Drift Reconciliation Screen
===================================
Read-only audit screen that compares Batch.remaining_quantity against
StockMovement aggregates to detect data inconsistencies.

Calls: GET /api/inventory/stock/drift-reconciliation/
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QCheckBox, QDoubleSpinBox, QProgressBar,
)
from PySide6.QtCore import Qt, Slot

from ui.screens.base_screen import BaseScreen
from ui.components.tables import EnterpriseTable, TableColumn
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.constants import (
    SPACING_SM, SPACING_MD, MARGIN_PAGE,
    TEXT_PAGE_TITLE, TEXT_BODY, TEXT_HELPER,
    COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED, COLOR_PRIMARY,
    COLOR_BG_DIALOG, COLOR_BORDER_INPUT,
    BORDER_RADIUS_MD,
)


class DriftReconciliationScreen(BaseScreen):
    """Read-only screen for stock drift reconciliation audits."""

    def __init__(self, api_client=None, **kwargs):
        self._api_client = api_client
        self._result_data = None
        super().__init__(screen_id="drift_reconciliation", **kwargs)
        self.setWindowTitle("Stock Drift Reconciliation")

    def _setup_screen(self):
        super()._setup_screen()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE, MARGIN_PAGE)
        layout.setSpacing(SPACING_MD)

        # ── Header ──
        header_layout = QHBoxLayout()
        title = QLabel("Stock Drift Reconciliation")
        title.setStyleSheet(UIStyleBuilder.get_page_header_style())
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.run_btn = EnterpriseButton(
            "Run Reconciliation", variant=ButtonVariant.PRIMARY,
            size=ButtonSize.MEDIUM,
        )
        self.run_btn.clicked.connect(self._on_run_clicked)
        header_layout.addWidget(self.run_btn)
        layout.addLayout(header_layout)

        # Error banner (hidden by default)
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(UIStyleBuilder.get_label_style("error"))
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        layout.addWidget(self._error_label)

        # ── Health summary bar ──
        self._summary_frame = QFrame()
        self._summary_frame.setFrameStyle(QFrame.StyledPanel)
        self._summary_frame.setStyleSheet(UIStyleBuilder.get_card_style())
        summary_layout = QHBoxLayout(self._summary_frame)
        summary_layout.setContentsMargins(SPACING_MD, SPACING_SM, SPACING_MD, SPACING_SM)
        summary_layout.setSpacing(SPACING_MD * 2)

        self._health_label = QLabel("Health: —")
        self._health_label.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self._health_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: {TEXT_BODY}pt; font-weight: 600;")
        self._health_bar = QProgressBar()
        self._health_bar.setFixedHeight(20)
        self._health_bar.setRange(0, 100)
        self._health_bar.setValue(0)
        self._health_bar.setTextVisible(True)
        self._health_bar.setFormat("%p%")

        self._checked_label = QLabel("Checked: 0")
        self._checked_label.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self._clean_label = QLabel("Clean: 0")
        self._clean_label.setStyleSheet(UIStyleBuilder.get_label_style("body"))
        self._clean_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: {TEXT_BODY}pt; font-weight: 600;")
        self._drift_label = QLabel("Drifts: 0")
        self._drift_label.setStyleSheet(UIStyleBuilder.get_label_style("error"))
        self._total_drift_label = QLabel("Total Drift: 0")
        self._total_drift_label.setStyleSheet(UIStyleBuilder.get_label_style("muted"))

        summary_layout.addWidget(self._health_label)
        summary_layout.addWidget(self._health_bar)
        summary_layout.addWidget(self._checked_label)
        summary_layout.addWidget(self._clean_label)
        summary_layout.addWidget(self._drift_label)
        summary_layout.addWidget(self._total_drift_label)
        layout.addWidget(self._summary_frame)

        # ── Filter controls ──
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(SPACING_SM)

        filter_layout.addWidget(QLabel("Tolerance:"))
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0, 999999.0)
        self.tolerance_spin.setDecimals(2)
        self.tolerance_spin.setValue(0.0)
        self.tolerance_spin.setFixedWidth(100)
        filter_layout.addWidget(self.tolerance_spin)

        self.positive_only_cb = QCheckBox("Positive stock only")
        self.positive_only_cb.setChecked(True)
        filter_layout.addWidget(self.positive_only_cb)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # ── Results table ──
        columns = [
            TableColumn("batch_number", "Batch #", width=130),
            TableColumn("product_name", "Product", width=180),
            TableColumn("warehouse_name", "Warehouse", width=140),
            TableColumn("stored_quantity", "Stored Qty", width=110, align="right"),
            TableColumn("computed_quantity", "Computed Qty", width=110, align="right"),
            TableColumn("drift_amount", "Drift", width=110, align="right"),
            TableColumn("movement_count", "Movements", width=90, align="center"),
        ]
        self.table = EnterpriseTable(columns, density="compact")
        layout.addWidget(self.table, 1)

        # ── Truncated notice ──
        self._truncated_label = QLabel("")
        self._truncated_label.setStyleSheet(UIStyleBuilder.get_label_style("warning"))
        self._truncated_label.setVisible(False)
        layout.addWidget(self._truncated_label)

    # ── Data loading ──

    def _on_screen_shown(self):
        """No-op — reconciliation is manual, not auto-loaded."""
        pass

    @Slot()
    def _on_run_clicked(self):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running…")
        self._error_label.setVisible(False)
        self.load_data()

    def _show_error(self, message: str):
        """Display an error message visibly in the error banner."""
        self._error_label.setText(f"⚠ {message}")
        self._error_label.setVisible(True)
        self.set_state("error")

    def load_data(self, params=None):
        if not self._api_client:
            self._show_error("No API client configured")
            return
        try:
            query = {}
            if self.tolerance_spin.value() > 0:
                query["tolerance"] = str(self.tolerance_spin.value())
            if self.positive_only_cb.isChecked():
                query["only_positive_stock"] = "true"
            else:
                query["only_positive_stock"] = "false"

            result = self._api_client.get(
                "/api/inventory/stock/drift-reconciliation/", params=query,
            )
            self._result_data = result
            self._update_display(result)
        except Exception as exc:
            self._show_error(f"Reconciliation failed: {exc}")
        finally:
            self.run_btn.setEnabled(True)
            self.run_btn.setText("Run Reconciliation")

    def _update_display(self, data):
        # Summary bar
        score = data.get("health_score", 100)
        is_healthy = data.get("is_healthy", True)
        total = data.get("total_batches_checked", 0)
        clean = data.get("batches_clean", 0)
        with_drift = data.get("batches_with_drift", 0)
        total_drift = data.get("total_drift_value", "0")
        truncated = data.get("truncated", False)

        self._health_label.setText(
            f"Health: {'✅ Healthy' if is_healthy else '⚠️ Drift Detected'}"
        )
        self._health_bar.setValue(int(score))
        if is_healthy:
            self._health_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #28A745; }"
            )
        else:
            self._health_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #DC3545; }"
            )

        self._checked_label.setText(f"Checked: {total}")
        self._clean_label.setText(f"Clean: {clean}")
        self._drift_label.setText(f"Drifts: {with_drift}")
        self._total_drift_label.setText(f"Total Drift: {total_drift}")

        # Truncated notice
        if truncated:
            self._truncated_label.setText(
                "⚠ Result truncated — some batches were not checked. "
                "Increase max_drifts or remove the limit for a full scan."
            )
            self._truncated_label.setVisible(True)
        else:
            self._truncated_label.setVisible(False)

        # Table
        drifts = data.get("drifts", [])
        self.table.set_data(drifts)
