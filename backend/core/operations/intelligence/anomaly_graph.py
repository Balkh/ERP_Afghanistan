"""
Phase 5B.5 — Cross-Domain Anomaly Graph Engine.

Builds anomaly relationships across domains using statistical correlation.
NO inference of causality beyond statistical correlation.
"""
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
from math import sqrt

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    AnomalyGraph, AnomalyNode, AnomalyEdge,
    ConfidenceLevel, ModelLimitations,
)

logger = logging.getLogger('erp.intelligence.graph')

ANOMALY_GRAPH_VERSION = "1.0.0"

# Known cross-domain event relationships (from Phase 5B.4)
CROSS_DOMAIN_PAIRS = [
    ("sales_purchase", "inventory"),
    ("inventory", "accounting"),
    ("sales_purchase", "accounting"),
    ("hr", "accounting"),
    ("fixed_assets", "accounting"),
]


class CrossDomainAnomalyGraphEngine:
    """Builds anomaly correlation graphs across domains.

    All correlations are statistical only — never causal.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def build_anomaly_graph(
        self,
        domain: Domain,
        min_correlation: float = 0.3,
    ) -> AnomalyGraph:
        """Build anomaly graph for a domain, finding cross-domain links.

        Args:
            domain: Primary domain to analyze.
            min_correlation: Minimum correlation strength to include.

        Returns:
            AnomalyGraph with statistical correlations only.
        """
        nodes: List[AnomalyNode] = []
        edges: List[AnomalyEdge] = []
        domains_involved: Set[str] = {domain.value}

        primary_events = self._store.get_by_domain(domain)
        if not primary_events:
            return AnomalyGraph()

        for pair_domain in self._get_related_domains(domain):
            partner_domain = Domain(pair_domain)
            partner_events = self._store.get_by_domain(partner_domain)

            if not partner_events:
                continue

            correlation = self._compute_correlation(primary_events, partner_events)
            if correlation < min_correlation:
                continue

            domains_involved.add(pair_domain)

            for pe in primary_events[:20]:
                node_id = f"anom_{pe.event_id}"
                nodes.append(AnomalyNode(
                    anomaly_id=node_id,
                    event_id=pe.event_id,
                    domain=pe.domain.value,
                    event_type=pe.event_type,
                    aggregate_id=pe.aggregate_id,
                    timestamp=pe.timestamp,
                    anomaly_score=round(correlation, 4),
                ))

            for pe in partner_events[:10]:
                node_id = f"anom_{pe.event_id}"
                target_id = f"anom_{primary_events[0].event_id}" if primary_events else ""
                edges.append(AnomalyEdge(
                    source_anomaly_id=f"anom_{primary_events[0].event_id}" if primary_events else "",
                    target_anomaly_id=node_id,
                    correlation_strength=round(correlation, 4),
                    domains_crossed=True,
                ))

        return AnomalyGraph(
            nodes=nodes[:50],
            edges=edges[:50],
            domains_involved=sorted(domains_involved),
            confidence_level=ConfidenceLevel.MEDIUM if len(nodes) > 5 else ConfidenceLevel.LOW,
            model_limitations=ModelLimitations(
                statistical_approximations=[
                    "Pearson correlation on event counts",
                    "Limited to top 20/10 events per domain",
                ],
                known_bias=[
                    "Correlation does not imply causation",
                ],
            ),
        )

    def build_cross_domain_graph(self) -> AnomalyGraph:
        """Build a complete cross-domain anomaly graph."""
        all_nodes: List[AnomalyNode] = []
        all_edges: List[AnomalyEdge] = []
        all_domains: Set[str] = set()

        for domain_a, domain_b in CROSS_DOMAIN_PAIRS:
            graph = self.build_anomaly_graph(Domain(domain_a))
            all_nodes.extend(graph.nodes)
            all_edges.extend(graph.edges)
            all_domains.update(graph.domains_involved)

            graph_b = self.build_anomaly_graph(Domain(domain_b))
            all_nodes.extend(graph_b.nodes)
            all_edges.extend(graph_b.edges)
            all_domains.update(graph_b.domains_involved)

        seen_nodes: Set[str] = set()
        deduped_nodes = []
        for n in all_nodes:
            if n.event_id not in seen_nodes:
                seen_nodes.add(n.event_id)
                deduped_nodes.append(n)

        return AnomalyGraph(
            nodes=deduped_nodes,
            edges=all_edges,
            domains_involved=sorted(all_domains),
            confidence_level=ConfidenceLevel.MEDIUM,
            model_limitations=ModelLimitations(
                statistical_approximations=["Cross-domain Pearson correlation"],
                known_bias=["Correlation does not imply causation"],
            ),
        )

    def _get_related_domains(self, domain: Domain) -> List[str]:
        for a, b in CROSS_DOMAIN_PAIRS:
            if a == domain.value:
                return [b]
            if b == domain.value:
                return [a]
        return []

    def _compute_correlation(
        self,
        events_a: List[Any],
        events_b: List[Any],
    ) -> float:
        days_a = self._get_daily_counts(events_a)
        days_b = self._get_daily_counts(events_b)

        all_days = set(list(days_a.keys()) + list(days_b.keys()))
        if len(all_days) < 3:
            return 0.0

        vals_a = [days_a.get(d, 0) for d in sorted(all_days)]
        vals_b = [days_b.get(d, 0) for d in sorted(all_days)]

        return self._pearson(vals_a, vals_b)

    def _get_daily_counts(self, events: List[Any]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for e in events:
            day = e.timestamp[:10] if len(e.timestamp) >= 10 else e.timestamp
            counts[day] += 1
        return counts

    def _pearson(self, x: List[float], y: List[float]) -> float:
        n = len(x)
        if n < 3:
            return 0.0
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(a * b for a, b in zip(x, y))
        sum_x2 = sum(a * a for a in x)
        sum_y2 = sum(b * b for b in y)
        num = n * sum_xy - sum_x * sum_y
        den = sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y))
        if den == 0:
            return 0.0
        r = num / den
        return max(-1.0, min(1.0, r))
