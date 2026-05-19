"""
Unified Print Engine — orchestrates Document → Template → Renderer → Device Output.
Reuses existing QPrinter, HTML templates, and ReportLab infrastructure.
"""

from typing import Dict, Any, Optional
from enum import Enum

from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtGui import QTextDocument, QFont, QPdfWriter, QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

from utils.invoice_template_engine import InvoiceTemplateEngine
from utils.template_registry import TemplateRegistry


class PrintTarget(Enum):
    PRINTER = "printer"
    PDF = "pdf"
    PREVIEW = "preview"


class DocumentRenderer:
    """Renders documents into HTML for printing."""

    @staticmethod
    def render_invoice(invoice_data: Dict[str, Any], template_engine: InvoiceTemplateEngine) -> str:
        company_info = {
            "name": invoice_data.get("company_name", "Pharmacy ERP"),
            "address": invoice_data.get("company_address", ""),
            "phone": invoice_data.get("company_phone", ""),
            "logo": invoice_data.get("logo", ""),
        }
        return template_engine.render(invoice_data, company_info)

    @staticmethod
    def render_receipt(receipt_data: Dict[str, Any], template_engine: InvoiceTemplateEngine) -> str:
        company_info = {
            "name": receipt_data.get("company_name", "Pharmacy ERP"),
            "address": receipt_data.get("company_address", ""),
            "phone": receipt_data.get("company_phone", ""),
        }
        return template_engine.render(receipt_data, company_info)

    @staticmethod
    def render_report(title: str, text_content: str) -> str:
        lines = [f"<html><head><style>body{{font-family:'Courier New',monospace;font-size:11pt;white-space:pre-wrap;}}</style></head><body><pre>{text_content}</pre></body></html>"]
        return lines[0]

    @staticmethod
    def render_label(product_name: str, price: str, barcode_html: str) -> str:
        return f"""<html><body style="font-family:Arial;text-align:center;padding:5px;">
<div style="font-size:14pt;font-weight:bold;">{product_name}</div>
<div style="font-size:18pt;color:#2c3e50;">{price}</div>
<div>{barcode_html}</div>
</body></html>"""


class PrintEngine:
    """
    Unified print engine.
    Usage:
        engine = PrintEngine(api_client)
        engine.print_invoice(invoice_data)
        engine.print_report("TB", text)
        engine.save_as_pdf(invoice_data, "path/to/output.pdf")
    """

    def __init__(self, api_client=None):
        self._api_client = api_client
        self._template_registry = TemplateRegistry(api_client)
        self._renderer = DocumentRenderer()

    def get_template_engine(self, doc_type: str = "invoice") -> InvoiceTemplateEngine:
        config = self._template_registry.get_template(doc_type)
        return InvoiceTemplateEngine(config)

    def print_invoice(self, invoice_data: Dict[str, Any]):
        template_engine = self.get_template_engine("invoice")
        html = self._renderer.render_invoice(invoice_data, template_engine)
        self._print_html(html, "Print Invoice")

    def print_receipt(self, receipt_data: Dict[str, Any]):
        template_engine = self.get_template_engine("receipt")
        html = self._renderer.render_receipt(receipt_data, template_engine)
        self._print_html(html, "Print Receipt", width_mm=58)

    def print_report(self, title: str, text_content: str):
        html = self._renderer.render_report(title, text_content)
        self._print_html(html, f"Print {title}")

    def preview_invoice(self, invoice_data: Dict[str, Any]) -> str:
        template_engine = self.get_template_engine("invoice")
        return self._renderer.render_invoice(invoice_data, template_engine)

    def print_pdf(self, html: str, file_path: str, title: str = "Document"):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        printer.setDocName(title)
        printer.setPageSize(QPageSize(QPageSize.A4))

        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)

    def show_print_dialog(self, html: str, title: str = "Print"):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(title)
        dialog = QPrintDialog(printer)
        if dialog.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)

    def show_preview_dialog(self, html: str, title: str = "Preview"):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintPreviewDialog(printer)
        dialog.setWindowTitle(title)
        doc = QTextDocument()
        doc.setHtml(html)
        dialog.paintRequested.connect(lambda pr: doc.print_(pr))
        dialog.exec()

    def _print_html(self, html: str, title: str, width_mm: Optional[int] = None):
        from PySide6.QtWidgets import QApplication
        if not QApplication.instance():
            QMessageBox.warning(None, "No Application", "Printing requires an active application.")
            return
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setDocName(title)
            if width_mm:
                from PySide6.QtCore import QSizeF
                printer.setPageSize(QPageSize(QSizeF(width_mm, 297)))
            dialog = QPrintDialog(printer)
            if dialog.exec() == QPrintDialog.Accepted:
                doc = QTextDocument()
                doc.setHtml(html)
                doc.print_(printer)
        except RuntimeError as e:
            QMessageBox.warning(None, "Printer Error",
                f"Could not print: {e}\n\nPlease check your printer configuration and try again.")
