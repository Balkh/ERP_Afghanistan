"""
Payroll Accounting Integration Service

CRITICAL: This service handles all accounting entries for payroll.
All operations must be atomic - if any step fails,entire transaction rolls back.

Journal Entry Structure for Payroll:
- Debit: Salary Expense Account
- Credit: Cash/Bank Account
- Debit: Tax Payable (for tax deductions)
"""
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.accounting_registry import ACC

User = get_user_model()


class PayrollAccountingService:
    """
    Service for payroll-accounting integration.
    Generates journal entries for payroll transactions.
    """
    
    # Default accounts for payroll — resolved via ACC registry
    SALARY_EXPENSE_ACCOUNT_KEY = 'payroll_salary'   # 7010
    CASH_ACCOUNT_KEY = 'cash_on_hand'               # 1010
    TAX_PAYABLE_ACCOUNT_KEY = 'tax_payable'         # 2120
    
    @staticmethod
    @transaction.atomic
    def create_payroll_journal_entry(payroll_cycle, approved_by):
        """
        Create journal entry for approved payroll cycle.
        
        CRITICAL: This is transactional - if any step fails, 
        entire payroll is rolled back.
        
        Args:
            payroll_cycle: PayrollCycle instance
            approved_by: User who approved
            
        Returns:
            JournalEntry instance
        """
        from accounting.models import Account, JournalEntry
        from accounting.services.journal_engine import JournalEngine
        
        if payroll_cycle.status != 'APPROVED':
            raise ValidationError('Can only create journal for APPROVED payroll.')
        
        # Get accounts via registry
        try:
            salary_expense_code = ACC[PayrollAccountingService.SALARY_EXPENSE_ACCOUNT_KEY]
            cash_account_code = ACC[PayrollAccountingService.CASH_ACCOUNT_KEY]
            tax_payable_code = ACC[PayrollAccountingService.TAX_PAYABLE_ACCOUNT_KEY]
        except KeyError as e:
            raise ValidationError(f'Payroll account key not in registry: {e}')

        for key, code in [('salary_expense', salary_expense_code), ('cash_account', cash_account_code), ('tax_payable', tax_payable_code)]:
            if not Account.objects.filter(code=code, is_active=True).exists():
                raise ValidationError(f'Payroll account {key} (code {code}) not found or inactive.')
        
        total_gross = payroll_cycle.total_gross or Decimal('0')
        total_deductions = payroll_cycle.total_deductions or Decimal('0')
        total_net = payroll_cycle.total_net or Decimal('0')

        lines = [
            {'account_code': salary_expense_code, 'debit': total_gross, 'credit': Decimal('0.00'), 'description': f'Salary expense for {payroll_cycle.name}'},
            {'account_code': cash_account_code, 'debit': Decimal('0.00'), 'credit': total_net, 'description': f'Net cash payment for {payroll_cycle.name}'},
        ]
        if total_deductions > 0:
            lines.append({'account_code': tax_payable_code, 'debit': Decimal('0.00'), 'credit': total_deductions, 'description': f'Tax withheld for {payroll_cycle.name}'})

        created_by_id = approved_by.id if hasattr(approved_by, 'id') else approved_by
        result = JournalEngine.create_entry(
            entry_type='PAYROLL',
            description=f"Payroll {payroll_cycle.name} - {payroll_cycle.employee_count} employees",
            lines=lines,
            entry_date=payroll_cycle.end_date,
            reference=f"PAY-{payroll_cycle.period_month:02d}{payroll_cycle.period_year}",
            auto_post=True,
            source_module='payroll',
            source_document=str(payroll_cycle.id),
            change_reason=f'Payroll cycle {payroll_cycle.name}',
            created_by=created_by_id,
        )
        if not result.get('success'):
            raise ValidationError(f'Failed to create payroll journal entry: {result.get("errors")}')

        journal_entry = JournalEntry.objects.get(id=result['entry_id'])
        payroll_cycle.accounting_entry_id = journal_entry.id
        payroll_cycle.save()

        return result
    
    @staticmethod
    @transaction.atomic
    def reverse_payroll_journal_entry(payroll_cycle, reversed_by, reason):
        """
        Reverse a payroll journal entry (requires new reversing entry).
        
        Args:
            payroll_cycle: PayrollCycle instance
            reversed_by: User making the reversal
            reason: Reason for reversal
            
        Returns:
            New JournalEntry (reversing)
        """
        from accounting.models import JournalEntry
        from accounting.services.journal_engine import JournalEngine

        if not payroll_cycle.accounting_entry_id:
            raise ValidationError('No accounting entry to reverse.')

        try:
            original = JournalEntry.objects.get(id=payroll_cycle.accounting_entry_id)
        except JournalEntry.DoesNotExist:
            raise ValidationError('Original accounting entry not found.')

        if original.is_reversed:
            raise ValidationError('Entry has already been reversed.')

        reversed_by_id = reversed_by.id if hasattr(reversed_by, 'id') else reversed_by
        result = JournalEngine.reverse_entry(
            entry_id=str(original.id),
            reason=reason or f'Payroll reversal for {payroll_cycle.name}',
            user_id=reversed_by_id,
        )
        if not result.get('success'):
            raise ValidationError(f'Failed to reverse payroll journal entry: {result.get("errors")}')

        payroll_cycle.status = 'CANCELLED'
        payroll_cycle.accounting_entry_id = None
        payroll_cycle.save()

        return result
    
    @staticmethod
    def validate_payroll_accounts():
        """
        Validate required payroll accounts exist.
        
        Returns:
            dict with account existence status
        """
        from accounting.models import Account
        
        accounts = {
            'SALARY_EXPENSE': ACC[PayrollAccountingService.SALARY_EXPENSE_ACCOUNT_KEY],
            'CASH': ACC[PayrollAccountingService.CASH_ACCOUNT_KEY],
            'TAX_PAYABLE': ACC[PayrollAccountingService.TAX_PAYABLE_ACCOUNT_KEY],
        }
        
        status = {}
        for name, code in accounts.items():
            try:
                Account.objects.get(code=code)
                status[name] = True
            except Account.DoesNotExist:
                status[name] = False
        
        return status
    
    @staticmethod
    @transaction.atomic
    def process_payroll_with_accounting(payroll_cycle, approved_by):
        """
        Complete payroll processing with accounting - CRITICAL OPERATION.
        
        This method:
        1. Approves payroll
        2. Creates journal entries
        3. Is fully atomic - any failure rolls back everything
        
        Args:
            payroll_cycle: PayrollCycle instance
            approved_by: User
            
        Returns:
            tuple: (payroll_cycle, journal_entry)
        """
        
        
        # Validate accounting accounts exist
        accounts_valid = PayrollAccountingService.validate_payroll_accounts()
        if not all(accounts_valid.values()):
            missing = [k for k, v in accounts_valid.items() if not v]
            raise ValidationError(
                f'Missing required accounts: {missing}. Please configure in accounting.'
            )
        
        # Step 1: Approve payroll
        payroll_cycle = PayrollAccountingService._approve_payroll(payroll_cycle, approved_by)
        
        # Step 2: Generate journal entry
        journal = PayrollAccountingService.create_payroll_journal_entry(
            payroll_cycle, approved_by
        )
        
        return payroll_cycle, journal
    
    @staticmethod
    def _approve_payroll(payroll_cycle, approved_by):
        """Internal method to approve payroll"""
        if payroll_cycle.status != 'GENERATED':
            raise ValidationError('Payroll must be in GENERATED status to approve.')
        
        payroll_cycle.status = 'APPROVED'
        payroll_cycle.approved_by = approved_by
        payroll_cycle.approved_at = timezone.now()
        payroll_cycle.save()
        
        return payroll_cycle

