from PySide6.QtWidgets import (QVBoxLayout, QTextEdit,
                                QHBoxLayout, QLabel, QFileDialog, QWidget)
from PySide6.QtGui import QFont
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from api.document_action_service import DocumentActionService
from ui.components.buttons import EnterpriseButton, ButtonVariant
from ui.components.dialogs import EnterpriseDialog, DialogType, AlertDialog
from utils.invoice_template_engine import InvoiceTemplateEngine
from utils.qr_generator import QRCodeGenerator
from api.client import APIClient
from ui.constants import (COLOR_WHATSAPP, SPACING_MD, SPACING_SM, SPACING_LG, SPACING_XL,
    SPACING_XS, TEXT_BODY, TEXT_BODY_SMALL, TEXT_CARD_TITLE,
                           TEXT_SECTION_TITLE, TEXT_TABLE)


class PrintableInvoiceDialog(EnterpriseDialog):
    """Dialog for previewing and printing invoices."""

    def __init__(self, parent=None, invoice_data=None, invoice_type="sale", api_client=None):
        self.invoice_data = invoice_data or {}
        self.invoice_type = invoice_type
        self._api_client = api_client or APIClient()
        self.template_engine = InvoiceTemplateEngine()
        self.company_info = self._load_company_info()
        super().__init__("Print Invoice", DialogType.CUSTOM, parent)
        self.setModal(True)
        self.resize(900, 700)
        content = self._build_content()
        self.set_content(content)
        self.render_invoice()

    def _create_button_area(self):
        return None
    
    def _load_company_info(self):
        """Load company info from backend API (SSOT)."""
        try:
            resp = self._api_client.get("/api/companies/config/")
            if isinstance(resp, dict) and resp.get("success"):
                data = resp.get("data", resp)
                return {
                    "name": data.get("company_name", "Pharmacy ERP"),
                    "address": data.get("address", ""),
                    "phone": data.get("phone", ""),
                    "email": data.get("email", ""),
                    "tax_number": data.get("tax_number", ""),
                    "default_currency": data.get("default_currency", "AFN"),
                    "invoice_footer": data.get("invoice_footer", ""),
                }
        except Exception:
            pass
        return {
            "name": "Pharmacy ERP",
            "address": "",
            "phone": "",
            "email": "",
            "tax_number": "",
            "default_currency": "AFN",
            "invoice_footer": "",
        }

    def _build_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)

        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel("Invoice Preview")
        title_label.setFont(QFont("Segoe UI", TEXT_CARD_TITLE, QFont.Weight.Bold))
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

        self.print_btn = EnterpriseButton("Print", variant=ButtonVariant.SECONDARY)
        self.print_btn.clicked.connect(self.print_invoice)

        self.print_preview_btn = EnterpriseButton("Print Preview", variant=ButtonVariant.SECONDARY)
        self.print_preview_btn.clicked.connect(self.print_preview)

        self.save_pdf_btn = EnterpriseButton("Save as PDF", variant=ButtonVariant.SECONDARY)
        self.save_pdf_btn.clicked.connect(self.save_as_pdf)

        self.share_wa_btn = EnterpriseButton("Share to WhatsApp", variant=ButtonVariant.SUCCESS)
        self.share_wa_btn.clicked.connect(self.share_invoice)

        close_btn = EnterpriseButton("Close", variant=ButtonVariant.SECONDARY)
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.print_btn)
        button_layout.addWidget(self.print_preview_btn)
        button_layout.addWidget(self.save_pdf_btn)
        button_layout.addWidget(self.share_wa_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        return widget

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
        __is_sale = self.invoice_type == "sale"

        __company_name = self.company_info["name"]
        __company_address = self.company_info["address"]
        __company_phone = self.company_info["phone"]
        __company_email = self.company_info["email"]
        __company_tax = self.company_info["tax_number"]
        __currency = self.company_info["default_currency"]
        __invoice_footer = self.company_info["invoice_footer"]

        from ui.constants import (
            COLOR_BG_MAIN, COLOR_BG_SURFACE, COLOR_PRIMARY, COLOR_BORDER,
            COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED, COLOR_TEXT_ON_PRIMARY,
            COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
            SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
            BORDER_RADIUS_MD, BORDER_RADIUS_LG,
            TEXT_BODY, TEXT_SECTION_TITLE, TEXT_CARD_TITLE, TEXT_TABLE, TEXT_TABLE_HEADER, TEXT_HELPER
        )

        __header_color = COLOR_PRIMARY
        __accent_color = COLOR_PRIMARY
        __table_border_color = COLOR_BORDER
        __even_row_bg = COLOR_BG_MAIN
        __footer_text_color = COLOR_TEXT_MUTED
        __footer_border_color = COLOR_BORDER
        __status_paid_bg = COLOR_SUCCESS
        __status_unpaid_bg = COLOR_DANGER
        __status_partial_bg = COLOR_WARNING

        html = """
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: {SPACING_XL}px; font-size: {TEXT_BODY}px; color: {COLOR_TEXT_PRIMARY}; background-color: {COLOR_BG_SURFACE}; }}
                .header {{ background-color: {header_color}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_XL}px; border-radius: {BORDER_RADIUS_LG}px; }}
                .header h1 {{ margin: 0; font-size: {TEXT_SECTION_TITLE}px; }}
                .header p {{ margin: {SPACING_XS}px 0; opacity: 0.9; }}
                .invoice-info {{ display: flex; justify-content: space-between; margin: {SPACING_XL}px 0; }}
                .invoice-info div {{ width: 48%; }}
                table {{ width: 100%; border-collapse: collapse; margin: {SPACING_XL}px 0; }}
                th {{ background-color: {accent_color}; color: {COLOR_TEXT_ON_PRIMARY}; padding: {SPACING_MD}px; text-align: left; font-weight: 600; }}
                td {{ padding: {SPACING_SM}px 10px; border-bottom: 1px solid {table_border_color}; color: {COLOR_TEXT_PRIMARY}; }}
                tr:nth-child(even) {{ background-color: {even_row_bg}; }}
                .totals {{ text-align: right; margin: {SPACING_XL}px 0; }}
                .totals table {{ width: 300px; margin-left: auto; }}
                .totals th {{ text-align: right; background-color: transparent; color: {COLOR_TEXT_SECONDARY}; }}
                .totals td {{ text-align: right; font-weight: 500; }}
                .grand-total {{ font-size: {TEXT_CARD_TITLE}px; font-weight: bold; background-color: {header_color} !important; color: {COLOR_TEXT_ON_PRIMARY} !important; }}
                .footer {{ text-align: center; margin-top: 40px; color: {footer_text_color}; font-size: {TEXT_TABLE}px; border-top: 1px solid {footer_border_color}; padding-top: 10px; }}
                .status {{ display: inline-block; padding: {SPACING_XS}px 10px; border-radius: 4px; font-weight: bold; text-transform: uppercase; font-size: {TEXT_TABLE}px; }}
                .status-paid {{ background-color: {status_paid_bg}; color: {COLOR_TEXT_ON_PRIMARY}; }}
                .status-unpaid {{ background-color: {status_unpaid_bg}; color: {COLOR_TEXT_ON_PRIMARY}; }}
                .status-partial {{ background-color: {status_partial_bg}; color: {COLOR_TEXT_ON_PRIMARY}; }}
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
            html += """
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

        html += """
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
                {self._render_qr_code_fallback(inv)}
            </div>
        </body>
        </html>
        """

        return html

    def _render_qr_code_fallback(self, inv: dict) -> str:
        """Render a QR code for the invoice using local generator."""
        try:
            from ui.constants import SPACING_XS, SPACING_MD, TEXT_HELPER, COLOR_TEXT_MUTED
            qr_data = QRCodeGenerator.generate_invoice_qr_data(inv)
            qr_uri = QRCodeGenerator.generate_data_uri(qr_data, size=80)
            if qr_uri:
                return f'''
                <div style="text-align: center; margin-top: {SPACING_MD}px;">
                    <img src="{qr_uri}" alt="QR Code" width="80" height="80">
                    <p style="font-size: {TEXT_HELPER}px; color: {COLOR_TEXT_MUTED}; margin-top: {SPACING_XS}px;">Scan to Verify Invoice</p>
                </div>
                '''
        except Exception:
            pass
        return ""

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
            f"Invoice_{self.invoice_data.get('invoice_number', 'draft')}.pd",
            "PDF Files (*.pdf)"
        )

        if file_path:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            self.preview.print_(printer)

            AlertDialog.info("Success", f"Invoice saved to:\n{file_path}", self)

    def share_invoice(self):
        """Share the invoice via WhatsApp."""
        phone = self.invoice_data.get("phone", "")
        DocumentActionService.share_via_whatsapp("invoice", self.invoice_data, phone)
