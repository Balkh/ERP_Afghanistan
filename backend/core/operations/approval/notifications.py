"""
Phase 5B.2 — Deterministic Notification & Reminder System.

STRICTLY NON-COERCIVE. Fixed, bounded, non-adaptive reminders.
NEVER behavioral influence. NEVER urgency amplification.

Safety guarantees:
- Fixed reminder intervals (non-adaptive)
- Bounded total reminders (max N)
- Deterministic scheduling (same time → same reminders)
- No priority/urgency/salience amplification
- No behavioral pressure
- No notification frequency optimization
- Informational only
"""
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Deque

from core.operations.approval.models import (
    ApprovalState, ApprovalWorkflow, NotificationRecord,
    SIMULATION_CONTEXT_MARKER,
)

logger = logging.getLogger('erp.approval.notifications')

NOTIFICATION_SYSTEM_VERSION = "1.0.0"
MAX_NOTIFICATION_HISTORY = 5000
MAX_QUEUED_NOTIFICATIONS = 1000


class NotificationRegistry:
    """Deterministic, bounded notification registry.

    All notifications are:
    - Fixed interval (no adaptation)
    - Bounded count (max_reminders)
    - Non-prioritized (no sorting by urgency)
    - Informational only
    """

    def __init__(self):
        self._history: Deque[NotificationRecord] = deque(maxlen=MAX_NOTIFICATION_HISTORY)
        self._queue: Deque[NotificationRecord] = deque(maxlen=MAX_QUEUED_NOTIFICATIONS)

    def record_notification(self, notification: NotificationRecord) -> None:
        """Record a notification in history."""
        if notification.context_marker != SIMULATION_CONTEXT_MARKER:
            raise ValueError("Notification missing simulation context marker")
        self._history.append(notification)

    def enqueue(self, notification: NotificationRecord) -> None:
        """Queue a notification for delivery."""
        self._queue.append(notification)

    def dequeue(self) -> Optional[NotificationRecord]:
        """Get next notification from queue (FIFO)."""
        if not self._queue:
            return None
        return self._queue.popleft()

    def get_history(self, workflow_id: Optional[str] = None) -> List[NotificationRecord]:
        """Get notification history, optionally filtered by workflow.

        Returns in insertion order — NO priority sorting.
        """
        if workflow_id:
            return [n for n in self._history if n.workflow_id == workflow_id]
        return list(self._history)

    def get_queue_length(self) -> int:
        return len(self._queue)

    def count_by_workflow(self, workflow_id: str) -> int:
        return sum(1 for n in self._history if n.workflow_id == workflow_id)

    def clear(self) -> None:
        self._history.clear()
        self._queue.clear()

    def replay_rebuild(self, history: List[NotificationRecord]) -> None:
        """Rebuild notification history from replay data."""
        self.clear()
        for n in history:
            self._history.append(n)


# Global notification registry
_registry: Optional[NotificationRegistry] = None


def get_registry() -> NotificationRegistry:
    global _registry
    if _registry is None:
        _registry = NotificationRegistry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None


def generate_reminders(workflow: ApprovalWorkflow) -> List[NotificationRecord]:
    """Generate deterministic reminders for a workflow.

    Reminder schedule is FIXED — determined by config, never adaptive.
    Same workflow + same config = same reminders.

    Args:
        workflow: The approval workflow.

    Returns:
        List of reminder notifications to send.
    """
    if workflow.state not in (ApprovalState.PENDING, ApprovalState.UNDER_REVIEW, ApprovalState.ESCALATED):
        return []

    if workflow.config.reminder_interval_minutes <= 0:
        return []

    max_reminders = workflow.config.max_reminders
    if max_reminders <= 0:
        return []

    registry = get_registry()
    existing_count = registry.count_by_workflow(workflow.workflow_id)

    if existing_count >= max_reminders:
        return []

    reminders_to_send = max_reminders - existing_count
    if reminders_to_send <= 0:
        return []

    created_at = datetime.fromisoformat(workflow.created_at.replace("Z", "+00:00")).replace(tzinfo=None)
    now = datetime.utcnow()
    elapsed_minutes = (now - created_at).total_seconds() / 60.0

    interval = workflow.config.reminder_interval_minutes
    expected_reminders = int(elapsed_minutes / interval)

    if expected_reminders <= existing_count:
        return []

    new_reminders = []
    for i in range(existing_count, min(expected_reminders, max_reminders)):
        notification = NotificationRecord(
            workflow_id=workflow.workflow_id,
            recipient_id="",  # Would be assigned by delivery system
            notification_type="REMINDER",
            message=(
                f"Approval workflow {workflow.workflow_id} "
                f"({workflow.action_type}, risk={workflow.risk_level}) "
                f"is in state {workflow.state.value}. "
                f"Reminder {i + 1}/{max_reminders}."
            ),
            interval_index=i,
        )
        registry.record_notification(notification)
        new_reminders.append(notification)

    return new_reminders


def generate_status_notification(
    workflow: ApprovalWorkflow,
    notification_type: str,
) -> NotificationRecord:
    """Generate a single status change notification.

    Args:
        workflow: The workflow with the state change.
        notification_type: Type of notification (STATUS_CHANGE, etc.)

    Returns:
        A deterministic notification record.
    """
    message_map = {
        "CREATED": f"Approval workflow created for {workflow.action_type} (risk={workflow.risk_level})",
        "APPROVED": f"Workflow {workflow.workflow_id} has been APPROVED",
        "REJECTED": f"Workflow {workflow.workflow_id} has been REJECTED",
        "ESCALATED": f"Workflow {workflow.workflow_id} has been ESCALATED",
        "EXPIRED": f"Workflow {workflow.workflow_id} has EXPIRED (timeout)",
        "CANCELLED": f"Workflow {workflow.workflow_id} has been CANCELLED",
        "STATUS_CHANGE": f"Workflow {workflow.workflow_id} is now {workflow.state.value}",
    }

    message = message_map.get(notification_type, message_map["STATUS_CHANGE"])

    notification = NotificationRecord(
        workflow_id=workflow.workflow_id,
        notification_type=notification_type,
        message=message,
    )

    registry = get_registry()
    registry.record_notification(notification)
    return notification


def get_notification_summary(workflow_id: Optional[str] = None) -> Dict[str, Any]:
    """Get deterministic notification summary.

    Informational only. NO behavioral influence.
    """
    registry = get_registry()
    if workflow_id:
        notifications = registry.get_history(workflow_id)
        return {
            "workflow_id": workflow_id,
            "total_notifications": len(notifications),
            "reminder_count": sum(1 for n in notifications if n.notification_type == "REMINDER"),
            "status_changes": sum(1 for n in notifications if n.notification_type != "REMINDER"),
            "context_marker": SIMULATION_CONTEXT_MARKER,
        }
    return {
        "total_notifications": len(registry.get_history()),
        "queued_notifications": registry.get_queue_length(),
        "notification_system_version": NOTIFICATION_SYSTEM_VERSION,
        "context_marker": SIMULATION_CONTEXT_MARKER,
    }
