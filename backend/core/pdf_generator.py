"""Shared PDF generation utilities for Pharmacy ERP.

Provides reusable PDF rendering patterns for invoices, receipts, and reports.
All PDF generation uses ReportLab — no browser engines, no HTML rendering.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Optional

from django.http import HttpResponse


def _get_company_info():
    """Load company branding from the active Company model (single source of truth).

    Returns a dict with: name, address, phone, email, tax_number.
    Falls back to safe defaults only if no active company exists.
    """
    from core.models.system import Company

    company = Company.objects.active()
    if company:
        return {
            "name": company.name,
            "address": company.address or "",
            "phone": company.phone or "",
            "email": company.email or "",
            "tax_number": company.tax_number or "",
        }
    return {
        "name": "Pharmacy ERP",
        "address": "",
        "phone": "",
        "email": "",
        "tax_number": "",
    }


def _get_styles():
    """Get standardized paragraph styles for PDF documents."""
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=18, spaceAfter=6, alignment=TA_CENTER,
        textColor=colors.HexColor('#1a1a2e')
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, spaceAfter=12, alignment=TA_CENTER,
        textColor=colors.HexColor('#666666')
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'],
        fontSize=12, spaceBefore=12, spaceAfter=6,
        textColor=colors.HexColor('#1a1a2e')
    )
    normal_style = ParagraphStyle(
        'CustomNormal', parent=styles['Normal'],
        fontSize=9, spaceAfter=3, textColor=colors.HexColor('#333333')
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'],
        fontSize=9, spaceAfter=3, textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Bold'
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#999999')
    )

    return {
        'title': title_style, 'subtitle': subtitle_style,
        'heading': heading_style, 'normal': normal_style,
        'label': label_style, 'footer': footer_style,
    }


def _build_info_table(rows, col_widths=None):
    """Build a standard info table for PDF documents."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    if col_widths is None:
        col_widths = [100, 200, 80, 120]

    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#666666')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return table


def _build_items_table(headers, rows, col_widths=None, total_row=None):
    """Build a standard items table for PDF documents."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    data = [headers]
    data.extend(rows)
    if total_row:
        data.append(total_row)

    if col_widths is None:
        col_widths = [30, 150, 50, 60, 70, 60, 70]

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -2 if total_row else -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -2 if total_row else -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -2 if total_row else -1), 4),
    ]))
    if total_row:
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
    return table


def _add_qr_placeholder(story, width=80, height=80):
    """Add a QR code placeholder box to the PDF story."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    qr_table = Table([['QR Code']], colWidths=[width])
    qr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#999999')),
        ('HEIGHT', (0, 0), (-1, -1), height),
    ]))
    story.append(qr_table)


def _add_barcode_placeholder(story, text='', width=200, height=30):
    """Add a barcode placeholder box to the PDF story."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    display_text = text or 'Barcode'
    bc_table = Table([[display_text]], colWidths=[width])
    bc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, -1), 'Courier'),
        ('HEIGHT', (0, 0), (-1, -1), height),
    ]))
    story.append(bc_table)


def _add_company_details(story, company):
    """Add company address/contact details to the PDF story after the title.

    Renders address, phone, email, and tax_number in a compact centered block.
    Skips empty fields gracefully.
    """
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Spacer

    lines = []
    if company.get("address"):
        lines.append(company["address"])
    if company.get("phone"):
        lines.append(f"Tel: {company['phone']}")
    if company.get("email"):
        lines.append(f"Email: {company['email']}")
    if company.get("tax_number"):
        lines.append(f"Tax#: {company['tax_number']}")

    if not lines:
        return

    contact_text = " | ".join(lines)
    contact_table = Table([[contact_text]], colWidths=[460])
    contact_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(contact_table)
    story.append(Spacer(1, 4))


def generate_sales_invoice_pdf(invoice, mode='a4'):
    """Generate PDF for a sales invoice.

    Args:
        invoice: SalesInvoice instance
        mode: 'a4' for full invoice, 'thermal' for receipt (80mm)

    Returns:
        bytes: PDF content
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib import colors

    styles = _get_styles()
    buffer = BytesIO()

    if mode == 'thermal':
        page_width = 80 * mm
        doc = SimpleDocTemplate(
            buffer, pagesize=(page_width, 500 * mm),
            topMargin=5 * mm, bottomMargin=5 * mm,
            leftMargin=3 * mm, rightMargin=3 * mm
        )
    else:
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch
        )

    story = []

    company = _get_company_info()
    story.append(Paragraph(company["name"], styles['title']))
    story.append(Paragraph('Sales Invoice', styles['subtitle']))
    _add_company_details(story, company)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=12))

    # Invoice info
    customer_name = invoice.customer.name if invoice.customer else 'N/A'
    invoice_date = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else 'N/A'

    info_rows = [
        ['Invoice #:', invoice.invoice_number, 'Date:', invoice_date],
        ['Customer:', customer_name, 'Status:', invoice.status],
    ]
    if invoice.due_date:
        info_rows.append(['Due Date:', invoice.due_date.strftime('%Y-%m-%d'), '', ''])
    story.append(_build_info_table(info_rows))
    story.append(Spacer(1, 12))

    # Line items
    story.append(Paragraph('Invoice Items', styles['heading']))

    item_rows = []
    for i, item in enumerate(invoice.items.all(), 1):
        discount = getattr(item, 'discount_amount', item.discount) if hasattr(item, 'discount') else getattr(item, 'discount_amount', Decimal('0.00'))
        tax = getattr(item, 'tax_amount', item.tax) if hasattr(item, 'tax') else getattr(item, 'tax_amount', Decimal('0.00'))
        line_total = getattr(item, 'line_total', item.total) if hasattr(item, 'total') else getattr(item, 'line_total', Decimal('0.00'))
        item_rows.append([
            str(i),
            item.product.name if item.product else 'N/A',
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{discount:.2f}",
            f"{tax:.2f}",
            f"{line_total:.2f}",
        ])

    total_row = ['', '', '', '', '', 'Total:', f"{invoice.total_amount:.2f}"]
    story.append(_build_items_table(
        ['#', 'Product', 'Qty', 'Unit Price', 'Discount', 'Tax', 'Total'],
        item_rows,
        total_row=total_row,
    ))
    story.append(Spacer(1, 12))

    # Payment summary
    paid = invoice.paid_amount or Decimal('0.00')
    balance = invoice.total_amount - paid
    story.append(Paragraph('Payment Summary', styles['heading']))
    payment_status = getattr(invoice, 'payment_status', 'N/A')
    payment_rows = [
        ['Total Amount:', f"{invoice.total_amount:.2f}", 'Paid:', f"{paid:.2f}"],
        ['Balance Due:', f"{balance:.2f}", 'Payment Status:', payment_status or 'N/A'],
    ]
    story.append(_build_info_table(payment_rows))
    story.append(Spacer(1, 18))

    # QR/barcode placeholders
    if mode == 'a4':
        story.append(_build_info_table([
            ['QR Code:', '[Scan for verification]', 'Barcode:', invoice.invoice_number],
        ], col_widths=[80, 180, 70, 170]))
        story.append(Spacer(1, 6))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        f'Generated on {date.today()} | {company["name"]} | Invoice {invoice.invoice_number}',
        styles['footer']
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_return_receipt_pdf(return_order, mode='a4'):
    """Generate PDF for a return order receipt.

    Args:
        return_order: ReturnOrder instance
        mode: 'a4' for full receipt, 'thermal' for receipt (80mm)

    Returns:
        bytes: PDF content
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib import colors

    styles = _get_styles()
    buffer = BytesIO()

    if mode == 'thermal':
        page_width = 80 * mm
        doc = SimpleDocTemplate(
            buffer, pagesize=(page_width, 500 * mm),
            topMargin=5 * mm, bottomMargin=5 * mm,
            leftMargin=3 * mm, rightMargin=3 * mm
        )
    else:
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch, rightMargin=0.75 * inch
        )

    story = []

    company = _get_company_info()
    story.append(Paragraph(company["name"], styles['title']))
    story.append(Paragraph('Return Receipt', styles['subtitle']))
    _add_company_details(story, company)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=12))

    # Return info
    created_at = return_order.created_at.strftime('%Y-%m-%d %H:%M') if return_order.created_at else 'N/A'
    party_name = return_order.party.name if return_order.party else 'N/A'
    invoice_ref = 'N/A'
    if return_order.invoice:
        invoice_ref = return_order.invoice.invoice_number
    elif return_order.purchase_invoice:
        invoice_ref = return_order.purchase_invoice.invoice_number

    info_rows = [
        ['Return #:', return_order.return_number, 'Date:', created_at],
        ['Return Type:', return_order.get_return_type_display(), 'Status:', return_order.status],
        ['Party:', party_name, 'Invoice:', invoice_ref],
    ]
    story.append(_build_info_table(info_rows))
    story.append(Spacer(1, 12))

    # Reason
    if return_order.reason:
        story.append(Paragraph('Reason', styles['heading']))
        story.append(Paragraph(return_order.reason, styles['normal']))
        story.append(Spacer(1, 6))

    # Return items
    story.append(Paragraph('Return Items', styles['heading']))

    item_rows = []
    for i, item in enumerate(return_order.items.all(), 1):
        line_total = getattr(item, 'line_total', item.total_price) if hasattr(item, 'total_price') else getattr(item, 'line_total', Decimal('0.00'))
        item_rows.append([
            str(i),
            item.product.name if item.product else 'N/A',
            item.batch.batch_number if item.batch else 'N/A',
            str(item.return_quantity),
            f"{item.unit_price:.2f}",
            f"{item.discount_amount:.2f}",
            f"{item.tax_amount:.2f}",
            f"{line_total:.2f}",
        ])

    total_row = ['', '', '', '', '', '', 'Total:', f"{return_order.total_amount:.2f}"]
    story.append(_build_items_table(
        ['#', 'Product', 'Batch', 'Qty', 'Unit Price', 'Discount', 'Tax', 'Total'],
        item_rows,
        col_widths=[30, 150, 80, 50, 70, 60, 50, 70],
        total_row=total_row,
    ))
    story.append(Spacer(1, 12))

    # Approval info
    if return_order.approved_by:
        story.append(Paragraph('Approval Information', styles['heading']))
        approval_rows = [
            ['Approved By:', return_order.approved_by.name],
            ['Approved At:', return_order.approved_at.strftime('%Y-%m-%d %H:%M') if return_order.approved_at else 'N/A'],
        ]
        if return_order.voided_at:
            approval_rows.append(['Voided At:', return_order.voided_at.strftime('%Y-%m-%d %H:%M')])
            approval_rows.append(['Void Reason:', return_order.void_reason or 'N/A'])
        story.append(_build_info_table(approval_rows, col_widths=[100, 400]))
        story.append(Spacer(1, 12))

    # QR/barcode placeholders
    if mode == 'a4':
        story.append(_build_info_table([
            ['QR Code:', '[Scan for verification]', 'Return #:', return_order.return_number],
        ], col_widths=[80, 180, 70, 170]))
        story.append(Spacer(1, 6))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        f'Generated on {date.today()} | {company["name"]} | Return {return_order.return_number}',
        styles['footer']
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_customer_statement_pdf(customer, statements_data, generated_by=''):
    """Generate a customer account statement PDF.

    Args:
        customer: Customer model instance
        statements_data: dict with invoices, payments, balance info
        generated_by: User who generated the statement

    Returns:
        bytes: PDF content
    """
    from datetime import date
    from decimal import Decimal
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
    heading_style = ParagraphStyle('Head', parent=styles['Heading2'], fontSize=11, spaceBefore=10, spaceAfter=4)
    normal_style = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=9, spaceAfter=2)
    footer_style = ParagraphStyle('Foot', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#999999'))
    right_style = ParagraphStyle('Right', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

    story = []

    company = _get_company_info()
    story.append(Paragraph(company["name"], title_style))
    story.append(Paragraph('Customer Account Statement', subtitle_style))
    _add_company_details(story, company)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=10))

    info_rows = [
        ['Customer:', customer.name, 'Code:', customer.code],
        ['Balance:', f"{customer.balance:.2f}", 'Credit Limit:', f"{customer.credit_limit:.2f}" if customer.credit_limit else 'N/A'],
        ['Statement Date:', str(date.today()), 'Generated By:', generated_by or 'System'],
    ]
    story.append(Table(info_rows, colWidths=[80, 200, 80, 140]).setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])))
    story.append(Spacer(1, 10))

    invoices = statements_data.get('invoices', [])
    if invoices:
        story.append(Paragraph('Outstanding Invoices', heading_style))
        inv_rows = [['#', 'Invoice #', 'Date', 'Due Date', 'Total', 'Paid', 'Balance']]
        for i, inv in enumerate(invoices, 1):
            inv_rows.append([
                str(i), inv.get('invoice_number', ''), str(inv.get('invoice_date', '')),
                str(inv.get('due_date', '')), f"{inv.get('total', 0):.2f}",
                f"{inv.get('paid', 0):.2f}", f"{inv.get('balance', 0):.2f}"
            ])
        inv_table = Table(inv_rows, colWidths=[30, 90, 70, 70, 80, 80, 80])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(inv_table)
        story.append(Spacer(1, 8))

    payments = statements_data.get('payments', [])
    if payments:
        story.append(Paragraph('Recent Payments', heading_style))
        pay_rows = [['#', 'Reference', 'Date', 'Method', 'Amount']]
        for i, pay in enumerate(payments, 1):
            pay_rows.append([
                str(i), pay.get('reference', ''), str(pay.get('date', '')),
                pay.get('method', ''), f"{pay.get('amount', 0):.2f}"
            ])
        pay_table = Table(pay_rows, colWidths=[30, 120, 80, 100, 100])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(pay_table)
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        f'Generated on {date.today()} | {company["name"]} | Customer: {customer.name}',
        footer_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_supplier_statement_pdf(supplier, statements_data, generated_by=''):
    """Generate a supplier account statement PDF."""
    from datetime import date
    from decimal import Decimal
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
    heading_style = ParagraphStyle('Head', parent=styles['Heading2'], fontSize=11, spaceBefore=10, spaceAfter=4)
    normal_style = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=9, spaceAfter=2)
    footer_style = ParagraphStyle('Foot', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#999999'))

    story = []

    company = _get_company_info()
    story.append(Paragraph(company["name"], title_style))
    story.append(Paragraph('Supplier Account Statement', subtitle_style))
    _add_company_details(story, company)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=10))

    info_rows = [
        ['Supplier:', supplier.name, 'Code:', supplier.code],
        ['Balance:', f"{supplier.balance:.2f}", 'Statement Date:', str(date.today())],
        ['Generated By:', generated_by or 'System', '', ''],
    ]
    story.append(Table(info_rows, colWidths=[80, 200, 100, 120]).setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])))
    story.append(Spacer(1, 10))

    invoices = statements_data.get('invoices', [])
    if invoices:
        story.append(Paragraph('Outstanding Invoices', heading_style))
        inv_rows = [['#', 'Invoice #', 'Date', 'Due Date', 'Total', 'Paid', 'Balance']]
        for i, inv in enumerate(invoices, 1):
            inv_rows.append([
                str(i), inv.get('invoice_number', ''), str(inv.get('invoice_date', '')),
                str(inv.get('due_date', '')), f"{inv.get('total', 0):.2f}",
                f"{inv.get('paid', 0):.2f}", f"{inv.get('balance', 0):.2f}"
            ])
        inv_table = Table(inv_rows, colWidths=[30, 90, 70, 70, 80, 80, 80])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(inv_table)
        story.append(Spacer(1, 8))

    payments = statements_data.get('payments', [])
    if payments:
        story.append(Paragraph('Recent Payments', heading_style))
        pay_rows = [['#', 'Reference', 'Date', 'Method', 'Amount']]
        for i, pay in enumerate(payments, 1):
            pay_rows.append([
                str(i), pay.get('reference', ''), str(pay.get('date', '')),
                pay.get('method', ''), f"{pay.get('amount', 0):.2f}"
            ])
        pay_table = Table(pay_rows, colWidths=[30, 120, 80, 100, 100])
        pay_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(pay_table)
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        f'Generated on {date.today()} | {company["name"]} | Supplier: {supplier.name}',
        footer_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_period_closing_summary_pdf(period, closing_data, generated_by=''):
    """Generate a fiscal period closing summary PDF."""
    from datetime import date
    from decimal import Decimal
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
    heading_style = ParagraphStyle('Head', parent=styles['Heading2'], fontSize=11, spaceBefore=10, spaceAfter=4)
    normal_style = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=9, spaceAfter=2)
    footer_style = ParagraphStyle('Foot', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#999999'))
    green_style = ParagraphStyle('Green', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#228B22'))
    red_style = ParagraphStyle('Red', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#CC0000'))

    story = []

    company = _get_company_info()
    story.append(Paragraph(company["name"], title_style))
    story.append(Paragraph('Fiscal Period Closing Summary', subtitle_style))
    _add_company_details(story, company)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=10))

    info_rows = [
        ['Period:', period.name, 'Code:', period.code],
        ['Start Date:', str(period.start_date), 'End Date:', str(period.end_date)],
        ['Status:', period.status, 'Generated By:', generated_by or 'System'],
    ]
    story.append(Table(info_rows, colWidths=[80, 200, 80, 140]).setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])))
    story.append(Spacer(1, 10))

    summary = closing_data.get('summary', {})
    story.append(Paragraph('Period Summary', heading_style))
    summary_rows = [
        ['Total Journal Entries:', str(summary.get('total_journal_entries', 0))],
        ['Posted Entries:', str(summary.get('posted_journal_entries', 0))],
        ['Total Debits:', summary.get('total_debits', '0.00')],
        ['Total Credits:', summary.get('total_credits', '0.00')],
    ]
    story.append(Table(summary_rows, colWidths=[150, 350]).setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
    ])))
    story.append(Spacer(1, 8))

    blockers = closing_data.get('blockers', [])
    if blockers:
        story.append(Paragraph('Blockers', heading_style))
        for b in blockers:
            story.append(Paragraph(f"  • {b.get('message', '')}", red_style))
        story.append(Spacer(1, 4))

    warnings = closing_data.get('warnings', [])
    if warnings:
        story.append(Paragraph('Warnings', heading_style))
        for w in warnings:
            story.append(Paragraph(f"  • {w.get('message', '')}", normal_style))
        story.append(Spacer(1, 4))

    if not blockers and not warnings:
        story.append(Paragraph('No blockers or warnings — period is clean.', green_style))
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        f'Generated on {date.today()} | {company["name"]} | Period: {period.code}',
        footer_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_reversal_audit_pdf(entry, impact_data, generated_by=''):
    """Generate a reversal audit trail PDF."""
    from datetime import date
    from decimal import Decimal
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
    heading_style = ParagraphStyle('Head', parent=styles['Heading2'], fontSize=11, spaceBefore=10, spaceAfter=4)
    normal_style = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=9, spaceAfter=2)
    footer_style = ParagraphStyle('Foot', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#999999'))
    red_style = ParagraphStyle('Red', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#CC0000'))
    green_style = ParagraphStyle('Green', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#228B22'))

    story = []

    company = _get_company_info()
    story.append(Paragraph(company["name"], title_style))
    story.append(Paragraph('Reversal Audit Report', subtitle_style))
    _add_company_details(story, company)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=10))

    info_rows = [
        ['Entry #:', entry.entry_number, 'Type:', entry.entry_type],
        ['Date:', str(entry.entry_date), 'Status:', 'Posted' if entry.is_posted else 'Draft'],
        ['Generated By:', generated_by or 'System', 'Date:', str(date.today())],
    ]
    story.append(Table(info_rows, colWidths=[80, 200, 80, 140]).setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])))
    story.append(Spacer(1, 10))

    story.append(Paragraph('Entry Description', heading_style))
    story.append(Paragraph(entry.description, normal_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Affected Accounts', heading_style))
    accounts = impact_data.get('affected_accounts', [])
    if accounts:
        acc_rows = [['Code', 'Name', 'Type', 'Debit', 'Credit', 'Rev Debit', 'Rev Credit']]
        for acc in accounts:
            acc_rows.append([
                acc.get('account_code', ''), acc.get('account_name', ''),
                acc.get('account_type', ''), acc.get('current_debit', '0'),
                acc.get('current_credit', '0'), acc.get('reversal_debit', '0'),
                acc.get('reversal_credit', '0'),
            ])
        acc_table = Table(acc_rows, colWidths=[50, 100, 70, 70, 70, 70, 70])
        acc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        story.append(acc_table)
        story.append(Spacer(1, 8))

    chain = impact_data.get('reversal_chain', [])
    if chain:
        story.append(Paragraph('Reversal Chain', heading_style))
        for node in chain:
            story.append(Paragraph(
                f"  → {node.get('entry_number', '')} ({node.get('entry_type', '')}) - {node.get('entry_date', '')}",
                normal_style
            ))
        story.append(Spacer(1, 8))

    blockers = impact_data.get('blockers', [])
    if blockers:
        story.append(Paragraph('Safety Blockers', heading_style))
        for b in blockers:
            story.append(Paragraph(f"  ✗ {b.get('message', '')}", red_style))
        story.append(Spacer(1, 4))

    if impact_data.get('is_safe', True):
        story.append(Paragraph('Reversal is SAFE — no blockers detected.', green_style))
        story.append(Spacer(1, 8))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
    story.append(Paragraph(
        f'Generated on {date.today()} | {company["name"]} | Entry: {entry.entry_number}',
        footer_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def pdf_response(pdf_bytes: bytes, filename: str) -> HttpResponse:
    """Create an HttpResponse with PDF content."""
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
