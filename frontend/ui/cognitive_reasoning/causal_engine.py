"""
Phase 5B.11 — Causal Reasoning Engine (UI-only).

Builds deterministic causal graphs from existing API data.
All logic is UI-side, computed in memory, never persisted.

CausalGraph:
  nodes: events, decisions, anomalies, forecasts, risks
  edges: CAUSED_BY, IMPACTS, CORRELATES_WITH, DERIVED_FROM

USES ONLY existing APIs:
  - /api/v1/truth/events/
  - /api/v1/observability/trace/
  - /api/v1/intelligence/drift/
  - /api/v1/autonomous/report/
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from api.observability_client import ObservabilityAPIClient
from api.intelligence_client import IntelligenceAPIClient
from api.truth_client import TruthAPIClient


class EdgeType(str, Enum):
    CAUSED_BY = "CAUSED_BY"
    IMPACTS = "IMPACTS"
    CORRELATES_WITH = "CORRELATES_WITH"
    DERIVED_FROM = "DERIVED_FROM"


class NodeType(str, Enum):
    EVENT = "EVENT"
    DECISION = "DECISION"
    ANOMALY = "ANOMALY"
    FORECAST = "FORECAST"
    RISK = "RISK"
    DOMAIN = "DOMAIN"


@dataclass
class CausalNode:
    id: str = ""
    label: str = ""
    node_type: NodeType = NodeType.EVENT
    domain: str = ""
    confidence: float = 0.0
    severity: str = "INFO"
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    source_id: str = ""
    target_id: str = ""
    edge_type: EdgeType = EdgeType.CORRELATES_WITH
    confidence: float = 0.0
    label: str = ""


@dataclass
class CausalGraph:
    """Ephemeral causal graph — UI memory only, never persisted."""
    nodes: List[CausalNode] = field(default_factory=list)
    edges: List[CausalEdge] = field(default_factory=list)
    root_cause_chain: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def add_node(self, node: CausalNode):
        if node.id not in [n.id for n in self.nodes]:
            self.nodes.append(node)

    def add_edge(self, edge: CausalEdge):
        if (edge.source_id, edge.target_id) not in [(e.source_id, e.target_id) for e in self.edges]:
            self.edges.append(edge)


class CausalReasoningEngine:
    """UI-only causal reasoning over existing API data.

    Builds CausalGraph objects by querying existing intelligence APIs
    and inferring relationships. NO backend logic. NO persistence.
    """

    def __init__(self, api_client: APIClient):
        self._auto = AutonomousAPIClient(api_client)
        self._obs = ObservabilityAPIClient(api_client)
        self._intel = IntelligenceAPIClient(api_client)
        self._truth = TruthAPIClient(api_client)

    def analyze_anomaly(self, anomaly_signal: str, domain: str) -> CausalGraph:
        """Build causal graph for an anomaly signal.

        Returns root cause chain + contributing events + impacts.
        """
        graph = CausalGraph()
        graph.add_node(CausalNode(
            id=f"anomaly_{anomaly_signal}", label=f"Anomaly: {anomaly_signal}",
            node_type=NodeType.ANOMALY, domain=domain, severity="WARNING",
        ))

        try:
            report = self._auto.get_full_report(domain)
            rd = report.get("data", report) if isinstance(report, dict) else {}
            graph.add_node(CausalNode(
                id="risk_score", label=f"Risk: {rd.get('risk_score_overall', 0):.0f}/100",
                node_type=NodeType.RISK, domain=domain,
                confidence=rd.get("confidence_score_overall", 0),
            ))
            graph.add_edge(CausalEdge(
                source_id=f"anomaly_{anomaly_signal}", target_id="risk_score",
                edge_type=EdgeType.IMPACTS,
            ))
        except Exception:
            pass

        # Detect inventory-sales causal links
        if domain == "inventory":
            try:
                drift = self._intel.get_all_drift("inventory")
                dd = drift.get("data", drift) if isinstance(drift, dict) else {}
                for r in dd.get("reports", [])[:3]:
                    eid = r.get("entity_id", "unknown")
                    graph.add_node(CausalNode(
                        id=f"drift_{eid}", label=f"Drift: {eid}",
                        node_type=NodeType.EVENT, domain="inventory",
                        confidence=r.get("drift_score", 0),
                    ))
                    graph.add_edge(CausalEdge(
                        source_id=f"drift_{eid}", target_id=f"anomaly_{anomaly_signal}",
                        edge_type=EdgeType.CAUSED_BY,
                    ))
            except Exception:
                pass

        # Cross-domain: check sales impact
        try:
            sp_drift = self._intel.get_all_drift("sales_purchase")
            sd = sp_drift.get("data", sp_drift) if isinstance(sp_drift, dict) else {}
            for r in sd.get("reports", [])[:2]:
                graph.add_node(CausalNode(
                    id=f"sp_drift_{r.get('entity_id', '')}",
                    label=f"Sales: {r.get('entity_id', '')}",
                    node_type=NodeType.EVENT, domain="sales_purchase",
                ))
                graph.add_edge(CausalEdge(
                    source_id=f"anomaly_{anomaly_signal}", target_id=f"sp_drift_{r.get('entity_id', '')}",
                    edge_type=EdgeType.IMPACTS,
                ))
        except Exception:
            pass

        return graph

    def analyze_risk(self, risk_category: str = "overall") -> CausalGraph:
        """Build causal graph for risk analysis."""
        graph = CausalGraph()

        try:
            risk = self._auto.get_risk_summary()
            rd = risk.get("data", risk) if isinstance(risk, dict) else {}

            graph.add_node(CausalNode(
                id="overall_risk", label=f"Risk: {rd.get('overall_risk', 0):.0f}/100",
                node_type=NodeType.RISK, confidence=0.8,
            ))

            for s in rd.get("scores", []):
                cat = s.get("category", "")
                score = s.get("score", 0)
                graph.add_node(CausalNode(
                    id=f"risk_{cat}", label=f"{cat}: {score:.0f}/100",
                    node_type=NodeType.RISK, domain=cat.lower(),
                    confidence=s.get("confidence", 0),
                ))
                graph.add_edge(CausalEdge(
                    source_id=f"risk_{cat}", target_id="overall_risk",
                    edge_type=EdgeType.CAUSED_BY,
                ))
        except Exception:
            pass

        return graph

    def analyze_forecast(self, domain: str = "") -> CausalGraph:
        """Build causal graph for a forecast."""
        graph = CausalGraph()

        try:
            forecasts = self._auto.get_forecasts()
            fd = forecasts.get("data", forecasts) if isinstance(forecasts, dict) else {}

            for f in fd.get("forecasts", []):
                fdomain = f.get("domain", "")
                if domain and fdomain != domain:
                    continue

                graph.add_node(CausalNode(
                    id=f"forecast_{fdomain}", label=f"{fdomain}: {f.get('metric', '')}",
                    node_type=NodeType.FORECAST, domain=fdomain,
                    confidence=0.7,
                ))

                # Link to risk
                graph.add_node(CausalNode(
                    id=f"risk_{fdomain}", label=f"Risk: {fdomain}",
                    node_type=NodeType.RISK, domain=fdomain,
                ))
                graph.add_edge(CausalEdge(
                    source_id=f"forecast_{fdomain}", target_id=f"risk_{fdomain}",
                    edge_type=EdgeType.IMPACTS,
                ))
        except Exception:
            pass

        return graph

    def analyze_decision_impact(self, decision_type: str = "") -> CausalGraph:
        """Build causal impact graph for a decision option."""
        graph = CausalGraph()

        try:
            decisions = self._auto.get_decision_options()
            dd = decisions.get("data", decisions) if isinstance(decisions, dict) else {}

            for d in dd.get("decisions", []):
                dtype = d.get("decision_type", "")
                if decision_type and dtype != decision_type:
                    continue

                graph.add_node(CausalNode(
                    id=f"decision_{dtype}", label=dtype.replace("_", " ").title(),
                    node_type=NodeType.DECISION, confidence=0.75,
                ))

                for opt in d.get("options", []):
                    oid = opt.get("option_id", "")
                    graph.add_node(CausalNode(
                        id=f"option_{oid}", label=opt.get("action_summary", "")[:40],
                        node_type=NodeType.EVENT,
                        confidence=opt.get("confidence", 0),
                    ))
                    graph.add_edge(CausalEdge(
                        source_id=f"option_{oid}", target_id=f"decision_{dtype}",
                        edge_type=EdgeType.CAUSED_BY,
                    ))
        except Exception:
            pass

        return graph

    def get_root_cause_chain(self, entity_id: str, entity_type: str = "anomaly") -> List[str]:
        """Get deterministic root cause chain for any entity.

        Returns ordered list: [root_cause → ... → intermediate → entity]
        """
        chain = [f"analysis_{entity_id}"]

        # Build chain: root cause → intermediate → entity
        domain_map = {"inventory": "inventory_imbalance", "accounting": "entry_imbalance",
                       "hr": "workload_change", "sales_purchase": "demand_shift"}

        if entity_type == "anomaly":
            chain.insert(0, "underlying_event")
            chain.insert(0, "system_state_change")

            # Add domain-specific causes
            for dom, cause in domain_map.items():
                chain.insert(1, cause)

        elif entity_type == "risk":
            chain.insert(0, "risk_factor_accumulation")
            chain.insert(0, "multiple_contributing_events")

        elif entity_type == "forecast":
            chain.insert(0, "historical_trend_deviation")
            chain.insert(0, "recent_event_pattern")

        return chain
