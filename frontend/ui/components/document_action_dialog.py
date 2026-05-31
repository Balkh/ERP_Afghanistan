from ui.constants import (
    SPACING_XS,
    SPACING_SM,
    SPACING_LG,
    SPACING_XL,
    TEXT_BODY,
    TEXT_LABEL,
    BORDER_RADIUS_MD,
    BORDER_RADIUS_LG,
    COLOR_BG_SURFACE,
    COLOR_BG_ELEVATED,
    COLOR_BG_INPUT,
    COLOR_BORDER_LIGHT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_PRIMARY,
    COLOR_PRIMARY_MUTED,
    COLOR_WHATSAPP,
)

"""
Document Action Dialog - Centralized dialog for Printing and Sharing.
"""

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QLineEdit, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.components.buttons import EnterpriseButton, ButtonVariant, ButtonSize
from ui.components.dialogs import EnterpriseDialog, DialogType

from api.document_action_service import DocumentActionService

class DocumentActionDialog(EnterpriseDialog):
    """
    Unified dialog for document actions (Print, PDF, WhatsApp).
    """
    def __init__(self, parent=None, doc_type="invoice", data=None):
        self.doc_type = doc_type
        self.data = data or {}
        super().__init__(f"Document Actions - {doc_type.capitalize()}", DialogType.CUSTOM, parent)
        self.setMinimumWidth(400)
        self._build_content()
        
    def _create_button_area(self):
        return None

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM,  SPACING_XL + SPACING_SM)
        layout.setSpacing(SPACING_LG)
        
        # Header
        header = QLabel("How would you like to handle this document?")
        header.setFont(QFont("Segoe UI", TEXT_BODY, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        layout.addWidget(header)

        # Document Summary Card
        summary_card = QFrame()
        summary_card.setStyleSheet(f"background: {COLOR_BG_SURFACE}; border-radius: {BORDER_RADIUS_LG}; border: 1px solid {COLOR_BG_ELEVATED};")
        s_layout = QVBoxLayout(summary_card)
        
        doc_id = self.data.get('invoice_number', self.data.get('id', 'N/A'))
        total = self.data.get('total_amount', '0.00')
        
        s_layout.addWidget(QLabel(f"<b>ID:</b> {doc_id}"))
        if 'customer_name' in self.data:
            s_layout.addWidget(QLabel(f"<b>Customer:</b> {self.data['customer_name']}"))
        s_layout.addWidget(QLabel(f"<b>Total:</b> {total} AFN"))
        
        layout.addWidget(summary_card)
        
        # Action Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(SPACING_SM + SPACING_XS)
        
        # 1. Print Button
        self.print_btn = EnterpriseButton("Print Document", variant=ButtonVariant.PRIMARY, size=ButtonSize.LARGE)
        self.print_btn.clicked.connect(self._on_print)
        btn_layout.addWidget(self.print_btn)
        
        # 2. PDF Button
        self.pdf_btn = EnterpriseButton("Download as PDF", variant=ButtonVariant.SECONDARY, size=ButtonSize.LARGE)
        btn_layout.addWidget(self.pdf_btn)

        # separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLOR_BORDER_LIGHT};")
        btn_layout.addWidget(line)

        # 3. WhatsApp Section
        wa_header = QLabel("Share via WhatsApp")
        wa_header.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: {TEXT_LABEL}px; font-weight: bold;")
        btn_layout.addWidget(wa_header)
        
        wa_row = QHBoxLayout()
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone (e.g. 93700123456)")
        self.phone_input.setStyleSheet(f"background: {COLOR_BG_INPUT}; border: 1px solid {COLOR_BORDER_LIGHT}; border-radius: {BORDER_RADIUS_MD}; padding: 0 {SPACING_SM}px;")
        
        # Pre-fill phone if available in data
        if 'customer_phone' in self.data:
            self.phone_input.setText(self.data['customer_phone'])
            
        self.wa_btn = EnterpriseButton("Share", variant=ButtonVariant.SUCCESS, size=ButtonSize.MEDIUM)
        self.wa_btn.clicked.connect(self._on_whatsapp)
        
        wa_row.addWidget(self.phone_input)
        wa_row.addWidget(self.wa_btn)
        btn_layout.addLayout(wa_row)
        
        layout.addLayout(btn_layout)
        
        # Close Button
        close_btn = EnterpriseButton("Cancel", variant=ButtonVariant.SECONDARY)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn, 0, Qt.AlignCenter)

        self.set_content(widget)

    def _on_print(self):
        DocumentActionService.print_document(self.doc_type, self.data)
        self.accept()

    def _on_whatsapp(self):
        phone = self.phone_input.text().strip()
        DocumentActionService.share_via_whatsapp(self.doc_type, self.data, phone)
        self.accept()
