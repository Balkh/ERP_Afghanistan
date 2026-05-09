from decimal import Decimal
from datetime import date
from typing import Optional, List
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from django.utils import timezone


@dataclass
class DepreciationResult:
    """Result of depreciation calculation."""
    period_start: date
    period_end: date
    depreciation_amount: Decimal
    book_value_start: Decimal
    book_value_end: Decimal
    is_fully_depreciated: bool


class DepreciationCalculationService:
    """
    Service for calculating asset depreciation using various methods.
    """

    @staticmethod
    def calculate_straight_line(
        purchase_cost: Decimal,
        salvage_value: Decimal,
        useful_life_months: int,
        current_month: int = 1
    ) -> Decimal:
        """
        Calculate straight-line depreciation for a given month.

        Args:
            purchase_cost: Original purchase cost
            salvage_value: Expected salvage value at end of life
            useful_life_months: Total useful life in months
            current_month: Month number (1-indexed)

        Returns:
            Monthly depreciation amount
        """
        if useful_life_months <= 0:
            return Decimal('0.00')

        depreciable_amount = purchase_cost - salvage_value
        if depreciable_amount <= 0:
            return Decimal('0.00')

        return depreciable_amount / useful_life_months

    @staticmethod
    def calculate_declining_balance(
        book_value: Decimal,
        depreciation_rate: Decimal,
        salvage_value: Decimal
    ) -> Decimal:
        """
        Calculate declining balance depreciation.

        Args:
            book_value: Current book value of the asset
            depreciation_rate: Annual depreciation rate as decimal (e.g., 0.20 for 20%)
            salvage_value: Minimum salvage value

        Returns:
            Monthly depreciation amount
        """
        if book_value <= salvage_value:
            return Decimal('0.00')

        annual_depreciation = book_value * depreciation_rate
        monthly_depreciation = annual_depreciation / 12

        potential_end_value = book_value - monthly_depreciation
        if potential_end_value <= salvage_value:
            return book_value - salvage_value

        return round(monthly_depreciation, 2)

    @staticmethod
    def calculate_monthly_depreciation(
        asset,
        as_of_date: Optional[date] = None
    ) -> DepreciationResult:
        """
        Calculate depreciation for a specific month for an asset.

        Args:
            asset: FixedAsset instance
            as_of_date: Calculate depreciation as of this date (defaults to today)

        Returns:
            DepreciationResult with calculation details
        """
        if as_of_date is None:
            as_of_date = timezone.now().date()

        period_start = date(as_of_date.year, as_of_date.month, 1)

        if as_of_date.month == 12:
            period_end = date(as_of_date.year, 12, 31)
        else:
            period_end = date(as_of_date.year, as_of_date.month + 1, 1) - relativedelta(days=1)

        book_value_start = asset.current_book_value

        if asset.depreciation_method == 'STRAIGHT_LINE':
            monthly_dep = DepreciationCalculationService.calculate_straight_line(
                asset.purchase_cost,
                asset.salvage_value,
                asset.useful_life_months
            )
        elif asset.depreciation_method == 'DECLINING_BALANCE':
            rate = asset.depreciation_rate or Decimal('0.20')
            monthly_dep = DepreciationCalculationService.calculate_declining_balance(
                book_value_start,
                rate,
                asset.salvage_value
            )
        else:
            monthly_dep = Decimal('0.00')

        book_value_end = book_value_start - monthly_dep
        if book_value_end < asset.salvage_value:
            book_value_end = asset.salvage_value
            monthly_dep = book_value_start - book_value_end

        is_fully_depreciated = book_value_end <= asset.salvage_value

        return DepreciationResult(
            period_start=period_start,
            period_end=period_end,
            depreciation_amount=monthly_dep,
            book_value_start=book_value_start,
            book_value_end=book_value_end,
            is_fully_depreciated=is_fully_depreciated
        )

    @staticmethod
    def calculate_period_depreciation(
        asset,
        start_date: date,
        end_date: date
    ) -> List[DepreciationResult]:
        """
        Calculate depreciation for a range of months.

        Args:
            asset: FixedAsset instance
            start_date: Start of calculation period
            end_date: End of calculation period

        Returns:
            List of DepreciationResult for each month in the period
        """
        results = []
        current_date = start_date

        while current_date <= end_date:
            result = DepreciationCalculationService.calculate_monthly_depreciation(
                asset,
                as_of_date=current_date
            )
            results.append(result)
            current_date = date(current_date.year, current_date.month + 1, 1) if current_date.month < 12 else date(current_date.year + 1, 1, 1)

        return results

    @staticmethod
    def calculate_total_depreciation(asset) -> Decimal:
        """
        Calculate total depreciation to date for an asset.

        Args:
            asset: FixedAsset instance

        Returns:
            Total accumulated depreciation
        """
        return asset.accumulated_depreciation

    @staticmethod
    def calculate_remaining_depreciation(asset) -> Decimal:
        """
        Calculate remaining depreciation to be recognized.

        Args:
            asset: FixedAsset instance

        Returns:
            Remaining depreciation amount
        """
        total_depreciable = asset.purchase_cost - asset.salvage_value
        remaining = total_depreciable - asset.accumulated_depreciation
        return max(remaining, Decimal('0.00'))

    @staticmethod
    def calculate_useful_life_remaining(asset) -> int:
        """
        Calculate remaining useful life in months.

        Args:
            asset: FixedAsset instance

        Returns:
            Remaining months of useful life
        """
        if asset.status not in ['ACTIVE', 'DRAFT']:
            return 0

        total_months = asset.useful_life_months
        months_depreciated = asset.accumulated_depreciation / asset.monthly_depreciation if asset.monthly_depreciation > 0 else 0

        remaining = int(total_months - months_depreciated)
        return max(remaining, 0)

    @staticmethod
    def validate_depreciation_inputs(
        purchase_cost: Decimal,
        salvage_value: Decimal,
        useful_life_months: int
    ) -> List[str]:
        """
        Validate depreciation input parameters.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if purchase_cost <= 0:
            errors.append('Purchase cost must be positive.')

        if salvage_value < 0:
            errors.append('Salvage value cannot be negative.')

        if salvage_value >= purchase_cost:
            errors.append('Salvage value must be less than purchase cost.')

        if useful_life_months <= 0:
            errors.append('Useful life must be a positive number of months.')

        return errors