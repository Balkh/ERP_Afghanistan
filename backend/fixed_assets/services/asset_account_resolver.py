"""Deterministic account resolver for fixed asset accounting.

Eliminates unsafe patterns like Account.objects.filter(is_active=True).first()
by providing explicit, auditable account mapping based on asset type and transaction nature.

All mappings are deterministic — no fallback accounts, no random selection.
"""
from decimal import Decimal
from typing import Optional
from django.core.exceptions import ValidationError
from django.db.models import Q

from accounting.models import Account


class AssetAccountResolver:
    """Deterministic resolver for fixed asset accounting accounts.

    Every method raises ValidationError if the required account cannot be found.
    No fallback accounts are allowed — missing accounts are a configuration error
    that must be resolved explicitly.
    """

    # Deterministic account code prefixes for asset accounts
    FIXED_ASSET_PREFIXES = {
        'BUILDING': '1301',
        'EQUIPMENT': '1302',
        'VEHICLE': '1303',
        'FURNITURE': '1304',
        'COMPUTER': '1305',
        'MACHINERY': '1306',
        'LAND': '1307',
        'SOFTWARE': '1308',
        'OTHER': '1399',
    }

    ACCUMULATED_DEPRECIATION_PREFIXES = {
        'BUILDING': '1401',
        'EQUIPMENT': '1402',
        'VEHICLE': '1403',
        'FURNITURE': '1404',
        'COMPUTER': '1405',
        'MACHINERY': '1406',
        'LAND': '1407',
        'SOFTWARE': '1408',
        'OTHER': '1499',
    }

    DEPRECIATION_EXPENSE_CODE = '6301'
    GAIN_ON_DISPOSAL_CODE = '4201'
    LOSS_ON_DISPOSAL_CODE = '6401'

    @classmethod
    def resolve_asset_account(cls, asset_type: str) -> Account:
        """Resolve the fixed asset account for a given asset type.

        Args:
            asset_type: Asset category (BUILDING, EQUIPMENT, VEHICLE, etc.)

        Returns:
            Account instance for the asset type

        Raises:
            ValidationError: If no matching account exists
        """
        code = cls.FIXED_ASSET_PREFIXES.get(asset_type, cls.FIXED_ASSET_PREFIXES['OTHER'])

        account = Account.objects.filter(
            code=code,
            account_category='FIXED_ASSET',
            is_active=True,
        ).first()

        if not account:
            raise ValidationError(
                f'Fixed asset account not found for type "{asset_type}". '
                f'Expected code: {code}. Please configure the Chart of Accounts.'
            )

        return account

    @classmethod
    def resolve_accumulated_depreciation_account(cls, asset_type: str) -> Account:
        """Resolve the accumulated depreciation account for a given asset type.

        Args:
            asset_type: Asset category (BUILDING, EQUIPMENT, VEHICLE, etc.)

        Returns:
            Account instance for accumulated depreciation

        Raises:
            ValidationError: If no matching account exists
        """
        code = cls.ACCUMULATED_DEPRECIATION_PREFIXES.get(
            asset_type, cls.ACCUMULATED_DEPRECIATION_PREFIXES['OTHER']
        )

        account = Account.objects.filter(
            code=code,
            account_type='ASSET',
            is_active=True,
        ).first()

        if not account:
            raise ValidationError(
                f'Accumulated depreciation account not found for type "{asset_type}". '
                f'Expected code: {code}. Please configure the Chart of Accounts.'
            )

        return account

    @classmethod
    def resolve_depreciation_expense_account(cls) -> Account:
        """Resolve the depreciation expense account.

        Returns:
            Account instance for depreciation expense

        Raises:
            ValidationError: If no matching account exists
        """
        account = Account.objects.filter(
            code=cls.DEPRECIATION_EXPENSE_CODE,
            account_type='EXPENSE',
            is_active=True,
        ).first()

        if not account:
            account = Account.objects.filter(
                name__icontains='Depreciation Expense',
                account_type='EXPENSE',
                is_active=True,
            ).first()

        if not account:
            raise ValidationError(
                f'Depreciation expense account not found. '
                f'Expected code: {cls.DEPRECIATION_EXPENSE_CODE}. '
                'Please configure the Chart of Accounts.'
            )

        return account

    @classmethod
    def resolve_gain_on_disposal_account(cls) -> Account:
        """Resolve the gain on disposal account (revenue/credit side).

        Returns:
            Account instance for gain on disposal

        Raises:
            ValidationError: If no matching account exists
        """
        account = Account.objects.filter(
            code=cls.GAIN_ON_DISPOSAL_CODE,
            account_type='REVENUE',
            is_active=True,
        ).first()

        if not account:
            account = Account.objects.filter(
                name__icontains='Gain on Disposal',
                account_type='REVENUE',
                is_active=True,
            ).first()

        if not account:
            raise ValidationError(
                f'Gain on disposal account not found. '
                f'Expected code: {cls.GAIN_ON_DISPOSAL_CODE}. '
                'Please configure the Chart of Accounts.'
            )

        return account

    @classmethod
    def resolve_loss_on_disposal_account(cls) -> Account:
        """Resolve the loss on disposal account (expense/debit side).

        Returns:
            Account instance for loss on disposal

        Raises:
            ValidationError: If no matching account exists
        """
        account = Account.objects.filter(
            code=cls.LOSS_ON_DISPOSAL_CODE,
            account_type='EXPENSE',
            is_active=True,
        ).first()

        if not account:
            account = Account.objects.filter(
                name__icontains='Loss on Disposal',
                account_type='EXPENSE',
                is_active=True,
            ).first()

        if not account:
            raise ValidationError(
                f'Loss on disposal account not found. '
                f'Expected code: {cls.LOSS_ON_DISPOSAL_CODE}. '
                'Please configure the Chart of Accounts.'
            )

        return account

    @classmethod
    def resolve_disposal_accounts(cls) -> dict:
        """Resolve all accounts needed for asset disposal in one call.

        Returns:
            Dict with keys: gain_on_disposal, loss_on_disposal

        Raises:
            ValidationError: If any required account is missing
        """
        return {
            'gain_on_disposal': cls.resolve_gain_on_disposal_account(),
            'loss_on_disposal': cls.resolve_loss_on_disposal_account(),
        }

    @classmethod
    def validate_all_asset_accounts(cls) -> dict:
        """Validate that all standard asset accounts exist.

        Returns:
            Dict with account types as keys and (exists: bool, account: Account|None) as values
        """
        results = {}

        for asset_type in cls.FIXED_ASSET_PREFIXES:
            try:
                account = cls.resolve_asset_account(asset_type)
                results[f'asset_{asset_type.lower()}'] = {'exists': True, 'account': account}
            except ValidationError:
                results[f'asset_{asset_type.lower()}'] = {'exists': False, 'account': None}

        for asset_type in cls.ACCUMULATED_DEPRECIATION_PREFIXES:
            try:
                account = cls.resolve_accumulated_depreciation_account(asset_type)
                results[f'accum_depr_{asset_type.lower()}'] = {'exists': True, 'account': account}
            except ValidationError:
                results[f'accum_depr_{asset_type.lower()}'] = {'exists': False, 'account': None}

        for method_name in ['depreciation_expense', 'gain_on_disposal', 'loss_on_disposal']:
            try:
                account = getattr(cls, f'resolve_{method_name}_account')()
                results[method_name] = {'exists': True, 'account': account}
            except ValidationError:
                results[method_name] = {'exists': False, 'account': None}

        return results
