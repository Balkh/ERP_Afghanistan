from ui.constants import (SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL, SPACING_XXL, MARGIN_PAGE)
from ui.constants import (COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_BG_ELEVATED, COLOR_BG_INPUT, COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_PRIMARY_ACTIVE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_STATUS_VALID, COLOR_STATUS_WARNING, COLOR_INFO)
"""
System Integrity Screen - ERP-wide Validation Dashboard.
Executes cross-module consistency tests and displays results.
"""

import time
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QScrollArea, QPushButton, QProgressBar,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QSizePolicy, QGroupBox, QTextEdit)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from ui.screens.base_screen import BaseScreen
from ui.constants import (COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO)
from api.integrity_service import SystemIntegrityService


class IntegrityTestThread(QThread):
    """Worker thread for running integrity tests asynchronously."""
    results_received = Signal(list)
    progress_update = Signal(int, str)
    error_occurred = Signal(str)

    def __init__(self, service: SystemIntegrityService):
        super().__init__()
        self.service = service

    def run(self):
        try:
            self.progress_update.emit(10, "Initializing system-wide scan...")
            time.sleep(0.5)
            
            self.progress_update.emit(30, "Checking Sales & Accounting consistency...")
            results = self.service.test_sales_accounting_consistency()
            
            self.progress_update.emit(50, "Validating Inventory synchronization...")
            results.extend(self.service.test_inventory_synchronization())
            
            self.progress_update.emit(70, "Verifying Workflow state truth...")
            results.extend(self.service.test_workflow_state_truth())
            
            self.progress_update.emit(85, "Auditing Control Center metrics...")
            results.extend(self.service.test_control_center_truth())
            
            self.progress_update.emit(95, "Scanning for data duplications...")
            results.extend(self.service.test_duplication_detection())
            
            self.progress_update.emit(100, "Scan complete.")
            self.results_received.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))


class SystemIntegrityScreen(BaseScreen):
    """Dashboard for system-wide integrity and cross-module validation."""
    
    def __init__(self, parent=None, screen_id="system_integrity", config=None, api_client=None):
        super().__init__(parent, screen_id, config)
        self._api_client = api_client
        self._service = SystemIntegrityService(api_client)
        self._test_thread = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM)
        layout.setSpacing(SPACING_LG + SPACING_XS)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("System Integrity & Validation")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: COLOR_TEXT_PRIMARY;")
        
        self.scan_btn = QPushButton("Run Full System Scan")
        self.scan_btn.setFixedWidth(200)
        self.scan_btn.clicked.connect(self._run_scan)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.scan_btn)
        layout.addLayout(header)
        
        # Progress Section
        self.progress_container = QFrame()
        self.progress_container.setVisible(False)
        p_layout = QVBoxLayout(self.progress_container)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("QProgressBar { background: COLOR_BG_ELEVATED; border-radius: 5px; text-align: center; } QProgressBar::chunk { background: COLOR_PRIMARY; border-radius: 5px; }")
        self.progress_label = QLabel("Initializing...")
        self.progress_label.setStyleSheet("color: COLOR_TEXT_SECONDARY; font-size: 11px;")
        p_layout.addWidget(self.progress_bar)
        p_layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_container)
        
        # Results Summary Cards
        summary_layout = QHBoxLayout()
        self.pass_card = self._create_summary_card("Passed Tests", "0", COLOR_SUCCESS)
        self.fail_card = self._create_summary_card("Failed Tests", "0", COLOR_DANGER)
        self.warn_card = self._create_summary_card("Warnings", "0", COLOR_WARNING)
        summary_layout.addWidget(self.pass_card)
        summary_layout.addWidget(self.fail_card)
        summary_layout.addWidget(self.warn_card)
        layout.addLayout(summary_layout)
        
        # Results Table
        results_group = QGroupBox("Validation Report")
        results_group.setStyleSheet("QGroupBox { color: COLOR_PRIMARY; font-weight: bold; border: 1px solid COLOR_BG_ELEVATED; border-radius: 12px; margin-top: 15px; background: COLOR_BG_MAIN; } QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }")
        rg_layout = QVBoxLayout(results_group)
        rg_layout.setContentsMargins(SPACING_MD,  SPACING_XL + SPACING_SM,  SPACING_MD,  SPACING_MD)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Test Name", "Modules", "Status", "Severity"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.cellClicked.connect(self._show_details)
        self.results_table.setStyleSheet("QTableWidget { background: COLOR_BG_SURFACE; color: COLOR_TEXT_PRIMARY; border: none; gridline-color: COLOR_BG_ELEVATED; } QHeaderView::section { background: COLOR_BG_ELEVATED; color: COLOR_PRIMARY; border: none; padding: 8px; font-weight: bold; }")
        rg_layout.addWidget(self.results_table)
        layout.addWidget(results_group)
        
        # Details Panel
        self.details_group = QGroupBox("Test Details")
        self.details_group.setVisible(False)
        self.details_group.setStyleSheet(results_group.styleSheet())
        dg_layout = QVBoxLayout(self.details_group)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("background: COLOR_BG_INPUT; color: COLOR_TEXT_PRIMARY; border: none; font-family: 'Consolas'; font-size: 11px;")
        dg_layout.addWidget(self.details_text)
        layout.addWidget(self.details_group)
        
        self.current_results = []

    def _create_summary_card(self, title, val, color):
        card = QFrame()
        card.setStyleSheet(f"background: COLOR_BG_MAIN; border: 1px solid COLOR_BG_ELEVATED; border-radius: 10px; border-left: 4px solid {color};")
        l = QVBoxLayout(card)
        t_label = QLabel(title)
        t_label.setStyleSheet("color: COLOR_TEXT_SECONDARY; font-size: 11px;")
        v_label = QLabel(val)
        v_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        l.addWidget(t_label)
        l.addWidget(v_label)
        return card

    def _run_scan(self):
        if self._test_thread and self._test_thread.isRunning():
            return
            
        self.scan_btn.setEnabled(False)
        self.progress_container.setVisible(True)
        self.details_group.setVisible(False)
        self.results_table.setRowCount(0)
        
        self._test_thread = IntegrityTestThread(self._service)
        self._test_thread.progress_update.connect(self._update_progress)
        self._test_thread.results_received.connect(self._handle_results)
        self._test_thread.error_occurred.connect(self._handle_error)
        self._test_thread.start()

    def _update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.progress_label.setText(msg)

    def _handle_results(self, results):
        self.current_results = results
        self.scan_btn.setEnabled(True)
        self.progress_container.setVisible(False)
        
        passed = sum(1 for r in results if r['status'] == 'PASS')
        failed = sum(1 for r in results if r['status'] == 'FAIL')
        warns = sum(1 for r in results if r['status'] == 'WARNING')
        
        self.pass_card.layout().itemAt(1).widget().setText(str(passed))
        self.fail_card.layout().itemAt(1).widget().setText(str(failed))
        self.warn_card.layout().itemAt(1).widget().setText(str(warns))
        
        self.results_table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(r['name']))
            self.results_table.setItem(i, 1, QTableWidgetItem(", ".join(r['modules'])))
            
            status_item = QTableWidgetItem(r['status'])
            color = COLOR_SUCCESS if r['status'] == 'PASS' else (COLOR_DANGER if r['status'] == 'FAIL' else COLOR_WARNING)
            status_item.setForeground(QColor(color))
            self.results_table.setItem(i, 2, status_item)
            
            sev_item = QTableWidgetItem(r['severity'])
            self.results_table.setItem(i, 3, sev_item)

    def _show_details(self, row, col):
        if row < len(self.current_results):
            r = self.current_results[row]
            self.details_group.setVisible(True)
            details = f"TEST: {r['name']}\n"
            details += f"STATUS: {r['status']} | SEVERITY: {r['severity']}\n"
            details += f"MODULES: {', '.join(r['modules'])}\n"
            details += f"TIMESTAMP: {r['timestamp']}\n"
            details += "-"*50 + "\n"
            details += f"DESCRIPTION: {r['description']}\n\n"
            if r['details']:
                details += f"MISMATCH DETAILS:\n{r['details']}\n\n"
            if r['fix']:
                details += f"SUGGESTED FIX:\n{r['fix']}\n"
            
            self.details_text.setText(details)

    def _handle_error(self, err):
        self.scan_btn.setEnabled(True)
        self.progress_label.setText(f"Critical scan failure: {err}")
        self.progress_label.setStyleSheet("color: #f38ba8;")

    def _on_screen_shown(self):
        # Auto-run scan if results are empty
        if not self.current_results:
            self._run_scan()
