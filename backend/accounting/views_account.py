from decimal import Decimal
from datetime import date
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from core.view_logging import log_business_event
from core.multitenant.views import CompanyScopedViewSetMixin
from core.multitenant.context import TenantContext
from accounting.models import Account, JournalEntry, JournalEntryLine, JournalEventLog
from accounting.serializers import (
    AccountSerializer,
    AccountTreeSerializer,
    JournalEntrySerializer,
    JournalEntryLineSerializer,
    JournalEventLogSerializer,
)
from accounting.services.account_hierarchy import AccountHierarchyService
from accounting.services.financial_reports import FinancialReportEngine
from accounting.services.report_exporter import ReportExporter
from accounting.services.reconciliation import AccountingReconciliationService
from security.permissions import RoleBasedPermission

# AllowAny retained for read-only utility endpoints (calculate-invoice, convert-currency, etc.)


class JournalEventLogViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Journal Event Logs (audit trail).
    Read-only in practice - events are created by the system.
    """
    queryset = JournalEventLog.objects.all()
    serializer_class = JournalEventLogSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['entry', 'event_type', 'user']
    search_fields = ['entry__entry_number', 'reference', 'notes']
    ordering_fields = ['timestamp', 'event_type']
    ordering = ['-timestamp']


class AccountViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD API for Chart of Accounts management.
    """
    queryset = Account.objects.filter(is_active=True)
    serializer_class = AccountSerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'account_category', 'is_active', 'is_system', 'parent']
    search_fields = ['code', 'name', 'description']
    ordering_fields = ['code', 'name', 'account_type', 'balance', 'created_at']
    ordering = ['code']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = Account.objects.all()
        return queryset

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get complete account hierarchy as a tree."""
        tree = AccountHierarchyService.get_account_tree()
        return Response(tree)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get accounts filtered by type."""
        account_type = request.query_params.get('type')
        if not account_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        accounts = AccountHierarchyService.get_accounts_by_type(account_type)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def leaf_accounts(self, request):
        """Get all leaf accounts (can have journal entries)."""
        accounts = AccountHierarchyService.get_leaf_accounts()
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """Get direct children of an account."""
        include_inactive = request.query_params.get('include_inactive', 'false') == 'true'
        children = AccountHierarchyService.get_children(pk, include_inactive)
        serializer = self.get_serializer(children, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def descendants(self, request, pk=None):
        """Get all descendants of an account."""
        include_inactive = request.query_params.get('include_inactive', 'false') == 'true'
        descendants = AccountHierarchyService.get_descendants(pk, include_inactive)
        serializer = self.get_serializer(descendants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def ancestors(self, request, pk=None):
        """Get all ancestors of an account."""
        ancestors = AccountHierarchyService.get_ancestors(pk)
        serializer = self.get_serializer(ancestors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get account balance, optionally including children."""
        include_children = request.query_params.get('include_children', 'true') == 'true'
        balance = AccountHierarchyService.get_account_balance(pk, include_children)
        
        try:
            account = Account.objects.get(id=pk)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found'}, status=404)
        
        return Response({
            'account_id': account.id,
            'account_code': account.code,
            'account_name': account.name,
            'own_balance': account.balance,
            'total_balance': balance if include_children else account.balance,
            'include_children': include_children,
        })

    @action(detail=False, methods=['post'])
    def initialize_chart(self, request):
        """Initialize the default chart of accounts."""
        created = AccountHierarchyService.initialize_default_chart()
        return Response({
            'message': f'Created {len(created)} accounts',
            'created_accounts': [
                {'code': acc.code, 'name': acc.name}
                for acc in created
            ]
        })

    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """Generate trial balance report."""
        # Handle both DRF Request (query_params) and plain Django Request (GET)
        if hasattr(request, 'query_params'):
            as_of = request.query_params.get('as_of_date')
            include_zero = request.query_params.get('include_zero', 'false') == 'true'
            fmt = request.query_params.get('format') or request.parser_context.get('kwargs', {}).get('format', 'json')
        else:
            as_of = request.GET.get('as_of_date')
            include_zero = request.GET.get('include_zero', 'false') == 'true'
            fmt = request.GET.get('format', 'json')
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_trial_balance(as_of_date, include_zero, company_id)
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'trial_balance')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'trial_balance')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def balance_sheet(self, request):
        """Generate balance sheet report."""
        as_of = request.query_params.get('as_of_date')
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_balance_sheet(as_of_date, company_id=company_id)
        fmt = request.query_params.get('format') or request.parser_context.get('kwargs', {}).get('format', 'json')
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'balance_sheet')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'balance_sheet')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def income_statement(self, request):
        """Generate income statement report."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        compare_start = request.query_params.get('compare_start_date')
        compare_end = request.query_params.get('compare_end_date')
        group = request.query_params.get('group_by_category', 'true') == 'true'
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_profit_and_loss(
            start_date, end_date,
            compare_start=date.fromisoformat(compare_start) if compare_start else None,
            compare_end=date.fromisoformat(compare_end) if compare_end else None,
            group_by_category=group,
            company_id=company_id
        )
        fmt = request.query_params.get('format') or request.parser_context.get('kwargs', {}).get('format', 'json')
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'profit_loss')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'profit_loss')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def cash_flow(self, request):
        """Generate cash flow statement."""
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')
        if not start or not end:
            return Response(
                {'error': 'start_date and end_date parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_cash_flow_statement(start_date, end_date, company_id)
        fmt = request.query_params.get('format') or request.parser_context.get('kwargs', {}).get('format', 'json')
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'cash_flow')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'cash_flow')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def account_summary(self, request):
        """Get summary of all account balances by type."""
        as_of = request.query_params.get('as_of_date')
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
        company_id = TenantContext.get_company_id()
        summary = FinancialReportEngine.get_account_summary(as_of_date, company_id)
        return Response(summary)

    @action(detail=False, methods=['get'])
    def ledger(self, request):
        """Get ledger for a specific account."""
        # Handle both DRF Request (query_params) and plain Django Request (GET)
        if hasattr(request, 'query_params'):
            account_id = request.query_params.get('account_id')
            start = request.query_params.get('start_date')
            end = request.query_params.get('end_date')
            fmt = request.query_params.get('format', 'json')
        else:
            account_id = request.GET.get('account_id')
            start = request.GET.get('start_date')
            end = request.GET.get('end_date')
            fmt = request.GET.get('format', 'json')
        if not account_id:
            return Response(
                {'error': 'account_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_account_ledger(
            account_id,
            start_date=date.fromisoformat(start) if start else None,
            end_date=date.fromisoformat(end) if end else None,
            company_id=company_id
        )
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'ledger')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'ledger')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def ar_aging(self, request):
        """Generate Accounts Receivable aging report."""
        as_of = request.query_params.get('as_of_date')
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_ar_aging(as_of_date, company_id=company_id)
        fmt = request.query_params.get('format', 'json')
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'ar_aging')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'ar_aging')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def ap_aging(self, request):
        """Generate Accounts Payable aging report."""
        as_of = request.query_params.get('as_of_date')
        as_of_date = date.fromisoformat(as_of) if as_of else date.today()
        company_id = TenantContext.get_company_id()
        report = FinancialReportEngine.get_ap_aging(as_of_date, company_id=company_id)
        fmt = request.query_params.get('format', 'json')
        if fmt == 'csv':
            csv_data = ReportExporter.to_csv(report, 'ap_aging')
            return HttpResponse(csv_data, content_type='text/csv')
        elif fmt == 'text':
            text = ReportExporter.to_text(report, 'ap_aging')
            return HttpResponse(text, content_type='text/plain')
        return Response(report)

    @action(detail=False, methods=['get'])
    def reconciliation(self, request):
        """
        Run full accounting reconciliation checks.
        Verifies integrity between operational data and accounting records.
        """
        result = AccountingReconciliationService.full_reconciliation()
        return Response(result)

    @action(detail=False, methods=['get'])
    def inventory_valuation(self, request):
        """Get inventory valuation with accounting reconciliation."""
        from inventory.views import StockMovementViewSet
        from inventory.service import StockIntegrationService
        from accounting.services.inventory_accounting import InventoryAccountingService

        warehouse_id = request.query_params.get('warehouse_id')
        as_of_date = request.query_params.get('as_of_date')

        # Get stock levels
        stock_levels = StockIntegrationService.get_stock_levels(
            include_expired=False
        )

        total_value = Decimal('0.00')
        for item in stock_levels:
            total_value += item.get('remaining_quantity', Decimal('0'))

        return Response({
            'total_value': total_value,
            'items': stock_levels,
        })

    def perform_destroy(self, instance):
        """Delete account with validation."""
        try:
            AccountHierarchyService.delete_account(instance.id)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class JournalEntryViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD API for Journal Entries.
    """
    queryset = JournalEntry.objects.filter(is_active=True)
    serializer_class = JournalEntrySerializer
    permission_classes = [RoleBasedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['entry_type', 'is_posted', 'is_active']
    search_fields = ['entry_number', 'description', 'reference']
    ordering_fields = ['entry_date', 'entry_number', 'created_at']
    ordering = ['-entry_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Use GET parameters (compatible with both Django and DRF Request)
        include_inactive = self.request.GET.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = JournalEntry.objects.all()
        return queryset

    @action(detail=True, methods=['post'])
    def post_entry(self, request, pk=None):
        """Post a journal entry (locks it from further editing)."""
        from accounting.services.journal_engine import JournalEngine
        result = JournalEngine.post_entry(pk)
        log_business_event(request, 'journal_entry.posted', {'entry_id': pk, 'success': result.get('success')})
        if result.get('success'):
            entry = JournalEntry.objects.get(id=pk)
            serializer = self.get_serializer(entry)
            return Response(serializer.data)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def unpost_entry(self, request, pk=None):
        """Unpost a journal entry (allows editing again)."""
        from accounting.services.journal_engine import JournalEngine
        result = JournalEngine.unpost_entry(pk)
        log_business_event(request, 'journal_entry.unposted', {'entry_id': pk, 'success': result.get('success')})
        if result.get('success'):
            entry = JournalEntry.objects.get(id=pk)
            serializer = self.get_serializer(entry)
            return Response(serializer.data)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reverse_entry(self, request, pk=None):
        """Reverse a posted journal entry."""
        from accounting.services.journal_engine import JournalEngine
        reason = request.data.get('reason', '')
        result = JournalEngine.reverse_entry(pk, reason=reason)
        log_business_event(request, 'journal_entry.reversed', {'entry_id': pk, 'reason': reason, 'success': result.get('success')})
        if result.get('success'):
            return Response(result)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def event_history(self, request, pk=None):
        """Get event history for a journal entry."""
        entry = self.get_object()
        events = JournalEventLog.objects.filter(entry=entry).order_by('-timestamp')
        serializer = JournalEventLogSerializer(events, many=True)
        return Response(serializer.data)


# Export API Views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import HttpResponse


@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def export_report(request):
    """Export report to various formats."""
    from accounting.services.export_engine import ExportEngine
    from core.models import Company
    from core.multitenant.context import TenantContext
    
    report_type = request.data.get('report_type')
    format = request.data.get('format', 'excel')
    report_data = request.data.get('report_data', {})
    
    if not report_type:
        return Response({'error': 'report_type is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get company name
    company_id = TenantContext.get_company_id()
    company_name = ''
    if company_id:
        company = Company.objects.filter(id=company_id).first()
        if company:
            company_name = company.name
    
    try:
        content = ExportEngine.export(report_data, report_type, format, company_name)
        
        # Set content type
        if format == 'excel':
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename = f'{report_type}_{date.today()}.xlsx'
        elif format == 'pdf':
            content_type = 'application/pdf'
            filename = f'{report_type}_{date.today()}.pdf'
        elif format == 'csv':
            content_type = 'text/csv'
            filename = f'{report_type}_{date.today()}.csv'
        else:
            content_type = 'application/json'
            filename = f'{report_type}_{date.today()}.json'
        
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Export failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Advanced Reports API
@api_view(['POST'])
@permission_classes([RoleBasedPermission])
def advanced_report(request):
    """Generate advanced analytical reports."""
    from accounting.services.advanced_reports import AdvancedReportsService, ReportBuilderService
    from datetime import datetime, timedelta
    
    report_name = request.data.get('report_name')
    report_type = request.data.get('report_type')
    
    if not report_type:
        return Response({'error': 'report_type is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Parse dates
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = date.today() - timedelta(days=30)
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = date.today()
        
        # Generate requested report
        if report_type == 'inventory_valuation':
            result = AdvancedReportsService.get_inventory_valuation(as_of_date=end_date)
        
        elif report_type == 'sales_by_product':
            result = AdvancedReportsService.get_sales_analysis(
                start_date, end_date, group_by='product')
        
        elif report_type == 'sales_by_customer':
            result = AdvancedReportsService.get_sales_analysis(
                start_date, end_date, group_by='customer')
        
        elif report_type == 'sales_by_category':
            result = AdvancedReportsService.get_sales_analysis(
                start_date, end_date, group_by='category')
        
        elif report_type == 'purchase_by_supplier':
            result = AdvancedReportsService.get_purchase_analysis(
                start_date, end_date, group_by='supplier')
        
        elif report_type == 'purchase_by_category':
            result = AdvancedReportsService.get_purchase_analysis(
                start_date, end_date, group_by='category')
        
        elif report_type == 'cash_book':
            account_code = request.data.get('account_code', '1100')
            result = AdvancedReportsService.get_cash_book(start_date, end_date, account_code)
        
        elif report_type == 'custom':
            # Custom report builder
            config = request.data.get('config', {})
            result = ReportBuilderService.build_custom_report(config)
        
        else:
            return Response({'error': f'Unknown report_type: {report_type}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result)
    
    except Exception as e:
        return Response({'error': f'Report generation failed: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([RoleBasedPermission])
def report_options(request):
    """Get available report types and options."""
    return Response({
        'report_types': [
            {'id': 'inventory_valuation', 'name': 'Inventory Valuation', 'category': 'inventory'},
            {'id': 'sales_by_product', 'name': 'Sales by Product', 'category': 'sales'},
            {'id': 'sales_by_customer', 'name': 'Sales by Customer', 'category': 'sales'},
            {'id': 'sales_by_category', 'name': 'Sales by Category', 'category': 'sales'},
            {'id': 'purchase_by_supplier', 'name': 'Purchase by Supplier', 'category': 'purchases'},
            {'id': 'purchase_by_category', 'name': 'Purchase by Category', 'category': 'purchases'},
            {'id': 'cash_book', 'name': 'Cash Book', 'category': 'accounting'},
            {'id': 'custom', 'name': 'Custom Report', 'category': 'custom'},
        ],
        'export_formats': ['csv', 'excel', 'pdf', 'json']
    })
