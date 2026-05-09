from rest_framework import serializers
from fixed_assets.models import AssetCategory, FixedAsset, AssetDepreciation, AssetDisposal


class AssetCategorySerializer(serializers.ModelSerializer):
    asset_count = serializers.SerializerMethodField()

    class Meta:
        model = AssetCategory
        fields = [
            'id', 'name', 'code', 'description',
            'default_useful_life_months', 'default_depreciation_method',
            'is_active', 'asset_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_asset_count(self, obj):
        return obj.assets.count()


class AssetCategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'code']


class FixedAssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    depreciable_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    monthly_depreciation = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )
    is_fully_depreciated = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    depreciation_method_display = serializers.CharField(
        source='get_depreciation_method_display', read_only=True
    )

    class Meta:
        model = FixedAsset
        fields = [
            'id', 'asset_code', 'asset_name', 'category', 'category_name', 'category_code',
            'serial_number', 'purchase_date', 'purchase_cost', 'salvage_value',
            'useful_life_months', 'depreciation_method', 'depreciation_method_display',
            'current_book_value', 'accumulated_depreciation', 'status', 'status_display',
            'notes', 'location', 'responsible_person', 'depreciation_rate',
            'depreciable_amount', 'monthly_depreciation', 'is_fully_depreciated',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_book_value', 'accumulated_depreciation',
                           'created_at', 'updated_at']

    def validate(self, data):
        if data.get('purchase_cost') and data['purchase_cost'] <= 0:
            raise serializers.ValidationError({'purchase_cost': 'Purchase cost must be positive.'})
        if data.get('salvage_value') and data['purchase_cost']:
            if data['salvage_value'] >= data['purchase_cost']:
                raise serializers.ValidationError({'salvage_value': 'Salvage value must be less than purchase cost.'})
        return data


class FixedAssetListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = FixedAsset
        fields = [
            'id', 'asset_code', 'asset_name', 'category_name',
            'current_book_value', 'status', 'status_display', 'purchase_date'
        ]


class AssetDepreciationSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)

    class Meta:
        model = AssetDepreciation
        fields = [
            'id', 'asset', 'asset_code', 'asset_name',
            'period_start', 'period_end', 'depreciation_amount',
            'book_value_start', 'book_value_end',
            'is_posted', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetDisposalSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    disposal_method_display = serializers.CharField(
        source='get_disposal_method_display', read_only=True
    )

    class Meta:
        model = AssetDisposal
        fields = [
            'id', 'asset', 'asset_code', 'asset_name',
            'disposal_date', 'disposal_method', 'disposal_method_display',
            'proceeds', 'disposal_cost', 'gain_loss',
            'notes', 'buyer_info', 'reference_number',
            'is_posted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'gain_loss', 'is_posted', 'created_at', 'updated_at']


class AssetDepreciationCreateSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    period_date = serializers.DateField(required=False)


class AssetDisposalCreateSerializer(serializers.Serializer):
    disposal_date = serializers.DateField()
    disposal_method = serializers.CharField()
    proceeds = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    disposal_cost = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, default=0)
    buyer_info = serializers.CharField(required=False, allow_blank=True, default='')
    reference_number = serializers.CharField(required=False, allow_blank=True, default='')
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class AssetLifecycleActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['activate', 'dispose'])