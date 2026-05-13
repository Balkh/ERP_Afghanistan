"""
Phase 5B.4 — Event Trace Engine.

Reconstructs the full lifecycle of any entity from the Event Store.
Builds causation graphs, cross-domain links, and deterministic timelines.

Read-only. All outputs are derived from persisted events only.
"""
import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from core.operations.truth.models import Domain, Event
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.observability.models import (
    TraceObject, TraceEvent, CausationLink,
)

logger = logging.getLogger('erp.observability.trace')

TRACE_ENGINE_VERSION = "1.0.0"


class EventTraceEngine:
    """Reconstructs full entity lifecycles from Event Store.

    Capabilities:
    - Full event chain reconstruction by aggregate_id
    - Causation graph building (cause → effect)
    - Cross-domain event linking
    - Timeline reconstruction (strict deterministic order)
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def trace_aggregate(self, domain: Domain, aggregate_id: str) -> TraceObject:
        """Reconstruct full lifecycle of a single aggregate.

        Args:
            domain: The domain of the aggregate.
            aggregate_id: The aggregate ID.

        Returns:
            TraceObject with full event chain and causation graph.
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        if not events:
            return TraceObject(
                aggregate_id=aggregate_id,
                domain=domain.value,
                event_count=0,
                integrity_hash=hashlib.sha256(b"empty").hexdigest(),
            )

        trace_events = []
        causation_links: List[CausationLink] = []
        causation_ids: Set[str] = set()

        for event in events:
            trace_event = TraceEvent(
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                sequence=event.sequence,
                timestamp=event.timestamp,
                source_type=event.source_type.value,
                payload_summary={
                    k: v for k, v in event.payload.items()
                    if k in ("description", "reason", "status", "total_amount",
                             "quantity", "direction", "product_id", "order_type")
                },
                causation_id=event.metadata.get("causation_id", ""),
                correlation_id=event.metadata.get("correlation_id", ""),
            )
            trace_events.append(trace_event)

            if event.metadata.get("causation_id"):
                cause_id = event.metadata["causation_id"]
                causation_ids.add(cause_id)
                cause_event = self._store.get(cause_id)
                domain_crossing = (
                    cause_event is not None and cause_event.domain != event.domain
                )
                causation_links.append(CausationLink(
                    cause_event_id=cause_id,
                    effect_event_id=event.event_id,
                    relationship="DIRECT_CAUSE",
                    domain_crossing=domain_crossing,
                ))

        domain_map: Dict[str, List[str]] = defaultdict(list)
        for te in trace_events:
            domain_map[te.domain].append(te.event_id)

        h = hashlib.sha256()
        for te in trace_events:
            h.update(f"{te.event_id}:{te.sequence}".encode())
        integrity_hash = h.hexdigest()

        return TraceObject(
            aggregate_id=aggregate_id,
            domain=domain.value,
            root_event_id=trace_events[0].event_id if trace_events else "",
            full_event_chain=trace_events,
            causation_graph=causation_links,
            domain_participation_map=dict(domain_map),
            timestamp_range_start=trace_events[0].timestamp if trace_events else "",
            timestamp_range_end=trace_events[-1].timestamp if trace_events else "",
            event_count=len(trace_events),
            integrity_hash=integrity_hash,
        )

    def trace_by_event_id(self, event_id: str) -> Optional[TraceObject]:
        """Trace the full chain starting from a specific event ID.

        Follows causation links to build the full graph.
        """
        event = self._store.get(event_id)
        if event is None:
            return None

        domain = Domain(event.domain)
        return self.trace_aggregate(domain, event.aggregate_id)

    def build_causation_graph(self, event_id: str) -> Tuple[List[TraceEvent], List[CausationLink]]:
        """Build the causation graph for an event.

        Traces both forward (effects) and backward (causes).

        Returns:
            (nodes, edges) for the causation graph.
        """
        event = self._store.get(event_id)
        if event is None:
            return [], []

        nodes: Dict[str, TraceEvent] = {}
        edges: List[CausationLink] = []
        processed: Set[str] = set()
        queue: List[str] = [event_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in processed:
                continue
            processed.add(current_id)

            current = self._store.get(current_id)
            if current is None:
                continue

            trace_event = TraceEvent(
                event_id=current.event_id,
                event_type=current.event_type,
                domain=current.domain.value,
                aggregate_id=current.aggregate_id,
                sequence=current.sequence,
                timestamp=current.timestamp,
                source_type=current.source_type.value,
            )
            nodes[current_id] = trace_event

            causation_id = current.metadata.get("causation_id", "")
            if causation_id and causation_id not in processed:
                cause = self._store.get(causation_id)
                domain_crossing = cause is not None and cause.domain != current.domain
                edges.append(CausationLink(
                    cause_event_id=causation_id,
                    effect_event_id=current_id,
                    relationship="DIRECT_CAUSE",
                    domain_crossing=domain_crossing,
                ))
                queue.append(causation_id)

            for other in self._store.get_all():
                if other.metadata.get("causation_id") == current_id:
                    if other.event_id not in processed:
                        domain_crossing = other.domain != current.domain
                        edges.append(CausationLink(
                            cause_event_id=current_id,
                            effect_event_id=other.event_id,
                            relationship="DERIVED",
                            domain_crossing=domain_crossing,
                        ))
                        queue.append(other.event_id)

        return list(nodes.values()), edges

    def find_cross_domain_events(
        self,
        domain: Domain,
        aggregate_id: str,
    ) -> Dict[str, List[TraceEvent]]:
        """Find events in other domains linked to this aggregate.

        Uses correlation_id and causation_id metadata to trace
        cross-domain relationships.
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        correlation_ids: Set[str] = set()
        for e in events:
            cid = e.metadata.get("correlation_id", "")
            if cid:
                correlation_ids.add(cid)

        cross_domain: Dict[str, List[TraceEvent]] = defaultdict(list)
        for cid in correlation_ids:
            for other in self._store.get_all():
                if other.metadata.get("correlation_id") == cid and other.domain != domain:
                    cross_domain[other.domain.value].append(TraceEvent(
                        event_id=other.event_id,
                        event_type=other.event_type,
                        domain=other.domain.value,
                        aggregate_id=other.aggregate_id,
                        sequence=other.sequence,
                        timestamp=other.timestamp,
                        source_type=other.source_type.value,
                    ))

        return dict(cross_domain)

    def get_trace_integrity(self, trace: TraceObject) -> bool:
        """Verify that a trace's integrity hash matches current store state."""
        h = hashlib.sha256()
        for te in trace.full_event_chain:
            event = self._store.get(te.event_id)
            if event is None:
                return False
            h.update(f"{event.event_id}:{event.sequence}".encode())
        return h.hexdigest() == trace.integrity_hash
