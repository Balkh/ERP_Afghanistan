from decimal import Decimal
from rest_framework import serializers
from accounting.models import Account, JournalEntry, JournalEntryLine, JournalEventLog, FiscalPeriod, FiscalPeriodCloseLog


class AccountSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source='parent.code', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    level = serializers.IntegerField(read_only=True)
    full_path = serializers.CharField(read_only=True)
    is_leaf = serializers.BooleanField(read_only=True)
    has_children = serializers.BooleanField(read_only=True)
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'code', 'name', 'account_type', 'account_category',
            'parent', 'parent_code', 'parent_name', 'description',
            'is_active', 'is_system', 'balance', 'total_balance',
            'level', 'full_path', 'is_leaf', 'has_children', 'children_count',
            'currency', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at']
        extra_kwargs = {
            'code': {'required': True},
            'name': {'required': True},
            'account_type': {'required': True},
        }

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def validate_code(self, value):
        """Ensure account code is unique and numeric."""
        if not value.isdigit():
            raise serializers.ValidationError('Account code must contain only digits.')

        instance = self.instance
        if Account.objects.filter(code=value).exclude(id=instance.id if instance else None).exists():
            raise serializers.ValidationError('Account with this code already exists.')
        return value

    def validate_parent(self, value):
        """Validate parent account."""
        instance = self.instance
        if value and instance:
            if value.id == instance.id:
                raise serializers.ValidationError('An account cannot be its own parent.')

            current = value
            visited = set()
            while current is not None:
                if current.id in visited:
                    raise serializers.ValidationError('Circular reference detected.')
                visited.add(current.id)
                if current.id == instance.id:
                    raise serializers.ValidationError('Circular reference detected.')
                current = current.parent
        return value


class AccountTreeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    account_type = serializers.CharField()
    account_category = serializers.CharField()
    balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    level = serializers.IntegerField()
    is_leaf = serializers.BooleanField()
    is_system = serializers.BooleanField()
    children = serializers.ListField()


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.code', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = JournalEntryLine
        fields = [
            'id', 'account', 'account_code', 'account_name',
            'debit', 'credit', 'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'account': {'required': True},
        }

    def validate(self, data):
        """Validate debit/credit rules."""
        debit = data.get('debit', Decimal('0.00'))
        credit = data.get('credit', Decimal('0.00'))

        if debit < 0 or credit < 0:
            raise serializers.ValidationError('Debit and credit amounts cannot be negative.')
        if debit == 0 and credit == 0:
            raise serializers.ValidationError('Either debit or credit must be positive.')
        if debit > 0 and credit > 0:
            raise serializers.ValidationError('Cannot have both debit and credit on the same line.')

        return data


class JournalEventLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()
    entry_number = serializers.CharField(source='entry.entry_number', read_only=True)

    class Meta:
        model = JournalEventLog
        fields = [
            'id', 'entry', 'entry_number', 'event_type', 'user', 'user_display',
            'timestamp', 'reference', 'notes', 'ip_address'
        ]
        read_only_fields = ['id', 'timestamp', 'ip_address']

    def get_user_display(self, obj):
        return str(obj.user) if obj.user else 'System'


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True, read_only=True)
    writable_lines = JournalEntryLineSerializer(many=True, write_only=True)
    total_debit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)
    event_history = serializers.SerializerMethodField()
    can_modify_field = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'entry_number', 'entry_date', 'entry_type', 'description',
            'reference', 'is_posted', 'is_active',
            'created_by', 'posted_by', 'reversed_by_entry',
            'source_module', 'source_document', 'change_reason',
            'total_debit', 'total_credit', 'is_balanced',
            'lines', 'writable_lines', 'event_history', 'can_modify_field',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_posted', 'created_by']
        extra_kwargs = {
            'entry_number': {'required': True},
            'entry_date': {'required': True},
            'entry_type': {'required': True},
            'description': {'required': True},
        }

    def get_event_history(self, obj):
        events = JournalEventLog.objects.filter(entry=obj).order_by('-timestamp')[:20]
        return JournalEventLogSerializer(events, many=True).data

    def get_can_modify_field(self, obj):
        return obj.can_modify()

    def create(self, validated_data):
        """Create journal entry with lines."""
        lines_data = validated_data.pop('writable_lines', [])
        entry = JournalEntry.objects.create(**validated_data)

        for line_data in lines_data:
            JournalEntryLine.objects.create(entry=entry, **line_data)

        return entry

    def update(self, instance, validated_data):
        """Update journal entry with lines."""
        if instance.is_posted:
            raise serializers.ValidationError('Posted journal entries cannot be modified.')

        lines_data = validated_data.pop('writable_lines', None)
        instance = super().update(instance, validated_data)

        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                JournalEntryLine.objects.create(entry=instance, **line_data)

        return instance

    def validate(self, data):
        """Validate journal entry is balanced."""
        instance = self.instance
        lines = data.get('writable_lines', [])

        if lines:
            total_debit = sum(line.get('debit', Decimal('0')) for line in lines)
            total_credit = sum(line.get('credit', Decimal('0')) for line in lines)

            if total_debit != total_credit:
                raise serializers.ValidationError(
                    f'Journal entry must be balanced. Debits: {total_debit}, Credits: {total_credit}'
                )

        return data


class FiscalPeriodSerializer(serializers.ModelSerializer):
    can_modify = serializers.BooleanField(read_only=True)
    can_post = serializers.BooleanField(read_only=True)
    journal_entry_count = serializers.SerializerMethodField()
    close_log_count = serializers.SerializerMethodField()

    class Meta:
        model = FiscalPeriod
        fields = [
            'id', 'name', 'code', 'start_date', 'end_date', 'status',
            'is_locked', 'locked_at', 'locked_by', 'notes',
            'closing_balance_carried_forward', 'closing_completed_at',
            'closing_completed_by', 'can_modify', 'can_post',
            'journal_entry_count', 'close_log_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_locked', 'locked_at']

    def get_journal_entry_count(self, obj):
        return JournalEntry.objects.filter(
            entry_date__gte=obj.start_date,
            entry_date__lte=obj.end_date,
        ).count()

    def get_close_log_count(self, obj):
        return obj.close_logs.count()

    def validate(self, data):
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError('End date must be after start date.')
        return data


class FiscalPeriodCloseLogSerializer(serializers.ModelSerializer):
    period_code = serializers.CharField(source='period.code', read_only=True)
    period_name = serializers.CharField(source='period.name', read_only=True)
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FiscalPeriodCloseLog
        fields = [
            'id', 'period', 'period_code', 'period_name', 'action',
            'reason', 'previous_status', 'new_status', 'performed_by',
            'performed_by_name', 'validation_summary', 'affected_entries_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_performed_by_name(self, obj):
        return str(obj.performed_by) if obj.performed_by else 'System'


class PeriodClosingReadinessSerializer(serializers.Serializer):
    period_id = serializers.UUIDField()
    period_code = serializers.CharField()
    period_name = serializers.CharField()
    is_ready = serializers.BooleanField()
    blocker_count = serializers.IntegerField()
    warning_count = serializers.IntegerField()
    blockers = serializers.ListField()
    warnings = serializers.ListField()
    summary = serializers.JSONField()


class PeriodCloseRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=10)
    force = serializers.BooleanField(default=False)


class PeriodReopenRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=10)
