"""
Phase 5B.8 — Risk Engine.

Cross-domain risk scoring (0–100):
- Financial risk
- Operational risk
- Supply chain risk
- HR risk
- Compliance risk
- Inventory risk

All scores are deterministic from Event Store data.
"""
import logging
from typing import Any, Dict, List, Optional

from core.operations.truth.models import Domain
from core.operations.truth.event_store import EventStore, get_event_store
from core.operations.intelligence_autonomous.models import (
    RiskScore, RiskCategory,
)

logger = logging.getLogger('erp.autonomous.risk')

RISK_ENGINE_VERSION = "1.0.0"


class RiskEngine:
    """Cross-domain deterministic risk scoring.

    All scores are 0–100 derived from Event Store patterns.
    Higher = more risk.
    """

    def __init__(self, store: Optional[EventStore] = None):
        self._store = store or get_event_store()

    def score_financial_risk(self) -> RiskScore:
        """Score financial risk based on accounting events."""
        events = self._store.get_by_domain(Domain.ACCOUNTING)
        score = 10.0
        factors: List[str] = []

        if not events:
            return RiskScore(category=RiskCategory.FINANCIAL, score=0,
                             confidence=1.0, contributing_factors=["No accounting data"])

        journals = [e for e in events if e.event_type == "journal_entry_posted"]
        reversals = [e for e in events if e.event_type == "journal_entry_reversed"]
        total = len(events)

        if total < 5:
            score += 15
            factors.append("Low event volume — limited visibility")

        reversal_rate = len(reversals) / max(len(journals), 1)
        if reversal_rate > 0.3:
            score += 25
            factors.append(f"High reversal rate ({reversal_rate:.0%})")
        elif reversal_rate > 0.1:
            score += 10
            factors.append(f"Moderate reversal rate ({reversal_rate:.0%})")

        if len(journals) > 0:
            unbalanced = sum(
                1 for j in journals
                if abs(sum(l.get("debit", 0) for l in j.payload.get("entries", []))
                       - sum(l.get("credit", 0) for l in j.payload.get("entries", []))) > 0.001
            )
            if unbalanced > 0:
                score += unbalanced * 5
                factors.append(f"{unbalanced} potentially unbalanced entries")

        return RiskScore(
            category=RiskCategory.FINANCIAL,
            score=min(100, round(score, 1)),
            confidence=0.8 if total >= 10 else 0.5,
            contributing_factors=factors,
            trend="INCREASING" if reversal_rate > 0.2 else "STABLE",
        )

    def score_operational_risk(self) -> RiskScore:
        """Score operational risk."""
        events = self._store.get_all()
        score = 5.0
        factors: List[str] = []

        if not events:
            return RiskScore(category=RiskCategory.OPERATIONAL, score=0,
                             confidence=1.0, contributing_factors=["No system activity"])

        timestamp_issues = 0
        for i in range(len(events) - 1):
            if events[i].timestamp > events[i + 1].timestamp:
                timestamp_issues += 1

        if timestamp_issues > 0:
            score += min(timestamp_issues * 5, 30)
            factors.append(f"{timestamp_issues} timestamp anomalies detected")

        total = len(events)
        if total < 10:
            score += 20
            factors.append("Low system activity — potential issue")

        return RiskScore(
            category=RiskCategory.OPERATIONAL,
            score=min(100, round(score, 1)),
            confidence=0.7,
            contributing_factors=factors,
            trend="STABLE" if timestamp_issues == 0 else "INCREASING",
        )

    def score_inventory_risk(self) -> RiskScore:
        """Score inventory/supply chain risk."""
        events = self._store.get_by_domain(Domain.INVENTORY)
        score = 5.0
        factors: List[str] = []

        if not events:
            return RiskScore(category=RiskCategory.INVENTORY, score=0,
                             confidence=1.0, contributing_factors=["No inventory data"])

        out_moves = [e for e in events if e.event_type == "stock_movement"
                     and e.payload.get("direction") == "out"]
        in_moves = [e for e in events if e.event_type == "stock_movement"
                    and e.payload.get("direction") == "in"]
        adjustments = [e for e in events if e.event_type == "stock_adjusted"]

        if len(in_moves) > 0 and len(out_moves) > len(in_moves) * 2:
            score += 25
            factors.append(f"Outbound exceeds inbound by {len(out_moves)/max(len(in_moves),1):.1f}x")

        if len(adjustments) >= 3:
            score += 15
            factors.append(f"{len(adjustments)} stock adjustments indicate accuracy issues")

        if len(events) < 5:
            score += 10
            factors.append("Limited inventory event history")

        return RiskScore(
            category=RiskCategory.INVENTORY,
            score=min(100, round(score, 1)),
            confidence=0.75,
            contributing_factors=factors,
            trend="INCREASING" if len(out_moves) > len(in_moves) else "STABLE",
        )

    def score_hr_risk(self) -> RiskScore:
        """Score HR risk."""
        events = self._store.get_by_domain(Domain.HR)
        score = 5.0
        factors: List[str] = []

        if not events:
            return RiskScore(category=RiskCategory.HR, score=0,
                             confidence=1.0, contributing_factors=["No HR data"])

        terminations = [e for e in events if e.event_type == "employee_terminated"]
        if len(terminations) >= 2:
            score += min(len(terminations) * 10, 40)
            factors.append(f"{len(terminations)} terminations detected")

        if len(events) < 5:
            score += 10
            factors.append("Limited HR activity")

        return RiskScore(
            category=RiskCategory.HR,
            score=min(100, round(score, 1)),
            confidence=0.7,
            contributing_factors=factors,
            trend="INCREASING" if len(terminations) >= 2 else "STABLE",
        )

    def score_all(self) -> List[RiskScore]:
        """Score all risk categories."""
        return [
            self.score_financial_risk(),
            self.score_operational_risk(),
            self.score_inventory_risk(),
            self.score_hr_risk(),
        ]

    def get_overall_risk(self) -> float:
        """Get weighted overall risk score (0–100)."""
        scores = self.score_all()
        if not scores:
            return 0.0
        weighted = sum(s.score * s.confidence for s in scores)
        total_weight = sum(s.confidence for s in scores)
        return round(weighted / max(total_weight, 0.01), 1)
