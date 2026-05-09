from rest_framework import serializers
from .models import BackupRecord, BackupSchedule, BackupLog, RestorePoint, RestoreValidation


class BackupRecordSerializer(serializers.ModelSerializer):
    file_size_mb = serializers.SerializerMethodField()
    database_size_mb = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)
    
    class Meta:
        model = BackupRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_file_size_mb(self, obj):
        return obj.file_size_mb
    
    def get_database_size_mb(self, obj):
        return obj.database_size_mb


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_run_at', 'next_run_at']


class BackupLogSerializer(serializers.ModelSerializer):
    backup_record_id = serializers.UUIDField(source='backup_record.id', read_only=True)
    schedule_id = serializers.UUIDField(source='schedule.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = BackupLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']


class CreateBackupSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, default='Manual backup')
    include_files = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[]
    )
    encrypted = serializers.BooleanField(required=False, default=True)
    compressed = serializers.BooleanField(required=False, default=True)


class RestoreBackupSerializer(serializers.Serializer):
    backup_path = serializers.CharField()
    target_db_path = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True)
    verify = serializers.BooleanField(required=False, default=True)


class RestoreValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestoreValidation
        fields = '__all__'
        read_only_fields = ['id', 'checked_at']


class RestorePointSerializer(serializers.ModelSerializer):
    validations = RestoreValidationSerializer(many=True, read_only=True)
    backup_record_filename = serializers.CharField(source='backup_record.filename', read_only=True)
    validated_by_username = serializers.CharField(source='validated_by.username', read_only=True)
    restored_by_username = serializers.CharField(source='restored_by.username', read_only=True)
    
    class Meta:
        model = RestorePoint
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']