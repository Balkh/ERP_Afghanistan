from rest_framework import viewsets
from core.multitenant.views import UnifiedEnterpriseViewSetMixin
from .models import Expense
from .serializers import ExpenseSerializer
from security.permissions import RoleBasedPermission

class ExpenseViewSet(UnifiedEnterpriseViewSetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [RoleBasedPermission]
    search_fields = ['expense_number', 'description', 'payee']
    filterset_fields = ['expense_account', 'payment_account', 'date']
