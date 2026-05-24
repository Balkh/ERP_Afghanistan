from django.contrib import admin
from .models import DeviceLicense, TrialSession


@admin.register(DeviceLicense)
class DeviceLicenseAdmin(admin.ModelAdmin):
    list_display = ['license_key', 'device_id', 'is_active', 'license_type',
                    'issued_to', 'issued_date', 'expires_date']
    list_filter = ['is_active', 'license_type']
    search_fields = ['license_key', 'device_id', 'issued_to']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TrialSession)
class TrialSessionAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'started_at', 'expires_at', 'extended', 'access_count']
    list_filter = ['extended']
    search_fields = ['device_id']
    readonly_fields = ['started_at', 'access_count']
