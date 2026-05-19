from django.contrib import admin
from .models import InsuranceProvider, InsurancePolicy, Claim, ClaimItem, ClaimApproval


@admin.register(InsuranceProvider)
class InsuranceProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact_phone', 'is_active']
    search_fields = ['name', 'code']


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_number', 'provider', 'customer', 'policy_type',
                    'coverage_percentage', 'annual_limit', 'start_date', 'end_date', 'is_active']
    list_filter = ['policy_type', 'is_active', 'provider']
    search_fields = ['policy_number', 'customer__name']


class ClaimItemInline(admin.TabularInline):
    model = ClaimItem
    extra = 1


class ClaimApprovalInline(admin.TabularInline):
    model = ClaimApproval
    readonly_fields = ['created_at']
    extra = 0


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'policy', 'status', 'total_amount',
                    'covered_amount', 'submitted_at', 'approved_at']
    list_filter = ['status']
    search_fields = ['claim_number', 'policy__policy_number']
    inlines = [ClaimItemInline, ClaimApprovalInline]
