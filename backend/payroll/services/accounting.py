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
from uuid import UUID
import uuid as uuid_lib

User = get_user_model()


class PayrollAccountingService:
    """
    Service for payroll-accounting integration.
    Generates journal entries for payroll transactions.
    """
    
    # Default accounts for payroll (configurable in settings)
    SALARY_EXPENSE_ACCOUNT_CODE = '6201'  # Salary Expense
    CASH_ACCOUNT_CODE = '1201'  # Cash at Bank
    TAX_PAYABLE_ACCOUNT_CODE = '2201'  # Tax Payable
    
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
        from accounting.models import JournalEntry, JournalEntryLine, Account
        from payroll.models import PayrollRecord
        
        if payroll_cycle.status != 'APPROVED':
            raise ValidationError('Can only create journal for APPROVED payroll.')
        
        # Get accounts
        try:
            salary_expense = Account.objects.get(code=PayrollAccountingService.SALARY_EXPENSE_ACCOUNT_CODE)
            cash_account = Account.objects.get(code=PayrollAccountingService.CASH_ACCOUNT_CODE)
            tax_payable = Account.objects.get(code=PayrollAccountingService.TAX_PAYABLE_ACCOUNT_CODE)
        except Account.DoesNotExist as e:
            raise ValidationError(f'Payroll account not configured: {e}')
        
        # Create journal entry
        journal_entry = JournalEntry.objects.create(
            entry_number=f"JE-PAY-{payroll_cycle.period_month:02d}{payroll_cycle.period_year}",
            entry_date=payroll_cycle.end_date,
            entry_type='PAYMENT',
            description=f"Payroll {payroll_cycle.name} - {payroll_cycle.employee_count} employees",
            reference_type='PAYROLL',
            reference_id=str(payroll_cycle.id),
            status='POSTED',
            created_by=approved_by
        )
        
        total_gross = payroll_cycle.total_gross or Decimal('0')
        total_deductions = payroll_cycle.total_deductions or Decimal('0')
        total_net = payroll_cycle.total_net or Decimal('0')
        
        # Debit: Salary Expense (Gross)
        JournalEntryLine.objects.create(
            entry=journal_entry,
            account=salary_expense,
            debit=total_gross,
            credit=0,
            memo='Salary Expense'
        )
        
        # Credit: Cash/Bank (Net - amount paid to employees)
        JournalEntryLine.objects.create(
            entry=journal_entry,
            account=cash_account,
            debit=0,
            credit=total_net,
            memo='Cash Payment'
        )
        
        # Credit: Tax Payable (Tax deducted)
        if total_deductions > 0:
            JournalEntryLine.objects.create(
                entry=journal_entry,
                account=tax_payable,
                debit=0,
                credit=total_deductions,
                memo='Tax Withheld'
            )
        
        # Verify double-entry balance
        lines = journal_entry.lines.all()
        total_debit = sum(line.debit for line in lines)
        total_credit = sum(line.credit for line in lines)
        
        if total_debit != total_credit:
            raise ValidationError(
                f'Journal entry out of balance: Debit={total_debit}, Credit={total_credit}'
            )
        
        # Link journal to payroll cycle
        payroll_cycle.accounting_entry_id = journal_entry.id
        payroll_cycle.save()
        
        return journal_entry
    
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
        from accounting.models import JournalEntry, JournalEntryLine
        
        if not payroll_cycle.accounting_entry_id:
            raise ValidationError('No accounting entry to reverse.')
        
        # Get original entry
        try:
            original = JournalEntry.objects.get(id=payroll_cycle.accounting_entry_id)
        except JournalEntry.DoesNotExist:
            raise ValidationError('Original accounting entry not found.')
        
        # Check if already reversed
        if original.status == 'REVERSED':
            raise ValidationError('Entry already reversed.')
        
        # Create reversing entry
        reversing_entry = JournalEntry.objects.create(
            entry_number=f"JE-PAY-RVS-{payroll_cycle.period_month:02d}{payroll_cycle.period_year}",
            entry_date=timezone.now().date(),
            entry_type='ADJUSTMENT',
            description=f"Reversal: {original.description}. Reason: {reason}",
            reference_type='PAYROLL_REVERSAL',
            reference_id=str(payroll_cycle.id),
            status='POSTED',
            created_by=reversed_by
        )
        
        # Reverse all lines (swap debits and credits)
        for line in original.lines.all():
            JournalEntryLine.objects.create(
                entry=reversing_entry,
                account=line.account,
                debit=line.credit,  # Swap
                credit=line.debit,    # Swap
                memo=f"Reversal of {line.memo}"
            )
        
        # Mark original as reversed
        original.status = 'REVERSED'
        original.save()
        
        # Update payroll cycle
        payroll_cycle.status = 'CANCELLED'
        payroll_cycle.accounting_entry_id = None
        payroll_cycle.save()
        
        return reversing_entry
    
    @staticmethod
    def validate_payroll_accounts():
        """
        Validate required payroll accounts exist.
        
        Returns:
            dict with account existence status
        """
        from accounting.models import Account
        
        accounts = {
            'SALARY_EXPENSE': PayrollAccountingService.SALARY_EXPENSE_ACCOUNT_CODE,
            'CASH': PayrollAccountingService.CASH_ACCOUNT_CODE,
            'TAX_PAYABLE': PayrollAccountingService.TAX_PAYABLE_ACCOUNT_CODE,
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
        from payroll.models import PayrollRecord
        
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


# Import at bottom to avoid circular imports
from accounting.models import Account, JournalEntry, JournalEntryLine
from payroll.models import PayrollCycle