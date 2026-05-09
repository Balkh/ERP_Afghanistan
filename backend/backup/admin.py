from django.contrib import admin
from .models import BackupRecord, BackupSchedule, BackupLog


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = ['filename', 'status', 'backup_type', 'file_size_mb', 'created_at', 'created_by']
    list_filter = ['status', 'backup_type', 'encrypted', 'compressed']
    search_fields = ['filename', 'description', 'checksum']
    readonly_fields = ['id', 'created_at', 'updated_at', 'checksum']
    date_hierarchy = 'created_at'


@admin.register(BackupSchedule)
class BackupScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'frequency', 'time', 'enabled', 'last_run_at', 'next_run_at']
    list_filter = ['frequency', 'enabled']
    search_fields = ['name', 'description']


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'level', 'event', 'message']
    list_filter = ['level', 'event']
    search_fields = ['message']
    date_hierarchy = 'timestamp'