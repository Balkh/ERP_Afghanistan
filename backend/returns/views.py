"""Returns API Views."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Q
from .models import ReturnOrder, ReturnItem, ReconciliationEntry
from .serializers import (
    ReturnOrderSerializer, ReturnOrderCreateSerializer,
    ReturnItemSerializer, ReconciliationEntrySerializer
)


class ReturnOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Return Orders."""
    queryset = ReturnOrder.objects.select_related(
        'invoice', 'purchase_invoice', 'party', 'supplier', 'approved_by'
    ).prefetch_related('items', 'items__product', 'items__batch')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReturnOrderCreateSerializer
        return ReturnOrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
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
            'total_amount': queryset.aggregate(total=models.Sum('total_amount'))['total'] or 0,
        })


class ReconciliationEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for Reconciliation Entries."""
    queryset = ReconciliationEntry.objects.select_related(
        'invoice', 'return_order', 'accounting_entry', 'party', 'supplier',
        'company', 'fixed_by'
    )
    serializer_class = ReconciliationEntrySerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def mismatches(self, request):
        """Get all mismatched reconciliation entries."""
        queryset = self.get_queryset().filter(status='MISMATCHED')
        
        return Response(ReconciliationEntrySerializer(queryset, many=True).data)
    
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