from typing import Any, Dict, List

from simulation.control_center.models import (
    IntelligenceSeverity,
    OperationalSignal,
    UnifiedTimelineEvent,
)


class IntelligenceTimelineBuilder:
    def build_from_signal(
        self, signal: OperationalSignal, tick: int
    ) -> UnifiedTimelineEvent:
        return UnifiedTimelineEvent(
            event_id=signal.signal_id,
            tick=tick,
            source_phase=signal.source_phase,
            event_type=signal.signal_type.value,
            description=signal.description,
            severity=signal.severity,
            payload=dict(signal.payload),
            related_event_ids=[],
        )

    def build_from_signals(
        self, signals: List[OperationalSignal], tick: int
    ) -> List[UnifiedTimelineEvent]:
        return [self.build_from_signal(s, tick) for s in signals]

    def build_mismatch_event(
        self, mismatch_data: Dict[str, Any], tick: int
    ) -> UnifiedTimelineEvent:
        return UnifiedTimelineEvent(
            event_id=mismatch_data.get('event_id', f"mismatch_{tick}"),
            tick=tick,
            source_phase=mismatch_data.get('source_phase', 'truth_engine'),
            event_type='truth_mismatch',
            description=mismatch_data.get('description', 'Truth mismatch detected'),
            severity=self._parse_severity(mismatch_data.get('severity', 'medium')),
            payload=dict(mismatch_data),
            related_event_ids=mismatch_data.get('related_event_ids', []),
        )

    def build_recovery_event(
        self, recovery_data: Dict[str, Any], tick: int
    ) -> UnifiedTimelineEvent:
        return UnifiedTimelineEvent(
            event_id=recovery_data.get('event_id', f"recovery_{tick}"),
            tick=tick,
            source_phase=recovery_data.get('source_phase', 'recovery_system'),
            event_type='recovery_event',
            description=recovery_data.get('description', 'Recovery event'),
            severity=self._parse_severity(recovery_data.get('severity', 'info')),
            payload=dict(recovery_data),
            related_event_ids=recovery_data.get('related_event_ids', []),
        )

    def build_replay_event(
        self, replay_data: Dict[str, Any], tick: int
    ) -> UnifiedTimelineEvent:
        return UnifiedTimelineEvent(
            event_id=replay_data.get('event_id', f"replay_{tick}"),
            tick=tick,
            source_phase=replay_data.get('source_phase', 'replay_system'),
            event_type='replay_event',
            description=replay_data.get('description', 'Replay event'),
            severity=self._parse_severity(replay_data.get('severity', 'info')),
            payload=dict(replay_data),
            related_event_ids=replay_data.get('related_event_ids', []),
        )

    @staticmethod
    def _parse_severity(value: str) -> IntelligenceSeverity:
        try:
            return IntelligenceSeverity(value)
        except ValueError:
            return IntelligenceSeverity.INFO
