from decimal import Decimal
from datetime import date
from typing import Optional, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from fixed_assets.models import FixedAsset, AssetDepreciation, AssetDisposal
from fixed_assets.services.depreciation_service import DepreciationCalculationService


class AssetLifecycleService:
    """
    Service for managing fixed asset lifecycle operations.
    """

    VALID_TRANSITIONS = {
        'DRAFT': ['ACTIVE', 'DISPOSED'],
        'ACTIVE': ['FULLY_DEPRECIATED', 'DISPOSED'],
        'FULLY_DEPRECIATED': ['DISPOSED', 'ACTIVE'],
        'DISPOSED': [],
    }

    @staticmethod
    @transaction.atomic
    def activate_asset(asset: FixedAsset) -> FixedAsset:
        """
        Activate a draft asset and initialize depreciation.

        Args:
            asset: FixedAsset instance in DRAFT status

        Returns:
            Updated FixedAsset instance
        """
        if asset.status != 'DRAFT':
            raise ValidationError('Only draft assets can be activated.')

        asset.status = 'ACTIVE'
        asset.current_book_value = asset.purchase_cost
        asset.accumulated_depreciation = Decimal('0.00')
        asset.full_clean()
        asset.save()

        return asset

    @staticmethod
    @transaction.atomic
    def depreciate_asset(asset: FixedAsset, period_date: Optional[date] = None) -> AssetDepreciation:
        """
        Run depreciation for a specific period.

        Args:
            asset: FixedAsset instance
            period_date: Date for which to calculate depreciation

        Returns:
            Created AssetDepreciation instance
        """
        if asset.status not in ['ACTIVE', 'DRAFT']:
            raise ValidationError(f'Cannot depreciate asset with status: {asset.status}')

        if asset.is_fully_depreciated:
            raise ValidationError('Asset is already fully depreciated.')

        if period_date is None:
            period_date = timezone.now().date()

        result = DepreciationCalculationService.calculate_monthly_depreciation(
            asset,
            as_of_date=period_date
        )

        depreciation = AssetDepreciation.objects.create(
            asset=asset,
            period_start=result.period_start,
            period_end=result.period_end,
            depreciation_amount=result.depreciation_amount,
            book_value_start=result.book_value_start,
            book_value_end=result.book_value_end,
            is_posted=False
        )

        asset.accumulated_depreciation += result.depreciation_amount
        asset.current_book_value = result.book_value_end
        asset.full_clean()
        asset.save()

        if result.is_fully_depreciated:
            asset.status = 'FULLY_DEPRECIATED'
            asset.full_clean()
            asset.save()

        return depreciation

    @staticmethod
    @transaction.atomic
    def batch_depreciate(
        assets: List[FixedAsset],
        period_date: Optional[date] = None
    ) -> List[AssetDepreciation]:
        """
        Run depreciation for multiple assets.

        Args:
            assets: List of FixedAsset instances
            period_date: Date for which to calculate depreciation

        Returns:
            List of created AssetDepreciation instances
        """
        results = []
        errors = []

        for asset in assets:
            try:
                depreciation = AssetLifecycleService.depreciate_asset(asset, period_date)
                results.append(depreciation)
            except ValidationError as e:
                errors.append(f'{asset.asset_code}: {str(e)}')

        if errors:
            raise ValidationError(f'Depreciation errors: {"; ".join(errors)}')

        return results

    @staticmethod
    @transaction.atomic
    def dispose_asset(
        asset: FixedAsset,
        disposal_date: date,
        disposal_method: str,
        proceeds: Decimal = Decimal('0.00'),
        disposal_cost: Decimal = Decimal('0.00'),
        buyer_info: str = '',
        reference_number: str = '',
        notes: str = ''
    ) -> AssetDisposal:
        """
        Dispose of a fixed asset.

        Args:
            asset: FixedAsset instance
            disposal_date: Date of disposal
            disposal_method: Method of disposal (SOLD, SCRAPPED, etc.)
            proceeds: Amount received from disposal
            disposal_cost: Cost incurred for disposal
            buyer_info: Information about buyer
            reference_number: Reference document number
            notes: Additional notes

        Returns:
            Created AssetDisposal instance
        """
        if asset.status == 'DISPOSED':
            raise ValidationError('Asset is already disposed.')

        disposal = AssetDisposal.objects.create(
            asset=asset,
            disposal_date=disposal_date,
            disposal_method=disposal_method,
            proceeds=proceeds,
            disposal_cost=disposal_cost,
            buyer_info=buyer_info,
            reference_number=reference_number,
            notes=notes,
            is_posted=False
        )

        asset.status = 'DISPOSED'
        asset.full_clean()
        asset.save()

        return disposal

    @staticmethod
    @transaction.atomic
    def reverse_disposal(asset: FixedAsset) -> None:
        """
        Reverse a disposal and restore asset to active status.

        Args:
            asset: FixedAsset instance that was disposed
        """
        if asset.status != 'DISPOSED':
            raise ValidationError('Only disposed assets can be reversed.')

        disposal = AssetDisposal.objects.filter(asset=asset).first()
        if disposal:
            disposal.delete()

        asset.status = 'ACTIVE'
        asset.full_clean()
        asset.save()

    @staticmethod
    @transaction.atomic
    def update_asset(
        asset: FixedAsset,
        **updates
    ) -> FixedAsset:
        """
        Update asset properties.

        Args:
            asset: FixedAsset instance
            **updates: Fields to update

        Returns:
            Updated FixedAsset instance
        """
        allowed_fields = [
            'asset_name', 'serial_number', 'salvage_value',
            'useful_life_months', 'depreciation_method', 'depreciation_rate',
            'location', 'responsible_person', 'notes'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(asset, field, value)

        asset.full_clean()
        asset.save()

        return asset

    @staticmethod
    def validate_status_transition(asset: FixedAsset, new_status: str) -> bool:
        """
        Validate if status transition is allowed.

        Args:
            asset: FixedAsset instance
            new_status: Target status

        Returns:
            True if transition is valid
        """
        allowed = AssetLifecycleService.VALID_TRANSITIONS.get(asset.status, [])
        return new_status in allowed

    @staticmethod
    def get_asset_summary(asset: FixedAsset) -> dict:
        """
        Get comprehensive asset summary.

        Args:
            asset: FixedAsset instance

        Returns:
            Dictionary with asset summary data
        """
        return {
            'asset_code': asset.asset_code,
            'asset_name': asset.asset_name,
            'category': asset.category.name,
            'status': asset.status,
            'purchase_cost': str(asset.purchase_cost),
            'current_book_value': str(asset.current_book_value),
            'accumulated_depreciation': str(asset.accumulated_depreciation),
            'salvage_value': str(asset.salvage_value),
            'depreciable_amount': str(asset.depreciable_amount),
            'monthly_depreciation': str(asset.monthly_depreciation),
            'useful_life_months': asset.useful_life_months,
            'remaining_useful_life': DepreciationCalculationService.calculate_useful_life_remaining(asset),
            'is_fully_depreciated': asset.is_fully_depreciated,
            'depreciation_method': asset.get_depreciation_method_display(),
            'purchase_date': str(asset.purchase_date),
            'location': asset.location,
            'responsible_person': asset.responsible_person,
        }