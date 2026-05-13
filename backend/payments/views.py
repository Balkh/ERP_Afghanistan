from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from payments.models import (
    PaymentMethod,
    PaymentAccount,
    FinancialTransaction,
    TransactionSettlement,
    SettlementTransaction,
)
from payments.serializers import (
    PaymentMethodSerializer,
    PaymentAccountSerializer,
    FinancialTransactionSerializer,
    TransactionSettlementSerializer,
    SettlementTransactionSerializer,
)
from payments.services import PaymentEngine


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """CRUD API for payment methods."""
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['method_type', 'is_active', 'is_default']
    search_fields = ['name', 'code', 'provider_name']
    ordering_fields = ['code', 'name', 'created_at']
    ordering = ['code']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = PaymentMethod.objects.all()
        return queryset

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get payment methods filtered by type."""
        method_type = request.query_params.get('type')
        if not method_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        methods = PaymentMethod.objects.filter(method_type=method_type, is_active=True)
        serializer = self.get_serializer(methods, many=True)
        return Response(serializer.data)


class PaymentAccountViewSet(viewsets.ModelViewSet):
    """CRUD API for payment accounts."""
    queryset = PaymentAccount.objects.filter(is_active=True)
    serializer_class = PaymentAccountSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'currency', 'is_active', 'is_default']
    search_fields = ['name', 'code', 'provider_name', 'account_number']
    ordering_fields = ['code', 'name', 'current_balance', 'created_at']
    ordering = ['code']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = PaymentAccount.objects.all()
        return queryset

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get payment accounts filtered by type."""
        account_type = request.query_params.get('type')
        if not account_type:
            return Response(
                {'error': 'type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        accounts = PaymentAccount.objects.filter(account_type=account_type, is_active=True)
        serializer = self.get_serializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get all transactions for a payment account."""
        account = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        txn_type = request.query_params.get('transaction_type')
        txn_status = request.query_params.get('status')

        result = PaymentEngine.get_account_transactions(
            account_code=account.code,
            start_date=start_date,
            end_date=end_date,
            transaction_type=txn_type,
            status=txn_status,
        )
        return Response(result)

    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get current balance for a payment account."""
        account = self.get_object()
        return Response({
            'account_id': str(account.id),
            'account_code': account.code,
            'account_name': account.name,
            'account_type': account.account_type,
            'currency': account.currency,
            'current_balance': str(account.current_balance),
            'min_balance': str(account.min_balance),
            'max_balance': str(account.max_balance),
            'below_minimum': account.current_balance < account.min_balance,
            'above_maximum': account.max_balance > 0 and account.current_balance > account.max_balance,
        })


class FinancialTransactionViewSet(viewsets.ModelViewSet):
    """CRUD API for financial transactions."""
    queryset = FinancialTransaction.objects.filter(is_active=True)
    serializer_class = FinancialTransactionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'status', 'payment_method', 'is_settled']
    search_fields = ['transaction_number', 'description', 'reference_number', 'party_name']
    ordering_fields = ['transaction_date', 'amount', 'created_at']
    ordering = ['-transaction_date']

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if include_inactive == 'true':
            queryset = FinancialTransaction.objects.all()
        return queryset

    @action(detail=False, methods=['post'])
    def receipt(self, request):
        """Process a receipt (money in)."""
        data = request.data
        result = PaymentEngine.process_receipt(
            payment_method_code=data.get('payment_method_code'),
            destination_account_code=data.get('destination_account_code'),
            amount=data.get('amount'),
            description=data.get('description', ''),
            currency=data.get('currency', 'AFN'),
            party_type=data.get('party_type', ''),
            party_id=data.get('party_id'),
            party_name=data.get('party_name', ''),
            invoice_type=data.get('invoice_type', ''),
            invoice_id=data.get('invoice_id'),
            reference_number=data.get('reference_number', ''),
            mobile_number=data.get('mobile_number', ''),
            exchange_rate=data.get('exchange_rate', '1.000000'),
            fee_override=data.get('fee'),
            hawala_dealer=data.get('hawala_dealer', ''),
            hawala_token=data.get('hawala_token', ''),
            hawala_origin=data.get('hawala_origin', ''),
            hawala_destination=data.get('hawala_destination', ''),
            value_date=data.get('value_date'),
            performed_by=data.get('performed_by', ''),
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def payment(self, request):
        """Process a payment (money out)."""
        data = request.data
        result = PaymentEngine.process_payment(
            payment_method_code=data.get('payment_method_code'),
            source_account_code=data.get('source_account_code'),
            amount=data.get('amount'),
            description=data.get('description', ''),
            currency=data.get('currency', 'AFN'),
            party_type=data.get('party_type', ''),
            party_id=data.get('party_id'),
            party_name=data.get('party_name', ''),
            invoice_type=data.get('invoice_type', ''),
            invoice_id=data.get('invoice_id'),
            reference_number=data.get('reference_number', ''),
            exchange_rate=data.get('exchange_rate', '1.000000'),
            fee_override=data.get('fee'),
            hawala_dealer=data.get('hawala_dealer', ''),
            hawala_token=data.get('hawala_token', ''),
            hawala_origin=data.get('hawala_origin', ''),
            hawala_destination=data.get('hawala_destination', ''),
            value_date=data.get('value_date'),
            performed_by=data.get('performed_by', ''),
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Process a transfer between accounts."""
        data = request.data
        result = PaymentEngine.process_transfer(
            source_account_code=data.get('source_account_code'),
            destination_account_code=data.get('destination_account_code'),
            amount=data.get('amount'),
            description=data.get('description', ''),
            currency=data.get('currency', 'AFN'),
            fee_override=data.get('fee'),
            reference_number=data.get('reference_number', ''),
            performed_by=data.get('performed_by', ''),
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def refund(self, request):
        """Process a refund for a previous transaction."""
        data = request.data
        result = PaymentEngine.process_refund(
            original_transaction_number=data.get('original_transaction_number'),
            refund_amount=data.get('refund_amount'),
            description=data.get('description', ''),
            performed_by=data.get('performed_by', ''),
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending transaction."""
        txn = self.get_object()
        if txn.status != 'PENDING':
            return Response(
                {'error': 'Only pending transactions can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        txn.status = 'CANCELLED'
        txn.save(update_fields=['status', 'updated_at'])
        serializer = self.get_serializer(txn)
        return Response(serializer.data)


class SettlementViewSet(viewsets.ModelViewSet):
    """CRUD API for transaction settlements."""
    queryset = TransactionSettlement.objects.all()
    serializer_class = TransactionSettlementSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['settlement_type', 'status', 'payment_account']
    search_fields = ['settlement_number', 'description', 'external_reference']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'])
    def create_settlement(self, request):
        """Create a new settlement batch."""
        data = request.data
        result = PaymentEngine.create_settlement(
            settlement_type=data.get('settlement_type'),
            payment_account_code=data.get('payment_account_code'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            expected_amount=data.get('expected_amount'),
            description=data.get('description', ''),
            external_reference=data.get('external_reference', ''),
            performed_by=data.get('performed_by', ''),
        )

        if result.get('success'):
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get all transactions in a settlement."""
        settlement = self.get_object()
        settlement_txns = settlement.transactions.all()
        serializer = SettlementTransactionSerializer(settlement_txns, many=True)
        return Response(serializer.data)


class PaymentDashboardViewSet(viewsets.ViewSet):
    """Dashboard endpoints for payment overview."""

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get payment dashboard overview."""
        from django.db.models import Sum, Count, Q

        total_receipts = FinancialTransaction.objects.filter(
            transaction_type='RECEIPT', status='COMPLETED', is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_payments = FinancialTransaction.objects.filter(
            transaction_type='PAYMENT', status='COMPLETED', is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_transfers = FinancialTransaction.objects.filter(
            transaction_type='TRANSFER', status='COMPLETED', is_active=True
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_fees = FinancialTransaction.objects.filter(
            status='COMPLETED', is_active=True
        ).aggregate(total=Sum('fee'))['total'] or 0

        unsettled_count = FinancialTransaction.objects.filter(
            is_settled=False, status='COMPLETED', is_active=True
        ).count()

        account_balances = []
        for account in PaymentAccount.objects.filter(is_active=True):
            account_balances.append({
                'code': account.code,
                'name': account.name,
                'type': account.account_type,
                'currency': account.currency,
                'balance': str(account.current_balance),
            })

        return Response({
            'total_receipts': str(total_receipts),
            'total_payments': str(total_payments),
            'total_transfers': str(total_transfers),
            'total_fees': str(total_fees),
            'net_position': str(total_receipts - total_payments),
            'unsettled_transactions': unsettled_count,
            'account_balances': account_balances,
        })
