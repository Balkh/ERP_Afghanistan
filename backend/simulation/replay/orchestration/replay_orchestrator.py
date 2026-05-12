"""Replay orchestrator — top-level orchestrator for the replay system."""
from collections import deque
from typing import Any, Dict, List, Optional
from simulation.replay.models import (ReplayMode, ReplayStatus, FullReplayReport,
                                        ReplayIntegrityReport)
from simulation.replay.timeline.timeline_builder import TimelineBuilder
from simulation.replay.timeline.timeline_indexer import TimelineIndexer
from simulation.replay.timeline.timeline_cursor import TimelineCursorManager
from simulation.replay.timeline.timeline_validator import TimelineValidator
from simulation.replay.snapshots.snapshot_loader import SnapshotLoader
from simulation.replay.snapshots.snapshot_reconstructor import SnapshotReconstructor
from simulation.replay.snapshots.snapshot_integrity import SnapshotIntegrity
from simulation.replay.snapshots.snapshot_history import SnapshotHistory
from simulation.replay.replay_engine.replay_engine import ReplayEngine
from simulation.replay.reconstruction.workflow_reconstructor import WorkflowReconstructor
from simulation.replay.reconstruction.event_chain_builder import EventChainBuilder
from simulation.replay.reconstruction.incident_reconstructor import IncidentReconstructor
from simulation.replay.reconstruction.state_reconstructor import StateReconstructor
from simulation.replay.navigation.time_travel import TimeTravel
from simulation.replay.navigation.replay_navigation import ReplayNavigation
from simulation.replay.navigation.replay_bookmarks import ReplayBookmarks
from simulation.replay.navigation.replay_windows import ReplayWindows
from simulation.replay.forensics.forensic_analyzer import ForensicAnalyzer
from simulation.replay.forensics.incident_forensics import IncidentForensics
from simulation.replay.forensics.causal_forensics import CausalForensics
from simulation.replay.forensics.operational_evidence import OperationalEvidence
from simulation.replay.determinism.replay_determinism import ReplayDeterminism
from simulation.replay.determinism.replay_consistency import ReplayConsistency
from simulation.replay.determinism.divergence_detector import DivergenceDetector
from simulation.replay.validation.replay_validator import ReplayValidator
from simulation.replay.validation.snapshot_validator import SnapshotValidator
from simulation.replay.validation.timeline_integrity import TimelineIntegrity
from simulation.replay.validation.causal_integrity import CausalIntegrity
from simulation.replay.orchestration.replay_router import ReplayRouter
from simulation.replay.orchestration.replay_pipeline import ReplayPipeline


class ReplayOrchestrator:
    def __init__(self, max_history: int = 500):
        self._timeline_builder = TimelineBuilder()
        self._timeline_indexer = TimelineIndexer()
        self._timeline_cursor = TimelineCursorManager()
        self._timeline_validator = TimelineValidator()
        self._snapshot_loader = SnapshotLoader()
        self._snapshot_reconstructor = SnapshotReconstructor()
        self._snapshot_integrity = SnapshotIntegrity()
        self._snapshot_history = SnapshotHistory()
        self._replay_engine = ReplayEngine()
        self._workflow_reconstructor = WorkflowReconstructor()
        self._event_chain = EventChainBuilder()
        self._incident_reconstructor = IncidentReconstructor()
        self._state_reconstructor = StateReconstructor()
        self._time_travel = TimeTravel()
        self._navigation = ReplayNavigation()
        self._bookmarks = ReplayBookmarks()
        self._windows = ReplayWindows()
        self._forensic_analyzer = ForensicAnalyzer()
        self._incident_forensics = IncidentForensics()
        self._causal_forensics = CausalForensics()
        self._evidence = OperationalEvidence()
        self._determinism = ReplayDeterminism()
        self._consistency = ReplayConsistency()
        self._divergence = DivergenceDetector()
        self._replay_validator = ReplayValidator()
        self._snapshot_validator = SnapshotValidator()
        self._timeline_integrity = TimelineIntegrity()
        self._causal_integrity = CausalIntegrity()
        self._router = ReplayRouter()
        self._pipeline: Optional[ReplayPipeline] = None
        self._execution_history: deque = deque(maxlen=max_history)
        self._replay_count: int = 0

    @property
    def timeline_builder(self) -> TimelineBuilder:
        return self._timeline_builder

    @property
    def timeline_indexer(self) -> TimelineIndexer:
        return self._timeline_indexer

    @property
    def timeline_cursor(self) -> TimelineCursorManager:
        return self._timeline_cursor

    @property
    def timeline_validator(self) -> TimelineValidator:
        return self._timeline_validator

    @property
    def snapshot_loader(self) -> SnapshotLoader:
        return self._snapshot_loader

    @property
    def snapshot_reconstructor(self) -> SnapshotReconstructor:
        return self._snapshot_reconstructor

    @property
    def snapshot_integrity(self) -> SnapshotIntegrity:
        return self._snapshot_integrity

    @property
    def snapshot_history(self) -> SnapshotHistory:
        return self._snapshot_history

    @property
    def replay_engine(self) -> ReplayEngine:
        return self._replay_engine

    @property
    def workflow_reconstructor(self) -> WorkflowReconstructor:
        return self._workflow_reconstructor

    @property
    def event_chain(self) -> EventChainBuilder:
        return self._event_chain

    @property
    def incident_reconstructor(self) -> IncidentReconstructor:
        return self._incident_reconstructor

    @property
    def state_reconstructor(self) -> StateReconstructor:
        return self._state_reconstructor

    @property
    def time_travel(self) -> TimeTravel:
        return self._time_travel

    @property
    def navigation(self) -> ReplayNavigation:
        return self._navigation

    @property
    def bookmarks(self) -> ReplayBookmarks:
        return self._bookmarks

    @property
    def windows(self) -> ReplayWindows:
        return self._windows

    @property
    def forensic_analyzer(self) -> ForensicAnalyzer:
        return self._forensic_analyzer

    @property
    def incident_forensics(self) -> IncidentForensics:
        return self._incident_forensics

    @property
    def causal_forensics(self) -> CausalForensics:
        return self._causal_forensics

    @property
    def evidence(self) -> OperationalEvidence:
        return self._evidence

    @property
    def determinism(self) -> ReplayDeterminism:
        return self._determinism

    @property
    def consistency(self) -> ReplayConsistency:
        return self._consistency

    @property
    def divergence(self) -> DivergenceDetector:
        return self._divergence

    @property
    def replay_validator(self) -> ReplayValidator:
        return self._replay_validator

    @property
    def snapshot_validator(self) -> SnapshotValidator:
        return self._snapshot_validator

    @property
    def timeline_integrity(self) -> TimelineIntegrity:
        return self._timeline_integrity

    @property
    def causal_integrity(self) -> CausalIntegrity:
        return self._causal_integrity

    @property
    def router(self) -> ReplayRouter:
        return self._router

    def run_replay(self, session_id: str, events: List[Dict[str, Any]],
                   mode: ReplayMode = ReplayMode.FULL) -> Dict[str, Any]:
        self._replay_count += 1
        session = self._replay_engine.sessions.create_session(
            session_id, mode, 0, max(e.get('tick', 0) for e in events) if events else 0)
        for e in events:
            self._timeline_builder.add_event(
                e.get('tick', 0), e.get('event_type', 'unknown'),
                e.get('source', 'unknown'), e.get('description', ''),
                e.get('payload'), e.get('causal_parent'))
            self._timeline_indexer.index_event(
                e.get('event_id', ''), e.get('tick', 0),
                e.get('event_type', ''), e.get('source', ''))
        routing = self._router.route_replay(mode, session_id, events)
        result = self._replay_engine.execute_replay(session_id, events)
        report = FullReplayReport(
            report_id=f"rpr_{self._replay_count}",
            session=session, timeline_events=len(events),
        )
        self._execution_history.append({
            'session_id': session_id, 'events': len(events),
            'executed': result.get('executed', False),
        })
        return {'replay_id': report.report_id, 'session_id': session_id,
                'executed': result.get('executed', False),
                'events_replayed': len(events),
                'routing': routing,
                'session': session}

    def reset(self):
        self._timeline_builder.clear()
        self._timeline_indexer.clear()
        self._timeline_cursor.clear()
        self._timeline_validator.clear()
        self._snapshot_loader.clear()
        self._snapshot_reconstructor.clear()
        self._snapshot_integrity.clear()
        self._snapshot_history.clear()
        self._replay_engine.clear()
        self._workflow_reconstructor.clear()
        self._event_chain.clear()
        self._incident_reconstructor.clear()
        self._state_reconstructor.clear()
        self._time_travel.clear()
        self._navigation.clear()
        self._bookmarks.clear()
        self._windows.clear()
        self._forensic_analyzer.clear()
        self._incident_forensics.clear()
        self._causal_forensics.clear()
        self._evidence.clear()
        self._determinism.clear()
        self._consistency.clear()
        self._divergence.clear()
        self._replay_validator.clear()
        self._snapshot_validator.clear()
        self._timeline_integrity.clear()
        self._causal_integrity.clear()
        self._router.clear()
        self._execution_history.clear()
        self._replay_count = 0
