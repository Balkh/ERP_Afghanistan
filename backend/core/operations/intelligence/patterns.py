"""
Phase 5B.5 — Event Pattern Mining Engine.

Identifies recurring or abnormal event patterns deterministically:
- frequent sequence mining
- rare event detection
- cyclic behavior detection
- burst pattern detection
- event clustering (non-prioritized)

NO ranking by severity. Purely statistical grouping.
"""
import logging
from collections import Counter, defaultdict
from datetime import datetime
from math import sqrt
from typing import Any, Dict, List, Optional, Set, Tuple

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence.models import (
    EventPattern, PatternType, ConfidenceLevel, ModelLimitations,
)

logger = logging.getLogger('erp.intelligence.pattern')

PATTERN_ENGINE_VERSION = "1.0.0"

MIN_SEQUENCE_LENGTH = 2
MAX_SEQUENCE_LENGTH = 5
RARE_EVENT_THRESHOLD = 0.05
BURST_WINDOW_SECONDS = 3600


class EventPatternMiningEngine:
    """Deterministic event pattern mining over Event Store.

    All outputs are statistical only — no prioritization, no recommendations.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def mine_frequent_sequences(
        self,
        domain: Domain,
        min_support: int = 2,
        max_length: int = MAX_SEQUENCE_LENGTH,
    ) -> List[EventPattern]:
        """Mine frequent event type sequences.

        Deterministic — same events always produce same patterns.

        Args:
            domain: Domain to analyze.
            min_support: Minimum occurrences for a pattern.
            max_length: Maximum sequence length.

        Returns:
            List of EventPattern sorted alphabetically (no priority).
        """
        events = self._store.get_by_domain(domain)
        if len(events) < min_support:
            return []

        event_types = [e.event_type for e in events if e.source_type.value != "SIMULATION"]
        patterns: Dict[str, int] = defaultdict(int)

        for length in range(MIN_SEQUENCE_LENGTH, max_length + 1):
            for i in range(len(event_types) - length + 1):
                seq = tuple(event_types[i:i + length])
                patterns[str(seq)] += 1

        result = []
        for seq_str, count in patterns.items():
            if count >= min_support:
                types = eval(seq_str)
                freq = count / max(len(event_types), 1)
                result.append(EventPattern(
                    pattern_type=PatternType.FREQUENT_SEQUENCE,
                    domain=domain.value,
                    event_types=list(types),
                    occurrence_count=count,
                    frequency=round(freq, 4),
                    confidence_level=ConfidenceLevel.HIGH if count >= 10 else ConfidenceLevel.MEDIUM,
                    model_limitations=ModelLimitations(
                        statistical_approximations=["Support-based frequent sequence mining"],
                        known_bias=["Shorter sequences may appear more frequent"],
                    ),
                ))

        result.sort(key=lambda p: (p.occurrence_count, str(p.event_types)))
        return result

    def detect_rare_events(
        self,
        domain: Domain,
        threshold: float = RARE_EVENT_THRESHOLD,
    ) -> List[EventPattern]:
        """Detect rare event types.

        Rare = event type frequency below threshold.
        """
        events = self._store.get_by_domain(domain)
        if not events:
            return []

        total = len(events)
        type_counts = Counter(e.event_type for e in events)

        rare = []
        for event_type, count in type_counts.items():
            freq = count / total
            if freq <= threshold:
                rare.append(EventPattern(
                    pattern_type=PatternType.RARE_EVENT,
                    domain=domain.value,
                    event_types=[event_type],
                    occurrence_count=count,
                    frequency=round(freq, 4),
                    confidence_level=ConfidenceLevel.HIGH if total >= 100 else ConfidenceLevel.MEDIUM,
                    model_limitations=ModelLimitations(
                        statistical_approximations=[
                            f"Rare threshold={threshold}",
                            "Small sample sizes may produce unreliable detection",
                        ],
                    ),
                ))

        rare.sort(key=lambda p: p.occurrence_count)
        return rare

    def detect_bursts(
        self,
        domain: Domain,
        window_seconds: int = BURST_WINDOW_SECONDS,
        burst_multiplier: float = 2.0,
    ) -> List[EventPattern]:
        """Detect burst patterns — unusually high event frequency windows.

        Burst = window with event count > burst_multiplier * average.
        """
        events = self._store.get_by_domain(domain)
        if len(events) < 10:
            return []

        timestamps = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
                timestamps.append((ts, e.event_type))
            except (ValueError, TypeError):
                continue

        if not timestamps:
            return []

        total_span = (timestamps[-1][0] - timestamps[0][0]).total_seconds()
        avg_rate = len(timestamps) / total_span * window_seconds if total_span > 0 else 0
        burst_threshold = avg_rate * burst_multiplier

        window_start = timestamps[0][0]
        burst_events: List[Tuple[str, int]] = []
        i = 0

        while i < len(timestamps):
            window_end = window_start + timedelta(seconds=window_seconds)
            count = 0
            j = i
            while j < len(timestamps) and timestamps[j][0] <= window_end:
                count += 1
                j += 1
            if count > burst_threshold:
                types_in_window = [t[1] for t in timestamps[i:j]]
                burst_events.append((window_start.isoformat(), count))
            i = j
            window_start = timestamps[i][0] if i < len(timestamps) else window_start

        result = []
        for ts, count in burst_events:
            result.append(EventPattern(
                pattern_type=PatternType.BURST_DETECTION,
                domain=domain.value,
                occurrence_count=count,
                frequency=round(count / len(timestamps), 4) if timestamps else 0,
                window_start=ts + "Z",
                window_end=(datetime.fromisoformat(ts) +
                           timedelta(seconds=window_seconds)).isoformat() + "Z",
                confidence_level=ConfidenceLevel.MEDIUM,
                model_limitations=ModelLimitations(
                    statistical_approximations=[
                        f"Window={window_seconds}s, multiplier={burst_multiplier}",
                    ],
                ),
            ))

        return result

    def detect_cycles(
        self,
        domain: Domain,
    ) -> List[EventPattern]:
        """Detect cyclic event patterns.

        Cycle = event type recurring at regular intervals.
        """
        events = self._store.get_by_domain(domain)
        if len(events) < 5:
            return []

        type_timestamps: Dict[str, List[datetime]] = defaultdict(list)
        for e in events:
            try:
                ts = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
                type_timestamps[e.event_type].append(ts)
            except (ValueError, TypeError):
                continue

        result = []
        for event_type, timestamps in type_timestamps.items():
            if len(timestamps) < 3:
                continue

            gaps = []
            for i in range(1, len(timestamps)):
                gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
                gaps.append(gap)

            mean_gap = sum(gaps) / len(gaps) if gaps else 0
            if mean_gap <= 0:
                continue

            variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            std_gap = sqrt(variance)

            cv = std_gap / mean_gap if mean_gap > 0 else float('inf')

            if cv < 0.5:
                result.append(EventPattern(
                    pattern_type=PatternType.CYCLIC_PATTERN,
                    domain=domain.value,
                    event_types=[event_type],
                    occurrence_count=len(timestamps),
                    frequency=round(1.0 / (mean_gap / 3600), 4) if mean_gap > 0 else 0,
                    confidence_level=ConfidenceLevel.HIGH if cv < 0.2 else ConfidenceLevel.MEDIUM,
                    model_limitations=ModelLimitations(
                        statistical_approximations=[
                            "CV-based cyclic detection",
                            "Limited to regular interval detection",
                        ],
                    ),
                ))

        result.sort(key=lambda p: p.occurrence_count, reverse=True)
        return result

    def mine_all_patterns(self, domain: Domain) -> Dict[str, List[EventPattern]]:
        """Run all pattern mining algorithms for a domain."""
        return {
            "frequent_sequences": self.mine_frequent_sequences(domain),
            "rare_events": self.detect_rare_events(domain),
            "bursts": self.detect_bursts(domain),
            "cycles": self.detect_cycles(domain),
        }


from datetime import timedelta
