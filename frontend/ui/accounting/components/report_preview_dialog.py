from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                               QPushButton, QLabel, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextDocument, QPrinter
from api.document_action_service import DocumentActionService


class ReportPreviewDialog(QDialog):
    """Dialog to preview a report in text format with print/PDF support."""

    def __init__(self, parent=None, title="", text_content=""):
        super().__init__(parent)
        self.title = title
        self.setWindowTitle(f"Report Preview - {title}")
        self.setMinimumSize(800, 600)
        self.text_content = text_content
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(f"Report: {self.windowTitle()}")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Courier New", 10))
        self.preview.setPlainText(self.text_content)
        layout.addWidget(self.preview)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.btn_print = QPushButton("Print")
        self.btn_print.setMinimumHeight(32)
        self.btn_print.clicked.connect(self.print_report)
        buttons.addWidget(self.btn_print)

        self.btn_pdf = QPushButton("Save as PDF")
        self.btn_pdf.setMinimumHeight(32)
        self.btn_pdf.clicked.connect(self.save_pdf)
        buttons.addWidget(self.btn_pdf)

        self.btn_share = QPushButton("Share to WhatsApp")
        self.btn_share.setMinimumHeight(32)
        self.btn_share.setStyleSheet("background-color: #25D366; color: white; font-weight: bold;")
        self.btn_share.clicked.connect(self.share_report)
        buttons.addWidget(self.btn_share)

        self.btn_close = QPushButton("Close")
        self.btn_close.setMinimumHeight(32)
        self.btn_close.clicked.connect(self.reject)
        buttons.addWidget(self.btn_close)

        layout.addLayout(buttons)

    def print_report(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrinter.QPrintDialog(printer, self)
        if dialog.exec():
            doc = QTextDocument()
            doc.setPlainText(self.text_content)
            doc.setDefaultFont(QFont("Courier New", 10))
            doc.print_(printer)

    def save_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save as PDF", "report.pdf", "PDF Files (*.pdf)"
        )
        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)

            doc = QTextDocument()
            doc.setPlainText(self.text_content)
            doc.setDefaultFont(QFont("Courier New", 10))
            doc.print_(printer)

            QMessageBox.information(self, "Success", f"PDF saved to {file_path}")

    def share_report(self):
        """Share the report summary via WhatsApp."""
        # For general reports, we share a summary message
        report_data = {
            'report_name': self.title,
            'summary': {
                'Content': 'Full report details available in PDF/Print format.',
                'Note': 'This is a computer generated summary.'
            }
        }
        DocumentActionService.share_via_whatsapp("report", report_data)
