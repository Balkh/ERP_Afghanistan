from PySide6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QTextEdit,
                               QScrollArea, QWidget, QHBoxLayout, QLabel,
                               QMessageBox, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextDocument, QTextCursor, QPageSize, QPdfWriter
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
import os
from api.document_action_service import DocumentActionService
from utils.invoice_template_engine import InvoiceTemplateEngine
from api.client import APIClient


class PrintableInvoiceDialog(QDialog):
    """Dialog for previewing and printing invoices."""

    def __init__(self, parent=None, invoice_data=None, invoice_type="sale", api_client=None):
        super().__init__(parent)
        self.invoice_data = invoice_data or {}
        self.invoice_type = invoice_type
        self._api_client = api_client or APIClient()
        self.template_engine = InvoiceTemplateEngine()
        
        self.setWindowTitle("Print Invoice")
        self.setModal(True)
        self.resize(900, 700)
        self.setup_ui()
        self.render_invoice()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel("Invoice Preview")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Preview area
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMinimumHeight(500)
        layout.addWidget(self.preview, 1)

        # Buttons
        button_layout = QHBoxLayout()

        self.print_btn = QPushButton("Print")
        self.print_btn.clicked.connect(self.print_invoice)

        self.print_preview_btn = QPushButton("Print Preview")
        self.print_preview_btn.clicked.connect(self.print_preview)

        self.save_pdf_btn = QPushButton("Save as PDF")
        self.save_pdf_btn.clicked.connect(self.save_as_pdf)

        self.share_wa_btn = QPushButton("Share to WhatsApp")
        self.share_wa_btn.setStyleSheet("background-color: #25D366; color: white; font-weight: bold;")
        self.share_wa_btn.clicked.connect(self.share_invoice)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.print_btn)
        button_layout.addWidget(self.print_preview_btn)
        button_layout.addWidget(self.save_pdf_btn)
        button_layout.addWidget(self.share_wa_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

    def render_invoice(self):
        """Render invoice using dynamic engine if possible, else fallback."""
        try:
            # 1. Fetch active template config from API
            response = self._api_client.get("/api/core/invoice-templates/active/")
            if response and response.get("config"):
                self.template_engine = InvoiceTemplateEngine(response["config"])
                
                # 2. Prepare company info
                company_info = {
                    "name": "Pharmacy ERP",
                    "address": "Kabul, Afghanistan",
                    "phone": "+93 70 123 4567",
                    "logo": ""
                }
                
                # 3. Render using engine
                html = self.template_engine.render(self.invoice_data, company_info)
                self.preview.setHtml(html)
                return
        except Exception as e:
            print(f"Dynamic template failed: {e}")
            
        # Fallback to static HTML
        html = self.generate_invoice_html()
        self.preview.setHtml(html)

    def generate_invoice_html(self):
        inv = self.invoice_data
        is_sale = self.invoice_type == "sale"

        company_name = "Pharmacy ERP"
        company_address = "Kabul, Afghanistan"
        company_phone = "+93 70 123 4567"

        header_color = "#2c3e50"
        accent_color = "#3498db"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; font-size: 12px; }}
                .header {{ background-color: {header_color}; color: white; padding: 20px; border-radius: 5px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 5px 0; }}
                .invoice-info {{ display: flex; justify-content: space-between; margin: 20px 0; }}
                .invoice-info div {{ width: 48%; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background-color: {accent_color}; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .totals {{ text-align: right; margin: 20px 0; }}
                .totals table {{ width: 300px; margin-left: auto; }}
                .totals th {{ text-align: right; }}
                .totals td {{ text-align: right; }}
                .grand-total {{ font-size: 16px; font-weight: bold; background-color: {header_color}; color: white; }}
                .footer {{ text-align: center; margin-top: 40px; color: #666; font-size: 10px; border-top: 1px solid #ddd; padding-top: 10px; }}
                .status {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                .status-paid {{ background-color: #27ae60; color: white; }}
                .status-unpaid {{ background-color: #e74c3c; color: white; }}
                .status-partial {{ background-color: #f39c12; color: white; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{company_name}</h1>
                <p>{company_address}</p>
                <p>Phone: {company_phone}</p>
            </div>

            <h2 style="text-align: center; color: {header_color};">{"SALES" if is_sale else "PURCHASE"} INVOICE</h2>

            <div class="invoice-info">
                <div>
                    <h3>{"Customer" if is_sale else "Supplier"} Details</h3>
                    <p><strong>Name:</strong> {inv.get("customer_name" if is_sale else "supplier_name", "N/A")}</p>
                    <p><strong>Phone:</strong> {inv.get("phone", "N/A")}</p>
                    <p><strong>Address:</strong> {inv.get("address", "N/A")}</p>
                </div>
                <div style="text-align: right;">
                    <h3>Invoice Details</h3>
                    <p><strong>Invoice #:</strong> {inv.get("invoice_number", "N/A")}</p>
                    <p><strong>Date:</strong> {inv.get("invoice_date", "N/A")}</p>
                    <p><strong>Due Date:</strong> {inv.get("due_date", "N/A")}</p>
                    <p><strong>Status:</strong> <span class="status status-{inv.get("payment_status", "unpaid").lower()}">{inv.get("payment_status", "Unpaid")}</span></p>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Product</th>
                        <th>Batch</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Discount</th>
                        <th>Tax</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        items = inv.get("items", [])
        for i, item in enumerate(items, 1):
            html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{item.get("product_name", "N/A")}</td>
                        <td>{item.get("batch_number", item.get("batch", "N/A"))}</td>
                        <td>{item.get("quantity", 0)}</td>
                        <td>{inv.get("currency", "$")}{item.get("unit_price", 0):.2f}</td>
                        <td>{inv.get("currency", "$")}{item.get("discount", 0):.2f}</td>
                        <td>{inv.get("currency", "$")}{item.get("tax", 0):.2f}</td>
                        <td>{inv.get("currency", "$")}{item.get("total", 0):.2f}</td>
                    </tr>
            """

        html += f"""
                </tbody>
            </table>

            <div class="totals">
                <table>
                    <tr>
                        <th>Subtotal:</th>
                        <td>{inv.get("currency", "$")}{inv.get("subtotal", 0):.2f}</td>
                    </tr>
                    <tr>
                        <th>Discount:</th>
                        <td>-{inv.get("currency", "$")}{inv.get("discount", 0):.2f}</td>
                    </tr>
                    <tr>
                        <th>Tax:</th>
                        <td>{inv.get("currency", "$")}{inv.get("tax", 0):.2f}</td>
                    </tr>
                    <tr class="grand-total">
                        <th>Total:</th>
                        <td>{inv.get("currency", "$")}{inv.get("total_amount", 0):.2f}</td>
                    </tr>
                    <tr>
                        <th>Paid:</th>
                        <td>{inv.get("currency", "$")}{inv.get("paid_amount", 0):.2f}</td>
                    </tr>
                    <tr>
                        <th>Balance Due:</th>
                        <td>{inv.get("currency", "$")}{inv.get("remaining_balance", 0):.2f}</td>
                    </tr>
                </table>
            </div>

            <div class="footer">
                <p>Thank you for your business!</p>
                <p>This is a computer-generated invoice from {company_name} Pharmacy ERP System</p>
            </div>
        </body>
        </html>
        """

        return html

    def print_invoice(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            self.preview.print_(printer)

    def print_preview(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintPreviewDialog(printer, self)
        dialog.paintRequested.connect(self.preview.print_)
        dialog.exec()

    def save_as_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Invoice as PDF",
            f"Invoice_{self.invoice_data.get('invoice_number', 'draft')}.pdf",
            "PDF Files (*.pdf)"
        )

        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            self.preview.print_(printer)

            QMessageBox.information(self, "Success", f"Invoice saved to:\n{file_path}")

    def share_invoice(self):
        """Share the invoice via WhatsApp."""
        phone = self.invoice_data.get("phone", "")
        DocumentActionService.share_via_whatsapp("invoice", self.invoice_data, phone)
