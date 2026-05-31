# Top 5 Problematic Frontend Files (missing connect targets)

## frontend/ui/components/dialogs.py
- Missing target `accept` at line 156: `self._yes_btn.clicked.connect(self.accept)`

```py
    148:         
    149:         layout.addStretch()
    150:         
    151:         # Default buttons based on dialog type
    152:         if self._dialog_type == DialogType.CONFIRM:
    153:             self._yes_btn = EnterpriseButton("Yes", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    154:             self._no_btn = EnterpriseButton("No", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    155:             
>>  156:             self._yes_btn.clicked.connect(self.accept)
    157:             self._no_btn.clicked.connect(self.reject)
    158:             
    159:             layout.addWidget(self._no_btn)
    160:             layout.addWidget(self._yes_btn)
    161:             
    162:         elif self._dialog_type == DialogType.ALERT:
    163:             self._ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    164:             self._ok_btn.clicked.connect(self.accept)
```

- Missing target `reject` at line 157: `self._no_btn.clicked.connect(self.reject)`

```py
    149:         layout.addStretch()
    150:         
    151:         # Default buttons based on dialog type
    152:         if self._dialog_type == DialogType.CONFIRM:
    153:             self._yes_btn = EnterpriseButton("Yes", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    154:             self._no_btn = EnterpriseButton("No", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    155:             
    156:             self._yes_btn.clicked.connect(self.accept)
>>  157:             self._no_btn.clicked.connect(self.reject)
    158:             
    159:             layout.addWidget(self._no_btn)
    160:             layout.addWidget(self._yes_btn)
    161:             
    162:         elif self._dialog_type == DialogType.ALERT:
    163:             self._ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    164:             self._ok_btn.clicked.connect(self.accept)
    165:             layout.addWidget(self._ok_btn)
```

- Missing target `accept` at line 164: `self._ok_btn.clicked.connect(self.accept)`

```py
    156:             self._yes_btn.clicked.connect(self.accept)
    157:             self._no_btn.clicked.connect(self.reject)
    158:             
    159:             layout.addWidget(self._no_btn)
    160:             layout.addWidget(self._yes_btn)
    161:             
    162:         elif self._dialog_type == DialogType.ALERT:
    163:             self._ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
>>  164:             self._ok_btn.clicked.connect(self.accept)
    165:             layout.addWidget(self._ok_btn)
    166:             
    167:         else:
    168:             self._cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    169:             self._save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    170:             
    171:             self._cancel_btn.clicked.connect(self.reject)
    172:             self._save_btn.clicked.connect(self.accept)
```

- Missing target `reject` at line 171: `self._cancel_btn.clicked.connect(self.reject)`

```py
    163:             self._ok_btn = EnterpriseButton("OK", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    164:             self._ok_btn.clicked.connect(self.accept)
    165:             layout.addWidget(self._ok_btn)
    166:             
    167:         else:
    168:             self._cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    169:             self._save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    170:             
>>  171:             self._cancel_btn.clicked.connect(self.reject)
    172:             self._save_btn.clicked.connect(self.accept)
    173:             
    174:             layout.addWidget(self._cancel_btn)
    175:             layout.addWidget(self._save_btn)
    176:             
    177:         button_area.setStyleSheet(f"""
    178:             QFrame {{
    179:                 background-color: {COLOR_BG_MAIN};
```

- Missing target `accept` at line 172: `self._save_btn.clicked.connect(self.accept)`

```py
    164:             self._ok_btn.clicked.connect(self.accept)
    165:             layout.addWidget(self._ok_btn)
    166:             
    167:         else:
    168:             self._cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    169:             self._save_btn = EnterpriseButton("Save", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
    170:             
    171:             self._cancel_btn.clicked.connect(self.reject)
>>  172:             self._save_btn.clicked.connect(self.accept)
    173:             
    174:             layout.addWidget(self._cancel_btn)
    175:             layout.addWidget(self._save_btn)
    176:             
    177:         button_area.setStyleSheet(f"""
    178:             QFrame {{
    179:                 background-color: {COLOR_BG_MAIN};
    180:                 border-top: 1px solid {COLOR_FORM_FOOTER_BORDER};
```

## frontend/ui/components/navigation_header.py
- Missing target `back_clicked` at line 79: `self.back_btn.clicked.connect(self.back_clicked.emit)`

```py
     71:         main_layout.setContentsMargins(SPACING_SM,  0,  SPACING_SM,  0)
     72:         main_layout.setSpacing(SPACING_SM + SPACING_XS)
     73:         
     74:         # --- LEFT: Back + Home buttons ---
     75:         left_layout = QHBoxLayout()
     76:         left_layout.setSpacing(SPACING_SM)
     77:         
     78:         self.back_btn = IconButton(icon="←", tooltip="Back (Alt+Left)", size=ButtonSize.SMALL)
>>   79:         self.back_btn.clicked.connect(self.back_clicked.emit)
     80:         left_layout.addWidget(self.back_btn)
     81: 
     82:         self.home_btn = IconButton(icon="⌂", tooltip="Home (Ctrl+Home)", size=ButtonSize.SMALL)
     83:         self.home_btn.clicked.connect(self.home_clicked.emit)
     84:         left_layout.addWidget(self.home_btn)
     85:         
     86:         main_layout.addLayout(left_layout)
     87:         
```

- Missing target `home_clicked` at line 83: `self.home_btn.clicked.connect(self.home_clicked.emit)`

```py
     75:         left_layout = QHBoxLayout()
     76:         left_layout.setSpacing(SPACING_SM)
     77:         
     78:         self.back_btn = IconButton(icon="←", tooltip="Back (Alt+Left)", size=ButtonSize.SMALL)
     79:         self.back_btn.clicked.connect(self.back_clicked.emit)
     80:         left_layout.addWidget(self.back_btn)
     81: 
     82:         self.home_btn = IconButton(icon="⌂", tooltip="Home (Ctrl+Home)", size=ButtonSize.SMALL)
>>   83:         self.home_btn.clicked.connect(self.home_clicked.emit)
     84:         left_layout.addWidget(self.home_btn)
     85:         
     86:         main_layout.addLayout(left_layout)
     87:         
     88:         # --- CENTER: Title + Breadcrumb ---
     89:         center_layout = QVBoxLayout()
     90:         center_layout.setContentsMargins(0, 0, 0, 0)
     91:         center_layout.setSpacing(SPACING_XS)
```

- Missing target `close_clicked` at line 107: `self.close_btn.clicked.connect(self.close_clicked.emit)`

```py
     99:         self.breadcrumb_label.setFont(QFont("Segoe UI", TEXT_LABEL))
    100:         self.breadcrumb_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
    101:         center_layout.addWidget(self.breadcrumb_label)
    102:         
    103:         main_layout.addLayout(center_layout, 1)  # Stretch to fill center
    104:         
    105:         # --- RIGHT: Close button ---
    106:         self.close_btn = IconButton(icon="✕", tooltip="Close (Esc)", size=ButtonSize.SMALL)
>>  107:         self.close_btn.clicked.connect(self.close_clicked.emit)
    108:         main_layout.addWidget(self.close_btn)
    109:     
    110:     def set_title(self, title: str):
    111:         """Set the page title."""
    112:         self.title_label.setText(title)
    113:     
    114:     def set_breadcrumb(self, breadcrumb: list):
    115:         """Set breadcrumb path. Format: ['Home', 'Sales', 'Invoices']."""
```

## frontend/ui/inventory/base_screen.py
- Missing target `search_text_changed` at line 57: `self.search_input.textChanged.connect(self.search_text_changed.emit)`

```py
     49:                 border: 1px solid {COLOR_BORDER_INPUT};
     50:                 border-radius: {BORDER_RADIUS_MD}px;
     51:                 padding: {SPACING_SM}px {SPACING_SM}px;
     52:             }}
     53:             QLineEdit:focus {{
     54:                 border-color: {COLOR_BORDER_INPUT_HOVER};
     55:             }}
     56:         """)
>>   57:         self.search_input.textChanged.connect(self.search_text_changed.emit)
     58:         
     59:         # Filter bar
     60:         self.filter_combo = QComboBox()
     61:         self.filter_combo.setStyleSheet(f"""
     62:             QComboBox {{
     63:                 background-color: {COLOR_BG_DIALOG};
     64:                 color: {COLOR_TEXT_PRIMARY};
     65:                 border: 1px solid {COLOR_BORDER_INPUT};
```

- Missing target `add_requested` at line 101: `self.add_button.clicked.connect(self.add_requested.emit)`

```py
     93:         # Button bar with consistent spacing
     94:         button_layout = QHBoxLayout()
     95:         button_layout.setSpacing(SPACING_SM)
     96:         self.add_button = EnterpriseButton(text="Add", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
     97:         self.edit_button = EnterpriseButton(text="Edit", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
     98:         self.delete_button = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
     99:         self.refresh_button = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    100:         
>>  101:         self.add_button.clicked.connect(self.add_requested.emit)
    102:         self.edit_button.clicked.connect(self._on_edit_clicked)
    103:         self.delete_button.clicked.connect(self._on_delete_clicked)
    104:         self.refresh_button.clicked.connect(self.refresh_requested.emit)
    105:         
    106:         button_layout.addWidget(self.add_button)
    107:         button_layout.addWidget(self.edit_button)
    108:         button_layout.addWidget(self.delete_button)
    109:         button_layout.addWidget(self.refresh_button)
```

- Missing target `refresh_requested` at line 104: `self.refresh_button.clicked.connect(self.refresh_requested.emit)`

```py
     96:         self.add_button = EnterpriseButton(text="Add", variant=ButtonVariant.PRIMARY, size=ButtonSize.MEDIUM)
     97:         self.edit_button = EnterpriseButton(text="Edit", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
     98:         self.delete_button = EnterpriseButton(text="Delete", variant=ButtonVariant.DANGER, size=ButtonSize.MEDIUM)
     99:         self.refresh_button = EnterpriseButton(text="Refresh", variant=ButtonVariant.SECONDARY, size=ButtonSize.MEDIUM)
    100:         
    101:         self.add_button.clicked.connect(self.add_requested.emit)
    102:         self.edit_button.clicked.connect(self._on_edit_clicked)
    103:         self.delete_button.clicked.connect(self._on_delete_clicked)
>>  104:         self.refresh_button.clicked.connect(self.refresh_requested.emit)
    105:         
    106:         button_layout.addWidget(self.add_button)
    107:         button_layout.addWidget(self.edit_button)
    108:         button_layout.addWidget(self.delete_button)
    109:         button_layout.addWidget(self.refresh_button)
    110:         button_layout.addStretch()
    111:         
    112:         layout.addLayout(button_layout)
```

## frontend/ui/common/printable_invoice.py
- Missing target `reject` at line 99: `close_btn.clicked.connect(self.reject)`

```py
     91: 
     92:         self.save_pdf_btn = EnterpriseButton("Save as PDF", variant=ButtonVariant.SECONDARY)
     93:         self.save_pdf_btn.clicked.connect(self.save_as_pdf)
     94: 
     95:         self.share_wa_btn = EnterpriseButton("Share to WhatsApp", variant=ButtonVariant.SUCCESS)
     96:         self.share_wa_btn.clicked.connect(self.share_invoice)
     97: 
     98:         close_btn = EnterpriseButton("Close", variant=ButtonVariant.SECONDARY)
>>   99:         close_btn.clicked.connect(self.reject)
    100: 
    101:         button_layout.addWidget(self.print_btn)
    102:         button_layout.addWidget(self.print_preview_btn)
    103:         button_layout.addWidget(self.save_pdf_btn)
    104:         button_layout.addWidget(self.share_wa_btn)
    105:         button_layout.addStretch()
    106:         button_layout.addWidget(close_btn)
    107:         layout.addLayout(button_layout)
```

- Missing target `preview` at line 317: `dialog.paintRequested.connect(self.preview.print_)`

```py
    309:         printer = QPrinter(QPrinter.HighResolution)
    310:         dialog = QPrintDialog(printer, self)
    311:         if dialog.exec() == QPrintDialog.Accepted:
    312:             self.preview.print_(printer)
    313: 
    314:     def print_preview(self):
    315:         printer = QPrinter(QPrinter.HighResolution)
    316:         dialog = QPrintPreviewDialog(printer, self)
>>  317:         dialog.paintRequested.connect(self.preview.print_)
    318:         dialog.exec()
    319: 
    320:     def save_as_pdf(self):
    321:         file_path, _ = QFileDialog.getSaveFileName(
    322:             self,
    323:             "Save Invoice as PDF",
    324:             f"Invoice_{self.invoice_data.get('invoice_number', 'draft')}.pd",
    325:             "PDF Files (*.pdf)"
```

## frontend/ui/common/product_selection_dialog.py
- Missing target `search_timer` at line 37: `self.search_input.textChanged.connect(lambda: self.search_timer.start(300))`

```py
     29:     def _build_content(self):
     30:         widget = QWidget()
     31:         layout = QVBoxLayout(widget)
     32:         
     33:         # Search bar
     34:         search_layout = QHBoxLayout()
     35:         self.search_input = QLineEdit()
     36:         self.search_input.setPlaceholderText("Search by name, generic name, barcode, or SKU...")
>>   37:         self.search_input.textChanged.connect(lambda: self.search_timer.start(300))
     38:         search_layout.addWidget(QLabel("Search:"))
     39:         search_layout.addWidget(self.search_input)
     40:         layout.addLayout(search_layout)
     41:         
     42:         # Table
     43:         self.table = QTableWidget()
     44:         self.table.setColumnCount(5)
     45:         self.table.setHorizontalHeaderLabels(["Name", "Generic Name", "Barcode", "Price", "Stock"])
```

- Missing target `reject` at line 61: `self.cancel_btn.clicked.connect(self.reject)`

```py
     53:         btns = QHBoxLayout()
     54:         btns.addStretch()
     55:         
     56:         self.select_btn = EnterpriseButton("Select", variant=ButtonVariant.PRIMARY)
     57:         self.select_btn.clicked.connect(self.accept_selection)
     58:         btns.addWidget(self.select_btn)
     59:         
     60:         self.cancel_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY)
>>   61:         self.cancel_btn.clicked.connect(self.reject)
     62:         btns.addWidget(self.cancel_btn)
     63:         
     64:         layout.addLayout(btns)
     65:         
     66:         self.set_content(widget)
     67: 
     68:     def perform_search(self):
     69:         if not self._api_client:
```
