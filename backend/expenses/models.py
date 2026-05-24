from django.db import models, transaction
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from core.models import TimeStampedUUIDModel
from core.multitenant.models import CompanyScopedMixin, CompanyScopedManager
from accounting.models import Account, JournalEntry
from payments.models import PaymentAccount

class Expense(CompanyScopedMixin, TimeStampedUUIDModel):
    """
    Pharmacy expenses (Rent, Electricity, Supplies, etc.)
    Expense.save() is a data staging point ONLY — it does NOT mutate financial state.
    All financial truth flows through JournalEntry posting.
    PaymentAccount balance is derived from journal entries, never directly mutated.
    """
    objects = CompanyScopedManager()
    
    expense_number = models.CharField(max_length=50, unique=True, verbose_name=_('Expense #'))
    
    # The account that represents this expense in COA (e.g., 6100 - Rent)
    expense_account = models.ForeignKey(
        Account, 
        on_delete=models.PROTECT, 
        related_name='pharmacy_expenses',
        limit_choices_to={'account_type': 'EXPENSE'}
    )
    
    # The account from which money is paid (Cash, Bank)
    payment_account = models.ForeignKey(
        PaymentAccount, 
        on_delete=models.PROTECT, 
        related_name='pharmacy_expenses'
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    payee = models.CharField(max_length=255, blank=True, help_text=_('Who was paid?'))
    description = models.TextField(blank=True)
    
    # Accounting integration
    journal_entry = models.ForeignKey(
        JournalEntry, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='pharmacy_expenses'
    )

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.expense_number} - {self.expense_account.name} ({self.amount})"

    def clean(self):
        if self.amount <= 0:
            raise ValidationError(_('Expense amount must be positive.'))

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.expense_number:
            import uuid
            self.expense_number = f"EXP-{uuid.uuid4().hex[:8].upper()}"
        
        super().save(*args, **kwargs)
        
        if is_new:
            self._create_journal_entry()

    def _create_journal_entry(self):
        """Create a journal entry for the expense.

        CRITICAL: If journal entry creation fails, the entire transaction rolls back.
        The Expense record is NOT persisted without an accounting trail.
        No direct balance mutation occurs — PaymentAccount balance is derived
        from journal entries via the SSOT Control Plane.
        """
        from core.drift_prevention.migration_router import MigrationRouter

        lines = [
            {
                'account_code': self.expense_account.code,
                'debit': self.amount,
                'credit': 0,
                'description': f"Expense: {self.description or self.expense_account.name}"
            },
            {
                'account_code': self.payment_account.accounting_account.code,
                'debit': 0,
                'credit': self.amount,
                'description': f"Payment for {self.expense_number}"
            }
        ]

        result = MigrationRouter.create_entry(
            module='expenses',
            operation='create_entry',
            entry_type='EXPENSE',
            description=f"Pharmacy Expense {self.expense_number}: {self.description}",
            lines=lines,
            entry_date=self.date,
            reference=self.expense_number,
            auto_post=True,
            entity_type='Expense',
            entity_id=str(self.id),
        )

        if not result.get('success'):
            raise ValidationError(
                f'Journal entry creation failed for expense {self.expense_number}: '
                f'{result.get("error", "Unknown error")}. '
                'Expense cannot be saved without accounting trail.'
            )
        
        self.journal_entry_id = result.get('entry_id')
        Expense.objects.filter(id=self.id).update(journal_entry_id=self.journal_entry_id)
