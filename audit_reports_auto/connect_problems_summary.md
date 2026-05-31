# Connect Problems Summary

## frontend\ui\auth\totp_setup_dialog.py -> PARTIAL
- Missing reject @ 126: cancel_btn.clicked.connect(self.reject)

## frontend\ui\common\batch_selection.py -> PARTIAL
- Missing reject @ 96: cancel_button.clicked.connect(self.reject)

## frontend\ui\common\printable_invoice.py -> PARTIAL
- Missing reject @ 99: close_btn.clicked.connect(self.reject)
- Missing preview @ 317: dialog.paintRequested.connect(self.preview.print_)

## frontend\ui\common\product_selection_dialog.py -> PARTIAL
- Missing search_timer @ 37: self.search_input.textChanged.connect(lambda: self.search_timer.start(300))
- Missing reject @ 61: self.cancel_btn.clicked.connect(self.reject)

## frontend\ui\components\dialogs.py -> PARTIAL
- Missing accept @ 156: self._yes_btn.clicked.connect(self.accept)
- Missing reject @ 157: self._no_btn.clicked.connect(self.reject)
- Missing accept @ 164: self._ok_btn.clicked.connect(self.accept)
- Missing reject @ 171: self._cancel_btn.clicked.connect(self.reject)
- Missing accept @ 172: self._save_btn.clicked.connect(self.accept)

## frontend\ui\components\document_action_dialog.py -> PARTIAL
- Missing reject @ 125: close_btn.clicked.connect(self.reject)

## frontend\ui\components\forms.py -> PARTIAL
- Missing on_submit @ 388: form.form_submitted.connect(self.on_submit)
- Missing window @ 690: cancel_btn.clicked.connect(lambda: self.window().close() if self.window() else None)

## frontend\ui\components\navigation_header.py -> CRITICAL
- Missing back_clicked @ 79: self.back_btn.clicked.connect(self.back_clicked.emit)
- Missing home_clicked @ 83: self.home_btn.clicked.connect(self.home_clicked.emit)
- Missing close_clicked @ 107: self.close_btn.clicked.connect(self.close_clicked.emit)

## frontend\ui\components\notifications.py -> PARTIAL
- Missing close @ 168: close_btn.clicked.connect(self.close)

## frontend\ui\components\tables.py -> PARTIAL
- Missing page_changed @ 516: self.first_btn.clicked.connect(lambda: self.page_changed.emit(1))

## frontend\ui\finance\cost_centers_screen.py -> PARTIAL
- Missing reject @ 264: cancel_btn.clicked.connect(self.reject)

## frontend\ui\finance\expense_screen.py -> PARTIAL
- Missing _expense_search_debounce @ 67: self.search_input.textChanged.connect(self._expense_search_debounce)
- Missing reject @ 237: cancel_btn.clicked.connect(self.reject)

## frontend\ui\finance\mixed_payment_builder.py -> PARTIAL
- Missing reject @ 133: self.btn_cancel.clicked.connect(self.reject)

## frontend\ui\hr\employee_screen.py -> PARTIAL
- Missing _employee_search_debounce @ 88: self.search_input.textChanged.connect(self._employee_search_debounce)
- Missing reject @ 314: cancel_btn.clicked.connect(self.reject)

## frontend\ui\hr\payroll_screen.py -> PARTIAL
- Missing reject @ 429: cancel_btn.clicked.connect(self.reject)

## frontend\ui\hr\payslip_dialog.py -> PARTIAL
- Missing reject @ 62: close_btn.clicked.connect(self.reject)
- Missing preview @ 208: dialog.paintRequested.connect(self.preview.print_)

## frontend\ui\inventory\base_screen.py -> PARTIAL
- Missing search_text_changed @ 57: self.search_input.textChanged.connect(self.search_text_changed.emit)
- Missing add_requested @ 101: self.add_button.clicked.connect(self.add_requested.emit)
- Missing refresh_requested @ 104: self.refresh_button.clicked.connect(self.refresh_requested.emit)

## frontend\ui\licensing\license_manager_dialog.py -> PARTIAL
- Missing accept @ 107: close_button.clicked.connect(self.accept)

## frontend\ui\licensing\license_status_screen.py -> PARTIAL
- Missing close @ 331: close_button.clicked.connect(self.close)

## frontend\ui\observability\replay_screen.py -> PARTIAL
- Missing seq_spin @ 97: self.seq_slider.valueChanged.connect(lambda v: self.seq_spin.setValue(v))

## frontend\ui\purchases\purchase_invoice_screen.py -> PARTIAL
- Missing product_search @ 399: QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.product_search.setFocus)
- Missing items_table @ 537: remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))

## frontend\ui\purchases\supplier_screen.py -> PARTIAL
- Missing reject @ 438: self.btn_cancel.clicked.connect(self.reject)

## frontend\ui\returns\returns_screen.py -> PARTIAL
- Missing _view_return @ 124: self.table.cellDoubleClicked.connect(lambda row, col: self._view_return(row))
- Missing reject @ 698: cancel_btn.clicked.connect(self.reject)

## frontend\ui\sales\credit_warning_dialog.py -> PARTIAL
- Missing reject @ 141: self.cancel_btn.clicked.connect(self.reject)
- Missing reject @ 157: self.ok_btn.clicked.connect(self.reject)

## frontend\ui\sales\customer_screen.py -> PARTIAL
- Missing reject @ 401: self.btn_cancel.clicked.connect(self.reject)

## frontend\ui\sales\fifo_allocation_dialog.py -> PARTIAL
- Missing accept @ 119: self.close_btn.clicked.connect(self.accept)

## frontend\ui\sales\sales_invoice_screen.py -> PARTIAL
- Missing barcode_search @ 403: QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.barcode_search.setFocus)
- Missing items_table @ 548: remove_btn.clicked.connect(lambda checked, r=row: self.items_table.removeRow(r))

## frontend\ui\system\backup_screen.py -> PARTIAL
- Missing reject @ 191: cancel_btn.clicked.connect(self.reject)
- Missing accept @ 197: confirm_btn.clicked.connect(self.accept)

## frontend\ui\system\email_config_dialog.py -> PARTIAL
- Missing reject @ 94: cancel_btn.clicked.connect(self.reject)

## frontend\ui\system\fixed_assets_screen.py -> PARTIAL
- Missing reject @ 335: cancel_btn.clicked.connect(self.reject)

## frontend\ui\system\role_management_screen.py -> PARTIAL
- Missing reject @ 358: cancel_btn.clicked.connect(self.reject)

## frontend\ui\system\user_management_screen.py -> PARTIAL
- Missing reject @ 414: cancel_btn.clicked.connect(self.reject)

## frontend\ui\accounting\components\account_form_dialog.py -> PARTIAL
- Missing reject @ 137: cancel_btn.clicked.connect(self.reject)

## frontend\ui\accounting\components\journal_entry_detail.py -> CRITICAL
- Missing reject @ 155: close_btn.clicked.connect(self.reject)

## frontend\ui\accounting\components\journal_entry_form.py -> PARTIAL
- Missing reject @ 175: cancel_btn.clicked.connect(self.reject)

## frontend\ui\accounting\components\report_preview_dialog.py -> PARTIAL
- Missing reject @ 77: self.btn_close.clicked.connect(self.reject)

## frontend\ui\inventory\components\batch_form_dialog.py -> PARTIAL
- Missing reject @ 88: cancel_btn.clicked.connect(self.reject)

## frontend\ui\inventory\components\category_form_dialog.py -> PARTIAL
- Missing reject @ 92: cancel_btn.clicked.connect(self.reject)

## frontend\ui\inventory\components\product_form.py -> PARTIAL
- Missing reject @ 227: cancel_btn.clicked.connect(self.reject)

## frontend\ui\inventory\components\warehouse_form_dialog.py -> PARTIAL
- Missing reject @ 83: cancel_btn.clicked.connect(self.reject)
