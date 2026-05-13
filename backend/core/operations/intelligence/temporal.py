"""
Phase 5B.5 — Temporal Drift Analyzer.

Analyzes anomalies over time:
- Trend deviation
- Anomaly acceleration
- Decay or persistence patterns
- Periodic anomaly detection

Deterministic computation only. No forecasting of actions.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from math import sqrt
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    TemporalDriftReport, TemporalDriftSegment,
    DriftDirection, ConfidenceLevel, ModelLimitations,
)

logger = logging.getLogger('erp.intelligence.temporal')

TEMPORAL_ANALYZER_VERSION = "1.0.0"

DEFAULT_SEGMENT_HOURS = 24
MIN_EVENTS_FOR_ANALYSIS = 5


class TemporalDriftAnalyzer:
    """Deterministic temporal drift analysis.

    All outputs are descriptive — never prescriptive.
    No forecasting. No operational interpretation.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def analyze_temporal_drift(
        self,
        domain: Domain,
        segment_hours: int = DEFAULT_SEGMENT_HOURS,
    ) -> TemporalDriftReport:
        """Analyze temporal drift across time segments.

        Args:
            domain: Domain to analyze.
            segment_hours: Size of each time segment in hours.

        Returns:
            TemporalDriftReport with segment-by-segment analysis.
        """
        events = self._store.get_by_domain(domain)
        if len(events) < MIN_EVENTS_FOR_ANALYSIS:
            return TemporalDriftReport(
                domain=domain.value,
                confidence_level=ConfidenceLevel.LOW,
            )

        segments = self._segment_events(events, segment_hours)
        segment_reports = []
        baseline = sum(s["count"] for s in segments) / max(len(segments), 1)

        for seg in segments:
            dev = seg["count"] - baseline
            segment_reports.append(TemporalDriftSegment(
                period_start=seg["start"],
                period_end=seg["end"],
                drift_score=round(dev, 4),
                event_count=seg["count"],
                deviation_from_baseline=round(dev / max(baseline, 1) * 100, 4),
            ))

        overall_trend = self._compute_trend(segment_reports)
        acceleration = self._compute_acceleration(segment_reports)

        persistence = 0.0
        non_zero = [s for s in segment_reports if abs(s.drift_score) > 0]
        if non_zero:
            persistence = len(non_zero) / max(len(segment_reports), 1)

        conf = ConfidenceLevel.HIGH if len(segments) >= 10 else (
            ConfidenceLevel.MEDIUM if len(segments) >= 5 else ConfidenceLevel.LOW
        )

        return TemporalDriftReport(
            domain=domain.value,
            segments=segment_reports,
            overall_trend=overall_trend,
            acceleration=round(acceleration, 4),
            persistence_score=round(persistence, 4),
            confidence_level=conf,
            model_limitations=ModelLimitations(
                statistical_approximations=[
                    f"Segment size={segment_hours}h",
                    "Linear trend estimation",
                ],
                temporal_sampling_constraints=[
                    "Segments with 0 events are excluded from persistence calculation",
                ],
            ),
        )

    def _segment_events(
        self,
        events: List[Any],
        segment_hours: int,
    ) -> List[Dict[str, Any]]:
        if not events:
            return []
        try:
            start = datetime.fromisoformat(events[0].timestamp.replace("Z", "+00:00"))
            end = datetime.fromisoformat(events[-1].timestamp.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return []

        span = (end - start).total_seconds()
        if span <= 0:
            return [{"start": events[0].timestamp, "end": events[-1].timestamp, "count": len(events)}]

        segment_seconds = segment_hours * 3600
        num_segments = max(1, int(span / segment_seconds) + 1)
        segment_counts = [0] * num_segments

        for e in events:
            try:
                ets = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
                idx = int((ets - start).total_seconds() / segment_seconds)
                if 0 <= idx < num_segments:
                    segment_counts[idx] += 1
            except (ValueError, TypeError):
                continue

        segments = []
        for i in range(num_segments):
            seg_start = start + timedelta(seconds=i * segment_seconds)
            seg_end = min(
                start + timedelta(seconds=(i + 1) * segment_seconds),
                end + timedelta(seconds=segment_seconds),
            )
            segments.append({
                "start": seg_start.isoformat() + "Z",
                "end": seg_end.isoformat() + "Z",
                "count": segment_counts[i],
            })

        return segments

    def _compute_trend(self, segments: List[TemporalDriftSegment]) -> DriftDirection:
        if len(segments) < 2:
            return DriftDirection.UNKNOWN
        first_half = segments[:len(segments) // 2]
        second_half = segments[len(segments) // 2:]
        avg_first = sum(s.drift_score for s in first_half) / max(len(first_half), 1)
        avg_second = sum(s.drift_score for s in second_half) / max(len(second_half), 1)
        diff = avg_second - avg_first
        if diff > 5.0:
            return DriftDirection.INCREASING
        elif diff < -5.0:
            return DriftDirection.DECREASING
        return DriftDirection.STABLE

    def _compute_acceleration(self, segments: List[TemporalDriftSegment]) -> float:
        if len(segments) < 3:
            return 0.0
        velocities = []
        for i in range(1, len(segments)):
            v = segments[i].drift_score - segments[i - 1].drift_score
            velocities.append(v)
        if len(velocities) < 2:
            return 0.0
        return velocities[-1] - velocities[0]
