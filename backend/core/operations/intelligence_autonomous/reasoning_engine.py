"""
Phase 5B.8 — Reasoning Engine.

Multi-domain deterministic inference over Event Store data.
Rule + pattern hybrid reasoning — read-only, no ML, no side effects.

Every insight must reference events, projections, or traces.
"""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence_autonomous.models import (
    Insight, InsightSeverity, IntelligenceReport, Recommendation,
)

logger = logging.getLogger('erp.autonomous.reasoning')

REASONING_ENGINE_VERSION = "1.0.0"

# Known cross-domain inference rules
INFERENCE_RULES = [
    {
        "name": "inventory_depletion_risk",
        "domain": "inventory",
        "trigger_ratio": 0.3,
        "description": "Stock level below 30% of baseline suggests restock needed",
        "severity": InsightSeverity.WARNING,
    },
    {
        "name": "sales_volume_anomaly",
        "domain": "sales_purchase",
        "description": "Unusual sales volume change detected",
        "severity": InsightSeverity.WARNING,
    },
    {
        "name": "accounting_imbalance_risk",
        "domain": "accounting",
        "description": "Journal entries approaching imbalance threshold",
        "severity": InsightSeverity.CRITICAL,
    },
    {
        "name": "hr_attrition_pattern",
        "domain": "hr",
        "description": "Elevated termination events detected",
        "severity": InsightSeverity.WARNING,
    },
]


class ReasoningEngine:
    """Multi-domain deterministic inference engine.

    All insights are derived from Event Store data only.
    No external state, no ML, no hallucination.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def analyze_domain(self, domain: Domain) -> List[Insight]:
        """Run all inference rules for a domain.

        Deterministic — same data produces same insights.
        """
        insights: List[Insight] = []
        events = self._store.get_by_domain(domain)

        if domain == Domain.INVENTORY:
            insights.extend(self._analyze_inventory(events))
        elif domain == Domain.ACCOUNTING:
            insights.extend(self._analyze_accounting(events))
        elif domain == Domain.HR:
            insights.extend(self._analyze_hr(events))
        elif domain == Domain.SALES_PURCHASE:
            insights.extend(self._analyze_sales_purchase(events))

        return insights

    def cross_domain_inference(self) -> List[Insight]:
        """Run inference across domain boundaries."""
        insights: List[Insight] = []

        inv_events = self._store.get_by_domain(Domain.INVENTORY)
        sp_events = self._store.get_by_domain(Domain.SALES_PURCHASE)
        acct_events = self._store.get_by_domain(Domain.ACCOUNTING)

        if inv_events and sp_events:
            inv_count = len(inv_events)
            sp_count = len(sp_events)
            ratio = inv_count / max(sp_count, 1)
            if ratio < 0.5:
                insights.append(Insight(
                    title="Sales-Imbalance Detected",
                    description=f"Low event ratio inventory/sales ({ratio:.2f}). "
                                "High sales volume with low inventory tracking.",
                    domain="cross_domain",
                    severity=InsightSeverity.WARNING,
                    supporting_event_ids=[e.event_id for e in (inv_events + sp_events)[:5]],
                ))

        if acct_events and inv_events:
            matching = self._find_cross_correlation(acct_events, inv_events)
            if len(matching) > 0:
                insights.append(Insight(
                    title="Accounting-Inventory Correlation",
                    description=f"{len(matching)} correlated entries between accounting and inventory events.",
                    domain="cross_domain",
                    severity=InsightSeverity.INFO,
                ))

        return insights

    def _analyze_inventory(self, events: List[Any]) -> List[Insight]:
        insights = []
        if len(events) < 3:
            return insights

        out_movements = [e for e in events if e.event_type == "stock_movement"
                         and e.payload.get("direction") == "out"]
        in_movements = [e for e in events if e.event_type == "stock_movement"
                        and e.payload.get("direction") == "in"]

        if len(in_movements) > 0 and len(out_movements) > len(in_movements) * 2:
            insights.append(Insight(
                title="Inventory Depletion Risk",
                description=f"Outbound movements ({len(out_movements)}) significantly "
                            f"exceed inbound ({len(in_movements)}). Restock recommended.",
                domain="inventory",
                severity=InsightSeverity.WARNING,
                supporting_event_ids=[e.event_id for e in out_movements[:3]],
            ))

        adjustments = [e for e in events if e.event_type == "stock_adjusted"]
        if len(adjustments) >= 3:
            insights.append(Insight(
                title="Frequent Stock Adjustments",
                description=f"{len(adjustments)} adjustments detected. May indicate "
                            "inventory accuracy issues.",
                domain="inventory",
                severity=InsightSeverity.WARNING,
                supporting_event_ids=[e.event_id for e in adjustments[:3]],
            ))

        return insights

    def _analyze_accounting(self, events: List[Any]) -> List[Insight]:
        insights = []
        if len(events) < 2:
            return insights

        journals = [e for e in events if e.event_type == "journal_entry_posted"]
        reversed_journals = [e for e in events if e.event_type == "journal_entry_reversed"]

        if len(reversed_journals) > len(journals) * 0.3 > 0:
            insights.append(Insight(
                title="High Journal Reversal Rate",
                description=f"{len(reversed_journals)} reversals out of {len(journals)} "
                            f"entries ({len(reversed_journals)/max(len(journals),1)*100:.0f}%).",
                domain="accounting",
                severity=InsightSeverity.CRITICAL,
                supporting_event_ids=[e.event_id for e in reversed_journals[:3]],
            ))

        return insights

    def _analyze_hr(self, events: List[Any]) -> List[Insight]:
        insights = []
        if len(events) < 2:
            return insights

        terminations = [e for e in events if e.event_type == "employee_terminated"]
        if len(terminations) >= 2:
            insights.append(Insight(
                title="Elevated Attrition",
                description=f"{len(terminations)} termination events detected.",
                domain="hr",
                severity=InsightSeverity.WARNING,
                supporting_event_ids=[e.event_id for e in terminations],
            ))

        return insights

    def _analyze_sales_purchase(self, events: List[Any]) -> List[Insight]:
        insights = []
        if len(events) < 2:
            return insights

        cancellations = [e for e in events if e.event_type == "order_cancelled"]
        if len(cancellations) >= 2:
            insights.append(Insight(
                title="Elevated Order Cancellation Rate",
                description=f"{len(cancellations)} cancellations detected out of {len(events)} orders.",
                domain="sales_purchase",
                severity=InsightSeverity.WARNING,
                supporting_event_ids=[e.event_id for e in cancellations[:3]],
            ))

        return insights

    def _find_cross_correlation(self, events_a: List[Any], events_b: List[Any]) -> List[Tuple[str, str]]:
        matching = []
        for ea in events_a[:20]:
            for eb in events_b[:20]:
                ca = ea.metadata.get("correlation_id", "")
                cb = eb.metadata.get("correlation_id", "")
                if ca and ca == cb:
                    matching.append((ea.event_id, eb.event_id))
        return matching

    def generate_recommendations(self, domain: Domain = None) -> List[Recommendation]:
        """Generate non-executable recommendations."""
        recs: List[Recommendation] = []

        domains = [domain] if domain else list(Domain)
        for d in domains:
            insights = self.analyze_domain(d)
            for ins in insights:
                if ins.severity == InsightSeverity.CRITICAL:
                    recs.append(Recommendation(
                        title=f"Review: {ins.title}",
                        description=ins.description,
                        decision_type=f"{ins.domain}_review",
                        risk_level="HIGH",
                        supporting_event_ids=ins.supporting_event_ids,
                        confidence_score=0.75,
                    ))

        return recs
