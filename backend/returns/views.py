"""Returns API Views."""
import csv
import io
from datetime import date
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import models
from django.db.models import Q
from .models import ReturnOrder, ReturnItem, ReconciliationEntry
from .serializers import (
    ReturnOrderSerializer, ReturnOrderCreateSerializer,
    ReturnItemSerializer, ReconciliationEntrySerializer
)
from security.permissions import RoleBasedPermission
from core.multitenant.views import CompanyScopedViewSetMixin, UnifiedEnterpriseViewSetMixin
from core.multitenant.context import TenantContext


class ReturnOrderViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """ViewSet for Return Orders."""
    queryset = ReturnOrder.objects.select_related(
        'invoice', 'purchase_invoice', 'party', 'supplier', 'approved_by'
    ).prefetch_related('items', 'items__product', 'items__batch')
    permission_classes = [RoleBasedPermission]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReturnOrderCreateSerializer
        return ReturnOrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        company_id = TenantContext.get_company_id()
        if company_id and not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(invoice__company_id=company_id) |
                Q(purchase_invoice__company_id=company_id)
            )
        
        return_type = self.request.query_params.get('return_type')
        if return_type:
            queryset = queryset.filter(return_type=return_type)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        party_id = self.request.query_params.get('party_id')
        if party_id:
            queryset = queryset.filter(party_id=party_id)
        
        supplier_id = self.request.query_params.get('supplier_id')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(return_number__icontains=search) |
                Q(invoice__invoice_number__icontains=search) |
                Q(purchase_invoice__invoice_number__icontains=search) |
                Q(party__name__icontains=search) |
                Q(supplier__name__icontains=search)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a return order."""
        return_order = self.get_object()
        
        if return_order.status != 'PENDING':
            return Response(
                {'error': 'Only pending returns can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from hr.models import Employee
        employee_id = request.data.get('employee_id')
        
        if not employee_id:
            return Response(
                {'error': 'employee_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = Employee.objects.get(id=employee_id)
            return_order.approve(employee)
            return Response(ReturnOrderSerializer(return_order).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a return order."""
        return_order = self.get_object()
        
        if return_order.status != 'PENDING':
            return Response(
                {'error': 'Only pending returns can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notes = request.data.get('notes', '')
        return_order.status = 'REJECTED'
        return_order.notes = f"{return_order.notes}\n\nRejection Reason: {notes}".strip()
        return_order.save()
        
        return Response(ReturnOrderSerializer(return_order).data)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        """Void an approved return order."""
        return_order = self.get_object()
        
        if return_order.status != 'APPROVED':
            return Response(
                {'error': 'Only approved returns can be voided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from hr.models import Employee
        employee_id = request.data.get('employee_id')
        reason = request.data.get('reason', '')
        
        if not employee_id:
            return Response(
                {'error': 'employee_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not reason.strip():
            return Response(
                {'error': 'reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = Employee.objects.get(id=employee_id)
            return_order.void(employee, reason=reason.strip())
            return Response(ReturnOrderSerializer(return_order).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def by_invoice(self, request):
        """Look up returns by invoice barcode/number. POS integration hook."""
        invoice_ref = request.query_params.get('q', '')
        if not invoice_ref:
            return Response(
                {'error': 'q parameter required (invoice number or barcode)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.db.models import Q
        returns = self.get_queryset().filter(
            Q(invoice__invoice_number__icontains=invoice_ref) |
            Q(purchase_invoice__invoice_number__icontains=invoice_ref)
        )

        page = self.paginate_queryset(returns)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(returns, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get return order summary statistics."""
        queryset = self.get_queryset()
        
        return Response({
            'total': queryset.count(),
            'pending': queryset.filter(status='PENDING').count(),
            'approved': queryset.filter(status='APPROVED').count(),
            'rejected': queryset.filter(status='REJECTED').count(),
            'completed': queryset.filter(status='COMPLETED').count(),
            'voided': queryset.filter(status='VOIDED').count(),
            'total_amount': queryset.aggregate(total=models.Sum('total_amount'))['total'] or 0,
        })

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export return orders to CSV."""
        queryset = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="returns_{date.today()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Return #', 'Type', 'Invoice #', 'Party', 'Supplier',
            'Total Amount', 'Status', 'Reason', 'Created At',
            'Approved By', 'Voided At', 'Void Reason'
        ])
        
        for ro in queryset:
            writer.writerow([
                ro.return_number,
                ro.get_return_type_display(),
                ro.invoice.invoice_number if ro.invoice else '',
                ro.party.name if ro.party else '',
                ro.supplier.name if ro.supplier else '',
                str(ro.total_amount or Decimal('0.00')),
                ro.status,
                ro.reason or '',
                ro.created_at.strftime('%Y-%m-%d %H:%M') if ro.created_at else '',
                ro.approved_by.name if ro.approved_by else '',
                ro.voided_at.strftime('%Y-%m-%d %H:%M') if ro.voided_at else '',
                ro.void_reason or '',
            ])
        
        return response

    @action(detail=True, methods=['get'])
    def receipt_pdf(self, request, pk=None):
        """Generate PDF receipt for a return order."""
        return_order = self.get_object()
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=A4,
                topMargin=0.75*inch, bottomMargin=0.75*inch,
                leftMargin=0.75*inch, rightMargin=0.75*inch
            )
            story = []
            
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
            
            story.append(Paragraph('Pharmacy ERP', title_style))
            story.append(Paragraph('Return Receipt', subtitle_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=12))
            
            story.append(Paragraph('Return Information', heading_style))
            
            info_data = [
                ['Return Number:', return_order.return_number, 'Date:', return_order.created_at.strftime('%Y-%m-%d %H:%M') if return_order.created_at else 'N/A'],
                ['Return Type:', return_order.get_return_type_display(), 'Status:', return_order.status],
                ['Party:', return_order.party.name if return_order.party else 'N/A', 'Invoice:', return_order.invoice.invoice_number if return_order.invoice else (return_order.purchase_invoice.invoice_number if return_order.purchase_invoice else 'N/A')],
            ]
            info_table = Table(info_data, colWidths=[90, 180, 50, 180])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#666666')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 12))
            
            if return_order.reason:
                story.append(Paragraph('Reason', heading_style))
                story.append(Paragraph(return_order.reason, normal_style))
                story.append(Spacer(1, 6))
            
            story.append(Paragraph('Return Items', heading_style))
            
            items_data = [['#', 'Product', 'Batch', 'Qty', 'Unit Price', 'Discount', 'Tax', 'Total']]
            for i, item in enumerate(return_order.items.all(), 1):
                items_data.append([
                    str(i),
                    item.product.name if item.product else 'N/A',
                    item.batch.batch_number if item.batch else 'N/A',
                    str(item.return_quantity),
                    f"{item.unit_price:.2f}",
                    f"{item.discount_amount:.2f}",
                    f"{item.tax_amount:.2f}",
                    f"{item.line_total:.2f}",
                ])
            
            items_data.append(['', '', '', '', '', '', 'Total:', f"{return_order.total_amount:.2f}"])
            
            item_table = Table(items_data, colWidths=[30, 150, 80, 50, 70, 60, 50, 70])
            item_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 1), (-1, -2), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -2), 4),
            ]))
            story.append(item_table)
            story.append(Spacer(1, 18))
            
            if return_order.approved_by:
                story.append(Paragraph('Approval Information', heading_style))
                approval_data = [
                    ['Approved By:', return_order.approved_by.name],
                    ['Approved At:', return_order.approved_at.strftime('%Y-%m-%d %H:%M') if return_order.approved_at else 'N/A'],
                ]
                if return_order.voided_at:
                    approval_data.append(['Voided At:', return_order.voided_at.strftime('%Y-%m-%d %H:%M')])
                    approval_data.append(['Void Reason:', return_order.void_reason or 'N/A'])
                
                approval_table = Table(approval_data, colWidths=[100, 400])
                approval_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                story.append(approval_table)
            
            story.append(Spacer(1, 24))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6))
            footer_style = ParagraphStyle(
                'Footer', parent=styles['Normal'],
                fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#999999')
            )
            story.append(Paragraph(f'Generated on {date.today()} | Pharmacy ERP | Return Receipt', footer_style))
            
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="return_{return_order.return_number}.pdf"'
            return response
            
        except ImportError:
            return Response(
                {'error': 'ReportLab is not installed. Install with: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReconciliationEntryViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
    """ViewSet for Reconciliation Entries."""
    queryset = ReconciliationEntry.objects.select_related(
        'invoice', 'return_order', 'accounting_entry', 'party', 'supplier',
        'company', 'fixed_by'
    )
    serializer_class = ReconciliationEntrySerializer
    permission_classes = [RoleBasedPermission]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def mismatches(self, request):
        """Get all mismatched reconciliation entries."""
        queryset = self.get_queryset().filter(status='MISMATCHED')
        
        return Response(ReconciliationEntrySerializer(queryset, many=True).data)
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export reconciliation entries to CSV."""
        queryset = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reconciliation_{date.today()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Transaction Type', 'Invoice #', 'Return #', 'Party', 'Supplier',
            'Amount', 'Status', 'Notes', 'Fixed By', 'Fixed At'
        ])
        
        for entry in queryset:
            writer.writerow([
                str(entry.id)[:8],
                entry.transaction_type,
                entry.invoice.invoice_number if entry.invoice else '',
                entry.return_order.return_number if entry.return_order else '',
                entry.party.name if entry.party else '',
                entry.supplier.name if entry.supplier else '',
                str(entry.amount or Decimal('0.00')),
                entry.status,
                entry.notes or '',
                entry.fixed_by.name if entry.fixed_by else '',
                entry.fixed_at.strftime('%Y-%m-%d %H:%M') if entry.fixed_at else '',
            ])
        
        return response
    
    @action(detail=True, methods=['post'])
    def fix(self, request, pk=None):
        """Fix a reconciliation entry."""
        entry = self.get_object()
        
        from hr.models import Employee
        employee_id = request.data.get('employee_id')
        
        if not employee_id:
            return Response(
                {'error': 'employee_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = Employee.objects.get(id=employee_id)
            entry.status = 'FIXED'
            entry.fixed_by = employee
            entry.fix_notes = request.data.get('notes', '')
            entry.save()
            
            return Response(ReconciliationEntrySerializer(entry).data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )