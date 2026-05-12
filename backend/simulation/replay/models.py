from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReplayStatus(str, Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'


class ReplayMode(str, Enum):
    FULL = 'full'
    STEP = 'step'
    WINDOW = 'window'
    BOOKMARK = 'bookmark'


class TimelineDirection(str, Enum):
    FORWARD = 'forward'
    BACKWARD = 'backward'


class SnapshotStatus(str, Enum):
    INTACT = 'intact'
    CORRUPTED = 'corrupted'
    PARTIAL = 'partial'
    VERIFIED = 'verified'


class ForensicSeverity(str, Enum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class DivergenceType(str, Enum):
    STATE_MISMATCH = 'state_mismatch'
    EVENT_MISMATCH = 'event_mismatch'
    TIMING_MISMATCH = 'timing_mismatch'
    ORDER_MISMATCH = 'order_mismatch'
    HASH_MISMATCH = 'hash_mismatch'


@dataclass
class TimelineEvent:
    event_id: str
    tick: int
    event_type: str
    source: str
    description: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    causal_parent: Optional[str] = None


@dataclass
class TimelineSegment:
    segment_id: str
    start_tick: int
    end_tick: int
    events: List[TimelineEvent] = field(default_factory=list)
    is_contiguous: bool = True


@dataclass
class TimelineCursor:
    cursor_id: str
    current_tick: int
    direction: TimelineDirection
    position: int = 0
    total_events: int = 0


@dataclass
class ReplaySnapshot:
    snapshot_id: str
    tick: int
    status: SnapshotStatus
    workflow_states: Dict[str, Any] = field(default_factory=dict)
    event_count: int = 0
    hash_value: str = ""
    parent_snapshot_id: Optional[str] = None


@dataclass
class ReplaySession:
    session_id: str
    status: ReplayStatus
    mode: ReplayMode
    start_tick: int = 0
    current_tick: int = 0
    end_tick: int = 0
    events_replayed: int = 0
    is_paused: bool = False


@dataclass
class ReplayBookmark:
    bookmark_id: str
    tick: int
    label: str
    description: str = ""
    snapshot_id: Optional[str] = None


@dataclass
class ReplayWindow:
    window_id: str
    start_tick: int
    end_tick: int
    event_count: int = 0
    is_loaded: bool = False


@dataclass
class ReplayHash:
    hash_id: str
    tick: int
    hash_value: str
    component: str = "timeline"
    previous_hash: Optional[str] = None


@dataclass
class ForensicEvidence:
    evidence_id: str
    tick: int
    source: str
    description: str
    evidence_type: str = "event"
    related_events: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayDivergence:
    divergence_id: str
    divergence_type: DivergenceType
    tick: int
    expected: str
    actual: str
    severity: ForensicSeverity
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReplayIntegrityReport:
    report_id: str
    is_consistent: bool
    divergences: List[ReplayDivergence] = field(default_factory=list)
    snapshots_verified: int = 0
    timeline_events_checked: int = 0
    causal_chains_verified: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FullReplayReport:
    report_id: str
    session: Optional[ReplaySession] = None
    timeline_events: int = 0
    snapshots_loaded: int = 0
    workflows_reconstructed: int = 0
    incidents_reconstructed: int = 0
    integrity: Optional[ReplayIntegrityReport] = None
    forensic_evidence_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
