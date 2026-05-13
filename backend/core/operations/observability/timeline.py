"""
Phase 5B.4 — Operational Timeline Renderer.

Creates deterministic, ordered timeline views of system events.

Strict rules:
- Ordered by timestamp + sequence
- No weighting or prioritization
- No salience amplification
- Grouped by domain (optional view only)
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.observability.models import (
    TimelineView, TimelineEntry,
)

logger = logging.getLogger('erp.observability.timeline')

TIMELINE_ENGINE_VERSION = "1.0.0"


class OperationalTimelineRenderer:
    """Deterministic timeline rendering from Event Store.

    All timelines are:
    - Strictly ordered by (timestamp, sequence)
    - Unweighted (no priority/salience)
    - Deterministic (same events → same timeline)
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def render_timeline(
        self,
        from_timestamp: str = "",
        to_timestamp: str = "",
        domains: Optional[List[Domain]] = None,
        source_types: Optional[List[str]] = None,
        max_entries: int = 1000,
    ) -> TimelineView:
        """Render a deterministic timeline of events.

        Args:
            from_timestamp: Start of time range (inclusive).
            to_timestamp: End of time range (inclusive).
            domains: Filter to specific domains (None = all).
            source_types: Filter to specific source types (None = all).
            max_entries: Maximum entries to return.

        Returns:
            Deterministic TimelineView.
        """
        all_events = self._store.get_all()

        if from_timestamp:
            all_events = [e for e in all_events if e.timestamp >= from_timestamp]
        if to_timestamp:
            all_events = [e for e in all_events if e.timestamp <= to_timestamp]
        if domains:
            domain_values = [d.value for d in domains]
            all_events = [e for e in all_events if e.domain.value in domain_values]
        if source_types:
            all_events = [e for e in all_events if e.source_type.value in source_types]

        all_events.sort(key=lambda e: (e.timestamp, e.sequence))

        entries = []
        for event in all_events[:max_entries]:
            summary = self._make_summary(event)
            entries.append(TimelineEntry(
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp,
                sequence=event.sequence,
                source_type=event.source_type.value,
                summary=summary,
            ))

        domains_present = sorted(set(e.domain for e in entries))
        source_types_present = sorted(set(e.source_type for e in entries))

        return TimelineView(
            from_timestamp=from_timestamp or (all_events[0].timestamp if all_events else ""),
            to_timestamp=to_timestamp or (all_events[-1].timestamp if all_events else ""),
            entries=entries,
            total_entries=len(entries),
            domains_present=domains_present,
            source_types_present=source_types_present,
        )

    def render_aggregate_timeline(
        self,
        domain: Domain,
        aggregate_id: str,
    ) -> TimelineView:
        """Render timeline for a single aggregate.

        Deterministic — same aggregate always produces same timeline.
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        events.sort(key=lambda e: (e.timestamp, e.sequence))

        entries = []
        for event in events:
            summary = self._make_summary(event)
            entries.append(TimelineEntry(
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp,
                sequence=event.sequence,
                source_type=event.source_type.value,
                summary=summary,
            ))

        return TimelineView(
            from_timestamp=entries[0].timestamp if entries else "",
            to_timestamp=entries[-1].timestamp if entries else "",
            entries=entries,
            total_entries=len(entries),
            domains_present=[domain.value] if entries else [],
            source_types_present=sorted(set(e.source_type for e in entries)),
        )

    def render_domain_timeline(
        self,
        domain: Domain,
        from_timestamp: str = "",
        to_timestamp: str = "",
        max_entries: int = 1000,
    ) -> TimelineView:
        """Render timeline filtered to a single domain."""
        return self.render_timeline(
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            domains=[domain],
            max_entries=max_entries,
        )

    def render_cross_domain_timeline(
        self,
        correlation_id: str,
    ) -> TimelineView:
        """Render timeline of all events sharing a correlation ID."""
        matching = []
        for event in self._store.get_all():
            if event.metadata.get("correlation_id") == correlation_id:
                matching.append(event)

        matching.sort(key=lambda e: (e.timestamp, e.sequence))

        entries = []
        for event in matching:
            summary = self._make_summary(event)
            entries.append(TimelineEntry(
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp,
                sequence=event.sequence,
                source_type=event.source_type.value,
                summary=summary,
            ))

        return TimelineView(
            entries=entries,
            total_entries=len(entries),
            domains_present=sorted(set(e.domain for e in entries)),
            source_types_present=sorted(set(e.source_type for e in entries)),
        )

    def _make_summary(self, event: Any) -> str:
        """Generate a deterministic text summary for an event.
        
        Summaries are purely informational — no behavioral influence.
        """
        p = event.payload
        et = event.event_type

        summaries = {
            "batch_created": f"Batch created: qty={p.get('initial_quantity', '?')}",
            "stock_movement": f"Stock moved: {p.get('quantity', '?')} {p.get('direction', '')}",
            "stock_reconciled": f"Stock reconciled: variance={p.get('variance', '?')}",
            "stock_adjusted": f"Stock adjusted: new_qty={p.get('new_quantity', '?')}",
            "journal_entry_posted": f"JE posted: {p.get('description', '')[:60]}",
            "journal_entry_reversed": f"JE reversed: {p.get('reason', '')[:60]}",
            "account_created": f"Account: {p.get('account_code', '')} {p.get('account_name', '')}",
            "employee_hired": f"Hired: {p.get('name', '')} as {p.get('position', '')}",
            "employee_terminated": f"Terminated: {p.get('reason', '')[:60]}",
            "attendance_recorded": f"Attendance: {p.get('type', '')} on {p.get('date', '')}",
            "payroll_processed": f"Payroll: {p.get('period', '')} net={p.get('net_pay', '?')}",
            "order_created": f"Order created: type={p.get('order_type', '')} total={p.get('total_amount', '?')}",
            "order_approved": f"Order approved by: {p.get('approver_id', '?')}",
            "order_cancelled": f"Order cancelled: {p.get('reason', '')[:60]}",
            "payment_received": f"Payment: {p.get('amount', '?')} via {p.get('method', '?')}",
            "goods_dispatched": "Goods dispatched",
            "goods_received": "Goods received",
            "asset_acquired": f"Asset acquired: cost={p.get('cost', '?')}",
            "depreciation_booked": f"Depreciation: {p.get('amount', '?')} period={p.get('period', '')}",
            "asset_disposed": f"Asset disposed: gain_loss={p.get('gain_loss', '?')}",
            "asset_revalued": f"Asset revalued: new_value={p.get('new_value', '?')}",
        }
        return summaries.get(et, f"{et}: {str(p)[:80]}")
