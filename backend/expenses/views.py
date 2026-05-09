from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.multitenant.views import CompanyScopedViewSetMixin
from .models import Expense
from .serializers import ExpenseSerializer

class ExpenseViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['expense_number', 'description', 'payee']
    filterset_fields = ['expense_account', 'payment_account', 'date']
