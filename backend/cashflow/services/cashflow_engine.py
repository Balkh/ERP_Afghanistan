"""
Cash Flow Engine - Operational Cash Flow Management
Extends existing forecasting with operational tracking and statement generation.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List, Dict
from django.db.models import Sum, Q

from accounting.models import Account, JournalEntryLine, JournalEntry


class CashFlowCategory:
    """Cash flow activity categories (IAS 7 format)."""
    
    # Operating Activities
    CASH_RECEIPT_CUSTOMERS = 'CASH_RECEIPT_CUSTOMERS'
    CASH_PAYMENT_SUPPLIERS = 'CASH_PAYMENT_SUPPLIERS'
    CASH_PAYMENT_EMPLOYEES = 'CASH_PAYMENT_EMPLOYEES'
    CASH_PAYMENT_OPERATING = 'CASH_PAYMENT_OPERATING'
    TAX_PAID = 'TAX_PAID'
    OTHER_OPERATING = 'OTHER_OPERATING'
    
    # Investing Activities
    PURCHASE_FIXED_ASSETS = 'PURCHASE_FIXED_ASSETS'
    SALE_FIXED_ASSETS = 'SALE_FIXED_ASSETS'
    INVESTMENT_PURCHASE = 'INVESTMENT_PURCHASE'
    INVESTMENT_SALE = 'INVESTMENT_SALE'
    LOAN_ADVANCE = 'LOAN_ADVANCE'
    LOAN_RECEIPT = 'LOAN_RECEIPT'
    
    # Financing Activities
    EQUITY_INJECTION = 'EQUITY_INJECTION'
    DIVIDEND_PAID = 'DIVIDEND_PAID'
    LOAN_RECEIVED = 'LOAN_RECEIVED'
    LOAN_REPAYMENT = 'LOAN_REPAYMENT'


class CashFlowEngine:
    """
    Operational Cash Flow Engine.
    
    Provides:
    - Transaction classification (Operating/Investing/Financing)
    - Cash Flow Statement generation
    - Cash position tracking
    - Lightweight forecasting
    """

    # Account type mappings to cash flow categories
    ACCOUNT_CATEGORY_MAP = {
        # Operating - Cash In
        '1200': CashFlowCategory.CASH_RECEIPT_CUSTOMERS,  # Accounts Receivable
        '1300': CashFlowCategory.CASH_RECEIPT_CUSTOMERS,  # Inventory (not cash but working capital)
        
        # Operating - Cash Out
        '2100': CashFlowCategory.CASH_PAYMENT_SUPPLIERS,  # Accounts Payable
        '5000': CashFlowCategory.CASH_PAYMENT_OPERATING,  # Expenses
        '5100': CashFlowCategory.CASH_PAYMENT_OPERATING,  # COGS
        '2110': CashFlowCategory.TAX_PAID,  # Tax Payable
        
        # Cash Accounts
        '1010': None,  # Cash - tracked separately
        '1020': None,  # Bank - tracked separately
        
        # Investing
        '1500': CashFlowCategory.PURCHASE_FIXED_ASSETS,  # Fixed Assets
        '1600': CashFlowCategory.INVESTMENT_PURCHASE,  # Investments
        
        # Financing
        '2200': CashFlowCategory.LOAN_REPAYMENT,  # Loans Payable
        '3100': CashFlowCategory.EQUITY_INJECTION,  # Equity
        '3200': CashFlowCategory.DIVIDEND_PAID,  # Retained Earnings (dividends)
    }

    @staticmethod
    def classify_transaction(
        debit_account_code: str,
        credit_account_code: str,
        amount: Decimal
    ) -> Dict[str, str]:
        """
        Classify a transaction into cash flow categories.
        
        Returns:
            Dict with 'inflow_category' and 'outflow_category'
        """
        debit_cat = CashFlowEngine.ACCOUNT_CATEGORY_MAP.get(debit_account_code)
        credit_cat = CashFlowEngine.ACCOUNT_CATEGORY_MAP.get(credit_account_code)
        
        # Determine which is cash account
        cash_in = None
        cash_out = None
        
        if debit_account_code in ['1010', '1020', '1030', '1040']:  # Cash/Bank accounts
            cash_in = credit_cat
        if credit_account_code in ['1010', '1020', '1030', '1040']:
            cash_out = debit_cat
        
        return {
            'inflow_category': cash_in,
            'outflow_category': cash_out,
            'amount': amount
        }

    @staticmethod
    def get_cash_flow_statement(
        start_date: date,
        end_date: date,
        method: str = 'DIRECT'
    ) -> Dict:
        """
        Generate Cash Flow Statement (IAS 7 format).
        
        Args:
            start_date: Period start
            end_date: Period end
            method: 'DIRECT' or 'INDIRECT'
            
        Returns:
            Dict with Operating, Investing, Financing sections
        """
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        from payments.models import FinancialTransaction
        
        result = {
            'period': {'start': start_date, 'end': end_date},
            'operating': {'total': Decimal('0.00'), 'items': []},
            'investing': {'total': Decimal('0.00'), 'items': []},
            'financing': {'total': Decimal('0.00'), 'items': []},
            'net_change': Decimal('0.00'),
            'opening_cash': Decimal('0.00'),
            'closing_cash': Decimal('0.00')
        }
        
        # Calculate operating activities
        sales_receipts = FinancialTransaction.objects.filter(
            transaction_type='RECEIPT',
            status='COMPLETED',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        supplier_payments = FinancialTransaction.objects.filter(
            transaction_type='PAYMENT',
            status='COMPLETED',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        result['operating']['items'] = [
            {'category': 'Cash from Customers', 'amount': sales_receipts},
            {'category': 'Cash to Suppliers', 'amount': -supplier_payments},
        ]
        result['operating']['total'] = sales_receipts - supplier_payments
        
        # Calculate investing activities
        fixed_asset_purchases = JournalEntryLine.objects.filter(
            account__code__in=['1500', '1600'],
            entry__is_posted=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
            debit__gt=0
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        
        result['investing']['items'] = [
            {'category': 'Purchase of Fixed Assets', 'amount': -fixed_asset_purchases},
        ]
        result['investing']['total'] = -fixed_asset_purchases
        
        # Calculate financing activities
        loans_received = JournalEntryLine.objects.filter(
            account__code='2200',
            entry__is_posted=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
            credit__gt=0
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
        
        loans_repaid = JournalEntryLine.objects.filter(
            account__code='2200',
            entry__is_posted=True,
            entry__entry_date__gte=start_date,
            entry__entry_date__lte=end_date,
            debit__gt=0
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        
        result['financing']['items'] = [
            {'category': 'Loans Received', 'amount': loans_received},
            {'category': 'Loan Repayments', 'amount': -loans_repaid},
        ]
        result['financing']['total'] = loans_received - loans_repaid
        
        # Calculate net change
        result['net_change'] = (
            result['operating']['total'] +
            result['investing']['total'] +
            result['financing']['total']
        )
        
        # Calculate opening/closing cash
        result['opening_cash'] = CashFlowEngine._get_cash_balance(start_date - timedelta(days=1))
        result['closing_cash'] = result['opening_cash'] + result['net_change']
        
        return result

    @staticmethod
    def _get_cash_balance(as_of_date: date) -> Decimal:
        """Get total cash balance as of date."""
        from payments.models import PaymentAccount, FinancialTransaction
        
        total = Decimal('0.00')
        accounts = PaymentAccount.objects.filter(is_active=True)
        
        for acc in accounts:
            inbound = FinancialTransaction.objects.filter(
                payment_account=acc,
                status='COMPLETED',
                transaction_date__lte=as_of_date,
                transaction_type__in=['RECEIPT', 'REFUND']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            outbound = FinancialTransaction.objects.filter(
                payment_account=acc,
                status='COMPLETED',
                transaction_date__lte=as_of_date,
                transaction_type__in=['PAYMENT', 'TRANSFER', 'REFUND']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            total += inbound - outbound
        
        return abs(total)

    @staticmethod
    def get_cash_position() -> Dict:
        """Get current cash position by account."""
        from payments.models import PaymentAccount, FinancialTransaction
        
        accounts = PaymentAccount.objects.filter(is_active=True)
        
        positions = []
        total = Decimal('0.00')
        
        for acc in accounts:
            inbound = FinancialTransaction.objects.filter(
                payment_account=acc,
                status='COMPLETED',
                transaction_type__in=['RECEIPT', 'REFUND']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            outbound = FinancialTransaction.objects.filter(
                payment_account=acc,
                status='COMPLETED',
                transaction_type__in=['PAYMENT', 'TRANSFER', 'REFUND']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            balance = abs(inbound - outbound)
            total += balance
            
            positions.append({
                'account_name': acc.name,
                'account_number': acc.account_number,
                'balance': balance
            })
        
        return {
            'total_cash': total,
            'accounts': positions
        }

    @staticmethod
    def get_cash_forecast_lightweight(
        days_ahead: int = 30
    ) -> Dict:
        """
        Lightweight cash forecast based on unpaid invoices and obligations.
        
        Uses:
        - Pending AR (expected receipts)
        - Pending AP (expected payments)
        - Historical collection/payment patterns
        """
        from sales.models import SalesInvoice
        from purchases.models import PurchaseInvoice
        
        today = date.today()
        end_forecast = today + timedelta(days=days_ahead)
        
        # Expected receipts from AR
        pending_ar = SalesInvoice.objects.filter(
            status__in=['DISPATCHED', 'PARTIAL_PAID'],
            payment_status__in=['UNPAID', 'PARTIAL']
        )
        
        expected_receipts = Decimal('0.00')
        for inv in pending_ar:
            if inv.due_date and inv.due_date <= end_forecast:
                expected_receipts += inv.total_amount - inv.paid_amount
        
        # Expected payments from AP
        pending_ap = PurchaseInvoice.objects.filter(
            status__in=['RECEIVED', 'PARTIAL_RECEIVED'],
            payment_status__in=['UNPAID', 'PARTIAL']
        )
        
        expected_payments = Decimal('0.00')
        for inv in pending_ap:
            if inv.due_date and inv.due_date <= end_forecast:
                expected_payments += inv.total_amount - inv.paid_amount
        
        current_cash = CashFlowEngine._get_cash_balance(today)
        
        return {
            'current_cash': current_cash,
            'expected_receipts': expected_receipts,
            'expected_payments': expected_payments,
            'projected_cash_min': current_cash + expected_receipts - expected_payments,
            'forecast_days': days_ahead,
            'forecast_end': end_forecast
        }

    @staticmethod
    def get_daily_cash_flow(
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get daily cash flow breakdown."""
        from payments.models import FinancialTransaction
        
        current = start_date
        results = []
        
        while current <= end_date:
            receipts = FinancialTransaction.objects.filter(
                transaction_type='RECEIPT',
                status='COMPLETED',
                transaction_date=current
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            payments = FinancialTransaction.objects.filter(
                transaction_type='PAYMENT',
                status='COMPLETED',
                transaction_date=current
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            results.append({
                'date': current,
                'receipts': receipts,
                'payments': payments,
                'net': receipts - payments
            })
            
            current += timedelta(days=1)
        
        return results

    @staticmethod
    def get_cash_flow_summary_by_category(
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get cash flow summary grouped by category."""
        from payments.models import FinancialTransaction
        
        receipts = FinancialTransaction.objects.filter(
            transaction_type='RECEIPT',
            status='COMPLETED',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).values('payment_method__name').annotate(total=Sum('amount'))
        
        payments = FinancialTransaction.objects.filter(
            transaction_type='PAYMENT',
            status='COMPLETED',
            transaction_date__gte=start_date,
            transaction_date__lte=end_date
        ).values('payment_method__name').annotate(total=Sum('amount'))
        
        return {
            'receipts_by_method': list(receipts),
            'payments_by_method': list(payments),
            'total_receipts': sum(r['total'] for r in receipts),
            'total_payments': sum(p['total'] for p in payments)
        }