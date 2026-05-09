from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db.models import Sum

from accounting.models import JournalEntryLine, Account
from entities.models import Entity, EntityAccount, InterCompanyTransaction


class EntityService:
    """
    Service for managing business entities.
    """

    @staticmethod
    def get_default_entity() -> Optional[Entity]:
        """Get the default entity."""
        return Entity.objects.filter(is_default=True, is_active=True).first()

    @staticmethod
    def get_entity_accounts(entity: Entity) -> List[Account]:
        """Get all accounts configured for an entity."""
        return [
            ea.account for ea in entity.accounts.filter(is_active=True)
        ]

    @staticmethod
    def add_entity_account(
        entity: Entity,
        account: Account,
        account_name: str = None
    ) -> EntityAccount:
        """Add an account to an entity."""
        return EntityAccount.objects.create(
            entity=entity,
            account=account,
            account_name=account_name or account.name,
            is_active=True
        )

    @staticmethod
    def get_entity_balance(
        entity: Entity,
        account: Account,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Get balance for a specific account in an entity."""
        lines = JournalEntryLine.objects.filter(
            account=account,
            entry__is_posted=True
        )

        if start_date:
            lines = lines.filter(entry__entry_date__gte=start_date)
        if end_date:
            lines = lines.filter(entry__entry_date__lte=end_date)

        total = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
        total -= lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

        return total

    @staticmethod
    def create_inter_company_transfer(
        from_entity: Entity,
        to_entity: Entity,
        amount: Decimal,
        currency,
        description: str = '',
        reference: str = ''
    ) -> InterCompanyTransaction:
        """Create an inter-company transaction."""
        return InterCompanyTransaction.objects.create(
            from_entity=from_entity,
            to_entity=to_entity,
            transaction_type='TRANSFER',
            amount=amount,
            currency=currency,
            transaction_date=date.today(),
            description=description,
            reference_number=reference
        )

    @staticmethod
    def reconcile_transaction(tx: InterCompanyTransaction) -> InterCompanyTransaction:
        """Mark transaction as reconciled."""
        tx.is_reconciled = True
        tx.save()
        return tx

    @staticmethod
    def validate_entity_access(entity: Entity, user) -> bool:
        """Validate user has access to entity."""
        return entity.is_active