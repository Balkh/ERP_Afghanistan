# Dialog Integrity Report (automated)

## frontend\ui\accounting\components\account_form_dialog.py
- Missing target `reject` at line 137: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\accounting\components\journal_entry_form.py
- Missing target `reject` at line 175: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\accounting\components\report_preview_dialog.py
- Missing target `reject` at line 77: `self.btn_close.clicked.connect(self.reject)`

## frontend\ui\auth\totp_setup_dialog.py
- Missing target `reject` at line 126: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\common\product_selection_dialog.py
- Missing target `search_timer` at line 37: `self.search_input.textChanged.connect(lambda: self.search_timer.start(300))`
- Missing target `reject` at line 61: `self.cancel_btn.clicked.connect(self.reject)`

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

## frontend\ui\hr\payslip_dialog.py
- Missing target `reject` at line 62: `close_btn.clicked.connect(self.reject)`
- Missing target `preview` at line 208: `dialog.paintRequested.connect(self.preview.print_)`

## frontend\ui\inventory\components\batch_form_dialog.py
- Missing target `reject` at line 88: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\inventory\components\category_form_dialog.py
- Missing target `reject` at line 92: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\inventory\components\product_form.py
- Missing target `reject` at line 227: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\inventory\components\warehouse_form_dialog.py
- Missing target `reject` at line 83: `cancel_btn.clicked.connect(self.reject)`

## frontend\ui\licensing\dialogs.py
- No missing connect targets detected

## frontend\ui\licensing\license_manager_dialog.py
- Missing target `accept` at line 107: `close_button.clicked.connect(self.accept)`

## frontend\ui\sales\credit_warning_dialog.py
- Missing target `reject` at line 141: `self.cancel_btn.clicked.connect(self.reject)`
- Missing target `reject` at line 157: `self.ok_btn.clicked.connect(self.reject)`

## frontend\ui\sales\fifo_allocation_dialog.py
- Missing target `accept` at line 119: `self.close_btn.clicked.connect(self.accept)`

## frontend\ui\system\email_config_dialog.py
- Missing target `reject` at line 94: `cancel_btn.clicked.connect(self.reject)`
