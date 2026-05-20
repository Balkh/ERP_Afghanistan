from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounting.models import Account, JournalEntry, JournalEntryLine
from accounting.services.journal_engine import JournalEngine
from fixed_assets.models import FixedAsset, AssetDepreciation, AssetDisposal
from fixed_assets.services.asset_account_resolver import AssetAccountResolver


class AssetAccountingIntegrationService:
    """
    Service for integrating fixed asset transactions with accounting.
    Handles journal entry creation for asset purchases, depreciation, and disposals.
    """

    @staticmethod
    @transaction.atomic
    def post_asset_purchase(
        asset: FixedAsset,
        cash_account: Account,
        description: Optional[str] = None
    ) -> JournalEntry:
        """
        Create journal entry for asset purchase.

        Debit: Fixed Asset Account
        Credit: Cash/Bank Account

        Args:
            asset: FixedAsset being purchased
            cash_account: Account being credited (payment account)
            description: Optional description override

        Returns:
            Created JournalEntry instance
        """
        if asset.status != 'ACTIVE':
            raise ValidationError('Asset must be active to post purchase.')

        entry_description = description or f"Purchase of {asset.asset_name} ({asset.asset_code})"

        asset_account = AssetAccountResolver.resolve_asset_account(
            asset.category.name.upper() if asset.category else 'OTHER'
        )

        entry = JournalEntry.objects.create(
            entry_number=JournalEngine.generate_entry_number('ASSET'),
            entry_date=asset.purchase_date,
            entry_type='ASSET_PURCHASE',
            description=entry_description,
            reference=asset.asset_code,
            is_posted=True
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=asset_account,
            debit=asset.purchase_cost,
            credit=Decimal('0.00'),
            description=f"Fixed asset acquisition: {asset.asset_name}"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=cash_account,
            debit=Decimal('0.00'),
            credit=asset.purchase_cost,
            description=f"Payment for {asset.asset_name}"
        )

        return entry

    @staticmethod
    @transaction.atomic
    def post_depreciation(
        depreciation: AssetDepreciation,
        depreciation_expense_account: Account,
        accumulated_depreciation_account: Account,
        description: Optional[str] = None
    ) -> JournalEntry:
        """
        Create journal entry for depreciation expense.

        Debit: Depreciation Expense Account
        Credit: Accumulated Depreciation Account

        Args:
            depreciation: AssetDepreciation instance
            depreciation_expense_account: Expense account for depreciation
            accumulated_depreciation_account: Contra-asset account for accumulated depreciation
            description: Optional description override

        Returns:
            Created JournalEntry instance
        """
        if depreciation.is_posted:
            raise ValidationError('Depreciation is already posted.')

        entry_description = description or f"Depreciation - {depreciation.asset.asset_name}"

        entry = JournalEntry.objects.create(
            entry_number=JournalEngine.generate_entry_number('DEPR'),
            entry_date=depreciation.period_end,
            entry_type='DEPRECIATION',
            description=entry_description,
            reference=depreciation.asset.asset_code,
            is_posted=True
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=depreciation_expense_account,
            debit=depreciation.depreciation_amount,
            credit=Decimal('0.00'),
            description=f"Depreciation for {depreciation.period_end.strftime('%Y-%m')}"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=accumulated_depreciation_account,
            debit=Decimal('0.00'),
            credit=depreciation.depreciation_amount,
            description=f"Accumulated depreciation"
        )

        depreciation.is_posted = True
        depreciation.save()

        return entry

    @staticmethod
    @transaction.atomic
    def post_disposal(
        disposal: AssetDisposal,
        cash_account: Account,
        accumulated_depr_account: Account,
        depreciation_expense_account: Account,
        gain_loss_account: Account,
        description: Optional[str] = None
    ) -> JournalEntry:
        """
        Create journal entry for asset disposal.

        Entries:
        - Debit: Cash (proceeds)
        - Debit: Accumulated Depreciation (full amount)
        - Debit: Loss on Disposal (if loss) OR Credit: Gain on Disposal (if gain)
        - Credit: Fixed Asset (original cost)

        Args:
            disposal: AssetDisposal instance
            cash_account: Account receiving proceeds
            accumulated_depr_account: Accumulated depreciation account
            depreciation_expense_account: Depreciation expense account
            gain_loss_account: Gain/loss on disposal account
            description: Optional description override

        Returns:
            Created JournalEntry instance
        """
        if disposal.is_posted:
            raise ValidationError('Disposal is already posted.')

        asset = disposal.asset
        entry_description = description or f"Disposal of {asset.asset_name}"

        asset_account = AssetAccountResolver.resolve_asset_account(asset.category.name.upper() if asset.category else 'OTHER')

        entry = JournalEntry.objects.create(
            entry_number=JournalEngine.generate_entry_number('DISP'),
            entry_date=disposal.disposal_date,
            entry_type='DISPOSAL',
            description=entry_description,
            reference=asset.asset_code,
            is_posted=True
        )

        if disposal.proceeds > 0:
            JournalEntryLine.objects.create(
                entry=entry,
                account=cash_account,
                debit=disposal.proceeds,
                credit=Decimal('0.00'),
                description=f"Proceeds from disposal"
            )

        JournalEntryLine.objects.create(
            entry=entry,
            account=accumulated_depr_account,
            debit=asset.accumulated_depreciation,
            credit=Decimal('0.00'),
            description="Remove accumulated depreciation"
        )

        JournalEntryLine.objects.create(
            entry=entry,
            account=asset_account,
            debit=Decimal('0.00'),
            credit=asset.purchase_cost,
            description="Remove asset cost"
        )

        if disposal.gain_loss != 0:
            if disposal.gain_loss > 0:
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=gain_loss_account,
                    debit=Decimal('0.00'),
                    credit=disposal.gain_loss,
                    description="Gain on disposal"
                )
            else:
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=gain_loss_account,
                    debit=abs(disposal.gain_loss),
                    credit=Decimal('0.00'),
                    description="Loss on disposal"
                )

        disposal.is_posted = True
        disposal.save()

        return entry

    @staticmethod
    @transaction.atomic
    def reverse_depreciation(depreciation: AssetDepreciation) -> JournalEntry:
        """
        Reverse a posted depreciation entry.

        Args:
            depreciation: AssetDepreciation instance to reverse

        Returns:
            Created reversal JournalEntry instance
        """
        if not depreciation.is_posted:
            raise ValidationError('Depreciation is not posted.')

        entry_description = f"REVERSAL - Depreciation {depreciation.asset.asset_name}"

        entry = JournalEntry.objects.create(
            entry_number=JournalEngine.generate_entry_number('REVR'),
            entry_date=timezone.now().date(),
            entry_type='REVERSAL',
            description=entry_description,
            reference=depreciation.asset.asset_code,
            is_posted=True
        )

        journal_lines = list(
            JournalEntryLine.objects.filter(
                entry__reference=depreciation.asset.asset_code,
                entry__entry_type='DEPRECIATION'
            ).order_by('-id')[:4]
        )

        for line in journal_lines:
            JournalEntryLine.objects.create(
                entry=entry,
                account=line.account,
                debit=line.credit,
                credit=line.debit,
                description=f"Reversal: {line.description}"
            )

        depreciation.is_posted = False
        depreciation.save()

        return entry

    @staticmethod
    def get_asset_accounts() -> dict:
        """
        Get standard fixed asset accounts.

        Returns:
            Dictionary with account types and instances
        """
        accounts = {
            'fixed_asset': None,
            'accumulated_depreciation': None,
            'depreciation_expense': None,
            'gain_loss_on_disposal': None,
        }

        try:
            accounts['fixed_asset'] = Account.objects.filter(
                account_category='FIXED_ASSET',
                is_active=True
            ).first()

            accounts['accumulated_depreciation'] = Account.objects.filter(
                name__icontains='Accumulated Depreciation',
                is_active=True
            ).first()

            accounts['depreciation_expense'] = Account.objects.filter(
                name__icontains='Depreciation',
                account_type='EXPENSE',
                is_active=True
            ).first()

            accounts['gain_loss_on_disposal'] = Account.objects.filter(
                name__icontains='Gain/Loss',
                is_active=True
            ).first()
        except Exception:
            pass

        return accounts

    @staticmethod
    def calculate_asset_value_report(as_of_date: date) -> List[dict]:
        """
        Generate asset value report as of a specific date.

        Args:
            as_of_date: Date for the report

        Returns:
            List of asset value dictionaries
        """
        assets = FixedAsset.objects.filter(
            status__in=['ACTIVE', 'FULLY_DEPRECIATED']
        ).select_related('category')

        results = []
        for asset in assets:
            results.append({
                'asset_code': asset.asset_code,
                'asset_name': asset.asset_name,
                'category': asset.category.name,
                'purchase_date': str(asset.purchase_date),
                'purchase_cost': asset.purchase_cost,
                'accumulated_depreciation': asset.accumulated_depreciation,
                'current_book_value': asset.current_book_value,
                'salvage_value': asset.salvage_value,
                'status': asset.get_status_display(),
            })

        return results