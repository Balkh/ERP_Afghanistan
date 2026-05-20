"""Shared PDF generation utilities for Pharmacy ERP.

Provides reusable PDF rendering patterns for invoices, receipts, and reports.
All PDF generation uses ReportLab — no browser engines, no HTML rendering.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Optional

from django.http import HttpResponse


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

    story.append(Paragraph('Pharmacy ERP', styles['title']))
    story.append(Paragraph('Sales Invoice', styles['subtitle']))
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
        f'Generated on {date.today()} | Pharmacy ERP | Invoice {invoice.invoice_number}',
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

    story.append(Paragraph('Pharmacy ERP', styles['title']))
    story.append(Paragraph('Return Receipt', styles['subtitle']))
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
        f'Generated on {date.today()} | Pharmacy ERP | Return {return_order.return_number}',
        styles['footer']
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
