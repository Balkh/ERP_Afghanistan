"""
Phase 17.5 — Unified Audit Collector.
Aggregates all audit sources into a single logical stream.
Non-destructive — existing audit models remain untouched.

Event sources:
- security.models.AuditLog (security app)
- audit.models.AuditTrail (audit app)
- Observability middleware logs
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("erp.audit.unified")


class UnifiedAuditCollector:
    """
    Aggregates audit events from all sources into one normalized structure.
    Does NOT delete or modify existing audit models.
    """

    @staticmethod
    def collect(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an audit event into the unified format.
        Accepts raw event dicts from any source.
        """
        return {
            "event_type": event.get("event_type", event.get("action", "unknown")),
            "actor_id": str(event.get("actor_id", event.get("user_id", ""))),
            "target_type": event.get("target_type", event.get("model_name", "")),
            "target_id": str(event.get("target_id", event.get("object_id", ""))),
            "company_id": str(event.get("company_id", "")) if event.get("company_id") else None,
            "description": event.get("description", event.get("message", "")),
            "metadata": event.get("metadata", event.get("details", {})),
            "timestamp": event.get("timestamp", datetime.utcnow().isoformat()),
            "source": event.get("source", "unknown"),
        }

    @staticmethod
    def collect_security_log(entry) -> Dict[str, Any]:
        """Normalize a security.models.AuditLog entry."""
        return UnifiedAuditCollector.collect({
            "event_type": getattr(entry, "action", getattr(entry, "event_type", "security_action")),
            "actor_id": str(getattr(entry, "user_id", getattr(entry, "actor_id", ""))),
            "target_type": getattr(entry, "content_type", getattr(entry, "model_name", "")),
            "target_id": str(getattr(entry, "object_id", "")),
            "company_id": str(getattr(entry, "company_id", "")) if getattr(entry, "company_id", None) else None,
            "description": getattr(entry, "description", getattr(entry, "message", "")),
            "metadata": getattr(entry, "metadata", getattr(entry, "details", {})),
            "timestamp": getattr(entry, "created_at", getattr(entry, "timestamp", datetime.utcnow().isoformat())),
            "source": "security.AuditLog",
        })

    @staticmethod
    def collect_event_log(entry) -> Dict[str, Any]:
        """Normalize an audit.models.AuditTrail or JournalEventLog entry."""
        return UnifiedAuditCollector.collect({
            "event_type": getattr(entry, "event_type", getattr(entry, "action", "audit_event")),
            "actor_id": str(getattr(entry, "actor_id", getattr(entry, "user_id", ""))),
            "target_type": getattr(entry, "target_type", getattr(entry, "model_name", "")),
            "target_id": str(getattr(entry, "target_id", getattr(entry, "object_id", ""))),
            "company_id": str(getattr(entry, "company_id", "")) if getattr(entry, "company_id", None) else None,
            "description": getattr(entry, "description", getattr(entry, "message", "")),
            "metadata": getattr(entry, "metadata", getattr(entry, "details", {})),
            "timestamp": getattr(entry, "created_at", getattr(entry, "timestamp", datetime.utcnow().isoformat())),
            "source": "audit.EventLog",
        })

    @staticmethod
    def collect_request_log(request, response) -> Dict[str, Any]:
        """Normalize an observability request log entry."""
        return UnifiedAuditCollector.collect({
            "event_type": "api_request",
            "actor_id": str(getattr(request, "user", None).id) if getattr(request, "user", None) and request.user.is_authenticated else "anonymous",
            "target_type": f"{request.method} {request.path}",
            "target_id": "",
            "company_id": getattr(request, "company_id", None),
            "description": f"{request.method} {request.path} -> {getattr(response, 'status_code', 0)}",
            "metadata": {
                "method": request.method,
                "path": request.path,
                "status_code": getattr(response, "status_code", 0),
                "query_params": dict(request.GET.items()) if hasattr(request, "GET") else {},
            },
            "timestamp": datetime.utcnow().isoformat(),
            "source": "observability.middleware",
        })
