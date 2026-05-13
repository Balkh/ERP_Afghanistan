"""
Phase 5B.8 — Decision Suggester.

Generates structured decision options with alternatives.
MUST NOT execute decisions. Output is informational only.
"""
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence_autonomous.models import (
    StructuredDecision, DecisionOption, Recommendation,
)
from core.operations.intelligence_autonomous.reasoning_engine import ReasoningEngine

logger = logging.getLogger('erp.autonomous.suggester')

DECISION_SUGGESTER_VERSION = "1.0.0"


class DecisionSuggester:
    """Generates structured, non-executable decision options.

    Every decision option includes:
    - Projected impact (descriptive only)
    - Risk level
    - Confidence score
    - Prerequisites
    - Tradeoffs
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()
        self._reasoning = ReasoningEngine(store)

    def suggest_inventory_restock(self, product_id: str = "") -> StructuredDecision:
        """Suggest inventory restock options.

        Returns structured decision with alternatives — never executes.
        """
        events = self._store.get_by_domain(Domain.INVENTORY)
        if product_id:
            relevant = [e for e in events if e.event_id == product_id]

        out_moves = [e for e in events if e.event_type == "stock_movement"
                     and e.payload.get("direction") == "out"]
        out_rate = len(out_moves) / max(len(events), 1) * 100

        options = [
            DecisionOption(
                action_summary="Increase order quantity by 25%",
                projected_impact={"expected_stock_days": "+15 days", "cost_increase": "25%"},
                risk_level="LOW",
                confidence=0.8,
                prerequisites=["Supplier capacity check"],
                tradeoffs=["Higher inventory holding cost"],
            ),
            DecisionOption(
                action_summary="Maintain current order levels",
                projected_impact={"expected_stock_days": "no change"},
                risk_level="MEDIUM" if out_rate > 50 else "LOW",
                confidence=0.6,
                prerequisites=[],
                tradeoffs=["Risk of stockout if demand increases"],
            ),
            DecisionOption(
                action_summary="Reduce order quantity by 10%",
                projected_impact={"expected_stock_days": "-5 days", "cost_savings": "10%"},
                risk_level="HIGH" if out_rate > 50 else "MEDIUM",
                confidence=0.5,
                prerequisites=["Demand forecast review"],
                tradeoffs=["Potential stockout risk"],
            ),
        ]

        return StructuredDecision(
            decision_type="inventory_restock",
            domain="inventory",
            context_summary=f"Inventory outbound rate: {out_rate:.0f}%. "
                            f"Total stock events: {len(events)}.",
            options=options,
            recommended_option_id=options[0].option_id if out_rate > 50 else options[1].option_id,
            supporting_analysis={
                "outbound_count": len(out_moves),
                "total_events": len(events),
                "out_rate_pct": round(out_rate, 1),
            },
        )

    def suggest_financial_action(self) -> StructuredDecision:
        """Suggest financial action options."""
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        journals = [e for e in events if e.event_type == "journal_entry_posted"]
        reversals = [e for e in events if e.event_type == "journal_entry_reversed"]
        reversal_rate = len(reversals) / max(len(journals), 1)

        options = [
            DecisionOption(
                action_summary="Review journal entry processes",
                projected_impact={"reversal_rate_reduction": "-50%", "accuracy_improvement": "HIGH"},
                risk_level="LOW",
                confidence=0.85,
                prerequisites=["Audit team assignment"],
                tradeoffs=["Time investment for process review"],
            ),
            DecisionOption(
                action_summary="Implement automated journal validation",
                projected_impact={"reversal_rate_reduction": "-80%", "automation_overhead": "MEDIUM"},
                risk_level="MEDIUM",
                confidence=0.7,
                prerequisites=["IT implementation", "Testing cycle"],
                tradeoffs=["Upfront development cost"],
            ),
        ]

        return StructuredDecision(
            decision_type="financial_process_improvement",
            domain="accounting",
            context_summary=f"Journal entries: {len(journals)}, "
                            f"Reversals: {len(reversals)} "
                            f"(rate: {reversal_rate:.1%})",
            options=options,
            recommended_option_id=options[0].option_id if reversal_rate > 0.2 else "",
            supporting_analysis={
                "journal_count": len(journals),
                "reversal_count": len(reversals),
                "reversal_rate": round(reversal_rate, 3),
            },
        )

    def generate_recommendations(self) -> List[Recommendation]:
        """Generate all recommendations from insights."""
        recs = self._reasoning.generate_recommendations()

        try:
            inv_decision = self.suggest_inventory_restock()
            recs.append(Recommendation(
                title="Inventory Restock Options Available",
                description=inv_decision.context_summary,
                decision_type="inventory_restock",
                risk_level=inv_decision.options[0].risk_level if inv_decision.options else "MEDIUM",
                options=[{"action": o.action_summary, "impact": o.projected_impact}
                         for o in inv_decision.options],
                confidence_score=inv_decision.options[0].confidence if inv_decision.options else 0.5,
            ))
        except Exception:
            pass

        try:
            fin_decision = self.suggest_financial_action()
            recs.append(Recommendation(
                title="Financial Process Review Recommended",
                description=fin_decision.context_summary,
                decision_type="financial_process_improvement",
                risk_level=fin_decision.options[0].risk_level if fin_decision.options else "MEDIUM",
                options=[{"action": o.action_summary, "impact": o.projected_impact}
                         for o in fin_decision.options],
                confidence_score=fin_decision.options[0].confidence if fin_decision.options else 0.5,
            ))
        except Exception:
            pass

        return recs
