from django.contrib import admin
from fixed_assets.models import AssetCategory, FixedAsset, AssetDepreciation, AssetDisposal


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'default_useful_life_months', 'default_depreciation_method', 'is_active']
    list_filter = ['is_active', 'default_depreciation_method']
    search_fields = ['code', 'name', 'description']
    ordering = ['code']


@admin.register(FixedAsset)
class FixedAssetAdmin(admin.ModelAdmin):
    list_display = ['asset_code', 'asset_name', 'category', 'status', 'purchase_cost', 'current_book_value', 'purchase_date']
    list_filter = ['status', 'depreciation_method', 'category']
    search_fields = ['asset_code', 'asset_name', 'serial_number', 'location']
    ordering = ['-created_at']
    date_hierarchy = 'purchase_date'


@admin.register(AssetDepreciation)
class AssetDepreciationAdmin(admin.ModelAdmin):
    list_display = ['asset', 'period_start', 'period_end', 'depreciation_amount', 'is_posted']
    list_filter = ['is_posted', 'period_end']
    search_fields = ['asset__asset_code', 'asset__asset_name']
    ordering = ['-period_end']
    date_hierarchy = 'period_end'


@admin.register(AssetDisposal)
class AssetDisposalAdmin(admin.ModelAdmin):
    list_display = ['asset', 'disposal_date', 'disposal_method', 'proceeds', 'gain_loss', 'is_posted']
    list_filter = ['disposal_method', 'is_posted']
    search_fields = ['asset__asset_code', 'asset__asset_name', 'reference_number']
    ordering = ['-disposal_date']
    date_hierarchy = 'disposal_date'