# Button Wiring Report (automated)

## frontend\ui\accounting\account_ledger_screen.py
## frontend\ui\accounting\chart_of_accounts_screen.py
## frontend\ui\accounting\components\account_form_dialog.py
- Missing target `reject` at line 137: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\accounting\components\journal_entry_detail.py
- Missing target `reject` at line 155: `close_btn.clicked.connect(self.reject)`
## frontend\ui\accounting\components\journal_entry_form.py
- Missing target `reject` at line 175: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\accounting\components\report_preview_dialog.py
- Missing target `reject` at line 77: `self.btn_close.clicked.connect(self.reject)`
## frontend\ui\accounting\financial_audit_log_screen.py
## frontend\ui\accounting\financial_integrity_screen.py
## frontend\ui\accounting\journal_entry_screen.py
## frontend\ui\accounting\report_browser.py
## frontend\ui\auth\login_screen.py
## frontend\ui\auth\totp_setup_dialog.py
- Missing target `reject` at line 126: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\causal_scoring\causal_strength_panel.py
## frontend\ui\causal_scoring\decision_ranking_dashboard.py
## frontend\ui\common\barcode_search.py
## frontend\ui\common\batch_selection.py
- Missing target `reject` at line 96: `cancel_button.clicked.connect(self.reject)`
## frontend\ui\common\printable_invoice.py
- Missing target `reject` at line 99: `close_btn.clicked.connect(self.reject)`
- Missing target `preview` at line 317: `dialog.paintRequested.connect(self.preview.print_)`
## frontend\ui\common\product_selection_dialog.py
- Missing target `search_timer` at line 37: `self.search_input.textChanged.connect(lambda: self.search_timer.start(300))`
- Missing target `reject` at line 61: `self.cancel_btn.clicked.connect(self.reject)`
## frontend\ui\components\buttons.py
## frontend\ui\components\dialogs.py
- Missing target `accept` at line 156: `self._yes_btn.clicked.connect(self.accept)`
- Missing target `reject` at line 157: `self._no_btn.clicked.connect(self.reject)`
- Missing target `accept` at line 164: `self._ok_btn.clicked.connect(self.accept)`
- Missing target `reject` at line 171: `self._cancel_btn.clicked.connect(self.reject)`
- Missing target `accept` at line 172: `self._save_btn.clicked.connect(self.accept)`
## frontend\ui\components\document_action_dialog.py
- Missing target `reject` at line 125: `close_btn.clicked.connect(self.reject)`
## frontend\ui\components\forms.py
- Missing target `on_submit` at line 388: `form.form_submitted.connect(self.on_submit)`
- Missing target `window` at line 690: `cancel_btn.clicked.connect(lambda: self.window().close() if self.window() else None)`
## frontend\ui\components\loading_spinner.py
## frontend\ui\components\navigation_header.py
- Missing target `back_clicked` at line 79: `self.back_btn.clicked.connect(self.back_clicked.emit)`
- Missing target `home_clicked` at line 83: `self.home_btn.clicked.connect(self.home_clicked.emit)`
- Missing target `close_clicked` at line 107: `self.close_btn.clicked.connect(self.close_clicked.emit)`
## frontend\ui\components\notifications.py
- Missing target `close` at line 168: `close_btn.clicked.connect(self.close)`
## frontend\ui\components\operator_safety.py
## frontend\ui\components\skeleton_loader.py
## frontend\ui\components\state_helper.py
## frontend\ui\components\tables.py
- Missing target `page_changed` at line 516: `self.first_btn.clicked.connect(lambda: self.page_changed.emit(1))`
## frontend\ui\control_tower\financial_control_tower_screen.py
## frontend\ui\control_tower\system_health_screen.py
## frontend\ui\control_tower\workflow_execution_screen.py
## frontend\ui\dashboard.py
## frontend\ui\finance\budgeting_screen.py
## frontend\ui\finance\cashflow_screen.py
## frontend\ui\finance\cost_centers_screen.py
- Missing target `reject` at line 264: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\finance\customer_payment_workspace.py
## frontend\ui\finance\expense_screen.py
- Missing target `_expense_search_debounce` at line 67: `self.search_input.textChanged.connect(self._expense_search_debounce)`
- Missing target `reject` at line 237: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\finance\financial_operations_console.py
## frontend\ui\finance\journal_reversal_explorer.py
## frontend\ui\finance\mixed_payment_builder.py
- Missing target `reject` at line 133: `self.btn_cancel.clicked.connect(self.reject)`
## frontend\ui\finance\payment_allocation_explorer.py
## frontend\ui\finance\payment_screen.py
## frontend\ui\finance\returns_explainability.py
## frontend\ui\finance\supplier_payment_workspace.py
## frontend\ui\finance\tax_screen.py
## frontend\ui\governance\approval_screen.py
## frontend\ui\hr\attendance_screen.py
## frontend\ui\hr\employee_screen.py
- Missing target `_employee_search_debounce` at line 88: `self.search_input.textChanged.connect(self._employee_search_debounce)`
- Missing target `reject` at line 314: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\hr\leave_screen.py
## frontend\ui\hr\payroll_screen.py
- Missing target `reject` at line 429: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\hr\payslip_dialog.py
- Missing target `reject` at line 62: `close_btn.clicked.connect(self.reject)`
- Missing target `preview` at line 208: `dialog.paintRequested.connect(self.preview.print_)`
## frontend\ui\inventory\base_screen.py
- Missing target `search_text_changed` at line 57: `self.search_input.textChanged.connect(self.search_text_changed.emit)`
- Missing target `add_requested` at line 101: `self.add_button.clicked.connect(self.add_requested.emit)`
- Missing target `refresh_requested` at line 104: `self.refresh_button.clicked.connect(self.refresh_requested.emit)`
## frontend\ui\inventory\batch_screen.py
## frontend\ui\inventory\category_screen.py
## frontend\ui\inventory\components\batch_form_dialog.py
- Missing target `reject` at line 88: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\inventory\components\category_form_dialog.py
- Missing target `reject` at line 92: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\inventory\components\product_form.py
- Missing target `reject` at line 227: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\inventory\components\warehouse_form_dialog.py
- Missing target `reject` at line 83: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\inventory\product_screen.py
## frontend\ui\inventory\warehouse_screen.py
## frontend\ui\investigation\anomaly_investigation_screen.py
## frontend\ui\investigation\event_investigation_screen.py
## frontend\ui\licensing\activation_screen.py
## frontend\ui\licensing\license_manager_dialog.py
- Missing target `accept` at line 107: `close_button.clicked.connect(self.accept)`
## frontend\ui\licensing\license_status_screen.py
- Missing target `close` at line 331: `close_button.clicked.connect(self.close)`
## frontend\ui\main_window.py
## frontend\ui\observability\base_view_model.py
## frontend\ui\observability\dashboards.py
## frontend\ui\observability\observability_screen.py
## frontend\ui\observability\replay_screen.py
- Missing target `seq_spin` at line 97: `self.seq_slider.valueChanged.connect(lambda v: self.seq_spin.setValue(v))`
## frontend\ui\pos\pos_screen.py
## frontend\ui\purchases\purchase_invoice_screen.py
- Missing target `product_search` at line 399: `QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.product_search.setFocus)`
- Missing target `items_table` at line 537: `remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))`
## frontend\ui\purchases\supplier_screen.py
- Missing target `reject` at line 438: `self.btn_cancel.clicked.connect(self.reject)`
## frontend\ui\returns\reconciliation_screen.py
## frontend\ui\returns\returns_screen.py
- Missing target `_view_return` at line 124: `self.table.cellDoubleClicked.connect(lambda row, col: self._view_return(row))`
- Missing target `reject` at line 698: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\sales\credit_warning_dialog.py
- Missing target `reject` at line 141: `self.cancel_btn.clicked.connect(self.reject)`
- Missing target `reject` at line 157: `self.ok_btn.clicked.connect(self.reject)`
## frontend\ui\sales\customer_screen.py
- Missing target `reject` at line 401: `self.btn_cancel.clicked.connect(self.reject)`
## frontend\ui\sales\fifo_allocation_dialog.py
- Missing target `accept` at line 119: `self.close_btn.clicked.connect(self.accept)`
## frontend\ui\sales\sales_invoice_screen.py
- Missing target `barcode_search` at line 403: `QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.barcode_search.setFocus)`
- Missing target `items_table` at line 548: `remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))`
## frontend\ui\screens\base_screen.py
## frontend\ui\sidebar.py
## frontend\ui\system\audit_screen.py
## frontend\ui\system\backup_screen.py
- Missing target `reject` at line 191: `cancel_btn.clicked.connect(self.reject)`
- Missing target `accept` at line 197: `confirm_btn.clicked.connect(self.accept)`
## frontend\ui\system\company_profile_screen.py
## frontend\ui\system\control_center_screen.py
## frontend\ui\system\correlation_screen.py
## frontend\ui\system\email_config_dialog.py
- Missing target `reject` at line 94: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\system\entity_management_screen.py
## frontend\ui\system\fixed_assets_screen.py
- Missing target `reject` at line 335: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\system\integrity_screen.py
## frontend\ui\system\intelligence_hub_screen.py
## frontend\ui\system\invoice_template_manager.py
## frontend\ui\system\licensing_screen.py
## frontend\ui\system\role_management_screen.py
- Missing target `reject` at line 358: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\system\settings_screen.py
## frontend\ui\system\user_management_screen.py
- Missing target `reject` at line 414: `cancel_btn.clicked.connect(self.reject)`
## frontend\ui\system\workflow_intelligence_screen.py
## frontend\ui\truth\event_store_screen.py
## frontend\ui\utils\debounce.py