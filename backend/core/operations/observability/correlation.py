"""
Phase 5B.4 — Cross-Domain Correlation Engine.

Builds relationships between domains:
- accounting ↔ inventory
- HR ↔ payroll ↔ accounting
- sales ↔ inventory ↔ accounting
- fixed assets ↔ depreciation ↔ accounting

Read-only. All outputs are derived from Event Store data.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from core.operations.truth.models import Domain, Event
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.observability.models import (
    CorrelationGraph, TraceEvent, CausationLink,
)

logger = logging.getLogger('erp.observability.correlation')

CORRELATION_ENGINE_VERSION = "1.0.0"

# Known cross-domain correlation patterns
CORRELATION_PATTERNS = {
    ("sales_purchase", "inventory"): {
        "description": "Order fulfillment triggers stock movements",
        "forward_events": ["goods_dispatched", "goods_received"],
        "reverse_events": ["stock_movement", "stock_adjusted"],
    },
    ("inventory", "accounting"): {
        "description": "Stock movements trigger journal entries",
        "forward_events": ["stock_movement", "stock_adjusted"],
        "reverse_events": ["journal_entry_posted"],
    },
    ("sales_purchase", "accounting"): {
        "description": "Payments and orders trigger journal entries",
        "forward_events": ["payment_received", "payment_refunded", "order_created"],
        "reverse_events": ["journal_entry_posted"],
    },
    ("hr", "accounting"): {
        "description": "Payroll processing triggers journal entries",
        "forward_events": ["payroll_processed"],
        "reverse_events": ["journal_entry_posted"],
    },
    ("fixed_assets", "accounting"): {
        "description": "Asset lifecycle triggers journal entries",
        "forward_events": ["asset_acquired", "depreciation_booked", "asset_disposed"],
        "reverse_events": ["journal_entry_posted"],
    },
    ("sales_purchase", "hr"): {
        "description": "Order approvals involve HR/employee records",
        "forward_events": ["order_approved"],
        "reverse_events": ["employee_role_changed"],
    },
}


class CrossDomainCorrelationEngine:
    """Builds correlation graphs across domain boundaries.

    Uses:
    - correlation_id in event metadata for explicit linking
    - causation_id for cause → effect chains
    - Known correlation patterns for domain pairs
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def correlate_by_correlation_id(self, correlation_id: str) -> CorrelationGraph:
        """Build correlation graph from a correlation ID."""
        nodes: List[TraceEvent] = []
        edges: List[CausationLink] = []
        domains: Set[str] = set()

        for event in self._store.get_all():
            if event.metadata.get("correlation_id") == correlation_id:
                nodes.append(TraceEvent(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    domain=event.domain.value,
                    aggregate_id=event.aggregate_id,
                    sequence=event.sequence,
                    timestamp=event.timestamp,
                    source_type=event.source_type.value,
                ))
                domains.add(event.domain.value)

                cause_id = event.metadata.get("causation_id", "")
                if cause_id:
                    cause_event = self._store.get(cause_id)
                    domain_crossing = cause_event is not None and cause_event.domain != event.domain
                    edges.append(CausationLink(
                        cause_event_id=cause_id,
                        effect_event_id=event.event_id,
                        relationship="DIRECT_CAUSE",
                        domain_crossing=domain_crossing,
                    ))

        root = nodes[0].event_id if nodes else ""
        return CorrelationGraph(
            root_event_id=root,
            nodes=nodes,
            edges=edges,
            domains_involved=sorted(domains),
            dependency_clusters=self._build_clusters(domains),
        )

    def correlate_by_event_id(self, event_id: str) -> CorrelationGraph:
        """Build correlation graph starting from a single event."""
        event = self._store.get(event_id)
        if event is None:
            return CorrelationGraph(root_event_id=event_id)

        correlation_id = event.metadata.get("correlation_id", "")
        if correlation_id:
            return self.correlate_by_correlation_id(correlation_id)

        domain = Domain(event.domain)
        agg_id = event.aggregate_id

        linked_events = self._find_linked_events(domain, agg_id)
        nodes = [
            TraceEvent(
                event_id=e.event_id,
                event_type=e.event_type,
                domain=e.domain.value,
                aggregate_id=e.aggregate_id,
                sequence=e.sequence,
                timestamp=e.timestamp,
                source_type=e.source_type.value,
            )
            for e in linked_events
        ]

        domains = set(e.domain.value for e in linked_events)
        edges = self._build_edges(linked_events)

        return CorrelationGraph(
            root_event_id=event_id,
            nodes=nodes,
            edges=edges,
            domains_involved=sorted(domains),
            dependency_clusters=self._build_clusters(domains),
        )

    def correlate_domain_pair(
        self,
        domain_a: Domain,
        domain_b: Domain,
    ) -> CorrelationGraph:
        """Find all correlation links between two domains."""
        pattern = CORRELATION_PATTERNS.get((domain_a.value, domain_b.value))
        if pattern is None:
            pattern = CORRELATION_PATTERNS.get((domain_b.value, domain_a.value))

        nodes: List[TraceEvent] = []
        edges: List[CausationLink] = []
        domains: Set[str] = {domain_a.value, domain_b.value}
        processed_pairs: Set[Tuple[str, str]] = set()

        all_events_a = self._store.get_by_domain(domain_a)
        all_events_b = self._store.get_by_domain(domain_b)

        for e_a in all_events_a:
            for e_b in all_events_b:
                pair = (e_a.event_id, e_b.event_id)
                if pair in processed_pairs:
                    continue
                processed_pairs.add(pair)

                if self._events_are_linked(e_a, e_b):
                    nodes.append(TraceEvent(
                        event_id=e_a.event_id, event_type=e_a.event_type,
                        domain=e_a.domain.value, aggregate_id=e_a.aggregate_id,
                        sequence=e_a.sequence, timestamp=e_a.timestamp,
                        source_type=e_a.source_type.value,
                    ))
                    nodes.append(TraceEvent(
                        event_id=e_b.event_id, event_type=e_b.event_type,
                        domain=e_b.domain.value, aggregate_id=e_b.aggregate_id,
                        sequence=e_b.sequence, timestamp=e_b.timestamp,
                        source_type=e_b.source_type.value,
                    ))
                    edges.append(CausationLink(
                        cause_event_id=e_a.event_id,
                        effect_event_id=e_b.event_id,
                        relationship="CORRELATED",
                        domain_crossing=True,
                    ))

        return CorrelationGraph(
            nodes=self._deduplicate_nodes(nodes),
            edges=edges,
            domains_involved=sorted(domains),
            dependency_clusters=self._build_clusters(domains),
        )

    def get_domain_dependency_map(self) -> Dict[str, List[str]]:
        """Get known domain dependency relationships."""
        deps: Dict[str, Set[str]] = defaultdict(set)
        for (a, b), _ in CORRELATION_PATTERNS.items():
            deps[a].add(b)
            deps[b].add(a)
        return {k: sorted(v) for k, v in deps.items()}

    def _find_linked_events(self, domain: Domain, aggregate_id: str) -> List[Event]:
        """Find events linked to this aggregate across domains."""
        primary = self._store.get_by_aggregate(domain, aggregate_id)
        correlation_ids: Set[str] = set()
        for e in primary:
            cid = e.metadata.get("correlation_id", "")
            if cid:
                correlation_ids.add(cid)

        linked: List[Event] = list(primary)
        for cid in correlation_ids:
            for other in self._store.get_all():
                if (other.metadata.get("correlation_id") == cid
                        and other.event_id not in [e.event_id for e in linked]):
                    linked.append(other)
        return linked

    def _events_are_linked(self, a: Event, b: Event) -> bool:
        """Check if two events are linked via metadata."""
        if a.metadata.get("correlation_id") and \
           a.metadata["correlation_id"] == b.metadata.get("correlation_id"):
            return True
        if a.metadata.get("causation_id") == b.event_id:
            return True
        if b.metadata.get("causation_id") == a.event_id:
            return True
        return False

    def _build_edges(self, events: List[Event]) -> List[CausationLink]:
        edges = []
        for e in events:
            cause_id = e.metadata.get("causation_id", "")
            if cause_id:
                cause = self._store.get(cause_id)
                domain_crossing = cause is not None and cause.domain != e.domain
                edges.append(CausationLink(
                    cause_event_id=cause_id,
                    effect_event_id=e.event_id,
                    relationship="DIRECT_CAUSE",
                    domain_crossing=domain_crossing,
                ))
        return edges

    def _build_clusters(self, domains: Set[str]) -> List[Dict[str, Any]]:
        clusters = []
        for (a, b), info in CORRELATION_PATTERNS.items():
            if a in domains and b in domains:
                clusters.append({
                    "domain_a": a,
                    "domain_b": b,
                    "description": info["description"],
                    "forward_events": info["forward_events"],
                    "reverse_events": info["reverse_events"],
                })
        return clusters

    def _deduplicate_nodes(self, nodes: List[TraceEvent]) -> List[TraceEvent]:
        seen: Set[str] = set()
        deduped = []
        for n in nodes:
            if n.event_id not in seen:
                seen.add(n.event_id)
                deduped.append(n)
        return deduped
