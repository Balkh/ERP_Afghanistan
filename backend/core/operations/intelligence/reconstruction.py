"""
Phase 5B.5 — Replay-Based Anomaly Reconstruction Engine.

Reconstructs full lifecycle of an anomaly from Event Store:
- first occurrence detection
- propagation path across domains
- event chain reconstruction
- causation trace (from event store only)
"""
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    AnomalyTimeline, AnomalyTimelineEntry,
    ConfidenceLevel, ModelLimitations,
)

logger = logging.getLogger('erp.intelligence.reconstruction')

RECONSTRUCTION_ENGINE_VERSION = "1.0.0"


class ReplayAnomalyReconstructionEngine:
    """Reconstructs anomaly lifecycles from Event Store.

    Deterministic — same events always produce same reconstruction.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def reconstruct_from_aggregate(
        self,
        domain: Domain,
        aggregate_id: str,
    ) -> AnomalyTimeline:
        """Reconstruct anomaly timeline from an aggregate's event chain.

        First occurrence detection + propagation path.

        Args:
            domain: Domain of the aggregate.
            aggregate_id: Aggregate to reconstruct.

        Returns:
            AnomalyTimeline with full event chain.
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        if not events:
            return AnomalyTimeline(
                anomaly_id=f"anomaly_{aggregate_id}",
                confidence_level=ConfidenceLevel.LOW,
            )

        entries = []
        affected_domains: Set[str] = {domain.value}
        first_ts = events[0].timestamp
        last_ts = events[-1].timestamp

        for i, event in enumerate(events):
            role = "FIRST_OCCURRENCE" if i == 0 else "DOWNSTREAM_EFFECT"

            cause_id = event.metadata.get("causation_id", "")
            if cause_id:
                cause = self._store.get(cause_id)
                if cause and cause.domain != event.domain:
                    affected_domains.add(cause.domain.value)
                    role = "PROPAGATION"
                    entries.append(AnomalyTimelineEntry(
                        sequence_index=len(entries),
                        event_id=cause.event_id,
                        event_type=cause.event_type,
                        domain=cause.domain.value,
                        aggregate_id=cause.aggregate_id,
                        timestamp=cause.timestamp,
                        role="ROOT_CAUSE",
                    ))

            entries.append(AnomalyTimelineEntry(
                sequence_index=len(entries),
                event_id=event.event_id,
                event_type=event.event_type,
                domain=event.domain.value,
                aggregate_id=event.aggregate_id,
                timestamp=event.timestamp,
                role=role,
            ))

        temporal_spread = 0.0
        try:
            t1 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            temporal_spread = (t2 - t1).total_seconds()
        except (ValueError, TypeError):
            pass

        h = hashlib.sha256()
        for entry in entries:
            h.update(f"{entry.event_id}:{entry.sequence_index}".encode())
        integrity_hash = h.hexdigest()

        return AnomalyTimeline(
            anomaly_id=f"anomaly_{aggregate_id}",
            full_event_chain=entries,
            affected_domains=sorted(affected_domains),
            temporal_spread_seconds=round(temporal_spread, 2),
            first_occurrence=first_ts,
            last_occurrence=last_ts,
            event_count=len(entries),
            integrity_hash=integrity_hash,
            confidence_level=ConfidenceLevel.HIGH if len(events) >= 3 else ConfidenceLevel.MEDIUM,
            model_limitations=ModelLimitations(
                statistical_approximations=[
                    "Propagation detected via causation_id metadata",
                ],
                known_bias=[
                    "Reconstruction quality depends on causation metadata completeness",
                ],
            ),
        )

    def reconstruct_from_event_id(self, event_id: str) -> Optional[AnomalyTimeline]:
        """Reconstruct anomaly timeline starting from a specific event.

        Traces forward and backward through causation links.
        """
        event = self._store.get(event_id)
        if event is None:
            return None
        return self.reconstruct_from_aggregate(
            Domain(event.domain), event.aggregate_id,
        )

    def find_anomaly_clusters(
        self,
        domain: Domain,
        max_gap_seconds: float = 3600,
    ) -> List[AnomalyTimeline]:
        """Find clusters of anomalies in close temporal proximity.

        Groups events within max_gap_seconds into potential anomaly clusters.
        """
        events = self._store.get_by_domain(domain)
        if not events:
            return []

        timed_events = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
                timed_events.append((ts, e))
            except (ValueError, TypeError):
                continue

        timed_events.sort(key=lambda x: x[0])

        clusters: List[List[Any]] = []
        current_cluster: List[Any] = [timed_events[0]]

        for i in range(1, len(timed_events)):
            gap = (timed_events[i][0] - timed_events[i - 1][0]).total_seconds()
            if gap <= max_gap_seconds:
                current_cluster.append(timed_events[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [timed_events[i]]
        if current_cluster:
            clusters.append(current_cluster)

        results = []
        for i, cluster in enumerate(clusters):
            if len(cluster) < 2:
                continue
            first_ts = cluster[0][1].timestamp
            last_ts = cluster[-1][1].timestamp
            entries = []
            for j, (_, ev) in enumerate(cluster):
                entries.append(AnomalyTimelineEntry(
                    sequence_index=j,
                    event_id=ev.event_id,
                    event_type=ev.event_type,
                    domain=ev.domain.value,
                    aggregate_id=ev.aggregate_id,
                    timestamp=ev.timestamp,
                    role="FIRST_OCCURRENCE" if j == 0 else "DOWNSTREAM_EFFECT",
                ))

            spread = (cluster[-1][0] - cluster[0][0]).total_seconds()
            h = hashlib.sha256()
            for entry in entries:
                h.update(f"{entry.event_id}:{entry.sequence_index}".encode())

            results.append(AnomalyTimeline(
                anomaly_id=f"cluster_{domain.value}_{i}",
                full_event_chain=entries,
                affected_domains=[domain.value],
                temporal_spread_seconds=round(spread, 2),
                first_occurrence=first_ts,
                last_occurrence=last_ts,
                event_count=len(entries),
                integrity_hash=h.hexdigest(),
                confidence_level=ConfidenceLevel.MEDIUM,
                model_limitations=ModelLimitations(
                    statistical_approximations=[
                        f"Cluster gap threshold={max_gap_seconds}s",
                    ],
                ),
            ))

        return results
