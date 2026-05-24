"""
Phase 5B.12 — Decision Impact Ranking Engine (UI-only).

Ranks decisions by weighted formula:
    overall_score = (impact_score * 0.4)
                  + ((100 - risk_score) * 0.3)
                  + (feasibility_score * 0.2)
                  + (confidence_score * 0.1)

No ML. Deterministic ranking only.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from api.client import APIClient
from api.autonomous_client import AutonomousAPIClient
from api.intelligence_client import IntelligenceAPIClient


@dataclass
class DecisionScore:
    decision_id: str = ""
    decision_type: str = ""
    option_id: str = ""
    action_summary: str = ""
    impact_score: float = 0.0
    risk_score: float = 0.0
    feasibility_score: float = 0.0
    confidence_score: float = 0.0
    overall_score: float = 0.0
    overall_rank: int = 0


@dataclass
class RankingResult:
    scores: List[DecisionScore] = field(default_factory=list)
    top_recommendation: str = ""
    average_confidence: float = 0.0
    total_decisions: int = 0
    generated_at: str = ""


# Weight constants
W_IMPACT = 0.4
W_RISK_INVERSE = 0.3
W_FEASIBILITY = 0.2
W_CONFIDENCE = 0.1


class DecisionImpactEngine:
    """Deterministic decision ranking engine.

    Consumes decision-options + drift + event data.
    Ranks by weighted formula. No ML.
    """

    def __init__(self, api_client: APIClient):
        self._auto = AutonomousAPIClient(api_client)
        self._intel = IntelligenceAPIClient(api_client)

    def rank_decisions(self, domain: str = "") -> RankingResult:
        """Fetch decision options and rank them."""
        result = RankingResult()
        all_scores: List[DecisionScore] = []

        try:
            decisions = self._auto.get_decision_options()
            dd = decisions.get("data", decisions) if isinstance(decisions, dict) else {}
            decision_list = dd.get("decisions", [])

            # Get system risk context
            try:
                risk = self._auto.get_risk_summary()
                rd = risk.get("data", risk) if isinstance(risk, dict) else {}
                system_risk = rd.get("overall_risk", 50)
            except Exception:
                system_risk = 50

            for d in decision_list:
                dtype = d.get("decision_type", "")
                if domain and dtype != domain:
                    continue

                risk_level_map = {"LOW": 20, "MEDIUM": 50, "HIGH": 80}

                for opt in d.get("options", []):
                    risk_lvl = opt.get("risk_level", "MEDIUM")
                    risk_score = risk_level_map.get(risk_lvl, 50)
                    confidence = opt.get("confidence", 0.5)

                    # Compute normalized scores
                    base_impact = 100 - risk_score
                    contextual_impact = max(0, base_impact - (system_risk * 0.2))

                    ds = DecisionScore(
                        decision_id=d.get("decision_id", ""),
                        decision_type=dtype,
                        option_id=opt.get("option_id", ""),
                        action_summary=opt.get("action_summary", ""),
                        impact_score=round(contextual_impact, 1),
                        risk_score=float(risk_score),
                        feasibility_score=round(max(0, 100 - risk_score * 0.5), 1),
                        confidence_score=float(confidence),
                    )

                    # Weighted formula
                    ds.overall_score = round(
                        (ds.impact_score * W_IMPACT)
                        + ((100 - ds.risk_score) * W_RISK_INVERSE)
                        + (ds.feasibility_score * W_FEASIBILITY)
                        + (ds.confidence_score * W_CONFIDENCE),
                        2,
                    )
                    all_scores.append(ds)

        except Exception:
            pass

        # Sort by overall_score descending
        all_scores.sort(key=lambda s: s.overall_score, reverse=True)

        # Assign ranks
        for i, s in enumerate(all_scores):
            s.overall_rank = i + 1

        result.scores = all_scores
        result.total_decisions = len(all_scores)
        if all_scores:
            result.top_recommendation = all_scores[0].action_summary
            result.average_confidence = round(
                sum(s.confidence_score for s in all_scores) / len(all_scores), 2
            )

        return result

    def get_risk_vs_impact_matrix(self, scores: List[DecisionScore]) -> List[Dict[str, Any]]:
        """Compute risk vs impact coordinates for visualization."""
        return [
            {
                "label": s.action_summary[:30],
                "risk": s.risk_score,
                "impact": s.impact_score,
                "rank": s.overall_rank,
            }
            for s in scores[:10]
        ]
