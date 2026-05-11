"""
Root cause analysis models for Phase 3B.
Read-only data structures. No mutation of ERP state.
"""
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional


class RootCauseType(Enum):
    LOGIC_ERROR = 'logic_error'
    CONCURRENCY_ISSUE = 'concurrency_issue'
    MISSING_MAPPING = 'missing_mapping'
    WORKFLOW_DESIGN_FLAW = 'workflow_design_flaw'
    DATA_INCONSISTENCY = 'data_inconsistency'
    TIMING_DESYNC = 'timing_desync'
    UNKNOWN_CAUSE = 'unknown_cause'


class NodeType(Enum):
    EVENT = 'event'
    WORKFLOW = 'workflow'
    AGENT = 'agent'
    MISMATCH = 'mismatch'
    SYSTEM_STATE = 'system_state'


class EdgeType(Enum):
    TRIGGERS = 'triggers'
    CAUSES = 'causes'
    CORRELATES_WITH = 'correlates_with'


class RootCause:
    __slots__ = (
        'cause_id', 'primary_type', 'secondary_types',
        'confidence', 'mismatch_id', 'description', 'evidence_refs',
    )

    def __init__(
        self,
        cause_id: str,
        primary_type: RootCauseType,
        confidence: float,
        mismatch_id: str,
        description: str,
        secondary_types: Optional[List[RootCauseType]] = None,
        evidence_refs: Optional[List[str]] = None,
    ):
        self.cause_id = cause_id
        self.primary_type = primary_type
        self.secondary_types = secondary_types or []
        self.confidence = confidence
        self.mismatch_id = mismatch_id
        self.description = description
        self.evidence_refs = evidence_refs or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cause_id': self.cause_id,
            'primary_type': self.primary_type.value,
            'secondary_types': [t.value for t in self.secondary_types],
            'confidence': self.confidence,
            'mismatch_id': self.mismatch_id,
            'description': self.description,
            'evidence_refs': list(self.evidence_refs),
        }


class CausalLink:
    __slots__ = (
        'link_id', 'source_id', 'target_id',
        'source_type', 'target_type', 'edge_type',
        'confidence', 'metadata',
    )

    def __init__(
        self,
        link_id: str,
        source_id: str,
        target_id: str,
        source_type: NodeType,
        target_type: NodeType,
        edge_type: EdgeType,
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
    ):
        self.link_id = link_id
        self.source_id = source_id
        self.target_id = target_id
        self.source_type = source_type
        self.target_type = target_type
        self.edge_type = edge_type
        self.confidence = confidence
        self.metadata = dict(metadata) if metadata else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'link_id': self.link_id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'source_type': self.source_type.value,
            'target_type': self.target_type.value,
            'edge_type': self.edge_type.value,
            'confidence': self.confidence,
            'metadata': dict(self.metadata),
        }


class CausalChain:
    def __init__(self, chain_id: str, mismatch_id: str, tick: int):
        self._chain_id = chain_id
        self._mismatch_id = mismatch_id
        self._tick = tick
        self._links: List[CausalLink] = []

    def add_link(self, link: CausalLink):
        self._links.append(link)

    @property
    def chain_id(self) -> str:
        return self._chain_id

    @property
    def mismatch_id(self) -> str:
        return self._mismatch_id

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def links(self) -> List[CausalLink]:
        return list(self._links)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chain_id': self._chain_id,
            'mismatch_id': self._mismatch_id,
            'tick': self._tick,
            'links': [l.to_dict() for l in self._links],
        }


class DriftPattern:
    __slots__ = (
        'pattern_id', 'pattern_type', 'description',
        'affected_module', 'frequency', 'matched_mismatch_ids',
        'first_seen_tick', 'last_seen_tick', 'occurrence_count',
    )

    def __init__(
        self,
        pattern_id: str,
        pattern_type: str,
        description: str,
        affected_module: str,
        frequency: int = 1,
        matched_mismatch_ids: Optional[List[str]] = None,
        first_seen_tick: int = 0,
        last_seen_tick: int = 0,
        occurrence_count: int = 1,
    ):
        self.pattern_id = pattern_id
        self.pattern_type = pattern_type
        self.description = description
        self.affected_module = affected_module
        self.frequency = frequency
        self.matched_mismatch_ids = matched_mismatch_ids or []
        self.first_seen_tick = first_seen_tick
        self.last_seen_tick = last_seen_tick
        self.occurrence_count = occurrence_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type,
            'description': self.description,
            'affected_module': self.affected_module,
            'frequency': self.frequency,
            'matched_mismatch_ids': list(self.matched_mismatch_ids),
            'first_seen_tick': self.first_seen_tick,
            'last_seen_tick': self.last_seen_tick,
            'occurrence_count': self.occurrence_count,
        }


class CausalGraph:
    def __init__(self):
        self._nodes: Dict[str, dict] = {}
        self._edges: Dict[str, CausalLink] = {}

    def add_node(self, node_id: str, node_type: NodeType, label: str,
                 metadata: Optional[dict] = None):
        self._nodes[node_id] = {
            'node_id': node_id,
            'node_type': node_type.value,
            'label': label,
            'metadata': dict(metadata) if metadata else {},
        }

    def add_edge(self, link: CausalLink):
        self._edges[link.link_id] = link

    @property
    def nodes(self) -> Dict[str, dict]:
        return dict(self._nodes)

    @property
    def edges(self) -> Dict[str, CausalLink]:
        return dict(self._edges)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': list(self._nodes.values()),
            'edges': [e.to_dict() for e in self._edges.values()],
        }


class Explanation:
    __slots__ = (
        'explanation_id', 'mismatch_id', 'problem_summary',
        'root_cause_chain', 'confidence', 'evidence',
        'recommendation', 'generated_at',
    )

    def __init__(
        self,
        explanation_id: str,
        mismatch_id: str,
        problem_summary: str,
        root_cause_chain: List[str],
        confidence: float,
        evidence: List[str],
        recommendation: str,
        generated_at: Any,
    ):
        self.explanation_id = explanation_id
        self.mismatch_id = mismatch_id
        self.problem_summary = problem_summary
        self.root_cause_chain = root_cause_chain
        self.confidence = confidence
        self.evidence = evidence
        self.recommendation = recommendation
        self.generated_at = generated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            'explanation_id': self.explanation_id,
            'mismatch_id': self.mismatch_id,
            'problem': self.problem_summary,
            'root_cause_chain': list(self.root_cause_chain),
            'confidence': self.confidence,
            'evidence': list(self.evidence),
            'recommendation': self.recommendation,
            'generated_at': str(self.generated_at),
        }
