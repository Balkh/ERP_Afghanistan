"""
Phase 5B.12 — Causal Scoring Engine (UI-only).

Enhances causal graphs with weighted scoring:
- impact_score (0–100)
- confidence_score (0–1)
- frequency_weight
- temporal_decay_factor
- causal_strength (0–1) per edge
- propagation_weight per edge

Strictly deterministic rule-based scoring. NO ML. NO probability models.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from api.intelligence_client import IntelligenceAPIClient
from api.truth_client import TruthAPIClient


SCORING_RULES = {
    "direct_causality_weight": 1.0,
    "indirect_causality_weight": 0.6,
    "cross_domain_bonus": 1.3,
    "recent_event_bonus_days": 7,
    "repeated_pattern_bonus": 1.2,
    "temporal_decay_rate": 0.85,
    "impact_score_max": 100.0,
    "min_confidence": 0.1,
}


@dataclass
class ScoredNode:
    id: str = ""
    label: str = ""
    node_type: str = "EVENT"
    domain: str = ""
    impact_score: float = 0.0
    confidence: float = 0.0
    frequency_weight: float = 1.0
    temporal_decay_factor: float = 1.0
    rank: int = 0


@dataclass
class ScoredEdge:
    source_id: str = ""
    target_id: str = ""
    edge_type: str = "CORRELATES_WITH"
    causal_strength: float = 0.0
    propagation_weight: float = 1.0
    dependency_type_weight: float = 1.0
    is_direct: bool = True


@dataclass
class ScoredCausalGraph:
    nodes: List[ScoredNode] = field(default_factory=list)
    edges: List[ScoredEdge] = field(default_factory=list)
    strongest_paths: List[List[str]] = field(default_factory=list)
    bottleneck_nodes: List[str] = field(default_factory=list)
    overall_impact_score: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class CausalScoringEngine:
    """Deterministic causal scoring engine.

    Applies rule-based weighting to causal graphs.
    All scores are computed from existing API data only.
    """

    def __init__(self, api_client: APIClient):
        self._auto = AutonomousAPIClient(api_client)
        self._intel = IntelligenceAPIClient(api_client)
        self._truth = TruthAPIClient(api_client)

    def score_anomaly_graph(self, domain: str = "inventory") -> ScoredCausalGraph:
        """Build and score a causal graph for an anomaly."""
        scored = ScoredCausalGraph()
        total_impact = 0.0

        try:
            report = self._auto.get_full_report(domain)
            rd = report.get("data", report) if isinstance(report, dict) else {}
            overall_risk = rd.get("risk_score_overall", 0)
            confidence = rd.get("confidence_score_overall", 0.5)
        except Exception:
            overall_risk = 0
            confidence = 0.3

        # Root node: the anomaly itself
        anomaly_impact = min(overall_risk + 20, 100)
        root = ScoredNode(
            id=f"anomaly_{domain}", label=f"Anomaly in {domain}",
            node_type="ANOMALY", domain=domain,
            impact_score=anomaly_impact, confidence=confidence,
            frequency_weight=1.2 if overall_risk > 50 else 1.0,
            temporal_decay_factor=1.0, rank=1,
        )
        scored.nodes.append(root)
        total_impact += anomaly_impact

        # Get drift data for contributing factors
        try:
            drift = self._intel.get_all_drift(domain)
            dd = drift.get("data", drift) if isinstance(drift, dict) else {}
            reports = dd.get("reports", [])
            for i, r in enumerate(reports[:5]):
                drift_score = abs(r.get("drift_score", 0))
                node_impact = min(drift_score * 10, 80)
                scored.nodes.append(ScoredNode(
                    id=f"drift_{r.get('entity_id', i)}",
                    label=f"Drift: {r.get('entity_id', '')}",
                    node_type="EVENT", domain=domain,
                    impact_score=node_impact,
                    confidence=r.get("confidence_level", "MEDIUM") == "HIGH" and 0.8 or 0.5,
                    frequency_weight=1.0 + (i * 0.1),
                    temporal_decay_factor=SCORING_RULES["temporal_decay_rate"] ** i,
                    rank=i + 2,
                ))
                scored.edges.append(ScoredEdge(
                    source_id=f"drift_{r.get('entity_id', i)}",
                    target_id=f"anomaly_{domain}",
                    edge_type="CAUSED_BY",
                    causal_strength=min(drift_score / 10, 1.0),
                    propagation_weight=1.0 / (i + 1),
                    is_direct=i < 2,
                ))
                total_impact += node_impact * SCORING_RULES["temporal_decay_rate"] ** i
        except Exception:
            pass

        # Cross-domain links
        try:
            sp_drift = self._intel.get_all_drift("sales_purchase")
            sd = sp_drift.get("data", sp_drift) if isinstance(sp_drift, dict) else {}
            for i, r in enumerate(sd.get("reports", [])[:3]):
                scored.nodes.append(ScoredNode(
                    id=f"cross_{r.get('entity_id', i)}",
                    label=f"Cross: {r.get('entity_id', '')}",
                    node_type="EVENT", domain="sales_purchase",
                    impact_score=abs(r.get("drift_score", 0)) * 8,
                    confidence=0.5,
                    frequency_weight=SCORING_RULES["cross_domain_bonus"],
                    temporal_decay_factor=0.7,
                    rank=10 + i,
                ))
                scored.edges.append(ScoredEdge(
                    source_id=f"cross_{r.get('entity_id', i)}",
                    target_id=f"anomaly_{domain}",
                    edge_type="IMPACTS",
                    causal_strength=0.5,
                    propagation_weight=0.5,
                    is_direct=False,
                ))
        except Exception:
            pass

        # Compute strongest paths
        scored.strongest_paths = self._find_strongest_paths(scored)
        scored.bottleneck_nodes = self._find_bottlenecks(scored)
        scored.overall_impact_score = min(total_impact / max(len(scored.nodes), 1), 100)

        return scored

    def _find_strongest_paths(self, graph: ScoredCausalGraph) -> List[List[str]]:
        """Find top 3 strongest causal paths (UI-side heuristic)."""
        paths = []
        for node in sorted(graph.nodes, key=lambda n: n.impact_score, reverse=True)[:3]:
            path = [node.id]
            for edge in graph.edges:
                if edge.target_id == node.id and edge.source_id not in path:
                    path.append(edge.source_id)
            if len(path) > 1:
                paths.append(path)
        return paths[:3]

    def _find_bottlenecks(self, graph: ScoredCausalGraph) -> List[str]:
        """Find nodes with highest betweenness (degree heuristic)."""
        edge_counts: Dict[str, int] = {}
        for edge in graph.edges:
            edge_counts[edge.source_id] = edge_counts.get(edge.source_id, 0) + 1
            edge_counts[edge.target_id] = edge_counts.get(edge.target_id, 0) + 1
        sorted_nodes = sorted(edge_counts.items(), key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in sorted_nodes[:3]]
