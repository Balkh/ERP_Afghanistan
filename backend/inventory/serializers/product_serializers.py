from rest_framework import serializers
from ..models import Category, Unit, Product


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model
    """
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'parent_name', 'is_active', 'children']
        read_only_fields = ['id']

    def get_children(self, obj):
        """
        Return serialized children categories
        """
        children = obj.children.all()
        return CategorySerializer(children, many=True).data


class UnitSerializer(serializers.ModelSerializer):
    """
    Serializer for the Unit model
    """
    class Meta:
        model = Unit
        fields = ['id', 'name', 'symbol', 'description', 'is_active']
        read_only_fields = ['id']


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_symbol = serializers.CharField(source='unit.symbol', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'generic_name', 'brand_name', 'category', 'category_name',
            'unit', 'unit_name', 'unit_symbol', 'strength', 'form', 'manufacturer',
            'barcode', 'sku', 'description', 'is_active', 'requires_prescription',
            'is_controlled_substance'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'barcode': {'required': True},
            'sku': {'required': True},
        }

    def validate_barcode(self, value):
        """
        Check that the barcode is unique (if being updated, exclude current instance)
        """
        if self.instance:
            # Update case: exclude current instance
            if Product.objects.exclude(id=self.instance.id).filter(barcode=value).exists():
                raise serializers.ValidationError("A product with this barcode already exists.")
        else:
            # Create case
            if Product.objects.filter(barcode=value).exists():
                raise serializers.ValidationError("A product with this barcode already exists.")
        return value

    def validate_sku(self, value):
        """
        Check that the SKU is unique (if being updated, exclude current instance)
        """
        if self.instance:
            # Update case: exclude current instance
            if Product.objects.exclude(id=self.instance.id).filter(sku=value).exists():
                raise serializers.ValidationError("A product with this SKU already exists.")
        else:
            # Create case
            if Product.objects.filter(sku=value).exists():
                raise serializers.ValidationError("A product with this SKU already exists.")
        return value