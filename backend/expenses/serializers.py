from rest_framework import serializers
from .models import Expense

class ExpenseSerializer(serializers.ModelSerializer):
    expense_account_name = serializers.ReadOnlyField(source='expense_account.name')
    payment_account_name = serializers.ReadOnlyField(source='payment_account.name')
    
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ('expense_number', 'journal_entry', 'company')
