"""
BFF bundle for Intelligence Hub + Control Center (single round-trip).
"""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.operations.control_center import (
    ControlCenterAggregator,
    QuickStatsProvider,
    JobsStatsProvider,
)
from core.operations.operational_intelligence import CachedIntelligenceAggregator
from core.operations.signal_coordinator import get_active_signals
from workflows.models import WorkflowInstance
from workflows.serializers import WorkflowInstanceListSerializer


def _ok(data):
    return {"status": "ok", "data": data}


def _workflow_instances_payload(limit=50):
    qs = WorkflowInstance.objects.filter(is_active=True).select_related(
        "pending_approver", "created_by"
    ).order_by("-created_at")[:limit]
    return WorkflowInstanceListSerializer(qs, many=True).data


def _correlation_sources(limit_invoices=20, limit_other=50):
    """Lightweight rows for correlation engine (no N+1)."""
    from sales.models import SalesInvoice
    from accounting.models import JournalEntry
    from sales.models import CustomerPayment

    invoices = list(
        SalesInvoice.objects.filter(is_active=True)
        .select_related("customer")
        .order_by("-created_at")[:limit_invoices]
        .values("id", "invoice_number", "status", "total_amount")
    )
    workflows = _workflow_instances_payload(limit=limit_other)
    journals = list(
        JournalEntry.objects.filter(is_active=True)
        .order_by("-entry_date")[:limit_other]
        .values("id", "description", "entry_number", "is_posted")
    )
    payments = [
        {
            "id": str(p["id"]),
            "invoice": str(p["invoice_id"]) if p.get("invoice_id") else None,
            "amount": p["amount"],
        }
        for p in CustomerPayment.objects.order_by("-payment_date")[:limit_other].values(
            "id", "invoice_id", "amount"
        )
    ]
    return {
        "invoices": invoices,
        "workflows": workflows,
        "journals": journals,
        "payments": payments,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def intelligence_hub_bundle(request):
    """
    Single aggregated payload for Hub overview, Control Center tab, Workflow, Correlation.
    Replaces 9+ separate HTTP calls from the desktop client.
    """
    try:
        signals = get_active_signals(
            request.query_params.get("category"),
            request.query_params.get("min_severity"),
        )
        pending = WorkflowService_list_pending(request.user)
        bundle = {
            "health": ControlCenterAggregator.get_live_health(),
            "stats": QuickStatsProvider.get_kpis(),
            "intelligence": CachedIntelligenceAggregator.get_all_intelligence(),
            "signals": signals if isinstance(signals, list) else signals.get("signals", signals),
            "jobs": JobsStatsProvider.get_job_stats(),
            "financial": ControlCenterAggregator.get_financial_dashboard(),
            "inventory": ControlCenterAggregator.get_inventory_dashboard(),
            "operations": ControlCenterAggregator.get_operations_dashboard(),
            "workflow_instances": _workflow_instances_payload(limit=100),
            "workflows_pending": pending,
            "correlation_sources": _correlation_sources(),
            "generated_at": timezone.now().isoformat(),
        }
        return Response(bundle)
    except Exception as exc:
        return Response(
            {"error": str(exc), "generated_at": timezone.now().isoformat()},
            status=500,
        )


def WorkflowService_list_pending(user):
    """Pending approvals summary (same shape as my-pending endpoint)."""
    from workflows.models import ApprovalRequest

    if not user or not user.is_authenticated:
        return {"pending": [], "overdue": []}

    now = timezone.now()
    pending_qs = ApprovalRequest.objects.filter(
        approver=user,
        status="PENDING",
        due_date__gte=now,
    ).select_related("workflow_instance", "requested_by")[:50]

    overdue_qs = ApprovalRequest.objects.filter(
        approver=user,
        status="PENDING",
        due_date__lt=now,
    ).select_related("workflow_instance", "requested_by")[:50]

    def _row(r):
        wf = r.workflow_instance
        return {
            "id": str(r.id),
            "workflow_id": str(wf.id),
            "entity_type": wf.content_type,
            "entity_ref": wf.object_reference,
            "title": wf.title,
        }

    return {
        "pending": [_row(r) for r in pending_qs],
        "overdue": [_row(r) for r in overdue_qs],
    }
