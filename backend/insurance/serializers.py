"""Insurance API Serializers."""
from rest_framework import serializers
from .models import InsuranceProvider, InsurancePolicy, Claim, ClaimItem, ClaimApproval


class InsuranceProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceProvider
        fields = '__all__'


class InsurancePolicySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    remaining_limit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = InsurancePolicy
        fields = '__all__'


class ClaimItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ClaimItem
        fields = '__all__'


class ClaimListSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    provider_name = serializers.CharField(source='policy.provider.name', read_only=True)
    customer_name = serializers.CharField(source='policy.customer.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = [
            'id', 'claim_number', 'policy', 'policy_number', 'provider_name',
            'customer_name', 'invoice', 'invoice_number',
            'status', 'total_amount', 'covered_amount', 'patient_amount',
            'deductible_applied', 'submitted_at', 'approved_at', 'paid_at',
            'notes', 'created_at', 'items_count',
        ]

    def get_items_count(self, obj):
        return obj.items.count()


class ClaimDetailSerializer(serializers.ModelSerializer):
    items = ClaimItemSerializer(many=True, read_only=True)
    approvals = serializers.SerializerMethodField()
    policy_number = serializers.CharField(source='policy.policy_number', read_only=True)
    provider_name = serializers.CharField(source='policy.provider.name', read_only=True)
    customer_name = serializers.CharField(source='policy.customer.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = Claim
        fields = '__all__'

    def get_approvals(self, obj):
        return ClaimApprovalSerializer(obj.approvals.all(), many=True).data


class ClaimCreateSerializer(serializers.ModelSerializer):
    items = ClaimItemSerializer(many=True)

    class Meta:
        model = Claim
        fields = ['policy', 'invoice', 'total_amount', 'covered_amount',
                  'patient_amount', 'deductible_applied', 'notes', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        claim = Claim.objects.create(**validated_data)
        for item_data in items_data:
            ClaimItem.objects.create(claim=claim, **item_data)
        return claim


class ClaimApprovalSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(source='performed_by.first_name', read_only=True)

    class Meta:
        model = ClaimApproval
        fields = '__all__'
