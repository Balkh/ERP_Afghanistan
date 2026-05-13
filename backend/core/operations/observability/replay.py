"""
Phase 5B.4 — Replay Visualization Engine.

Deterministic replay visualization with time-travel capability.
Read-only — renders historical state without modification.

Supports:
- Full system replay (time-travel mode)
- Single-aggregate replay
- Cross-domain replay
- Snapshot-based replay acceleration

Replay rules:
- Deterministic rendering only
- No interpretation layer
- No behavioral suggestions
"""
import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain, Event, ConsistencyResult
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.observability.models import (
    ReplayState, TimelineView, TimelineEntry, TraceObject,
)

logger = logging.getLogger('erp.observability.replay')

REPLAY_ENGINE_VERSION = "1.0.0"


class ReplayVisualizationEngine:
    """Deterministic replay engine for time-travel visualization.

    All replay outputs are read-only renderings of historical state.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def get_replay_state(
        self,
        from_sequence: int = 0,
        to_sequence: Optional[int] = None,
    ) -> ReplayState:
        """Get replay state for a sequence range.

        Args:
            from_sequence: Starting sequence (inclusive).
            to_sequence: Ending sequence (inclusive, None = latest).

        Returns:
            ReplayState with range information.
        """
        all_events = self._store.get_all()
        if to_sequence is None:
            to_sequence = len(all_events)

        events_in_range = [
            e for e in all_events
            if from_sequence <= self._get_event_position(e) <= to_sequence
        ]

        domains = set(e.domain.value for e in events_in_range)

        return ReplayState(
            from_sequence=from_sequence,
            to_sequence=to_sequence,
            current_sequence=from_sequence,
            total_events_in_range=len(events_in_range),
            domains_in_range=sorted(domains),
            is_complete=to_sequence >= len(all_events),
        )

    def render_at_sequence(self, sequence: int) -> List[TimelineEntry]:
        """Render system state as it appeared up to a given sequence.

        Time-travel: shows what the system looked like at sequence N.

        Args:
            sequence: The event sequence to render up to (inclusive).

        Returns:
            List of timeline entries representing state at that point.
        """
        events_up_to = [
            e for e in self._store.get_all()
            if e.sequence <= sequence
        ]

        entries = []
        for event in events_up_to:
            entries.append(TimelineEntry(
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp,
                sequence=event.sequence,
                source_type=event.source_type.value,
                summary=self._make_summary(event),
            ))

        return entries

    def render_aggregate_at_sequence(
        self,
        domain: Domain,
        aggregate_id: str,
        up_to_sequence: int,
    ) -> List[TimelineEntry]:
        """Render aggregate state as it appeared up to sequence N.

        Time-travel for a single aggregate.
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        events_up_to = [
            e for e in events if e.sequence <= up_to_sequence
        ]

        entries = []
        for event in events_up_to:
            entries.append(TimelineEntry(
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp,
                sequence=event.sequence,
                source_type=event.source_type.value,
                summary=self._make_summary(event),
            ))

        return entries

    def compute_replay_hash(self, replay: ReplayState) -> str:
        """Compute deterministic hash for a replay range.

        Ensures replay reproducibility.
        """
        h = hashlib.sha256()
        all_events = self._store.get_all()
        for i in range(replay.from_sequence, min(replay.to_sequence, len(all_events))):
            if i < len(all_events):
                h.update(f"{all_events[i].event_id}:{all_events[i].sequence}".encode())
        return h.hexdigest()

    def verify_replay_consistency(
        self,
        replay: ReplayState,
        expected_hash: str,
    ) -> bool:
        """Verify that a replay produces the expected hash.

        Deterministic — same range + same store = same hash.
        """
        return self.compute_replay_hash(replay) == expected_hash

    def _get_event_position(self, event: Event) -> int:
        """Get the ordinal position of an event in the store."""
        all_events = self._store.get_all()
        for i, e in enumerate(all_events):
            if e.event_id == event.event_id:
                return i
        return -1

    def _make_summary(self, event: Event) -> str:
        """Deterministic event summary."""
        p = event.payload
        summaries = {
            "batch_created": f"Batch: qty={p.get('initial_quantity', '?')}",
            "stock_movement": f"Move: {p.get('quantity', '?')} {p.get('direction', '')}",
            "stock_adjusted": f"Adjust: new={p.get('new_quantity', '?')}",
            "journal_entry_posted": f"JE: {p.get('description', '')[:40]}",
            "account_created": f"Acct: {p.get('account_code', '')}",
            "employee_hired": f"Hire: {p.get('name', '')}",
            "order_created": f"Order: {p.get('order_type', '')} ${p.get('total_amount', '?')}",
            "payment_received": f"Pay: ${p.get('amount', '?')}",
            "asset_acquired": f"Asset: ${p.get('cost', '?')}",
            "depreciation_booked": f"Depr: ${p.get('amount', '?')}",
        }
        return summaries.get(event.event_type, event.event_type)
