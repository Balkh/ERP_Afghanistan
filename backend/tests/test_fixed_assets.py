"""
Tests for Fixed Assets module.

Covers:
- AssetCategory model
- FixedAsset model
- AssetDepreciation model
- AssetDisposal model
- DepreciationCalculationService
- AssetLifecycleService
"""
import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError

from accounting.models import Currency
from fixed_assets.models import AssetCategory, FixedAsset, AssetDepreciation, AssetDisposal
from fixed_assets.services.depreciation_service import DepreciationCalculationService
from fixed_assets.services.asset_lifecycle_service import AssetLifecycleService


class TestHelper:
    """Helper class for test data creation."""

    @staticmethod
    def get_or_create_currency():
        currency, _ = Currency.objects.get_or_create(
            code='AFN',
            defaults={
                'name': 'Afghan Afghani',
                'symbol': '؋',
                'is_default': True,
                'is_active': True
            }
        )
        return currency


class AssetCategoryModelTests(TestCase):
    """Tests for AssetCategory model."""

    def test_create_asset_category(self):
        """Test creating an asset category."""
        category = AssetCategory.objects.create(
            name='Computer Equipment',
            code='COMP',
            description='Laptops, desktops, servers',
            default_useful_life_months=36,
            default_depreciation_method='STRAIGHT_LINE',
            is_active=True
        )
        self.assertEqual(category.name, 'Computer Equipment')
        self.assertEqual(category.code, 'COMP')
        self.assertTrue(category.is_active)

    def test_asset_category_str(self):
        """Test string representation of category."""
        category = AssetCategory.objects.create(
            name='Furniture',
            code='FURN',
            is_active=True
        )
        self.assertEqual(str(category), 'FURN - Furniture')

    def test_asset_category_unique_code(self):
        """Test that category code must be unique."""
        AssetCategory.objects.create(name='Test', code='TEST', is_active=True)
        with self.assertRaises(Exception):
            AssetCategory.objects.create(name='Test2', code='TEST', is_active=True)


class FixedAssetModelTests(TestCase):
    """Tests for FixedAsset model."""

    def setUp(self):
        TestHelper.get_or_create_currency()
        self.category = AssetCategory.objects.create(
            name='Computer Equipment',
            code='COMP',
            default_useful_life_months=36
        )

    def test_create_fixed_asset(self):
        """Test creating a fixed asset."""
        asset = FixedAsset.objects.create(
            asset_code='FA-001',
            asset_name='Dell Laptop',
            category=self.category,
            purchase_date=date.today(),
            purchase_cost=Decimal('50000.00'),
            salvage_value=Decimal('5000.00'),
            useful_life_months=36,
            depreciation_method='STRAIGHT_LINE',
            status='DRAFT'
        )
        self.assertEqual(asset.asset_code, 'FA-001')
        self.assertEqual(asset.asset_name, 'Dell Laptop')
        self.assertEqual(asset.status, 'DRAFT')

    def test_fixed_asset_str(self):
        """Test string representation of asset."""
        asset = FixedAsset.objects.create(
            asset_code='FA-002',
            asset_name='HP Printer',
            category=self.category,
            purchase_date=date.today(),
            purchase_cost=Decimal('15000.00'),
            salvage_value=Decimal('1000.00'),
            useful_life_months=24,
            status='DRAFT'
        )
        self.assertEqual(str(asset), 'FA-002 - HP Printer')

    def test_depreciable_amount(self):
        """Test depreciable amount calculation."""
        asset = FixedAsset.objects.create(
            asset_code='FA-003',
            asset_name='Test Asset',
            category=self.category,
            purchase_date=date.today(),
            purchase_cost=Decimal('30000.00'),
            salvage_value=Decimal('3000.00'),
            useful_life_months=24,
            status='ACTIVE'
        )
        self.assertEqual(asset.depreciable_amount, Decimal('27000.00'))

    def test_monthly_depreciation_straight_line(self):
        """Test monthly depreciation calculation for straight line."""
        asset = FixedAsset.objects.create(
            asset_code='FA-004',
            asset_name='Test Asset',
            category=self.category,
            purchase_date=date.today(),
            purchase_cost=Decimal('24000.00'),
            salvage_value=Decimal('0.00'),
            useful_life_months=24,
            status='ACTIVE'
        )
        self.assertEqual(asset.monthly_depreciation, Decimal('1000.00'))

    def test_asset_validation_salvage_greater_than_cost(self):
        """Test validation error when salvage >= purchase cost."""
        with self.assertRaises(ValidationError):
            asset = FixedAsset(
                asset_code='FA-005',
                asset_name='Test Asset',
                category=self.category,
                purchase_date=date.today(),
                purchase_cost=Decimal('10000.00'),
                salvage_value=Decimal('15000.00'),
                useful_life_months=24,
                status='DRAFT'
            )
            asset.full_clean()

    def test_asset_validation_negative_purchase_cost(self):
        """Test validation error for negative purchase cost."""
        with self.assertRaises(ValidationError):
            asset = FixedAsset(
                asset_code='FA-006',
                asset_name='Test Asset',
                category=self.category,
                purchase_date=date.today(),
                purchase_cost=Decimal('-10000.00'),
                salvage_value=Decimal('0.00'),
                useful_life_months=24,
                status='DRAFT'
            )
            asset.full_clean()

    def test_active_asset_has_book_value(self):
        """Test that active asset gets book value on save."""
        asset = FixedAsset.objects.create(
            asset_code='FA-007',
            asset_name='Test Asset',
            category=self.category,
            purchase_date=date.today(),
            purchase_cost=Decimal('50000.00'),
            salvage_value=Decimal('5000.00'),
            useful_life_months=24,
            status='ACTIVE'
        )
        self.assertEqual(asset.current_book_value, Decimal('50000.00'))


class DepreciationCalculationServiceTests(TestCase):
    """Tests for DepreciationCalculationService."""

    def test_straight_line_depreciation(self):
        """Test straight-line depreciation calculation."""
        monthly = DepreciationCalculationService.calculate_straight_line(
            purchase_cost=Decimal('120000.00'),
            salvage_value=Decimal('12000.00'),
            useful_life_months=60
        )
        self.assertEqual(monthly, Decimal('1800.00'))

    def test_straight_line_zero_useful_life(self):
        """Test straight-line with zero useful life."""
        monthly = DepreciationCalculationService.calculate_straight_line(
            purchase_cost=Decimal('120000.00'),
            salvage_value=Decimal('12000.00'),
            useful_life_months=0
        )
        self.assertEqual(monthly, Decimal('0.00'))

    def test_declining_balance_depreciation(self):
        """Test declining balance depreciation calculation."""
        monthly = DepreciationCalculationService.calculate_declining_balance(
            book_value=Decimal('100000.00'),
            depreciation_rate=Decimal('0.20'),
            salvage_value=Decimal('10000.00')
        )
        self.assertAlmostEqual(float(monthly), 1666.67, places=2)

    def test_declining_balance_at_salvage_boundary(self):
        """Test declining balance when depreciation would reach salvage value."""
        monthly = DepreciationCalculationService.calculate_declining_balance(
            book_value=Decimal('12000.00'),
            depreciation_rate=Decimal('0.20'),
            salvage_value=Decimal('10000.00')
        )
        self.assertEqual(monthly, Decimal('200.00'))

    def test_declining_balance_below_salvage(self):
        """Test declining balance when already below salvage value."""
        monthly = DepreciationCalculationService.calculate_declining_balance(
            book_value=Decimal('9500.00'),
            depreciation_rate=Decimal('0.20'),
            salvage_value=Decimal('10000.00')
        )
        self.assertEqual(monthly, Decimal('0.00'))

    def test_validate_depreciation_inputs_valid(self):
        """Test validation with valid inputs."""
        errors = DepreciationCalculationService.validate_depreciation_inputs(
            purchase_cost=Decimal('100000.00'),
            salvage_value=Decimal('10000.00'),
            useful_life_months=60
        )
        self.assertEqual(errors, [])

    def test_validate_depreciation_inputs_negative_cost(self):
        """Test validation with negative purchase cost."""
        errors = DepreciationCalculationService.validate_depreciation_inputs(
            purchase_cost=Decimal('-100000.00'),
            salvage_value=Decimal('10000.00'),
            useful_life_months=60
        )
        self.assertIn('Purchase cost must be positive.', errors)

    def test_validate_depreciation_inputs_salvage_greater(self):
        """Test validation when salvage >= cost."""
        errors = DepreciationCalculationService.validate_depreciation_inputs(
            purchase_cost=Decimal('100000.00'),
            salvage_value=Decimal('150000.00'),
            useful_life_months=60
        )
        self.assertIn('Salvage value must be less than purchase cost.', errors)

    def test_validate_depreciation_inputs_zero_useful_life(self):
        """Test validation with zero useful life."""
        errors = DepreciationCalculationService.validate_depreciation_inputs(
            purchase_cost=Decimal('100000.00'),
            salvage_value=Decimal('10000.00'),
            useful_life_months=0
        )
        self.assertIn('Useful life must be a positive number of months.', errors)

    def test_calculate_remaining_depreciation(self):
        """Test remaining depreciation calculation."""
        TestHelper.get_or_create_currency()
        category = AssetCategory.objects.create(
            name='Test',
            code='TEST',
            default_useful_life_months=60
        )
        asset = FixedAsset.objects.create(
            asset_code='TEST-002',
            asset_name='Test Asset',
            category=category,
            purchase_date=date(2024, 1, 1),
            purchase_cost=Decimal('120000.00'),
            salvage_value=Decimal('12000.00'),
            useful_life_months=60,
            accumulated_depreciation=Decimal('36000.00'),
            current_book_value=Decimal('84000.00'),
            status='ACTIVE'
        )

        remaining = DepreciationCalculationService.calculate_remaining_depreciation(asset)
        self.assertEqual(remaining, Decimal('72000.00'))


class AssetLifecycleServiceTests(TestCase):
    """Tests for AssetLifecycleService."""

    def setUp(self):
        TestHelper.get_or_create_currency()
        self.category = AssetCategory.objects.create(
            name='Test Category',
            code='TEST',
            default_useful_life_months=60
        )
        self.asset = FixedAsset.objects.create(
            asset_code='LIFE-001',
            asset_name='Test Asset',
            category=self.category,
            purchase_date=date(2024, 1, 1),
            purchase_cost=Decimal('120000.00'),
            salvage_value=Decimal('12000.00'),
            useful_life_months=60,
            status='DRAFT'
        )

    def test_activate_asset(self):
        """Test activating a draft asset."""
        activated = AssetLifecycleService.activate_asset(self.asset)
        self.assertEqual(activated.status, 'ACTIVE')
        self.assertEqual(activated.current_book_value, Decimal('120000.00'))

    def test_activate_non_draft_asset_fails(self):
        """Test that non-draft assets cannot be activated."""
        self.asset.status = 'ACTIVE'
        self.asset.save()

        with self.assertRaises(ValidationError):
            AssetLifecycleService.activate_asset(self.asset)

    def test_dispose_asset(self):
        """Test disposing of an asset."""
        self.asset.status = 'ACTIVE'
        self.asset.save()

        disposal = AssetLifecycleService.dispose_asset(
            self.asset,
            disposal_date=date.today(),
            disposal_method='SOLD',
            proceeds=Decimal('50000.00')
        )

        self.assertEqual(disposal.proceeds, Decimal('50000.00'))
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'DISPOSED')

    def test_dispose_already_disposed_fails(self):
        """Test that already disposed assets cannot be disposed again."""
        self.asset.status = 'DISPOSED'
        self.asset.save()

        with self.assertRaises(ValidationError):
            AssetLifecycleService.dispose_asset(
                self.asset,
                disposal_date=date.today(),
                disposal_method='SCRAPPED'
            )

    def test_reverse_disposal(self):
        """Test reversing a disposal."""
        self.asset.status = 'ACTIVE'
        self.asset.save()

        AssetLifecycleService.dispose_asset(
            self.asset,
            disposal_date=date.today(),
            disposal_method='SOLD',
            proceeds=Decimal('50000.00')
        )

        AssetLifecycleService.reverse_disposal(self.asset)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'ACTIVE')

    def test_validate_status_transition(self):
        """Test status transition validation."""
        self.assertTrue(AssetLifecycleService.validate_status_transition(self.asset, 'ACTIVE'))
        self.assertTrue(AssetLifecycleService.validate_status_transition(self.asset, 'DISPOSED'))

        self.asset.status = 'ACTIVE'
        self.assertTrue(AssetLifecycleService.validate_status_transition(self.asset, 'FULLY_DEPRECIATED'))
        self.assertTrue(AssetLifecycleService.validate_status_transition(self.asset, 'DISPOSED'))

    def test_get_asset_summary(self):
        """Test getting asset summary."""
        self.asset.status = 'ACTIVE'
        self.asset.save()

        summary = AssetLifecycleService.get_asset_summary(self.asset)

        self.assertEqual(summary['asset_code'], 'LIFE-001')
        self.assertEqual(summary['asset_name'], 'Test Asset')
        self.assertEqual(summary['status'], 'ACTIVE')
        self.assertEqual(summary['depreciable_amount'], '108000.00')


class AssetDisposalModelTests(TestCase):
    """Tests for AssetDisposal model."""

    def setUp(self):
        TestHelper.get_or_create_currency()
        self.category = AssetCategory.objects.create(
            name='Test',
            code='TEST',
            default_useful_life_months=60
        )
        self.asset = FixedAsset.objects.create(
            asset_code='DISP-001',
            asset_name='Test Asset',
            category=self.category,
            purchase_date=date(2024, 1, 1),
            purchase_cost=Decimal('50000.00'),
            salvage_value=Decimal('5000.00'),
            useful_life_months=60,
            current_book_value=Decimal('30000.00'),
            accumulated_depreciation=Decimal('20000.00'),
            status='ACTIVE'
        )

    def test_disposal_gain_loss_calculation(self):
        """Test gain/loss calculation on disposal."""
        disposal = AssetDisposal.objects.create(
            asset=self.asset,
            disposal_date=date.today(),
            disposal_method='SOLD',
            proceeds=Decimal('35000.00'),
            disposal_cost=Decimal('1000.00')
        )

        self.assertEqual(disposal.gain_loss, Decimal('4000.00'))

    def test_disposal_loss_calculation(self):
        """Test loss calculation when proceeds less than book value."""
        disposal = AssetDisposal.objects.create(
            asset=self.asset,
            disposal_date=date.today(),
            disposal_method='SOLD',
            proceeds=Decimal('20000.00'),
            disposal_cost=Decimal('1000.00')
        )

        self.assertEqual(disposal.gain_loss, Decimal('-11000.00'))

    def test_disposal_scrapped_no_proceeds(self):
        """Test disposal by scrapping with no proceeds."""
        disposal = AssetDisposal.objects.create(
            asset=self.asset,
            disposal_date=date.today(),
            disposal_method='SCRAPPED',
            proceeds=Decimal('0.00'),
            disposal_cost=Decimal('500.00')
        )

        self.assertEqual(disposal.gain_loss, Decimal('-30500.00'))


class AssetDepreciationModelTests(TestCase):
    """Tests for AssetDepreciation model."""

    def setUp(self):
        TestHelper.get_or_create_currency()
        self.category = AssetCategory.objects.create(
            name='Test',
            code='TEST',
            default_useful_life_months=60
        )
        self.asset = FixedAsset.objects.create(
            asset_code='DEPR-001',
            asset_name='Test Asset',
            category=self.category,
            purchase_date=date(2024, 1, 1),
            purchase_cost=Decimal('60000.00'),
            salvage_value=Decimal('6000.00'),
            useful_life_months=60,
            status='ACTIVE'
        )

    def test_create_depreciation_entry(self):
        """Test creating a depreciation entry."""
        depreciation = AssetDepreciation.objects.create(
            asset=self.asset,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            depreciation_amount=Decimal('900.00'),
            book_value_start=Decimal('60000.00'),
            book_value_end=Decimal('59100.00')
        )

        self.assertEqual(depreciation.asset, self.asset)
        self.assertFalse(depreciation.is_posted)

    def test_depreciation_validation_negative_amount(self):
        """Test validation rejects negative depreciation."""
        with self.assertRaises(ValidationError):
            depreciation = AssetDepreciation(
                asset=self.asset,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                depreciation_amount=Decimal('-100.00'),
                book_value_start=Decimal('60000.00'),
                book_value_end=Decimal('59000.00')
            )
            depreciation.full_clean()


class AssetLifecycleDepreciationTests(TestCase):
    """Integration tests for asset depreciation lifecycle."""

    def setUp(self):
        TestHelper.get_or_create_currency()
        self.category = AssetCategory.objects.create(
            name='Test',
            code='TEST',
            default_useful_life_months=12
        )
        self.asset = FixedAsset.objects.create(
            asset_code='MULT-001',
            asset_name='Multi Period Asset',
            category=self.category,
            purchase_date=date(2024, 1, 1),
            purchase_cost=Decimal('12000.00'),
            salvage_value=Decimal('0.00'),
            useful_life_months=12,
            status='ACTIVE'
        )

    def test_activate_and_depreciate_asset(self):
        """Test activating an asset and running depreciation."""
        self.assertEqual(self.asset.current_book_value, Decimal('12000.00'))

        depreciation = AssetLifecycleService.depreciate_asset(self.asset)
        self.assertIsNotNone(depreciation)
        self.assertEqual(depreciation.depreciation_amount, Decimal('1000.00'))

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.accumulated_depreciation, Decimal('1000.00'))
        self.assertEqual(self.asset.current_book_value, Decimal('11000.00'))

    def test_multiple_depreciation_periods(self):
        """Test running depreciation for multiple periods."""
        for month in range(1, 5):
            depreciation = AssetLifecycleService.depreciate_asset(self.asset)
            self.assertEqual(depreciation.depreciation_amount, Decimal('1000.00'))

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.accumulated_depreciation, Decimal('4000.00'))
        self.assertEqual(self.asset.current_book_value, Decimal('8000.00'))

    def test_calculate_monthly_depreciation(self):
        """Test calculating monthly depreciation for asset."""
        result = DepreciationCalculationService.calculate_monthly_depreciation(
            self.asset,
            as_of_date=date(2024, 2, 15)
        )

        self.assertEqual(result.depreciation_amount, Decimal('1000.00'))
        self.assertEqual(result.book_value_start, Decimal('12000.00'))
        self.assertEqual(result.book_value_end, Decimal('11000.00'))