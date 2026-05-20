"""Financial Truth Engine — Read-Only Derived Financial State.

Single source of truth for ALL financial state computations.
All balance values are DERIVED from invoices minus payments, NEVER from
stored balance fields. This eliminates dual-path inconsistency.

Usage:
    balance = FinancialTruthEngine.get_customer_balance(customer)
    summary = FinancialTruthEngine.get_customer_financial_summary(customer)
"""
from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone


class FinancialTruthEngine:
    """Read-only derived financial truth computations.
    
    Every method in this class is read-only — no writes, no mutations.
    Financial state is always derived from transactional data.
    """

    # Invoice statuses that contribute to outstanding balance
    CUSTOMER_BALANCE_STATUSES = ['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID', 'PAID']
    SUPPLIER_BALANCE_STATUSES = ['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID', 'PAID']

    @staticmethod
    def get_customer_balance(customer) -> Decimal:
        """Derive customer outstanding balance from transactions.
        
        Formula: sum(active invoices for CONFIRMED/DISPATCHED/PARTIAL_PAID/PAID)
                 - sum(all payments)
        
        Read-only — never writes to customer.balance.
        """
        from sales.models import SalesInvoice, CustomerPayment

        total_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=FinancialTruthEngine.CUSTOMER_BALANCE_STATUSES,
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        total_payments = CustomerPayment.objects.filter(
            customer=customer,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return total_invoices - total_payments

    @staticmethod
    def get_supplier_balance(supplier) -> Decimal:
        """Derive supplier outstanding balance from transactions.
        
        Formula: sum(active invoices for CONFIRMED/RECEIVED/PARTIAL_PAID/PAID)
                 - sum(all payments)
        
        Read-only — never writes to supplier.balance.
        """
        from purchases.models import PurchaseInvoice, SupplierPayment

        total_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=FinancialTruthEngine.SUPPLIER_BALANCE_STATUSES,
            is_active=True,
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        total_payments = SupplierPayment.objects.filter(
            supplier=supplier,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return total_invoices - total_payments

    @staticmethod
    def get_customer_available_credit(customer) -> Decimal:
        """Available credit = max(0, credit_limit - derived_balance)."""
        balance = FinancialTruthEngine.get_customer_balance(customer)
        return max(Decimal('0.00'), customer.credit_limit - balance)

    @staticmethod
    def get_customer_overdue_balance(customer, as_of=None) -> Decimal:
        """Sum of all invoice amounts past their due date for a customer."""
        from sales.models import SalesInvoice
        as_of = as_of or timezone.now().date()

        overdue_invoices = SalesInvoice.objects.filter(
            customer=customer,
            status__in=['CONFIRMED', 'DISPATCHED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lt=as_of,
        )

        total = overdue_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        paid = overdue_invoices.aggregate(
            total=Sum('paid_amount')
        )['total'] or Decimal('0.00')

        return total - paid

    @staticmethod
    def get_supplier_overdue_balance(supplier, as_of=None) -> Decimal:
        """Sum of all invoice amounts past their due date for a supplier."""
        from purchases.models import PurchaseInvoice
        as_of = as_of or timezone.now().date()

        overdue_invoices = PurchaseInvoice.objects.filter(
            supplier=supplier,
            status__in=['CONFIRMED', 'RECEIVED', 'PARTIAL_PAID'],
            is_active=True,
            due_date__lt=as_of,
        )

        total = overdue_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        paid = overdue_invoices.aggregate(
            total=Sum('paid_amount')
        )['total'] or Decimal('0.00')

        return total - paid

    @staticmethod
    def get_customer_financial_summary(customer) -> dict:
        """Full financial summary derived entirely from transactions.
        
        Returns a dict with all key financial metrics for a customer.
        No stored balance fields are used — everything is derived.
        """
        derived_balance = FinancialTruthEngine.get_customer_balance(customer)
        stored_balance = customer.balance

        return {
            'customer_id': str(customer.pk),
            'customer_name': customer.name,
            'derived_balance': derived_balance,
            'stored_balance': stored_balance,
            'balance_mismatch': abs(derived_balance - stored_balance) > Decimal('0.01'),
            'credit_limit': customer.credit_limit,
            'available_credit': max(Decimal('0.00'), customer.credit_limit - derived_balance),
            'credit_utilization_pct': float(
                (derived_balance / customer.credit_limit * 100)
                if customer.credit_limit > 0 else 0
            ),
            'overdue_balance': FinancialTruthEngine.get_customer_overdue_balance(customer),
            'status': customer.status,
        }

    @staticmethod
    def get_supplier_financial_summary(supplier) -> dict:
        """Full financial summary derived entirely from transactions for a supplier."""
        derived_balance = FinancialTruthEngine.get_supplier_balance(supplier)
        stored_balance = supplier.balance

        return {
            'supplier_id': str(supplier.pk),
            'supplier_name': supplier.name,
            'derived_balance': derived_balance,
            'stored_balance': stored_balance,
            'balance_mismatch': abs(derived_balance - stored_balance) > Decimal('0.01'),
            'credit_limit': supplier.credit_limit,
            'available_credit': max(Decimal('0.00'), supplier.credit_limit - derived_balance),
            'credit_utilization_pct': float(
                (derived_balance / supplier.credit_limit * 100)
                if supplier.credit_limit > 0 else 0
            ),
            'overdue_balance': FinancialTruthEngine.get_supplier_overdue_balance(supplier),
            'status': supplier.status,
        }
