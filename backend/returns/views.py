"""Returns API Views."""
import csv
import io
from datetime import date
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.http import HttpResponse
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
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

    # R-05: Block direct edits to lifecycle fields and direct delete on active returns.
    LIFECYCLE_FIELDS = {'status', 'approved_by', 'approved_at', 'journal_entry_id', 'credit_note_number'}

    def perform_update(self, serializer):
        for field in self.LIFECYCLE_FIELDS:
            if field in serializer.validated_data:
                raise ValidationError({
                    field: _('This field cannot be modified directly. Use the workflow actions (approve / complete / void).')
                })
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status not in ('PENDING', 'CANCELLED'):
            raise ValidationError({
                'detail': _('Only PENDING or CANCELLED returns can be deleted.')
            })
        instance.delete()

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
        mode = request.query_params.get('mode', 'a4')

        try:
            from core.pdf_generator import generate_return_receipt_pdf, pdf_response
            pdf_bytes = generate_return_receipt_pdf(return_order, mode=mode)
            filename = f"return_{return_order.return_number}.pdf"
            return pdf_response(pdf_bytes, filename)
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