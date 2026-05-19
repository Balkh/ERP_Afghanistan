"""Insurance API Views."""
from decimal import Decimal
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import InsuranceProvider, InsurancePolicy, Claim, ClaimApproval
from .serializers import (
    InsuranceProviderSerializer, InsurancePolicySerializer,
    ClaimListSerializer, ClaimDetailSerializer, ClaimCreateSerializer,
    ClaimApprovalSerializer
)
from security.permissions import RoleBasedPermission
from core.multitenant.views import CompanyScopedViewSetMixin
from core.multitenant.context import TenantContext


class InsuranceProviderViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = InsuranceProvider.objects.all()
    serializer_class = InsuranceProviderSerializer
    permission_classes = [RoleBasedPermission]


class InsurancePolicyViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = InsurancePolicy.objects.select_related('provider', 'customer')
    serializer_class = InsurancePolicySerializer
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        provider_id = self.request.query_params.get('provider_id')
        if provider_id:
            qs = qs.filter(provider_id=provider_id)
        active = self.request.query_params.get('active')
        if active:
            qs = qs.filter(is_active=(active.lower() == 'true'))
        return qs


class ClaimViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Claim.objects.select_related(
        'policy__provider', 'policy__customer', 'invoice'
    ).prefetch_related('items__product', 'approvals')
    permission_classes = [RoleBasedPermission]

    def get_serializer_class(self):
        if self.action == 'create':
            return ClaimCreateSerializer
        if self.action in ('retrieve', 'detail'):
            return ClaimDetailSerializer
        return ClaimListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        policy_id = self.request.query_params.get('policy_id')
        if policy_id:
            qs = qs.filter(policy_id=policy_id)
        invoice_id = self.request.query_params.get('invoice_id')
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        return qs.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        claim = self.get_object()
        if claim.status != 'DRAFT':
            return Response({'error': 'Only draft claims can be submitted.'},
                            status=status.HTTP_400_BAD_REQUEST)
        claim.status = 'SUBMITTED'
        claim.submitted_at = timezone.now()
        claim.save(update_fields=['status', 'submitted_at'])
        ClaimApproval.objects.create(
            claim=claim, action='SUBMIT',
            notes=request.data.get('notes', ''),
        )
        return Response(ClaimDetailSerializer(claim).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        claim = self.get_object()
        if claim.status not in ('SUBMITTED', 'IN_REVIEW', 'PARTIALLY_APPROVED'):
            return Response({'error': 'Claim is not in a submittable state.'},
                            status=status.HTTP_400_BAD_REQUEST)
        covered = request.data.get('covered_amount')
        if covered is not None:
            claim.covered_amount = Decimal(str(covered))
            claim.patient_amount = claim.total_amount - claim.covered_amount - claim.deductible_applied
        claim.status = 'APPROVED'
        claim.approved_at = timezone.now()
        claim.save()
        ClaimApproval.objects.create(
            claim=claim, action='APPROVE',
            notes=request.data.get('notes', ''),
        )
        from .services import InsuranceAccountingService
        InsuranceAccountingService.create_claim_receivable_entry(claim)
        return Response(ClaimDetailSerializer(claim).data)

    @action(detail=True, methods=['post'])
    def partial_approve(self, request, pk=None):
        claim = self.get_object()
        if claim.status not in ('SUBMITTED', 'IN_REVIEW'):
            return Response({'error': 'Claim is not in a submittable state.'},
                            status=status.HTTP_400_BAD_REQUEST)
        covered = request.data.get('covered_amount')
        if covered is not None:
            claim.covered_amount = Decimal(str(covered))
            claim.patient_amount = claim.total_amount - claim.covered_amount - claim.deductible_applied
        claim.status = 'PARTIALLY_APPROVED'
        claim.save()
        ClaimApproval.objects.create(
            claim=claim, action='PARTIAL_APPROVE',
            notes=request.data.get('notes', ''),
        )
        return Response(ClaimDetailSerializer(claim).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        claim = self.get_object()
        if claim.status not in ('SUBMITTED', 'IN_REVIEW', 'PARTIALLY_APPROVED'):
            return Response({'error': 'Claim is not in a rejectable state.'},
                            status=status.HTTP_400_BAD_REQUEST)
        claim.status = 'REJECTED'
        claim.rejection_reason = request.data.get('reason', '')
        claim.save(update_fields=['status', 'rejection_reason'])
        ClaimApproval.objects.create(
            claim=claim, action='REJECT',
            notes=request.data.get('notes', ''),
        )
        return Response(ClaimDetailSerializer(claim).data)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        claim = self.get_object()
        if claim.status != 'APPROVED':
            return Response({'error': 'Only approved claims can be marked as paid.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from .services import InsuranceAccountingService
        InsuranceAccountingService.record_claim_payment(claim)
        ClaimApproval.objects.create(
            claim=claim, action='PAY',
            notes=request.data.get('notes', ''),
        )
        return Response(ClaimDetailSerializer(claim).data)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        claim = self.get_object()
        if claim.status in ('PAID', 'VOIDED'):
            return Response({'error': 'Cannot void a paid or already voided claim.'},
                            status=status.HTTP_400_BAD_REQUEST)
        claim.status = 'VOIDED'
        claim.save(update_fields=['status'])
        ClaimApproval.objects.create(
            claim=claim, action='VOID',
            notes=request.data.get('notes', ''),
        )
        return Response(ClaimDetailSerializer(claim).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self.get_queryset()
        total = qs.count()
        return Response({
            'total': total,
            'draft': qs.filter(status='DRAFT').count(),
            'submitted': qs.filter(status='SUBMITTED').count(),
            'approved': qs.filter(status='APPROVED').count(),
            'paid': qs.filter(status='PAID').count(),
            'rejected': qs.filter(status='REJECTED').count(),
            'total_covered': sum(c.covered_amount for c in qs.filter(status__in=['APPROVED', 'PAID'])),
        })
