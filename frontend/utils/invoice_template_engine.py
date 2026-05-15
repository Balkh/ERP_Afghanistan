import os
import json
from typing import Dict, Any, Optional
from ui.constants import SPACING_XL, SPACING_SM, FONT_SIZE_LG, FONT_SIZE_24, FONT_SIZE_16, FONT_SIZE_SM, FONT_SIZE_8, FONT_SIZE_MD, FONT_SIZE_XXL, FONT_SIZE_XL
from utils.qr_generator import QRCodeGenerator

class InvoiceTemplateEngine:
    """
    Engine to render invoice layouts based on dynamic templates.
    Supports Standard, Compact, and Brand templates.
    """
    
    DEFAULT_CONFIG = {
        "template_name": "Standard",
        "header_style": "full", # full, minimal, centered
        "color_theme": {
            "primary": "#2c3e50",
            "accent": "#3498db",
            "text": "#333333",
            "background": "#ffffff"
        },
        "layout_type": "detailed", # detailed, compact
        "show_qr": True,
        "footer_text": "Thank you for your business!",
        "field_visibility": {
            "batch": True,
            "discount": True,
            "tax": True,
            "notes": True,
            "phone": True,
            "address": True
        }
    }

    def __init__(self, template_config: Optional[Dict[str, Any]] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if template_config:
            self.config.update(template_config)
            
    def render(self, invoice_data: Dict[str, Any], company_info: Dict[str, Any]) -> str:
        """
        Render the invoice data into an HTML string based on the current template.
        """
        layout = self.config.get("layout_type", "detailed")
        
        if layout == "compact":
            return self._render_compact(invoice_data, company_info)
        else:
            return self._render_standard(invoice_data, company_info)

    def _get_styles(self) -> str:
        colors = self.config.get("color_theme", self.DEFAULT_CONFIG["color_theme"])
        return f"""
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: {SPACING_XL}px; font-size: {FONT_SIZE_LG}px; color: {colors['text']}; background: {colors['background']}; }}
                .header {{ background-color: {colors['primary']}; color: white; padding: {SPACING_XL}px; border-radius: 5px; position: relative; }}
                .header h1 {{ margin: 0; font-size: {FONT_SIZE_24}px; }}
                .header p {{ margin: 5px 0; opacity: 0.9; }}
                .logo-container {{ position: absolute; top: 20px; right: 20px; }}
                .logo {{ max-height: 60px; }}
                .invoice-info {{ display: flex; justify-content: space-between; margin: 20px 0; border-bottom: 2px solid {colors['accent']}; padding-bottom: 10px; }}
                .invoice-info div {{ width: 48%; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; table-layout: fixed; }}
                th {{ background-color: {colors['accent']}; color: white; padding: 10px; text-align: left; }}
                td {{ padding: {SPACING_SM}px 10px; border-bottom: 1px solid #ddd; word-wrap: break-word; overflow: hidden; }}
                .col-id {{ width: 30px; }}
                .col-product {{ width: auto; }}
                .col-qty {{ width: 60px; text-align: center; }}
                .col-price {{ width: 80px; text-align: right; }}
                .col-total {{ width: 100px; text-align: right; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .totals {{ text-align: right; margin: 20px 0; }}
                .totals table {{ width: 300px; margin-left: auto; }}
                .totals th {{ text-align: right; border-bottom: none; }}
                .totals td {{ text-align: right; border-bottom: none; }}
                .grand-total {{ font-size: {FONT_SIZE_16}px; font-weight: bold; background-color: {colors['primary']}; color: white; }}
                .footer {{ text-align: center; margin-top: 40px; color: #666; font-size: {FONT_SIZE_SM}px; border-top: 1px solid #ddd; padding-top: 10px; }}
                .status {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; text-transform: uppercase; }}
                .qr-code {{ margin-top: 10px; text-align: center; }}
                @media print {{
                    body {{ padding: 0; }}
                    .no-print {{ display: none; }}
                }}
            </style>
        """

    def _render_standard(self, inv: Dict[str, Any], company: Dict[str, Any]) -> str:
        colors = self.config.get("color_theme", self.DEFAULT_CONFIG["color_theme"])
        fields = self.config.get("field_visibility", self.DEFAULT_CONFIG["field_visibility"])
        
        logo_html = ""
        if company.get("logo"):
            logo_html = f'<div class="logo-container"><img src="{company["logo"]}" class="logo"></div>'

        html = f"""
        <html>
        <head>{self._get_styles()}</head>
        <body>
            <div class="header">
                {logo_html}
                <h1>{company.get('name', 'Pharmacy ERP')}</h1>
                <p>{company.get('address', '')}</p>
                <p>Phone: {company.get('phone', '')}</p>
            </div>

            <h2 style="text-align: center; color: {colors['primary']};">INVOICE</h2>

            <div class="invoice-info">
                <div>
                    <h3>Bill To:</h3>
                    <p><strong>Name:</strong> {inv.get('customer_name', 'N/A')}</p>
                    {f"<p><strong>Phone:</strong> {inv.get('phone', 'N/A')}</p>" if fields.get('phone') else ""}
                    {f"<p><strong>Address:</strong> {inv.get('address', 'N/A')}</p>" if fields.get('address') else ""}
                </div>
                <div style="text-align: right;">
                    <h3>Invoice Details:</h3>
                    <p><strong>Invoice #:</strong> {inv.get('invoice_number', 'N/A')}</p>
                    <p><strong>Date:</strong> {inv.get('invoice_date', 'N/A')}</p>
                    <p><strong>Due Date:</strong> {inv.get('due_date', 'N/A')}</p>
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th class="col-id">#</th>
                        <th class="col-product">Product</th>
                        { "<th class='col-batch'>Batch</th>" if fields.get('batch') else "" }
                        <th class="col-qty">Qty</th>
                        <th class="col-price">Price</th>
                        { "<th class='col-discount'>Discount</th>" if fields.get('discount') else "" }
                        { "<th class='col-tax'>Tax</th>" if fields.get('tax') else "" }
                        <th class="col-total">Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        for i, item in enumerate(inv.get("items", []), 1):
            html += f"""
                <tr>
                    <td class="col-id">{i}</td>
                    <td class="col-product">{item.get('product_name', 'N/A')}</td>
                    { f"<td class='col-batch'>{item.get('batch_number', 'N/A')}</td>" if fields.get('batch') else "" }
                    <td class="col-qty">{item.get('quantity', 0)}</td>
                    <td class="col-price">{inv.get('currency', '$')}{item.get('unit_price', 0):.2f}</td>
                    { f"<td class='col-discount'>{inv.get('currency', '$')}{item.get('discount', 0):.2f}</td>" if fields.get('discount') else "" }
                    { f"<td class='col-tax'>{inv.get('currency', '$')}{item.get('tax', 0):.2f}</td>" if fields.get('tax') else "" }
                    <td class="col-total">{inv.get('currency', '$')}{item.get('total', 0):.2f}</td>
                </tr>
            """

        html += f"""
                </tbody>
            </table>

            <div class="totals">
                <table>
                    <tr>
                        <th>Subtotal:</th>
                        <td>{inv.get('currency', '$')}{inv.get('subtotal', 0):.2f}</td>
                    </tr>
                    { f"<tr><th>Discount:</th><td>-{inv.get('currency', '$')}{inv.get('discount', 0):.2f}</td></tr>" if fields.get('discount') else "" }
                    { f"<tr><th>Tax:</th><td>{inv.get('currency', '$')}{inv.get('tax', 0):.2f}</td></tr>" if fields.get('tax') else "" }
                    <tr class="grand-total">
                        <th>Total:</th>
                        <td>{inv.get('currency', '$')}{inv.get('total_amount', 0):.2f}</td>
                    </tr>
                </table>
            </div>

            <div class="footer">
                <p>{self.config.get('footer_text', '')}</p>
                { self._render_qr_section(inv) if self.config.get('show_qr') else "" }
                <p style="font-size: {FONT_SIZE_8}px;">Generated by Pharmacy ERP</p>
            </div>
        </body>
        </html>
        """
        return html

    def _render_qr_section(self, inv: Dict[str, Any]) -> str:
        qr_data = QRCodeGenerator.generate_invoice_qr_data(inv)
        qr_uri = QRCodeGenerator.generate_data_uri(qr_data, size=80)
        if not qr_uri:
            return ""
        return f"""
            <div class="qr-code">
                <img src="{qr_uri}" alt="QR Code" width="80" height="80">
                <div style="font-size: {FONT_SIZE_8}px; margin-top: 2px;">Scan to Verify</div>
            </div>
        """

    def _render_compact(self, inv: Dict[str, Any], company: Dict[str, Any]) -> str:
        # Simplified compact layout for thermal printers
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Courier New', monospace; padding: 0; margin: 0; font-size: {FONT_SIZE_MD}px; width: 280px; color: #000; }}
                .center {{ text-align: center; }}
                .bold {{ font-weight: bold; }}
                .header-line {{ font-size: {FONT_SIZE_XXL}px; margin-bottom: 2px; }}
                table {{ width: 100%; border-top: 1px dashed #000; border-bottom: 1px dashed #000; margin: 5px 0; border-collapse: collapse; }}
                th {{ text-align: left; padding: 2px 0; }}
                td {{ padding: 2px 0; vertical-align: top; }}
                .text-right {{ text-align: right; }}
                .totals {{ margin-top: 5px; border-top: 1px solid #000; padding-top: 5px; }}
                .qr-compact {{ margin-top: 10px; text-align: center; }}
                hr {{ border: none; border-top: 1px dashed #000; margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="center">
                <div class="bold header-line">{company.get('name', 'Pharmacy ERP')}</div>
                <div>{company.get('address', '')}</div>
                <div>Tel: {company.get('phone', '')}</div>
                <hr>
                <div class="bold">SALES RECEIPT</div>
                <div>No: {inv.get('invoice_number', 'N/A')}</div>
                <div>Date: {inv.get('invoice_date', 'N/A')}</div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th width="60%">Item</th>
                        <th width="15%" class="text-right">Qty</th>
                        <th width="25%" class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for item in inv.get("items", []):
            name = item.get('product_name', 'N/A')
            if len(name) > 20:
                name = name[:18] + ".."
            html += f"""
                <tr>
                    <td>{name}</td>
                    <td class="text-right">{item.get('quantity', 0)}</td>
                    <td class="text-right">{item.get('total', 0):.2f}</td>
                </tr>
            """
            
        html += f"""
                </tbody>
            </table>
            
            <div class="totals">
                <div style="display: flex; justify-content: space-between;">
                    <span>Subtotal:</span>
                    <span>{inv.get('currency', '$')}{inv.get('subtotal', 0):.2f}</span>
                </div>
                <div class="bold" style="display: flex; justify-content: space-between; font-size: {FONT_SIZE_XL}px; margin-top: 2px;">
                    <span>TOTAL:</span>
                    <span>{inv.get('currency', '$')}{inv.get('total_amount', 0):.2f}</span>
                </div>
            </div>
            
            <div class="center" style="margin-top: 10px;">
                <p>{self.config.get('footer_text', 'Thank you for your visit!')}</p>
                { self._render_qr_section(inv) if self.config.get('show_qr') else "" }
                <div style="font-size: {FONT_SIZE_8}px; margin-top: 5px;">Powered by Pharmacy ERP</div>
            </div>
        </body>
        </html>
        """
        return html
