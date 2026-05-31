from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QTextEdit,
                                QLabel, QFileDialog, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from api.document_action_service import DocumentActionService
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import AlertDialog, EnterpriseDialog, DialogType
from utils.qr_generator import QRCodeGenerator
from ui.constants import TEXT_DISPLAY, TEXT_BODY, COLOR_WHATSAPP


class ReportPreviewDialog(EnterpriseDialog):
    """Dialog to preview a report in text format with print/PDF support."""

    def __init__(self, parent=None, title="", text_content="", report_meta=None):
        self._title = title
        self.text_content = text_content
        self.report_meta = report_meta or {}
        self.qr_pixmap = None
        super().__init__(f"Report Preview - {title}", DialogType.CUSTOM, parent)
        self.setMinimumSize(800, 600)
        self._build_content()
        self._generate_qr_code()

    def _create_button_area(self):
        return None

    def _generate_qr_code(self):
        """Generate QR code for the report."""
        if self.report_meta:
            qr_data = QRCodeGenerator.generate_report_qr_data(self.report_meta)
            if qr_data:
                self.qr_pixmap = QRCodeGenerator.generate_pixmap(qr_data, size=80)

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        header_layout = QHBoxLayout()
        header = QLabel(f"Report: {self.windowTitle()}")
        header_font = QFont("Segoe UI", TEXT_DISPLAY)
        header_font.setWeight(QFont.Weight.Bold)
        header.setFont(header_font)
        header_layout.addWidget(header)

        if self.qr_pixmap:
            qr_label = QLabel()
            qr_label.setPixmap(self.qr_pixmap)
            qr_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            header_layout.addWidget(qr_label)

        layout.addLayout(header_layout)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Courier New", TEXT_BODY))
        self.preview.setPlainText(self.text_content)
        layout.addWidget(self.preview)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.btn_print = EnterpriseButton("Print", variant=ButtonVariant.SECONDARY)
        self.btn_print.clicked.connect(self.print_report)
        buttons.addWidget(self.btn_print)

        self.btn_pdf = EnterpriseButton("Save as PDF", variant=ButtonVariant.SECONDARY)
        self.btn_pdf.clicked.connect(self.save_pdf)
        buttons.addWidget(self.btn_pdf)

        self.btn_share = EnterpriseButton("Share to WhatsApp", variant=ButtonVariant.SUCCESS)
        self.btn_share.clicked.connect(self.share_report)
        buttons.addWidget(self.btn_share)

        self.btn_close = EnterpriseButton("Close", variant=ButtonVariant.SECONDARY)
        self.btn_close.clicked.connect(self.reject)
        buttons.addWidget(self.btn_close)

        layout.addLayout(buttons)

        self.set_content(widget)
        return widget

    def print_report(self):
        printer = QPrinter(QPrinter.HighResolution)
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            return
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            doc = QTextDocument()
            doc.setPlainText(self.text_content)
            doc.setDefaultFont(QFont("Courier New", TEXT_BODY))
            doc.print_(printer)

    def save_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save as PDF", "report.pd", "PDF Files (*.pdf)"
        )
        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

            doc = QTextDocument()
            doc.setPlainText(self.text_content)
            doc.setDefaultFont(QFont("Courier New", TEXT_BODY))
            doc.print_(printer)

            AlertDialog.info("Success", f"PDF saved to {file_path}", self)

    def share_report(self):
        """Share the report summary via WhatsApp."""
        # For general reports, we share a summary message
        report_data = {
            'report_name': self._title,
            'summary': {
                'Content': 'Full report details available in PDF/Print format.',
                'Note': 'This is a computer generated summary.'
            }
        }
        DocumentActionService.share_via_whatsapp("report", report_data)
