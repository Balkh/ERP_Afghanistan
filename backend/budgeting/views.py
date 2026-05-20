from decimal import Decimal
from django.db import models
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from accounting.models import Account
from budgeting.models import Budget, BudgetLine
from budgeting.serializers import (
    BudgetSerializer,
    BudgetListSerializer,
    BudgetLineSerializer,
    BudgetLineCreateSerializer,
    BudgetUpdateActualsSerializer,
)
from budgeting.services.budget_calculator import BudgetCalculator
from budgeting.services.budget_reporting import BudgetReportingService
from security.permissions import RoleBasedPermission


class BudgetViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Budget management.
    """
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fiscal_year', 'period_type', 'status']
    search_fields = ['name', 'notes']
    ordering_fields = ['fiscal_year', 'name', 'created_at']
    ordering = ['-fiscal_year', '-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BudgetListSerializer
        return BudgetSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create budget with lines."""
        data = request.data
        lines_data = data.pop('lines', [])

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()

        for line_data in lines_data:
            account_id = line_data.get('account_id')
            if account_id:
                try:
                    account = Account.objects.get(id=account_id)
                    BudgetLine.objects.create(
                        budget=budget,
                        account=account,
                        period=line_data.get('period', str(budget.fiscal_year)),
                        budgeted_amount=line_data.get('budgeted_amount', Decimal('0.00'))
                    )
                except Account.DoesNotExist:
                    pass

        budget = BudgetCalculator.update_budget_totals(budget)
        return Response(BudgetSerializer(budget).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Update budget and optionally lines."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data

        lines_data = data.pop('lines', None)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        budget = serializer.save()

        if lines_data is not None:
            budget.lines.all().delete()
            for line_data in lines_data:
                account_id = line_data.get('account_id')
                if account_id:
                    try:
                        account = Account.objects.get(id=account_id)
                        BudgetLine.objects.create(
                            budget=budget,
                            account=account,
                            period=line_data.get('period', str(budget.fiscal_year)),
                            budgeted_amount=line_data.get('budgeted_amount', Decimal('0.00'))
                        )
                    except Account.DoesNotExist:
                        pass

        budget = BudgetCalculator.update_budget_totals(budget)
        return Response(BudgetSerializer(budget).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a budget."""
        budget = self.get_object()

        if budget.status != 'DRAFT':
            return Response(
                {'error': 'Only draft budgets can be approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        budget.status = 'APPROVED'
        budget.approved_by = request.user.username if request.user else 'System'
        budget.approved_date = timezone.now().date()
        budget.save()

        return Response(BudgetSerializer(budget).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a budget."""
        budget = self.get_object()

        if budget.status != 'APPROVED':
            return Response(
                {'error': 'Only approved budgets can be closed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        budget.status = 'CLOSED'
        budget.save()
        return Response(BudgetSerializer(budget).data)

    @action(detail=True, methods=['post'])
    def update_actuals(self, request, pk=None):
        """Update actual amounts from posted journal entries.

        Budget actuals are derived from JournalEngine truth only.
        This endpoint triggers a recalculation — it does NOT allow manual overrides.
        """
        budget = self.get_object()
        budget.refresh_actuals()
        return Response(BudgetSerializer(budget).data)

    @action(detail=True, methods=['get'])
    def variance_report(self, request, pk=None):
        """Get budget vs actual variance report."""
        budget = self.get_object()
        period = request.query_params.get('period')

        report = BudgetReportingService.get_budget_variance_report(budget, period)
        return Response(report)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get all budgets summary."""
        budgets = Budget.objects.annotate(
            line_count=models.Count('lines')
        ).values('id', 'name', 'fiscal_year', 'status', 'total_budgeted', 'total_actual')

        results = []
        for b in budgets:
            variance = b['total_budgeted'] - b['total_actual']
            results.append({
                'id': b['id'],
                'name': b['name'],
                'fiscal_year': b['fiscal_year'],
                'status': b['status'],
                'total_budgeted': b['total_budgeted'],
                'total_actual': b['total_actual'],
                'variance': variance,
            })

        return Response(results)


class BudgetLineViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Budget Lines.
    """
    queryset = BudgetLine.objects.all()
    serializer_class = BudgetLineSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['budget', 'account', 'period']
    ordering_fields = ['period', 'budgeted_amount', 'actual_amount']
    ordering = ['period', 'account__code']

    def get_queryset(self):
        return super().get_queryset().select_related('account', 'budget')

    @action(detail=True, methods=['post'])
    def update_actual(self, request, pk=None):
        """Update actual amount from posted journal entries for a single line."""
        line = self.get_object()
        line.refresh_actual()
        return Response(BudgetLineSerializer(line).data)