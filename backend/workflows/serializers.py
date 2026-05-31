"""Workflow API serializers."""
from rest_framework import serializers
from workflows.models import WorkflowInstance, ApprovalChain, ApprovalRequest


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    """Full workflow instance for CRUD."""

    pending_approver_name = serializers.SerializerMethodField()
    state_display = serializers.CharField(source="get_current_state_display", read_only=True)

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "content_type",
            "object_id",
            "object_reference",
            "current_state",
            "state_display",
            "previous_state",
            "title",
            "amount",
            "currency",
            "is_active",
            "priority",
            "pending_approver",
            "pending_approver_name",
            "created_at",
            "updated_at",
            "submitted_at",
            "approved_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_pending_approver_name(self, obj):
        if obj.pending_approver_id and obj.pending_approver:
            return obj.pending_approver.get_full_name() or obj.pending_approver.username
        return None


class WorkflowInstanceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for intelligence dashboards."""

    pending_approver_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = [
            "id",
            "content_type",
            "object_id",
            "object_reference",
            "current_state",
            "title",
            "amount",
            "created_at",
            "pending_approver_name",
        ]

    def get_pending_approver_name(self, obj):
        if obj.pending_approver_id and obj.pending_approver:
            return obj.pending_approver.get_full_name() or obj.pending_approver.username
        return "System"


class ApprovalChainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalChain
        fields = "__all__"


class ApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRequest
        fields = "__all__"
