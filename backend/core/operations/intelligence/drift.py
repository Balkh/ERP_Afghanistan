"""
Phase 5B.5 — Drift Detection Engine.

Detects divergence from expected system behavior.
All outputs are descriptive, deterministic, and non-prescriptive.
"""
import math
import logging
from collections import defaultdict
from datetime import datetime
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    DriftReport, BaselineReference, DeviationVector,
    DriftDirection, ConfidenceLevel, ModelLimitations,
)

logger = logging.getLogger('erp.intelligence.drift')

DRIFT_ENGINE_VERSION = "1.0.0"


class DriftDetectionEngine:
    """Deterministic drift detection over Event Store.

    Capabilities:
    - Baseline computation per domain
    - Deviation scoring (statistical)
    - Drift velocity calculation
    - Drift accumulation tracking
    - Historical drift comparison
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def compute_baseline(self, domain: Domain) -> BaselineReference:
        """Compute baseline statistics for a domain.

        Deterministic — same events always produce same baseline.
        """
        events = self._store.get_by_domain(domain)
        if not events:
            return BaselineReference()

        timestamps = []
        for i in range(1, len(events)):
            try:
                t1 = datetime.fromisoformat(events[i - 1].timestamp.replace("Z", "+00:00"))
                t2 = datetime.fromisoformat(events[i].timestamp.replace("Z", "+00:00"))
                gap = (t2 - t1).total_seconds()
                if gap > 0:
                    timestamps.append(gap)
            except (ValueError, TypeError):
                continue

        mean_rate = mean(timestamps) if timestamps else 0.0
        std_rate = stdev(timestamps) if len(timestamps) > 1 else 0.0

        return BaselineReference(
            window_start=events[0].timestamp,
            window_end=events[-1].timestamp,
            total_events_in_window=len(events),
            domains_in_window=[domain.value],
            mean_event_rate=round(mean_rate, 4),
            std_event_rate=round(std_rate, 4),
        )

    def detect_drift(
        self,
        domain: Domain,
        aggregate_id: str,
        baseline: Optional[BaselineReference] = None,
    ) -> DriftReport:
        """Detect drift for a single aggregate.

        Args:
            domain: Domain of the aggregate.
            aggregate_id: Aggregate to analyze.
            baseline: Optional pre-computed baseline. Computed if None.

        Returns:
            DriftReport with deviation measurements.
        """
        events = self._store.get_by_aggregate(domain, aggregate_id)
        if not events:
            return DriftReport(
                domain=domain.value,
                entity_id=aggregate_id,
                confidence_level=ConfidenceLevel.LOW,
            )

        if baseline is None:
            baseline = self.compute_baseline(domain)

        current_rate = len(events)
        baseline_rate = baseline.total_events_in_window

        abs_dev = current_rate - baseline_rate
        pct_dev = (abs_dev / baseline_rate * 100) if baseline_rate > 0 else 0.0
        z_score = (abs_dev / baseline.std_event_rate) if baseline.std_event_rate > 0 else 0.0

        direction = DriftDirection.STABLE
        if abs_dev > 0 and z_score > 1.0:
            direction = DriftDirection.INCREASING
        elif abs_dev < 0 and z_score < -1.0:
            direction = DriftDirection.DECREASING

        velocity = 0.0
        if len(events) > 1:
            try:
                t_first = datetime.fromisoformat(events[0].timestamp.replace("Z", "+00:00"))
                t_last = datetime.fromisoformat(events[-1].timestamp.replace("Z", "+00:00"))
                span = (t_last - t_first).total_seconds()
                if span > 0:
                    velocity = len(events) / span * 3600
            except (ValueError, TypeError):
                pass

        conf = ConfidenceLevel.MEDIUM
        if baseline.total_events_in_window >= 100 and baseline.std_event_rate > 0:
            conf = ConfidenceLevel.HIGH
        elif baseline.total_events_in_window < 10:
            conf = ConfidenceLevel.LOW

        return DriftReport(
            domain=domain.value,
            entity_id=aggregate_id,
            drift_score=round(abs_dev, 4),
            drift_velocity=round(velocity, 4),
            baseline_reference=baseline,
            deviation_vector=DeviationVector(
                absolute_deviation=round(abs_dev, 4),
                percentage_deviation=round(pct_dev, 4),
                z_score=round(z_score, 4),
                direction=direction,
            ),
            timestamp_range_start=events[0].timestamp,
            timestamp_range_end=events[-1].timestamp,
            confidence_level=conf,
            model_limitations=ModelLimitations(
                statistical_approximations=[
                    "Z-score assumes normal distribution",
                    "Velocity is linear approximation",
                ],
                temporal_sampling_constraints=[
                    "Baseline window may not represent steady state",
                ],
            ),
        )

    def detect_drift_all_aggregates(self, domain: Domain) -> List[DriftReport]:
        """Detect drift for all aggregates in a domain."""
        baseline = self.compute_baseline(domain)
        reports = []
        all_events = self._store.get_by_domain(domain)
        agg_ids = set(e.aggregate_id for e in all_events)
        for aid in agg_ids:
            report = self.detect_drift(domain, aid, baseline)
            reports.append(report)
        return reports

    def compare_drift_historical(
        self,
        domain: Domain,
        aggregate_id: str,
        earlier_baseline: BaselineReference,
    ) -> DriftReport:
        """Compare current drift against an earlier baseline."""
        return self.detect_drift(domain, aggregate_id, earlier_baseline)
